"""Fake `canio`: a loopback bus whose listener honors `Match` filters."""

buses = []


def reset():
    buses.clear()


class BusState:
    ERROR_ACTIVE = "ERROR_ACTIVE"
    ERROR_WARNING = "ERROR_WARNING"
    ERROR_PASSIVE = "ERROR_PASSIVE"
    BUS_OFF = "BUS_OFF"


class Message:
    def __init__(self, id, data):
        self.id = id
        self.data = bytes(data)

    def __repr__(self):
        return f"Message(0x{self.id:03x}, {self.data.hex(' ')})"


class Match:
    def __init__(self, id, mask=None, extended=False):
        self.id = id


class Listener:
    def __init__(self, matches, timeout):
        self.ids = None if not matches else {m.id for m in matches}
        self.timeout = timeout
        self.inbox = []

    def deliver(self, message):
        if self.ids is None or message.id in self.ids:
            self.inbox.append(message)

    def receive(self):
        return self.inbox.pop(0) if self.inbox else None


class CAN:
    def __init__(self, rx, tx, baudrate=250000, auto_restart=False, **_):
        self.baudrate = baudrate
        self.auto_restart = auto_restart
        self.state = BusState.ERROR_ACTIVE
        self.sent = []
        self.listeners = []
        buses.append(self)

    def listen(self, matches=None, timeout=10):
        listener = Listener(matches, timeout)
        self.listeners.append(listener)
        return listener

    def send(self, message):
        if len(message.data) > 8:
            raise ValueError("CAN payload longer than 8 bytes")
        self.sent.append(message)

    def inject(self, message):
        for listener in self.listeners:
            listener.deliver(message)
