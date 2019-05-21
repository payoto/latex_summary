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
    r"chapter",
    r"paragraph",
    r"[sub]*section",
    r"appendix",
    r"[a-z]*matter",
    r"pagenumbering",
]

phrase_record_triggers = [
    r"%! *TO+DO+ *: *([^\.!\?]*[\.!\?]*)",
    r"%! *SU[M]+A[R]+Y *:* *([^\.!\?]*[\.!\?]*)",
]


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
        if records[prev_rec][0] == "%":
            prev_rec += -1
        else:
            flag = False

    if records[prev_rec] == start_item:
        records.pop(prev_rec)
        records.append("")  # needed to make sure the pdf breaks correctly
    elif records[prev_rec].find(item_str) >= 0:
        records.append(end_item)


def parse_file(
    file_in,
    records={'todos': [], 'summary': []},
    n_stacks=0,
):
    records['summary'].append("% Start file : " + file_in)
    start_item = "    \\begin{itemize}[noitemsep]"
    end_item = "    \\end{itemize}"
    item_str = "        \\item "
    todo_format = "{{\color{{red}}{0}}}"

    if n_stacks == 0:
        records['todos'].append(r"\section{List of To-dos}")
        records['todos'].append(start_item)

    with open(file_in, 'r') as f:
        for line_num, line in enumerate(f):

            line_info = "  % " + file_in + ":" + str(line_num + 1)
            record_type, record = detect_record(line)

            if "line" in record_type:
                close_itemlist(records['summary'],
                               start_item, end_item, item_str)
            if "todo" in record_type:
                record = todo_format.format(record)
            if "phrase" in record_type:
                record = item_str + record

            if record_type:
                record += line_info
                records['summary'].append(record)
            if "todo" in record_type:
                records['todos'].append(record)
            if "line" in record_type:
                records['summary'].append(start_item)

            next_file = detect_file(line, file_in)
            if next_file:
                print("Next file : " + next_file)
                parse_file(next_file, records, n_stacks + 1)

    if n_stacks == 0:
        close_itemlist(records['summary'], start_item, end_item, item_str)
        close_itemlist(records['todos'], start_item, end_item, item_str)

    records['summary'].append("% End file : " + file_in)
    return records


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
    records = parse_file(file_name)
    write_records(records, file_name)
