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

from mmecu import log
from qa.events import parse_line
from qa.spec import COLOR_NAMES, KEY_NUMBER, KEYS, decode_leds, key_state_payload  # noqa: F401  re-exported

# --- spec-derived protocol constants --------------------------------------
NMT_ID = 0x000
HEARTBEAT_ID = 0x715
KEY_STATE_ID = 0x195
LED_ID = 0x215
SDO_REQUEST_ID = 0x615
SDO_RESPONSE_ID = 0x595
SDO_READ_KEY_STATE = [0x40, 0x00, 0x20, 0x01]  # manual §15: read object 2000h sub 1
HV_BUS_ID = 0x126

HEARTBEAT = {"boot_up": 0x00, "stopped": 0x04, "pre_operational": 0x7F, "operational": 0x05}

RELAYS = {"D11": "REVERSE", "D12": "NEUTRAL", "D13": "DRIVE"}
BRAKE_ENGAGED_SENSOR = "D10"
BRAKE_DISENGAGED_SENSOR = "D9"
BRAKE_ENGAGE_OUT = "D6"
BRAKE_DISENGAGE_OUT = "D5"


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
    """`brake` is the sensor reading at boot: engaged, disengaged, invalid or both.

    The simulated keypad tracks which keys are physically `held` (they stay held
    across an ECU reset) and answers SDO key-state reads unless `sdo_replies=False`
    (a pad firmware without that object).
    """

    def __init__(self, brake="engaged", held=(), sdo_replies=True):
        self.physical_held = list(held)
        self.sdo_replies = sdo_replies
        self._sdo_seen = 0
        levels = {
            "engaged": (True, False),
            "disengaged": (False, True),
            "invalid": (False, False),
            "both": (True, True),
        }[brake]
        digitalio.input_levels[BRAKE_ENGAGED_SENSOR] = levels[0]
        digitalio.input_levels[BRAKE_DISENGAGED_SENSOR] = levels[1]
        self.event_lines = []
        log.set_event_sink(self.event_lines.append)
        self.clock = FakeTime()
        self.actions = RecordingActions()
        self.app = _build_app(self.clock, self.actions)
        self.bus = canio.buses[-1]

    # -- driving the ECU --
    def tick(self, count=1):
        for _ in range(count):
            self.app.tick()
            self._answer_sdo_reads()

    def _answer_sdo_reads(self):
        requests = self.sent(SDO_REQUEST_ID)
        for _, data in requests[self._sdo_seen :]:
            if self.sdo_replies and data[:4] == SDO_READ_KEY_STATE:
                levels = key_state_payload(*self.physical_held)
                self.receive(SDO_RESPONSE_ID, [0x4B, 0x00, 0x20, 0x01] + levels + [0, 0])
        self._sdo_seen = len(requests)

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
        self.physical_held = list(names)
        self.receive(KEY_STATE_ID, key_state_payload(*names))
        self.settle()

    def press(self, *names):
        """Tap: the pad sends a frame on press and another on release."""
        self.hold(*names)
        self.release()

    def wait(self, seconds):
        self.clock.now += seconds

    def release(self):
        self.physical_held = []
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

    def events(self, name=None):
        parsed = [parse_line(line) for line in self.event_lines]
        return [event for event in parsed if name is None or event.name == name]

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
