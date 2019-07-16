import latex_summary as lxs
import os
import sys
import re

keep_text = r"(.*)"


def concatenate_file(
    file_in,
    file_out=None,
    n_stacks=0,
    regex_keep=keep_text,
):
    keep_re = re.compile(regex_keep)
    if n_stacks == 0:
        pass
    if file_out is None:
        file, ext = os.path.splitext(file_in)
        new_file = file + "_auto_concatenate" + ext
        file_out = open(new_file, 'w')

    with open(file_in, 'r') as f:
        for line_num, lines in enumerate(f):
            line = lines.splitlines()[0]

            next_file = lxs.detect_file(line, file_in)
            if next_file:
                print("Next file : " + next_file)
                concatenate_file(
                    next_file, file_out,
                    n_stacks=n_stacks + 1,
                    regex_keep=regex_keep)
            else:
                m = keep_re.search(line)
                if m:
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
