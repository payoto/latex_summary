"""
Parses latex documents for %!(SU[M]+A[R]+Y) and %!TODO and sections to build
a summary.
"""


import os
import re
import sys


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
    r"paragraph",
    r"[sub]*section",
    r"appendix",
    r"[a-z]*matter",
    r"pagenumbering",
]

capture_directive = r"%! *"
capture_sentence = r" *:* *([^\.!\?]*[\.!\?]*)"
phrase_record_triggers = [
    r"%! *TO+DO+ *: *([^\.!\?]*[\.!\?]*)",
    r"%! *SU[M]+A[R]+Y *:* *([^\.!\?]*[\.!\?]*)",
    capture_directive + r"TO+DO+ *:*" + capture_sentence,
    capture_directive + r"SU[M]+A[R]+Y" + capture_sentence,
]

section_spacing = r"\vspace{-36pt}\hspace{11pt}"

def build_regex_list(patterns):
    return [re.compile(pattern) for pattern in patterns]


def build_file_parse_re(commands):

    file_capture = r"[\{\,\;] *([^\(\)\{\}\|\,\;]*) *[\}\,\;]"
    # file_capture = r"\{[^\{\}]*\}"
    patterns = [r"^[^%]*\\" + c + file_capture for c in commands]

    return build_regex_list(patterns)


def build_summary_parse_re(commands, patterns):

    re_type = [dict({"phrase": True}) for _ in patterns]
    re_type[0]["todo"] = True
    re_type.extend([dict({"line": True}) for _ in commands])
    re_type[len(patterns)] = {"title": True}
    re_type[len(patterns) + 1] = {"title": False}
    patterns.extend(
        [r"^[^%]*(\\" + c + ".*)" for c in commands]
    )
    return build_regex_list(patterns), re_type


file_parse_re = build_file_parse_re(file_parse_triggers)
summary_parse_re, summary_parse_re_types = build_summary_parse_re(
    line_record_triggers, phrase_record_triggers)


def close_itemlist(records, start_item, end_item, item_str):
    # Find the most recent record not starting with a %
    prev_rec = -1
    flag = True
    while flag:
        if -prev_rec > len(records):
            return
        if re.compile("\\s*%").match(records[prev_rec]):
            prev_rec += -1
        else:
            flag = False

    if records[prev_rec] == start_item:
        records.pop(prev_rec)
        # needed to make sure the pdf breaks correctly
        records.append(section_spacing)
    elif "line" not in detect_record(records[prev_rec])[0]:
        records.append(end_item)


def record_is(rec_str, record_type):
    return rec_str in record_type and record_type[rec_str]


def record_isnot(rec_str, record_type):
    return rec_str not in record_type or not record_type[rec_str]


def previous_record_is(rec_str, prev_record, record_type):
    return record_is(rec_str, prev_record) and\
        record_is("multiline", record_type)


def parse_file(
    file_in,
    records={'title': [], 'todos': [], 'summary': []},
    n_stacks=0,
    n_section=0,
):
    records['summary'].append("% Start file : " + file_in)
    start_item = "    \\begin{itemize}[noitemsep]"
    end_item = "    \\end{itemize}"
    item_str = "        \\item "
    todo_format = "{{\color{{red}}{0}}}"
    label_format = "\label{{autosec:{0}}}"
    ref_format = "\\ref{{autosec:{0}}}"
    current_label = label_format.format(n_section)
    current_ref = ref_format.format(n_section)

    if n_stacks == 0:
        records['todos'].append(r"\section{List of To-dos}")
        records['todos'].append(start_item)

    with open(file_in, 'r') as f:
        for line_num, line in enumerate(f):

            line_info = "        % " + file_in + ":" + str(line_num + 1)
            record_type, record = detect_record(line)

            if record_is("line", record_type):
                close_itemlist(records['summary'],
                               start_item, end_item, item_str)
            if "todo" in record_type:
                record = todo_format.format(record)
            if record_is("item", record_type):
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

            if "todo" in record_type:
                records['todos'].append(record +
                                        " (section~{0})".format(current_ref))
                records['todos'].append(line_info)

            if record_is("line", record_type):
                n_section += 1
                current_label = label_format.format(n_section)
                current_ref = ref_format.format(n_section)
                records['summary'].append(current_label)
                records['summary'].append(start_item)

            next_file = detect_file(line, file_in)
            if next_file:
                print("Next file : " + next_file)
                _, n_section = parse_file(next_file, records, n_stacks + 1,
                                          n_section)

    if n_stacks == 0:
        close_itemlist(records['summary'], start_item, end_item, item_str)
        close_itemlist(records['todos'], start_item, end_item, item_str)

    records['summary'].append("% End file : " + file_in)
    return records, n_section


def detect_file(line, current_file):
    next_file = None

    for file_re in file_parse_re:
        m = file_re.search(line)
        if m:
            break
    if m:
        next_file = m.group(1) + ".tex"

        if not os.path.exists(next_file):
            next_file_test = next_file
            base_path = current_file
            while not os.path.exists(next_file_test):
                base_path, _ = os.path.split(base_path)
                next_file_test = os.path.join(base_path, next_file)
            if os.path.exists(next_file_test):
                next_file = next_file_test
            else:
                raise IOError("File could not be found.")

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
    records, _ = parse_file(file_name)
    write_records(records, file_name)
