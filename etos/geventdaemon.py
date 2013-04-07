# Copyright (C) 2012, Antonin Amand <antonin.amand@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import gevent.monkey
import gevent.hub
import daemon
import signal


class GeventDaemonContext(daemon.DaemonContext):
    """ DaemonContext for gevent.

    Receive same options as a DaemonContext (python-daemon), Except:

    `monkey`: None by default, does nothing. Else it can be a dict or
    something that evaluate to True.
    If it is True, it patches all. (gevent.monkey.patch_all()).
    If it is a dict, it pass the dict as keywords arguments to patch_all().

    `signal_map`: receives a dict of signals, but handler is either a
    callable, a list of arguments [callable, arg1, arg2] or
    a string.
    callable without arguments will receive (signal, None) as arguments,
    meaning the `frame` parameter is always None.

    If the daemon context forks. It calls gevent.reinit().
    """

    def __init__(self, monkey_greenlet_report=True,
            monkey=True, gevent_hub=None, signal_map=None, **daemon_options):
        self.gevent_signal_map = signal_map
        self.monkey = monkey
        self.monkey_greenlet_report = monkey_greenlet_report
        self.gevent_hub = gevent_hub
        super(GeventDaemonContext, self).__init__(
                signal_map={}, **daemon_options)

    def open(self):
        super(GeventDaemonContext, self).open()
        # always reinit even when not forked when registering signals
        self._apply_monkey_patch()
        if self.gevent_hub is not None:
            # gevent 1.0 only
            gevent.get_hub(self.gevent_hub)
        gevent.reinit()
        self._setup_gevent_signals()

    def _apply_monkey_patch(self):
        if isinstance(self.monkey, dict):
            gevent.monkey.patch_all(**self.monkey)
        elif self.monkey:
            gevent.monkey.patch_all()

        if self.monkey_greenlet_report:
            import logging
            original_report = gevent.hub.Hub.print_exception

            def print_exception(self, context, type, value, tb):
                try:
                    logging.error("Error in greenlet: %s" % str(context),
                            exc_info=(type, value, tb))
                finally:
                    return original_report(self, context, type, value, tb)

            gevent.hub.Hub.print_exception = print_exception

    def _setup_gevent_signals(self):
        if self.gevent_signal_map is None:
            gevent.signal(signal.SIGTERM, self.terminate, signal.SIGTERM, None)
            return

        for sig, target in self.gevent_signal_map.items():
            if target is None:
                raise ValueError(
                        'invalid handler argument for signal %s', str(sig))
            tocall = target
            args = [sig, None]
            if isinstance(target, list):
                if not target:
                    raise ValueError(
                            'handler list is empty for signal %s', str(sig))
                tocall = target[0]
                args = target[1:]
            elif isinstance(target, basestring):
                assert not target.startswith('_')
                tocall = getattr(self, target)

            gevent.signal(sig, tocall, *args)

