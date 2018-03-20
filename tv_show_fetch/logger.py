class Logger(object):
    STYLES = {
        'BLACK': '\033[0;30m',
        'RED': '\033[0;31m',
        'GREEN': '\033[0;32m',
        'YELLOW': '\033[0;33m',
        'BLUE': '\033[0;34m',
        'PINK': '\033[0;35m',
        'CYAN': '\033[0;36m',
        'GRAY': '\033[0;37m',

        'BG_BLACK': '\033[0;40m',
        'BG_RED': '\033[0;41m',
        'BG_GREEN': '\033[0;42m',
        'BG_YELLOW': '\033[0;43m',
        'BG_BLUE': '\033[0;44m',
        'BG_PINK': '\033[0;45m',
        'BG_CYAN': '\033[0;46m',
        'BG_GRAY': '\033[0;47m',

        'RESET': '\033[0;0m'
    }

    def __init__(self, params=None):
        self.colorize = True
        self.verbose = False

        # override any default settings defined in params
        if params is not None:
            for param in params:
                self.__dict__[param] = params[param]

        self.prefix = None
        self.log_types = {
            'INFO': {'DATA': [], 'STYLE': self.STYLES['CYAN']},
            'SUCCESS': {'DATA': [], 'STYLE': self.STYLES['GREEN']},
            'WARNING': {'DATA': [], 'STYLE': self.STYLES['YELLOW']},
            'ERROR': {'DATA': [], 'STYLE': self.STYLES['RED']},
            'DEBUG': {'DATA': [], 'STYLE': self.STYLES['PINK']}
        }

    def set_prefix(self, value):
        self.prefix = value

    def reset_prefix(self):
        self.prefix = None

    def get_prefix(self):
        return self.prefix

    def get_logs_by_type(self, type):
        if type in self.log_types:
            return self.log_types[type]
        else:
            print("Invalid log type: {0}".format(type))
            return None

    def info(self, msg):
        self._add_to_log(msg, "INFO")

    def success(self, msg):
        self._add_to_log(msg, "SUCCESS")

    def debug(self, msg):
        self._add_to_log(msg, "DEBUG")

    def warning(self, msg):
        self._add_to_log(msg, "WARNING")

    def error(self, msg):
        self._add_to_log(msg, "ERROR")

    def _add_to_log(self, msg, type="INFO"):
        if type not in self.log_types:
            self._add_to_log("Invalid log type: {0}".format(type), "WARNING")
            type = "INFO"

        prefix = self.get_prefix()
        if prefix is not None:
            prefix = "[ {0} ] {1}".format(type, prefix)
        else:
            prefix = "[ {0} ]".format(type)

        msg_string = "{0} {1}".format(prefix, msg)
        self.log_types[type]['DATA'].append(msg_string)

        if self.colorize:
            print("{0}{1}{2}".format(self.log_types[type]['STYLE'], msg_string, self.STYLES['RESET']))
        else:
            print(msg_string)
