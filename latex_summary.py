"""
Parses latex documents for %!(SU[M]+A[R]+Y) and %!TODO and sections to build
a summary.
"""


import os
import re
import sys
import pdb

file_parse_triggers = [
    r"input",
    r"include",
    r"import",
    r"subfile",
]

line_record_triggers = [
    r"title",
    r"maketitle",
    r"chapter",
    r"[sub]*section",
    r"frontmatter",
    r"paragraph",
    r"appendix",
    r"[a-z]*matter",
    r"pagenumbering",
]
file_capture = r"[\{\,\;] *([^\(\)\{\}\|\,\;]*) *[\}\,\;](.*)"

capture_directive = r"%! *"
capture_sentence = r" *:* *([^\.!\?]*[\.!\?]*)"
phrase_record_triggers = [
    r"TO+DO+",
    r"SU[M]+A[R]+Y",
    r"MULT[ILINE]*",
    r"MUD+[LED]*",
    r"PLAN",
]
re_comment = re.compile("\\s*%")


def command_name_to_re_string(command):
    return r"^[^%]*(\\" + command + ".*)"


def pattern_name_to_re_string(pattern):
    return capture_directive + pattern + capture_sentence


"""
LaTeX output formatting module attributes.
"""
section_spacing = r"\vspace{-36pt}\hspace{11pt}"
start_item = "    \\begin{itemize}[noitemsep]"
start_enum = "    \\begin{enumerate}[noitemsep]"
end_item = "    \\end{itemize}"
end_enum = "    \\end{enumerate}"
item_str = "        \\item "
color_format = "{{\color{{{0}}}{1}}}"
label_format = "\label{{autosec:{0}}}"
ref_format = "\\ref{{autosec:{0}}}"


def build_regex_list(patterns):
    return [re.compile(pattern) for pattern in patterns]


def build_file_parse_re(commands):

    patterns = [r"^[^%]*\\" + c + file_capture for c in commands]

    return build_regex_list(patterns)


default_pattern_type = {"item": True}
default_command_type = {"line": True}


def build_summary_parse_re(commands, patterns):

    # Set all patterns type as "item" -> will trigger a new item
    re_type = [dict({"item": True}) for _ in patterns]
    re_type[0]["todo"] = True
    re_type[0]["color"] = "red"
    re_type[0]["count"] = "todo"
    re_type[1]["count"] = "summary"
    re_type[2]["multiline"] = True
    re_type[3]["muddle"] = True
    re_type[3]["color"] = "OliveGreen"
    re_type[3]["count"] = "muddle"
    re_type[4]["color"] = "blue"
    re_type[4]["count"] = "plan"
    del re_type[2]["item"]

    re_type.extend([dict({"line": True}) for _ in commands])
    re_type[len(patterns)] = {"title": True}  # \title{}
    re_type[len(patterns) + 1] = {"title": False}  # \maketitle
    re_type[len(patterns) + 2]["section"] = True  # \chapter{}
    re_type[len(patterns) + 2]["count"] = "section"  # \chapter{}
    re_type[len(patterns) + 3]["section"] = True  # \[sub]*section{}
    re_type[len(patterns) + 3]["count"] = "section"  # \[sub]*section{}
    re_type[len(patterns) + 4] = {"title": False}  # \frontmatter

    re_strings = [pattern_name_to_re_string(p) for p in patterns]
    re_strings.extend([command_name_to_re_string(c) for c in commands])

    return build_regex_list(re_strings), re_type


file_parse_re = build_file_parse_re(file_parse_triggers)
summary_parse_re, summary_parse_re_types = build_summary_parse_re(
    line_record_triggers, phrase_record_triggers)


def parse_new_pattern(pattern, regex_type=default_pattern_type):
    summary_parse_re.append(re.compile(pattern_name_to_re_string(pattern)))
    summary_parse_re_types.append(dict(regex_type))


def parse_new_command(command, regex_type=default_command_type):
    summary_parse_re.append(re.compile(command_name_to_re_string(command)))
    summary_parse_re_types.append(dict(regex_type))


def open_itemlist(records, start_item, end_item, item_str):
    # runs if this is an item
    # roll back until either:
    # begin itemize is encountered
    # end itemize
    # an item
    # or a section
    #
    # Skip comment lines and lines with non item text

    prev_rec = -1
    flag = True
    while flag:
        if -prev_rec > len(records):
            records.append(start_item)
            flag = False
        elif re_comment.match(records[prev_rec]):
            prev_rec += -1
        elif (records[prev_rec] == start_item
              or item_str in records[prev_rec]):
            flag = False
        elif ("line" in detect_record(records[prev_rec])[0]
              or records[prev_rec] == end_item):
            records.append(start_item)
            flag = False
        else:
            prev_rec -= 1
    pass


def close_itemlist(records, start_item, end_item, item_str):
    prev_rec = -1
    flag = True
    flag_text = False
    while flag:
        if -prev_rec > len(records):
            flag = False
        elif re_comment.match(records[prev_rec]) or\
                r"\label" == records[prev_rec][:len(r"\label")]:
            prev_rec += -1
        elif item_str in records[prev_rec]:
            records.append(end_item)
            flag = False
            flag_text = True
        elif records[prev_rec] == start_item:
            records.pop(prev_rec)
            if record_is("section", detect_record(records[prev_rec])[0]) \
                    and not flag_text:
                records.append(section_spacing)
            flag = False
        elif "line" in detect_record(records[prev_rec])[0]:
            if record_is("section", detect_record(records[prev_rec])[0]) \
                    and not flag_text:
                records.append(section_spacing)
            flag = False
        else:
            flag_text = True
            prev_rec -= 1


parser_summary_str = r"\item \textbf{{{0}s}}: {1} were detected."


def summarise_parser_activity(records, counters):

    records.append(r"\section{Parser results}")
    records.append(start_item)
    for count in counters:
        records.append(parser_summary_str.format(count, counters[count]))

    records.append(end_item)


def parse_file(file_in,
               records={'title': [], 'parser': [], 'todos': [], 'summary': []},
               n_stacks=0,
               counters={"section": 0},
               ):

    records['summary'].append("% Start file : " + file_in)
    prev_record = {}
    if n_stacks == 0:
        records['todos'].append(r"\section{List of To-dos}")
        records['todos'].append(start_enum)

    with open(file_in, 'r') as f:
        for line_num, line in enumerate(f):

            line_info = "        % " + file_in + ":" + str(line_num + 1)

            prev_record, counters = process_record(records,
                                                   line,
                                                   line_info,
                                                   prev_record,
                                                   counters)

            next_file = detect_file(line, file_in)
            if next_file:
                print("Next file : " + next_file)
                _, counters = parse_file(next_file, records, n_stacks + 1,
                                         counters)

    if n_stacks == 0:
        close_itemlist(records['summary'], start_item, end_item, item_str)
        close_itemlist(records['todos'], start_enum, end_enum, item_str)
        summarise_parser_activity(records['parser'], counters)

    records['summary'].append("% End file : " + file_in)
    return records, counters


def detect_file(line, current_file):
    next_file = None

    for index_re, file_re in enumerate(file_parse_re):
        m = file_re.search(line)
        if m:
            break
    if m:
        next_file = ""
        file_capture_re = re.compile(file_capture)
        while m:
            next_file += m.group(1).strip()
            m = file_capture_re.search(m.group(2))

        if not os.path.splitext(next_file)[1]:
            next_file += ".tex"

        if not os.path.exists(next_file):
            next_file_test = next_file
            base_path = current_file
            while not os.path.exists(next_file_test) and base_path:
                base_path, _ = os.path.split(base_path)
                next_file_test = os.path.join(base_path, next_file)
            if os.path.exists(next_file_test):
                next_file = next_file_test
            else:
                raise IOError(
                    "File input command detected but the file could not"
                    " be found. \n line : '{0}'\n\n If the latex document "
                    "compiles with this command report this error as an issue"
                    " on github.".format(line))

            pass

    return next_file


def detect_record(line):
    record_type = {}
    record = line
    for pat_re, pat_type in zip(summary_parse_re, summary_parse_re_types):
        m = pat_re.search(line)
        if m:
            break
    if m:
        record = m.group(1)
        record_type = pat_type

    return record_type, record


def record_is(rec_str, record_type):
    return rec_str in record_type and record_type[rec_str]


def record_isnot(rec_str, record_type):
    return rec_str not in record_type or not record_type[rec_str]


def previous_record_is(rec_str, prev_record, record_type):
    return record_is(rec_str, prev_record) and\
        record_is("multiline", record_type)


def records_are(rec_str, prev_record, curr_record):
    return record_is(rec_str, curr_record) \
        or previous_record_is(rec_str, prev_record, curr_record)


def records_are_value(rec_str, prev_record, curr_record):
    val = None
    logical = records_are(rec_str, prev_record, curr_record)
    if logical and record_is(rec_str, curr_record):
        val = curr_record[rec_str]
    elif logical:
        val = prev_record[rec_str]

    return logical, val


def process_record(records, line, line_info, prev_record, nums,):

    record_type, record = detect_record(line)

    if record_is("line", record_type):
        close_itemlist(records['summary'],
                       start_item, end_item, item_str)

    is_color, color = records_are_value("color", prev_record, record_type)
    if is_color:
        record = color_format.format(color, record)

    if record_is("item", record_type):
        open_itemlist(records['summary'], start_item, end_item, item_str)
        record = item_str + record
    if "title" in record_type:
        if record_type["title"]:
            record = re.sub(r"\\title\s*\{",
                            r"\\title{Summary of : ", record)
        records["title"].append(record)
        record_type = {}  # Stop it being recorded in the main text

    if record_type and record_isnot("newline", record_type):
        records['summary'].append(record)
        records['summary'].append(line_info)

    if records_are("todo", prev_record, record_type):
        if record_is("todo", record_type):
            records['todos'].append(
                record
                + " (section~{0})".format(ref_format.format(nums["section"])))
        else:
            records['todos'].append(record)

        records['todos'].append(line_info)

    if record_is("line", record_type):
        records['summary'].append(label_format.format(nums["section"]))

    if record_isnot("multiline", record_type):
        prev_record = record_type
    if record_is("count", record_type):
        try:
            nums[record_type["count"]] += 1
        except Exception as e:
            nums[record_type["count"]] = 1

    return prev_record, nums


def write_records(records, file_name, name_change='_auto_summary'):

    if not name_change:
        name_change = '_auto_summary'

    file, ext = os.path.splitext(file_name)
    new_file = file + "_auto_summary" + ext
    with open(new_file, 'w') as f:
        for rec in records:
            f.writelines("%s\n" % l for l in records[rec])
            f.write("\n")


if __name__ == "__main__":
    file_name = sys.argv[1]
    records, counters = parse_file(file_name)
    write_records(records, file_name)
