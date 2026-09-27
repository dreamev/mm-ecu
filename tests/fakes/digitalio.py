"""Fake `digitalio` that records every output write in a shared event log.

Tests set `input_levels[pin_name]` before the app is built to simulate sensors;
unset inputs read True, like a floating pin with a pull-up.
"""

events = []
input_levels = {}
pins = {}


def reset():
    events.clear()
    input_levels.clear()
    pins.clear()


class Direction:
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class Pull:
    UP = "UP"
    DOWN = "DOWN"


class DigitalInOut:
    def __init__(self, pin):
        self.name = pin.name
        self.direction = Direction.INPUT
        self.pull = None
        self._value = False
        pins[self.name] = self

    def switch_to_input(self, pull=None):
        self.direction = Direction.INPUT
        self.pull = pull

    def switch_to_output(self, value=False):
        self.direction = Direction.OUTPUT
        self.value = value

    @property
    def value(self):
        if self.direction == Direction.INPUT:
            return input_levels.get(self.name, True)
        return self._value

    @value.setter
    def value(self, value):
        if self.direction != Direction.OUTPUT:
            raise AttributeError(f"{self.name} is not an output")
        self._value = bool(value)
        events.append((self.name, self._value))
