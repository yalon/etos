import os
import stat
import errno
import sys
from gevent import Greenlet
from gevent.hub import get_hub
from gevent.socket import EAGAIN

READ_SIZE = 4096


class PipeInput(Greenlet):
    def __init__(self, path, output, read_size=READ_SIZE):
        super(PipeInput, self).__init__()
        self.path = path
        self.output = output
        self.read_size = read_size
        self.buffer = []

    def _run(self):
        try:
            os.mkfifo(self.path)
        except OSError, e:
            if e.errno != errno.EEXIST or not stat.S_ISFIFO(os.stat(self.path).st_mode):
                raise

        fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            hub = get_hub()
            while True:
                event = hub.loop.io(fd, 1)
                hub.wait(event)
                try:
                    buf = os.read(fd, self.read_size)
                    if len(buf) > 0:
                        self._split_and_output(buf)
                except OSError, e:
                    if e.errno not in (EAGAIN, errno.EINTR):
                        raise
                    sys.exc_clear()
        finally:
            os.close(fd)
            os.unlink(self.path)

    def _split_and_output(self, buf):
        prev_i = 0
        i = buf.find("\n", prev_i)
        while i != -1:
            self.buffer.append(buf[prev_i:i])
            self._send_to_output()
            prev_i = i + 1
            i = buf.find("\n", prev_i)
        self.buffer.append(buf[prev_i:])

    def _send_to_output(self):
        self.output("".join(self.buffer))
        self.buffer = []
