"""Turns key presses into vehicle actions and keypad LED colors."""

from mmecu import log
from mmecu.drivetrain import DriveState
from mmecu.keypad import Color, Key

DRIVE_KEYS = {
    DriveState.PARK: Key.PARK,
    DriveState.REVERSE: Key.REVERSE,
    DriveState.NEUTRAL: Key.NEUTRAL,
    DriveState.DRIVE: Key.DRIVE,
}
DRIVE_COLOR = Color.BLUE
TOGGLE_COLOR = Color.YELLOW
F1_COLOR = Color.CYAN
F2_COLOR = Color.YELLOW


class VehicleController:
    def __init__(self, keypad, shifter, parking_brake):
        self.keypad = keypad
        self.shifter = shifter
        self.parking_brake = parking_brake
        self.drive_state = DriveState.PARK
        self.hazard = False
        self.exhaust_sound = False
        self._handlers = {
            Key.HAZARD: self.toggle_hazard,
            Key.PARK: self.select_park,
            Key.REVERSE: self.select_reverse,
            Key.NEUTRAL: self.select_neutral,
            Key.DRIVE: self.select_drive,
            Key.EXHAUST_SOUND: self.toggle_exhaust_sound,
            Key.F1: self.select_f1,
            Key.F2: self.select_f2,
        }

    def handle_key(self, key):
        handler = self._handlers.get(key)
        if handler is None:
            log.debug(f"no action for key {key}")
        else:
            handler()

    def show_startup_drive_state(self):
        """Drive LEDs drawn whenever the keypad is (re)started.

        NEUTRAL is always lit and PARK is lit iff the brake is engaged, regardless
        of drive_state (see lode/plans/refactor-plan.md, open question 1).
        """
        if self.parking_brake.engaged:
            self.drive_state = DriveState.PARK
        for key in DRIVE_KEYS.values():
            self.keypad.set_color(key, Color.BLACK)
        self.keypad.set_color(Key.NEUTRAL, DRIVE_COLOR)
        if self.parking_brake.engaged:
            self.keypad.set_color(Key.PARK, DRIVE_COLOR)

    # -- drive selection --
    def select_park(self):
        self._change_drive_state(DriveState.PARK)
        self.parking_brake.engage()

    def select_reverse(self):
        self.parking_brake.disengage()
        self._change_drive_state(DriveState.REVERSE)
        self.shifter.pulse(DriveState.REVERSE)

    def select_neutral(self):
        self._change_drive_state(DriveState.NEUTRAL)
        self.shifter.pulse(DriveState.NEUTRAL)

    def select_drive(self):
        self.parking_brake.disengage()
        self._change_drive_state(DriveState.DRIVE)
        self.shifter.pulse(DriveState.DRIVE)

    def _change_drive_state(self, state):
        if state == self.drive_state:
            return
        self.drive_state = state
        for drive_state, key in DRIVE_KEYS.items():
            self.keypad.set_color(key, DRIVE_COLOR if drive_state == state else Color.BLACK)

    # -- toggles and modes --
    def toggle_hazard(self):
        self.hazard = not self.hazard
        self.keypad.set_color(Key.HAZARD, TOGGLE_COLOR if self.hazard else Color.BLACK)

    def toggle_exhaust_sound(self):
        self.exhaust_sound = not self.exhaust_sound
        self.keypad.set_color(Key.EXHAUST_SOUND, TOGGLE_COLOR if self.exhaust_sound else Color.BLACK)

    def select_f1(self):
        self.keypad.set_color(Key.F1, F1_COLOR)
        self.keypad.set_color(Key.F2, Color.BLACK)

    def select_f2(self):
        self.keypad.set_color(Key.F2, F2_COLOR)
        self.keypad.set_color(Key.F1, Color.BLACK)
