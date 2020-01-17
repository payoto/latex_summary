"""
Parses latex documents for %!(SU[M]+A[R]+Y) and %!TODO and sections to build
a summary.
"""


import os
import re
import sys
import ast
from collections import OrderedDict


file_parse_triggers = [
    r"input",
    r"include",
    r"import",
    r"subfile",
]

file_parsing_modifiers = {trigger: None for trigger in file_parse_triggers}


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
    r"SUPERVISOR_*[TOM]*",
    r"BADREF[ERENCE]*",
    r"OPT[IONAL]*_*TO+DO+",
    r"IDEA",
    r"CUSTOM_TRIG+ER_LINE",
    r"CUSTOM_TRIG+ER_PHRASE",
    r"CUSTOM_TRIG+ER_FILE",
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
    'full_line_done': {
        'pattern_prefix': ("(?:" + modifier_fullline + modifier_doneitem + "|"
                           + modifier_doneitem + modifier_fullline + ")"),
        'capture': capture_restofline,
        'typemodif': {"color": "Gray", "done": True},
    },
}

# Global controlling the change of name imposed to the counter when using
# "done", is also printed in the legend is used in a string comparison
done_marker = " (completed)"
default_name_change = '_auto_summary'


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
    return r"^[\b]*(\\" + command + ".*)"


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

    patterns = [r"^[\b]*\\" + c + file_capture for c in commands]
    temp_file_parse_re = []

    for command, regexp in zip(commands, build_regex_list(patterns)):
        temp_file_parse_re.append({
            "pattern": command,
            "regexp": regexp,
        })

    return temp_file_parse_re


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
    re_type[pat_offset + 0]["legend"] = "An item that needs doing."

    re_type[pat_offset + 1]["count"] = "summary"
    re_type[pat_offset + 1]["legend"] = "Summary of written a paragraph."

    re_type[pat_offset + 2]["multiline"] = True
    re_type[pat_offset + 2]["item"] = False

    re_type[pat_offset + 3]["muddle"] = True
    re_type[pat_offset + 3]["color"] = "OliveGreen"
    re_type[pat_offset + 3]["count"] = "muddle"
    re_type[pat_offset + 3]["legend"] = "A paragraph where the point is" +\
        " not clear."

    re_type[pat_offset + 4]["color"] = "blue"
    re_type[pat_offset + 4]["count"] = "plan"
    re_type[pat_offset + 4]["legend"] = "planned paragraph or idea."

    re_type[pat_offset + 5]["color"] = "DarkOrchid"
    re_type[pat_offset + 5]["count"] = "repetition"
    re_type[pat_offset + 5]["legend"] = "Paragraph is repeated."

    re_type[pat_offset + 6]["color"] = "ForestGreen"
    re_type[pat_offset + 6]["count"] = "question"
    re_type[pat_offset + 6]["todo"] = True
    re_type[pat_offset + 6]["legend"] = "question to ask."

    re_type[pat_offset + 7]["color"] = "WildStrawberry"
    re_type[pat_offset + 7]["count"] = "supervisor(Tom)"
    re_type[pat_offset + 7]["prefix"] = "Tom: "
    re_type[pat_offset + 7]["legend"] = "Comment from TOM."

    re_type[pat_offset + 8]["color"] = "Periwinkle"
    re_type[pat_offset + 8]["count"] = "bad reference"
    re_type[pat_offset + 8]["prefix"] = "ref: "
    re_type[pat_offset + 8]["legend"] = "bad or missing reference."

    re_type[pat_offset + 9] = dict(re_type[pat_offset + 0])  # = todo
    re_type[pat_offset + 9]["color"] = "Orange"
    re_type[pat_offset + 9]["count"] = "optional todo"
    re_type[pat_offset + 9]["legend"] = "An item that it would be nice to do."
    re_type[pat_offset + 9]["suffix"] = " (optional todo)"

    re_type[pat_offset + 10] = dict(re_type[pat_offset + 0])  # = todo
    re_type[pat_offset + 10]["color"] = "teal"
    re_type[pat_offset + 10]["count"] = "idea"
    re_type[pat_offset + 10]["legend"] = "An idea that should be explored."
    re_type[pat_offset + 10]["prefix"] = " Idea: "

    # Modify the list of regexps to add functionality
    re_type[pat_offset + 11]["modifier"] = "line_record_triggers"
    re_type[pat_offset + 12]["modifier"] = "phrase_record_triggers"
    re_type[pat_offset + 13]["modifier"] = "file_parse_triggers"

    re_type[cmd_offset + 0] = {"title": True}  # \title{}
    re_type[cmd_offset + 1] = {"title": False}  # \maketitle
    re_type[cmd_offset + 2]["section"] = True  # \chapter{}
    re_type[cmd_offset + 2]["count"] = "section"  # \chapter{}
    re_type[cmd_offset + 3]["section"] = True  # \[sub]*section{}
    re_type[cmd_offset + 3]["count"] = "section"  # \[sub]*section{}
    re_type[cmd_offset + 4] = {"title": False}  # \frontmatter

    for d in re_type:
        d["active"] = True

    re_strings.extend([command_name_to_re_string(c) for c in commands])

    re_strings, re_type = apply_capture_specifiers(
        patterns, re_type, pat_range,
        re_strings, capture_specifiers)

    return build_regex_list(re_strings), re_type, \
        {"cmd": cmd_offset, "pattern": pat_offset}


def apply_capture_specifiers(patterns, re_type, pat_range,
                             re_strings=[],
                             capture_specifiers=capture_specifiers):
    """Applies multiple capture specifiers to a set of capture patterns

    Args:
        patterns (string|list): a list of pattern strings which are recognised
         (e.g.: SUMMARY, PLAN, TODO, etc...)
        re_type (dict|list): Dictionaries which customise the behaviour of the
         tool for each patter (recommended keys:
             - 'color': <valid latex color string>;
             - 'count': <A name for the item type>;
             - 'description': <A legend for the type of item>.)
        pat_range (range()): The range of items of re_type which correspond to
         `patterns`
        re_strings (list, optional): list of re_strings preceding the ones
         which will be added.
        capture_specifiers (dictionaries, optional): See the definition of the
         module level variable `capture_specifiers`.

    Returns:
        (string|list, dict|list): The strings which will be used for regexp and
        a full list of dictionary descriptors for each re_string. There will be
        one item in each list for each combination of
        PATTERNS x CAPTURE_SPECIFIERS
    """
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
    return re_strings, re_type


class ParsingProperties(object):
    """
    Class handling the regular expressions used for parsing the file

    There are 3 main types of expression to capture 3 types of triggers:
        - File triggers: Indicates a latex file input command the text captured
         must correspond to a valid file path;
        - Line triggers: The entire line will be copied into the summary file,
         used to mirror the document structure for sections, and titles (for
         example);
        - Sentence triggers: Captures specially formatted comments used to
         build the summary file (e.g. SUMMARY, PLAN, TODO, etc..)

    During object instantiation the `__init__()` uses module level defaults,
    customisation is then possible in code via the `add_...` methods and in
    latex via the special sentence triggers:
        - `%! CUSTOM_TRIGGER_LINE: <your custom trigger>`
        - `%! CUSTOM_TRIGGER_PHRASE: <your custom trigger>`
        - `%! CUSTOM_TRIGGER_FILE: <your custom trigger>`

    """
    def __init__(self,):
        super(ParsingProperties, self).__init__()
        self.file_parse_re = build_file_parse_re(file_parse_triggers)

        self.summary_parse_re, self.summary_parse_re_types,\
            self.summary_starts = build_summary_parse_re(
                line_record_triggers, phrase_record_triggers)
        self.file_parsing_modifiers = file_parsing_modifiers

    def add_line_record_triggers(self, new_commands, new_re_types=None):
        re_type = self._match_re_and_type(
            new_commands, new_re_types, default_command_type)

        re_strings = [command_name_to_re_string(c) for c in new_commands]
        # Lines get prepended to the list as they are at the start
        self.summary_parse_re = (
            build_regex_list(re_strings)
            + self.summary_parse_re)
        self.summary_parse_re_types = (
            re_type + self.summary_parse_re_types)
        self.summary_starts["pattern"] += len(new_commands)

    def add_phrase_record_triggers(self, new_patterns, new_re_types=None):

        re_type = self._match_re_and_type(
            new_patterns, new_re_types, default_pattern_type)

        re_strings = []
        pat_range = range(0, 0 + len(new_patterns))
        re_strings, re_type = apply_capture_specifiers(
            new_patterns, re_type, pat_range,
            re_strings, capture_specifiers)

        # phrases get appended as that enables to add as many as possible
        self.summary_parse_re.extend(build_regex_list(re_strings))
        self.summary_parse_re_types.extend(re_type)

    def add_file_parse_triggers(self,
                                new_file_triggers, new_trigger_modifs):
        self.file_parse_re.extend(build_file_parse_re(new_file_triggers))
        for i, new_trigger in enumerate(new_file_triggers):
            self.file_parsing_modifiers[new_trigger] =\
                new_trigger_modifs[i]

    def _match_re_and_type(self, new_re_patterns, new_re_types, default_type):
        """Checks that patterns and types are compatible"""
        if new_re_types is None:
            re_type = [dict(re_type_default) for _ in new_re_patterns]
        else:
            re_type = []
            if len(new_re_patterns) != len(new_re_types):
                raise IndexError(
                    "pattern and type lists must be the same length;"
                    + "\n if type definitions are not needed pass 'None'.")
            else:
                for new_type in new_re_types:
                    if new_type is None:
                        re_type.append(dict(re_type_default))
                    else:
                        re_type.append(new_type)
        return re_type


module_parsing_properties = ParsingProperties()

# for compatibility, most of the module expects module level variables
file_parse_re = module_parsing_properties.file_parse_re
summary_parse_re = module_parsing_properties.summary_parse_re
summary_parse_re_types = module_parsing_properties.summary_parse_re_types
summary_starts = module_parsing_properties.summary_starts


def parse_new_pattern(pattern, regex_type=default_pattern_type):
    summary_parse_re.append(re.compile(pattern_name_to_re_string(pattern)))
    summary_parse_re_types.append(dict(regex_type))


def parse_new_command(command, regex_type=default_command_type):
    summary_parse_re.append(re.compile(command_name_to_re_string(command)))
    summary_parse_re_types.append(dict(regex_type))


def parse_new_file(new_file_triggers):
    file_parse_re.extend(build_file_parse_re(new_file_triggers))


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
        [('title', []), ('parser', []), ('legend', []),
         ('todos', []), ('summary', []), ('files', [])],
    ),
    n_stacks=0,
    counters=OrderedDict([("section", 0)]),
    do_process_record=True,
    generate_file_list=False,
    file_triggers=None,
):

    records['summary'].append("% Start file : " + file_in)
    prev_record = {}
    if n_stacks == 0:
        records['todos'].append(r"\section{List of To-dos and questions}")
        records['todos'].append(start_enum)
        records['legend'].append(r"\section{Key of colours and item types}")
        records['legend'].append(start_enum)
    if generate_file_list:
        records['files'].append(file_in)
    with open(file_in, 'r') as f:
        for line_num, lines in enumerate(f):
            line = lines.splitlines()[0]
            line_info = "        % " + file_in + ":" + str(line_num + 1)

            if do_process_record:
                prev_record, counters = process_record(
                    records,
                    line,
                    line_info,
                    prev_record,
                    counters,
                )

            next_file, next_file_triggers = detect_file(line, file_in)
            if next_file:
                print("Next file : " + next_file)
                _, counters = parse_file(
                    next_file, records, n_stacks + 1, counters,
                    do_process_record, generate_file_list, next_file_triggers
                )

    if n_stacks == 0:
        close_itemlist(records['summary'], start_item, end_item, item_str)
        close_itemlist(records['todos'], start_enum, end_enum, item_str)
        close_itemlist(records['legend'], start_enum, end_enum, item_str)
        summarise_parser_activity(records['parser'], counters)

    records['summary'].append("% End file : " + file_in)
    return records, counters


def detect_file(line, current_file):
    next_file = None
    next_file_triggers = None

    for index_re, file_re in enumerate(file_parse_re):
        m = file_re["regexp"].search(line)
        if m:
            next_file_triggers = file_parsing_modifiers[file_re["pattern"]]
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

    return next_file, next_file_triggers


def detect_record(line):
    record_type = {}
    record = line
    for pat_re, pat_type in zip(summary_parse_re, summary_parse_re_types):
        m = pat_re.search(line)
        if m:
            break
    if m and ("active" not in pat_type or pat_type["active"]):
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


def record_to_modifier_pattern(record):
    delimiter = ";"
    try:
        new_partial_re, new_re_type_string = record.split(delimiter, 1)[:]
    except ValueError:
        new_partial_re = record
        new_re_type_string = "None"

    new_partial_re = new_partial_re.strip()
    new_re_type = ast.literal_eval(new_re_type_string.strip())

    return new_partial_re, new_re_type


def process_modifier(record_type, record):
    modifier_call = getattr(
        module_parsing_properties,
        "add_" + record_type["modifier"])
    new_partial_re, new_re_type = record_to_modifier_pattern(record)
    print(new_partial_re)
    print(new_re_type)
    print(modifier_call)
    modifier_call([new_partial_re], [new_re_type])
    print("done.")
    file_parse_re = module_parsing_properties.file_parse_re
    summary_parse_re = module_parsing_properties.summary_parse_re
    summary_parse_re_types = module_parsing_properties.summary_parse_re_types
    summary_starts = module_parsing_properties.summary_starts


def process_record(records, line, line_info, prev_record, nums,):

    record_type, record = detect_record(line)

    # modifiers alter the capturing regexp and are treated first, if one is
    # encountered an early return is performed as the record should not be
    # written.
    if record_is("modifier", record_type):
        process_modifier(record_type, record)
        prev_record = record_type
        return prev_record, nums

    if record_is("line", record_type):
        close_itemlist(records['summary'],
                       start_item, end_item, item_str)

    if record_is("prefix", record_type):
        record = record_type["prefix"] + record
    if record_is("suffix", record_type):
        record = record + record_type["suffix"]
    if record_is("done", record_type):
        done_suffix = done_marker
        if record_is("count", record_type):
            done_suffix += " " + record_type["count"]
        record = record + " [" + done_suffix + "]"

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
        count_name = record_type["count"] + add_to_count_name
        try:
            nums[count_name] += 1
        except Exception:  # start a new count if increment fails
            nums[count_name] = 1
            if record_is("legend", record_type):  # add the count to the legend
                legend_str = count_name + " : " + record_type["legend"]
                if is_color:
                    legend_str = color_format.format(color, legend_str)

                records["legend"].append(item_str + legend_str)

    return prev_record, nums


def write_records(
        records, file_name, name_change=default_name_change, new_ext=None,
        records_to_print=None,):

    if not name_change:
        name_change = default_name_change

    file, ext = os.path.splitext(file_name)
    if new_ext is None:
        new_ext = ext
    new_file = file + name_change + new_ext
    with open(new_file, 'w') as f:
        if records_to_print is None:
            records_to_print = records
        for rec in records_to_print:
            f.writelines("%s\n" % l for l in records[rec])
            f.write("\n")

def main():

    file_name = sys.argv[1]

    parser_args = dict()
    record_writer_args = dict()
    if len(sys.argv) > 1:
        if "-s" in sys.argv:  # parse only summaries
            for i in range(
                    summary_starts["pattern"],
                    summary_starts["pattern"] + len(phrase_record_triggers) *
                    len(capture_specifiers)):
                if not summary_parse_re[i].match("%!SUMMARY"):
                    summary_parse_re_types[i]["active"] = False
            record_writer_args['name_change'] = default_name_change + "only"
        if "-f" in sys.argv:  # parse only file list
            parser_args['do_process_record'] = False
            parser_args['generate_file_list'] = True
            record_writer_args['name_change'] = "_texfilelist"
            record_writer_args['new_ext'] = '.txt'
            record_writer_args['records_to_print'] = ['files']

    records, counters = parse_file(file_name, **parser_args)
    write_records(records, file_name, **record_writer_args)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import pdb
        import traceback
        traceback.print_exc()
        pdb.post_mortem()
