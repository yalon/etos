#!/usr/bin/env python
"""ETOS - Everything To Syslog

Usage:
  etos.py [options] [-n FACILITY:PATH]...

Options:
  -d --daemonize        daemonize
  -p FILE --pid=FILE    pid file to use
  -n FACILITY:PATH --nginx=FACILITY:PATH nginx log file

Facility can be one of USER, MAIL, DAEMON, AUTH, SYSLOG, LPR, NEWS, UUCP, UUCP, CRON,
                       LOCAL0, LOCAL1, LOCAL2, LOCAL3, LOCAL4, LOCAL5, LOCAL6, LOCAL7
"""
import os
import sys

if __name__ == "__main__":
    module_path = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, module_path)

from docopt import docopt
import errno
import daemon
import syslog
import gevent
from lockfile.pidlockfile import PIDLockFile
from setproctitle import setproctitle
from contextlib import contextmanager

from etos.nginx_parser import NginxParser
from etos.pipe_input import PipeInput

FACILITY_NAME_TO_FACILITY = {
    "USER": syslog.LOG_USER,
    "MAIL": syslog.LOG_MAIL,
    "DAEMON": syslog.LOG_DAEMON,
    "AUTH": syslog.LOG_AUTH,
    "SYSLOG": syslog.LOG_SYSLOG,
    "LPR": syslog.LOG_LPR,
    "NEWS": syslog.LOG_NEWS,
    "UUCP": syslog.LOG_UUCP,
    "UUCP": syslog.LOG_UUCP,
    "CRON": syslog.LOG_CRON,
    "LOCAL0": syslog.LOG_LOCAL0,
    "LOCAL1": syslog.LOG_LOCAL1,
    "LOCAL2": syslog.LOG_LOCAL2,
    "LOCAL3": syslog.LOG_LOCAL3,
    "LOCAL4": syslog.LOG_LOCAL4,
    "LOCAL5": syslog.LOG_LOCAL5,
    "LOCAL6": syslog.LOG_LOCAL6,
    "LOCAL7": syslog.LOG_LOCAL7,
}


@contextmanager
def no_context():
    yield


def create_pid_file(path):
    pid_file = PIDLockFile(arguments['--pid'])
    if pid_file.is_locked():
        pid = pid_file.read_pid()
        try:
            os.kill(pid, 0)
            raise Exception("process already running")
        except OSError, e:
            if e.errno in (errno.ESRCH, errno.ENOENT):
                pid_file.break_lock()
            else:
                raise
    return pid_file

if __name__ == "__main__":
    arguments = docopt(__doc__)
    if not arguments["--nginx"]:
        print("no nginx log option was given, exitting.")
        sys.exit(0)

    pid_file = None
    if arguments['--pid']:
        pid_file = create_pid_file(arguments['--pid'])

    if arguments['--daemonize']:
        context = daemon.DaemonContext(pidfile=pid_file)
    elif pid_file:
        context = pid_file
    else:
        context = no_context

    nginx_raw_args = [arg.split(":", 1) for arg in arguments["--nginx"]]
    greenlets = []
    for arg in nginx_raw_args:
        if not isinstance(arg, (list, tuple)) or len(arg) != 2:
            raise Exception("failed to parse argument: {0}".format(arg))
        if arg[0].upper() not in FACILITY_NAME_TO_FACILITY:
            raise Exception("unknown facility 0}".format(arg[0]))
        parser = NginxParser(FACILITY_NAME_TO_FACILITY[arg[0].upper()])
        greenlets.append(PipeInput(arg[1], parser))

    with context:
        if arguments["--daemonize"]:
            setproctitle("[etos]")
        for g in greenlets:
            g.start()
        gevent.joinall(greenlets)
