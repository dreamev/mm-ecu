"""Fake `pwmio`."""


class PWMOut:
    def __init__(self, pin, duty_cycle=0, frequency=500, variable_frequency=False):
        self.pin = pin
        self.duty_cycle = duty_cycle
        self.frequency = frequency
