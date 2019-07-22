"""
Parses latex documents for %!(SU[M]+A[R]+Y) and %!TODO and sections to build
a summary.
"""


import os
import re
import sys
from collections import OrderedDict

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


default_pattern_type = {"item": True}
default_command_type = {"line": True}

phrase_record_triggers = [
    r"TO+DO+",
    r"SU[M]+A[R]+Y",
    r"MULT[ILINE]*",
    r"MUD+[LED]*",
    r"PLAN",
    r"REP[EA]*[TION]*",
    r"QUESTIONS*",
]

re_comment = re.compile("\\s*%")

recognise_directive = r"%! *"
end_of_keyword = r" *:* *"
capture_sentence = r"([^\.!\?]*[\.!\?]*)"

modifier_fullline = r"EOL[ _]*"
modifier_noitem = r"NI[ _]*"
modifier_doneitem = r"DONE[ _]*"
capture_restofline = r"(.*)"

input_str = '__INPUT__'

default_specifier = {
    'recognise': recognise_directive,  # The pattern to recognise at the start
    'pattern_prefix': '',  # Allows a change of behaviour with a prefix
    'precapture': end_of_keyword,  # After the pattern, to be discarded
    'capture': capture_sentence,  # What is read and copied into the summary
    'typemodif': {},  # Dictionary modification from the default type
    # The order in which fields are set
    're_fields': ['recognise', 'pattern_prefix', input_str,
                  'precapture', 'capture']
}
partial_specifiers = {
    'full_line': {
        'pattern_prefix': modifier_fullline,
        'capture': capture_restofline,
    },
    'not_item': {
        'pattern_prefix': modifier_noitem,
        'typemodif': {"item": False},
    },
    'item_done': {
        'pattern_prefix': modifier_doneitem,
        'typemodif': {"color": "Gray", "done": True},
    },
}

# Global controlling the change of name imposed to the counter when using
# "done"
done_marker = "_done"


def generate_capture_specifiers(default_specifier, partial_specifiers):
    capture_specifiers = OrderedDict(
        [('default', dict(default_specifier))],
    )

    for new_spec in partial_specifiers:
        if input_str in partial_specifiers[new_spec]:
            raise KeyError(
                "Key '{0}' is reserved and cannot be in "
                "partial_specifiers['{1}']".format(input_str, new_spec))
        capture_specifiers[new_spec] = {
            **default_specifier, **partial_specifiers[new_spec]}

    return capture_specifiers


capture_specifiers = generate_capture_specifiers(
    default_specifier, partial_specifiers)


def command_name_to_re_string(command):
    return r"^[^%]*(\\" + command + ".*)"


def pattern_name_to_re_string(pattern,
                              capture_specifier=capture_specifiers['default']):

    specifier = dict(capture_specifier)
    specifier[input_str] = pattern
    re_str = ''

    for field in specifier['re_fields']:
        re_str += specifier[field]
    return re_str


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


def build_summary_parse_re(commands, patterns):

    # Set all patterns type as "item" -> will trigger a new item
    cmd_offset = 0
    pat_offset = len(commands)
    pat_range = range(pat_offset, pat_offset + len(patterns))
    re_type = []
    re_strings = []

    re_type.extend([dict(default_command_type) for _ in commands])
    re_type.extend([dict(default_pattern_type) for _ in patterns])

    re_type[pat_offset + 0]["todo"] = True
    re_type[pat_offset + 0]["color"] = "red"
    re_type[pat_offset + 0]["count"] = "todo"
    re_type[pat_offset + 1]["count"] = "summary"
    re_type[pat_offset + 2]["multiline"] = True
    re_type[pat_offset + 2]["item"] = False
    re_type[pat_offset + 3]["muddle"] = True
    re_type[pat_offset + 3]["color"] = "OliveGreen"
    re_type[pat_offset + 3]["count"] = "muddle"
    re_type[pat_offset + 4]["color"] = "blue"
    re_type[pat_offset + 4]["count"] = "plan"
    re_type[pat_offset + 5]["color"] = "DarkOrchid"
    re_type[pat_offset + 5]["count"] = "repetition"
    re_type[pat_offset + 6]["color"] = "ForestGreen"
    re_type[pat_offset + 6]["count"] = "question"
    re_type[pat_offset + 6]["todo"] = True

    re_type[cmd_offset + 0] = {"title": True}  # \title{}
    re_type[cmd_offset + 1] = {"title": False}  # \maketitle
    re_type[cmd_offset + 2]["section"] = True  # \chapter{}
    re_type[cmd_offset + 2]["count"] = "section"  # \chapter{}
    re_type[cmd_offset + 3]["section"] = True  # \[sub]*section{}
    re_type[cmd_offset + 3]["count"] = "section"  # \[sub]*section{}
    re_type[cmd_offset + 4] = {"title": False}  # \frontmatter

    re_strings.extend([command_name_to_re_string(c) for c in commands])

    for spec in capture_specifiers:
        re_strings.extend([
            pattern_name_to_re_string(p, capture_specifiers[spec])
            for p in patterns])
        if spec != 'default':
            modifiers = capture_specifiers[spec]['typemodif']
            for i in pat_range:
                re_type.append(dict(re_type[i]))
                for modif in modifiers:
                    re_type[-1][modif] = modifiers[modif]

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
parser_summary_done_str = r"\item \textbf{{{0}s}}: {1}({2}) were detected"\
    + " (completed)."


def summarise_parser_activity(records, counters):

    records.append(r"\section{Parser results}")
    records.append(start_item)
    for count in counters:
        if ((done_marker not in count
                and (count + done_marker) not in counters)):
            records.append(parser_summary_str.format(count, counters[count]))
        elif (count[-len(done_marker):] == done_marker
                and count[:-len(done_marker)] not in counters):
            records.append(parser_summary_done_str.format(
                count[:-len(done_marker)],
                0,
                counters[count]))
        elif (count + done_marker) in counters:
            records.append(parser_summary_done_str.format(
                count,
                counters[count],
                counters[count + done_marker]))

    records.append(end_item)


def parse_file(
    file_in,
    records=OrderedDict(
        [('title', []), ('parser', []), ('todos', []), ('summary', [])],
    ),
    n_stacks=0,
    counters=OrderedDict([("section", 0)]),
):

    records['summary'].append("% Start file : " + file_in)
    prev_record = {}
    if n_stacks == 0:
        records['todos'].append(r"\section{List of To-dos and questions}")
        records['todos'].append(start_enum)

    with open(file_in, 'r') as f:
        for line_num, lines in enumerate(f):
            line = lines.splitlines()[0]
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
        todo_record = record
        if not record_is("item", record_type) \
                and not record_is("multiline", record_type):
            todo_record = item_str + record

        if record_is("todo", record_type):
            records['todos'].append(
                todo_record
                + " (section~{0})".format(ref_format.format(nums["section"])))
        else:
            records['todos'].append(todo_record)

        records['todos'].append(line_info)

    if record_is("line", record_type):
        records['summary'].append(label_format.format(nums["section"]))

    if record_isnot("multiline", record_type):
        prev_record = record_type
    if record_is("count", record_type):
        add_to_count_name = ""
        if record_is("done", record_type):
            add_to_count_name = done_marker
        try:
            nums[record_type["count"] + add_to_count_name] += 1
        except Exception as e:
            nums[record_type["count"] + add_to_count_name] = 1

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
