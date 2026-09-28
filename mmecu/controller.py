"""Turns key presses and releases into vehicle actions and keypad LED colors.

Every key has a press handler; keys whose behavior depends on hold time also have
a release handler that receives the held duration in seconds.
"""

from mmecu import log
from mmecu.actions import PowerMode
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
REGEN_COLOR = Color.WHITE
CRUISE_COLOR = Color.BLUE
SPEED_UP_COLOR = Color.GREEN
SPEED_DOWN_COLOR = Color.RED  # requirement says orange; key LEDs cannot show orange
HOLD_KEYS = (Key.AUTOPILOT_SPEED_UP, Key.AUTOPILOT_SPEED_DOWN)


class VehicleController:
    def __init__(self, keypad, shifter, parking_brake, actions, clock):
        self.keypad = keypad
        self.shifter = shifter
        self.parking_brake = parking_brake
        self.actions = actions
        self._clock = clock
        # Display state only: nothing is actuated at boot
        self.drive_state = DriveState.PARK if parking_brake.engaged else DriveState.NEUTRAL
        self.hazard = False
        self.exhaust_sound = False
        self.power_mode = None
        self.regen = False
        self.cruise = False
        self._pressed_at = {}
        self._on_press = {
            Key.HAZARD: self.toggle_hazard,
            Key.PARK: self.select_park,
            Key.REVERSE: self.select_reverse,
            Key.NEUTRAL: self.select_neutral,
            Key.DRIVE: self.select_drive,
            Key.AUTOPILOT_SPEED_UP: self.start_speed_up,
            Key.EXHAUST_SOUND: self.toggle_exhaust_sound,
            Key.F1: self.select_f1,
            Key.F2: self.select_f2,
            Key.REGEN: self.toggle_regen,
            Key.AUTOPILOT_ON: self.toggle_cruise,
            Key.AUTOPILOT_SPEED_DOWN: self.start_speed_down,
        }
        self._on_release = {
            Key.AUTOPILOT_SPEED_UP: self.finish_speed_up,
            Key.AUTOPILOT_SPEED_DOWN: self.finish_speed_down,
        }

    def key_pressed(self, key):
        self._pressed_at[key] = self._clock()
        handler = self._on_press.get(key)
        if handler is None:
            log.debug(f"no action for key {key}")
        else:
            handler()

    def key_released(self, key):
        pressed_at = self._pressed_at.pop(key, None)
        handler = self._on_release.get(key)
        if handler is not None and pressed_at is not None:
            handler(self._clock() - pressed_at)

    def keypad_restarted(self):
        """The pad was (re)started: abandon holds in progress and redraw the drive state."""
        self._pressed_at.clear()
        for key in HOLD_KEYS:
            self.keypad.set_color(key, Color.BLACK)
        self.show_drive_state()

    def show_drive_state(self):
        """Light exactly the key for the current drive state."""
        for drive_state, key in DRIVE_KEYS.items():
            self.keypad.set_color(key, DRIVE_COLOR if drive_state == self.drive_state else Color.BLACK)

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
        self.show_drive_state()

    # -- toggles --
    def toggle_hazard(self):
        self.hazard = not self.hazard
        self.keypad.set_color(Key.HAZARD, TOGGLE_COLOR if self.hazard else Color.BLACK)
        self.actions.set_hazard(self.hazard)

    def toggle_exhaust_sound(self):
        self.exhaust_sound = not self.exhaust_sound
        self.keypad.set_color(Key.EXHAUST_SOUND, TOGGLE_COLOR if self.exhaust_sound else Color.BLACK)
        self.actions.set_exhaust_sound(self.exhaust_sound)

    def toggle_regen(self):
        self.regen = not self.regen
        self.keypad.set_color(Key.REGEN, REGEN_COLOR if self.regen else Color.BLACK)
        self.actions.set_regen(self.regen)

    def toggle_cruise(self):
        self.cruise = not self.cruise
        self.keypad.set_color(Key.AUTOPILOT_ON, CRUISE_COLOR if self.cruise else Color.BLACK)
        self.actions.set_cruise(self.cruise)

    # -- power modes (radio group) --
    def select_f1(self):
        self.power_mode = PowerMode.LOW
        self.keypad.set_color(Key.F1, F1_COLOR)
        self.keypad.set_color(Key.F2, Color.BLACK)
        self.actions.set_power_mode(PowerMode.LOW)

    def select_f2(self):
        self.power_mode = PowerMode.HIGH
        self.keypad.set_color(Key.F2, F2_COLOR)
        self.keypad.set_color(Key.F1, Color.BLACK)
        self.actions.set_power_mode(PowerMode.HIGH)

    # -- cruise speed (lit while held, acts on release) --
    def start_speed_up(self):
        self.keypad.set_color(Key.AUTOPILOT_SPEED_UP, SPEED_UP_COLOR)

    def finish_speed_up(self, held_seconds):
        self.keypad.set_color(Key.AUTOPILOT_SPEED_UP, Color.BLACK)
        self.actions.adjust_cruise_speed(1, held_seconds)

    def start_speed_down(self):
        self.keypad.set_color(Key.AUTOPILOT_SPEED_DOWN, SPEED_DOWN_COLOR)

    def finish_speed_down(self, held_seconds):
        self.keypad.set_color(Key.AUTOPILOT_SPEED_DOWN, Color.BLACK)
        self.actions.adjust_cruise_speed(-1, held_seconds)
