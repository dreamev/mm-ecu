"""Blink Marine PKP-2600-SI keypad: CANopen protocol and LED model.

See lode/keypad/can-protocol.md for the wire format.
"""

from mmecu import log

NODE_ID = 0x15
NMT_ID = 0x000
NMT_START_ALL_NODES = (0x01, 0x00)
HEARTBEAT_ID = 0x700 + NODE_ID
KEY_STATE_ID = 0x180 + NODE_ID
LED_ID = 0x200 + NODE_ID

KEY_COUNT = 12
LED_PAYLOAD_LENGTH = 5


class Key:
    """Physical key numbers, 1 (top left) to 12."""

    HAZARD = 1
    PARK = 2
    REVERSE = 3
    NEUTRAL = 4
    DRIVE = 5
    AUTOPILOT_SPEED_UP = 6
    EXHAUST_SOUND = 7
    F1 = 8
    F2 = 9
    REGEN = 10
    AUTOPILOT_ON = 11
    AUTOPILOT_SPEED_DOWN = 12

    ALL = tuple(range(1, KEY_COUNT + 1))


class Color:
    """(red, green, blue) on/off; the keypad LEDs have one bit per channel."""

    BLACK = (0, 0, 0)
    RED = (1, 0, 0)
    GREEN = (0, 1, 0)
    BLUE = (0, 0, 1)
    YELLOW = (1, 1, 0)
    CYAN = (0, 1, 1)
    MAGENTA = (1, 0, 1)
    WHITE = (1, 1, 1)


class NodeState:
    UNKNOWN = "Unknown"
    BOOT_UP = "Boot-up"
    STOPPED = "Stopped"
    PRE_OPERATIONAL = "Pre-operational"
    OPERATIONAL = "Operational"


HEARTBEAT_STATES = {
    b"\x00": NodeState.BOOT_UP,
    b"\x04": NodeState.STOPPED,
    b"\x7f": NodeState.PRE_OPERATIONAL,
    b"\x05": NodeState.OPERATIONAL,
}


def decode_pressed_keys(data):
    """Keys held in a key-state frame, in key order; None if the payload is short."""
    if len(data) < 2:
        return None
    mask = data[0] | (data[1] << 8)
    return [key for key in Key.ALL if mask >> (key - 1) & 1]


def encode_leds(colors):
    """Pack 12 (r, g, b) tuples, indexed by key - 1, into the LED payload.

    Bit `channel * 12 + key - 1` of the little-endian payload is that key's channel.
    """
    payload = [0] * LED_PAYLOAD_LENGTH
    for index, rgb in enumerate(colors):
        for channel in range(3):
            if rgb[channel]:
                bit = channel * KEY_COUNT + index
                payload[bit >> 3] |= 1 << (bit & 7)
    return payload


class Keypad:
    """The ECU's view of the keypad: its node state and the LED colors it should show."""

    def __init__(self):
        self.state = NodeState.UNKNOWN
        self._colors = [Color.BLACK] * KEY_COUNT
        self._held = []
        self.leds_dirty = False

    def color(self, key):
        return self._colors[key - 1]

    def set_color(self, key, color):
        self._colors[key - 1] = color
        self.leds_dirty = True

    def led_payload(self):
        """Payload for the full LED frame; marks the LEDs as sent."""
        self.leds_dirty = False
        return encode_leds(self._colors)

    def key_edges(self, held):
        """(pressed, released) keys relative to the previous key-state frame.

        Key-state frames carry the level of every key and are sent on any change
        (and periodically if object 1800h is configured), so presses and releases
        are the edges between consecutive frames.
        """
        pressed = [key for key in held if key not in self._held]
        released = [key for key in self._held if key not in held]
        self._held = held
        return pressed, released

    def mark_started(self):
        """We sent NMT start: the pad is Operational with nothing known to be held."""
        self.state = NodeState.OPERATIONAL
        self._held = []

    def needs_start(self):
        return self.state in (NodeState.BOOT_UP, NodeState.STOPPED, NodeState.PRE_OPERATIONAL)

    def on_heartbeat(self, data):
        state = HEARTBEAT_STATES.get(bytes(data))
        if state is None:
            log.info(f"unknown keypad heartbeat: {data}")
        elif state != self.state:
            log.info(f"keypad is now {state}")
            self.state = state
