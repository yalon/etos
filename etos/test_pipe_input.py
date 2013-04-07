from .pipe_input import PipeInput


def print_line(s):
    print("got line: {}".format(s))


print("setting up pipe.")
p = PipeInput("test.pipe", print_line)
p.start()
p.join()
