"""Black-box simulator: the ECU application wired to fake CircuitPython hardware.

Tests talk to the ECU the way the car does: CAN frames in, and CAN frames,
GPIO writes and servo angles out. The protocol helpers here are derived from the
keypad/Tesla specs (see lode/keypad/can-protocol.md), not from the firmware, so
they check the firmware independently.

`_build_app` is the only function that knows how the firmware is constructed.
"""

import canio
import digitalio
from adafruit_motor import servo

# --- spec-derived protocol constants --------------------------------------
NMT_ID = 0x000
HEARTBEAT_ID = 0x715
KEY_STATE_ID = 0x195
LED_ID = 0x215
HV_BUS_ID = 0x126

HEARTBEAT = {"boot_up": 0x00, "stopped": 0x04, "pre_operational": 0x7F, "operational": 0x05}

KEYS = [
    "HAZARD",
    "PARK",
    "REVERSE",
    "NEUTRAL",
    "DRIVE",
    "AUTOPILOT_SPEED_UP",
    "EXHAUST_SOUND",
    "F1",
    "F2",
    "REGEN",
    "AUTOPILOT_ON",
    "AUTOPILOT_SPEED_DOWN",
]
KEY_NUMBER = {name: n for n, name in enumerate(KEYS, start=1)}

COLOR_NAMES = {
    (0, 0, 0): "black",
    (1, 0, 0): "red",
    (0, 1, 0): "green",
    (0, 0, 1): "blue",
    (1, 1, 0): "yellow",
    (0, 1, 1): "cyan",
    (1, 0, 1): "magenta",
    (1, 1, 1): "white",
}

RELAYS = {"D11": "REVERSE", "D12": "NEUTRAL", "D13": "DRIVE"}
BRAKE_ENGAGED_SENSOR = "D10"
BRAKE_DISENGAGED_SENSOR = "D9"
BRAKE_ENGAGE_OUT = "D6"
BRAKE_DISENGAGE_OUT = "D5"


def key_state_payload(*names):
    mask = 0
    for name in names:
        mask |= 1 << (KEY_NUMBER[name] - 1)
    return [mask & 0xFF, mask >> 8]


def decode_leds(payload):
    value = int.from_bytes(bytes(payload[:5]), "little")
    leds = {}
    for n, name in enumerate(KEYS, start=1):
        rgb = tuple((value >> (channel * 12 + n - 1)) & 1 for channel in range(3))
        leds[name] = COLOR_NAMES[rgb]
    return leds


def hv_bus_payload(volts):
    raw = int(round(volts * 2))
    return [raw & 0xFF, (raw >> 8) & 0x03, 0x00]


class FakeTime:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        digitalio.events.append(("sleep", seconds))
        self.now += seconds


class RecordingActions:
    """Stands in for mmecu.actions.VehicleActions and records every call."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        from mmecu.actions import VehicleActions

        if name.startswith("_") or not hasattr(VehicleActions, name):
            raise AttributeError(f"VehicleActions has no action {name!r}")
        return lambda *args: self.calls.append((name, *args))


# --- construction (the only firmware-specific part) -----------------------
def _build_app(clock, actions):
    from mmecu import hardware

    return hardware.build_application(sleep=clock.sleep, clock=clock.monotonic, actions=actions)


class Sim:
    """`brake` is the sensor reading at boot: engaged, disengaged, invalid or both."""

    def __init__(self, brake="engaged"):
        levels = {
            "engaged": (True, False),
            "disengaged": (False, True),
            "invalid": (False, False),
            "both": (True, True),
        }[brake]
        digitalio.input_levels[BRAKE_ENGAGED_SENSOR] = levels[0]
        digitalio.input_levels[BRAKE_DISENGAGED_SENSOR] = levels[1]
        self.clock = FakeTime()
        self.actions = RecordingActions()
        self.app = _build_app(self.clock, self.actions)
        self.bus = canio.buses[-1]

    # -- driving the ECU --
    def tick(self, count=1):
        for _ in range(count):
            self.app.tick()

    def settle(self, max_ticks=100):
        """Tick until the ECU has nothing left to send."""
        idle = 0
        for _ in range(max_ticks):
            before = len(self.bus.sent)
            self.tick()
            idle = idle + 1 if len(self.bus.sent) == before else 0
            if idle >= 2 and not any(listener.inbox for listener in self.bus.listeners):
                return
        raise AssertionError("ECU never went idle")

    def boot(self):
        self.settle()
        return self

    def receive(self, can_id, data):
        self.bus.inject(canio.Message(can_id, bytes(data)))

    def hold(self, *names):
        """Send the key-state frame for exactly these keys being down (manual §10: level, not events)."""
        self.receive(KEY_STATE_ID, key_state_payload(*names))
        self.settle()

    def press(self, *names):
        """Tap: the pad sends a frame on press and another on release."""
        self.hold(*names)
        self.release()

    def wait(self, seconds):
        self.clock.now += seconds

    def release(self):
        self.receive(KEY_STATE_ID, [0, 0])
        self.settle()

    def heartbeat(self, state):
        self.receive(HEARTBEAT_ID, [HEARTBEAT[state]])
        self.settle()

    def hv_bus(self, volts, count=1):
        for _ in range(count):
            self.receive(HV_BUS_ID, hv_bus_payload(volts))
            self.tick()

    # -- observing the ECU --
    def sent(self, can_id=None):
        return [(m.id, list(m.data)) for m in self.bus.sent if can_id is None or m.id == can_id]

    def leds(self):
        frames = self.sent(LED_ID)
        assert frames, "no LED frame sent yet"
        return decode_leds(frames[-1][1])

    def lit(self):
        return {name: color for name, color in self.leds().items() if color != "black"}

    def pulses(self):
        """Relay pulses as (drive state, seconds high) in chronological order."""
        result, high_since = [], {}
        for event in digitalio.events:
            if event[0] == "sleep":
                for pin in high_since:
                    high_since[pin] += event[1]
            elif event[0] in RELAYS:
                pin, value = event
                if value:
                    high_since[pin] = 0.0
                elif pin in high_since:
                    result.append((RELAYS[pin], high_since.pop(pin)))
        return result

    def clear_events(self):
        digitalio.events.clear()

    def brake_outputs(self):
        engage = digitalio.pins[BRAKE_ENGAGE_OUT].value
        disengage = digitalio.pins[BRAKE_DISENGAGE_OUT].value
        return {"engage": engage, "disengage": disengage}

    @property
    def gauge(self):
        return servo.instances[-1]
