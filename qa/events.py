"""Parse the firmware's `EVT <name> key=value ...` serial lines (see mmecu/log.py)."""

PREFIX = "EVT "


class Event:
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

    def __repr__(self):
        return f"Event({self.name!r}, {self.fields!r})"

    def __eq__(self, other):
        return isinstance(other, Event) and (self.name, self.fields) == (other.name, other.fields)


def parse_line(line):
    """The Event on this console line, or None if it is not an event line."""
    line = line.strip()
    if not line.startswith(PREFIX):
        return None
    tokens = line[len(PREFIX) :].split()
    if not tokens:
        return None
    fields = {}
    for token in tokens[1:]:
        key, _, value = token.partition("=")
        fields[key] = value
    return Event(tokens[0], fields)


def is_firmware_error(line):
    """Console lines that mean the firmware is unhealthy, whatever step is running."""
    line = line.strip()
    return line.startswith(("Traceback", "level=3 ")) or "Error:" in line
