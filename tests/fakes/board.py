"""Fake `board` module: named pin objects for the Feather M4 CAN."""


class Pin:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"board.{self.name}"


for _name in ("D5", "D6", "D9", "D10", "D11", "D12", "D13", "A1", "CAN_RX", "CAN_TX", "CAN_STANDBY", "BOOST_ENABLE"):
    globals()[_name] = Pin(_name)
