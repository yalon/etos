import syslog

NGINX_PRIORITY_TO_SYSLOG = {
    "[emerg]": syslog.LOG_EMERG,
    "[alert]": syslog.LOG_ALERT,
    "[crit]": syslog.LOG_CRIT,
    "[error]": syslog.LOG_ERR,
    "[warn]": syslog.LOG_WARNING,
    "[notice]": syslog.LOG_NOTICE,
    "[info]": syslog.LOG_INFO,
    "[debug]": syslog.LOG_DEBUG,
}


class NginxParser(object):
    def __init__(self, facility):
        self.facility = facility

    def __call__(self, line):
        # log levels: debug info notice warn error crit alert emerg
        date, time, priority, message = line.split(" ", 3)
        if priority in NGINX_PRIORITY_TO_SYSLOG:
            priority = NGINX_PRIORITY_TO_SYSLOG[priority]
        else:
            syslog.syslog(self.facility | syslog.LOG_WARN,
                          "etos: could not match nginx priority {0} to syslog, so using INFO. Full line: {1}", priority,
                          line)
            priority = syslog.LOG_INFO
        syslog.syslog(self.facility | priority, line)
