import latex_summary as lxs
import os
import sys
import re

keep_text = r"(.*)"

# record format [trigger, starting state]
lxs.file_parsing_modifiers["subfile"] = {
    "start_recording": {
        "type": "record", "action": [r"\begin{document}", False],
    },
    "stop_recording": {
        "type": "record", "action": [r"\end{document}", True],
    }
}


def is_recording(file_triggers, encountered_state=None):

    record_line = True
    if file_triggers is None:
        return record_line, encountered_state

    # if this is the first time, set the state to the initial state
    if encountered_state is None:
        encountered_state = {}
        for modif in file_triggers:
            if file_triggers[modif]["type"] == "record":
                encountered_state[modif] = False


    for modif in encountered_state:
        modifier_effect = (
            file_triggers[modif]["action"][1] ^ encountered_state[modif]
        )
        record_line &= modifier_effect

    return record_line, encountered_state

def is_encountered(line, file_triggers, encountered_state):

    tripped = False
    if file_triggers is None:
        return encountered_state, tripped

    for modif in encountered_state:
        check = file_triggers[modif]["action"][0] in line
        encountered_state[modif] = encountered_state[modif] or check
        tripped = tripped or check


    return encountered_state, tripped

def concatenate_file(
    file_in,
    file_out=None,
    n_stacks=0,
    regex_keep=keep_text,
    file_triggers=None,
):
    keep_re = re.compile(regex_keep)
    record_line, encountered_state = is_recording(file_triggers)

    if n_stacks == 0:
        pass
    if file_out is None:
        file, ext = os.path.splitext(file_in)
        new_file = file + "_auto_concatenate" + ext
        file_out = open(new_file, 'w')

    with open(file_in, 'r') as f:
        for line_num, lines in enumerate(f):
            line = lines.splitlines()[0]

            next_file, next_file_triggers = lxs.detect_file(line, file_in)
            if next_file:
                print("Next file : " + next_file)
                concatenate_file(
                    next_file, file_out,
                    n_stacks=n_stacks + 1,
                    regex_keep=regex_keep,
                    file_triggers=next_file_triggers,
                )
            else:
                record_line, encountered_state = is_recording(
                    file_triggers,
                    encountered_state=encountered_state,
                )
                encountered_state, tripped = is_encountered(
                    line, file_triggers, encountered_state)

                m = keep_re.search(line)
                if m and record_line and not tripped:
                    file_out.write(m.group(0) + "\n")

    if n_stacks == 0:
        file_out.close()


if __name__ == "__main__":
    file_name = sys.argv[1]
    if len(sys.argv) > 1:
        if "-c" in sys.argv:
            keep_text = r'([^%]*(?<!\\)(\\%)*)*'
    concatenate_file(
        file_name,
        regex_keep=keep_text,
    )
