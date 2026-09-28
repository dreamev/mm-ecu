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


# Structured events: one `EVT <name> key=value ...` line per observable change.
# Always on (they happen at human speed); the QA harness (qa/) parses them from
# the serial console. Values must not contain spaces.
EVENT_PREFIX = "EVT"
_event_sink = print


def set_event_sink(sink):
    """Where event lines go (print by default; tests capture them)."""
    global _event_sink
    _event_sink = sink


def event(name, **fields):
    parts = [EVENT_PREFIX, name]
    for key in fields:
        parts.append(f"{key}={fields[key]}")
    _event_sink(" ".join(parts))
