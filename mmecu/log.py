"""Leveled logging to the serial console (syslog severities)."""

ERROR = 3
WARNING = 4
INFO = 6
DEBUG = 7

_level = WARNING


def set_level(level):
    global _level
    _level = level


def _log(level, message):
    if level <= _level:
        print(f'level={level} message="{message}"')


def error(message):
    _log(ERROR, message)


def warning(message):
    _log(WARNING, message)


def info(message):
    _log(INFO, message)


def debug(message):
    _log(DEBUG, message)
