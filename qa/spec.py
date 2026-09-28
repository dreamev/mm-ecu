"""Keypad facts from the PKP-2600-SI manual, independent of the firmware.

Shared by the QA harness and the test simulator so both judge the firmware
against the spec rather than against itself.
"""

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
DRIVE_KEYS = ["PARK", "REVERSE", "NEUTRAL", "DRIVE"]

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


def key_state_payload(*names):
    """Key-state frame (manual §10) with exactly these keys held."""
    mask = 0
    for name in names:
        mask |= 1 << (KEY_NUMBER[name] - 1)
    return [mask & 0xFF, mask >> 8]


def decode_leds(payload):
    """{key name: color name} from an LED ON payload (manual §11)."""
    value = int.from_bytes(bytes(payload[:5]), "little")
    leds = {}
    for n, name in enumerate(KEYS, start=1):
        rgb = tuple((value >> (channel * 12 + n - 1)) & 1 for channel in range(3))
        leds[name] = COLOR_NAMES[rgb]
    return leds
