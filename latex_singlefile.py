import latex_summary as lxs
import os
import sys


def concatenate_file(
    file_in,
    file_out=None,
    n_stacks=0,
):

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
                    next_file, file_out, n_stacks + 1)
            else:
                file_out.write(line + "\n")

    if n_stacks == 0:
        file_out.close()



if __name__ == "__main__":
    file_name = sys.argv[1]
    concatenate_file(file_name)
