"""Examples copied verbatim from the PKP-2600-SI CANopen User Manual rev 1.1.

Section numbers refer to that manual. See lode/keypad/can-protocol.md.
"""

import pytest

from mmecu import keypad
from mmecu.keypad import Color, Key, NodeState


def test_cob_ids_derive_from_default_node_id():
    # §3 default node ID 15h; §8/§25 700h+ID; §10 180h+ID; §11 200h+ID; §4 NMT on 00h
    assert keypad.NODE_ID == 0x15
    assert (keypad.NMT_ID, keypad.HEARTBEAT_ID, keypad.KEY_STATE_ID, keypad.LED_ID) == (0x000, 0x715, 0x195, 0x215)


def test_nmt_start_command():
    # §4: byte 0 = 01h start, byte 1 = 00h (all keypads) or node ID
    assert keypad.NMT_START_ALL_NODES == (0x01, 0x00)


# §10 Keys state message: byte 0 = K8..K1, byte 1 = 0000 K12..K9, byte 4 = tick timer
@pytest.mark.parametrize(
    "frame, keys",
    [
        ([0x00, 0x00, 0x00, 0x00, 0x5A], []),
        ([0x08, 0x00, 0x00, 0x00, 0x5A], [4]),
        ([0x80, 0x00, 0x00, 0x00, 0x5A], [8]),
        ([0x21, 0x00, 0x00, 0x00, 0x5A], [1, 6]),
        ([0x00, 0x08, 0x00, 0x00, 0x5A], [12]),
        # §15 (SDO 2000h uses the same mapping)
        ([0x00, 0x02], [10]),
        ([0xFF, 0x0F], list(Key.ALL)),
    ],
)
def test_key_state_examples(frame, keys):
    assert keypad.decode_pressed_keys(frame) == keys


def _leds(red=(), green=(), blue=()):
    colors = []
    for key in Key.ALL:
        colors.append((int(key in red), int(key in green), int(key in blue)))
    return colors


# §11 Set LED ON message examples (bytes 0-4; bytes 5-7 are 00h and added by can.frame_data)
@pytest.mark.parametrize(
    "colors, payload",
    [
        (_leds(), [0x00, 0x00, 0x00, 0x00, 0x00]),
        (_leds(red=[1]), [0x01, 0x00, 0x00, 0x00, 0x00]),
        (_leds(red=[2, 7]), [0x42, 0x00, 0x00, 0x00, 0x00]),
        (_leds(green=[5]), [0x00, 0x00, 0x01, 0x00, 0x00]),
        (_leds(green=[1], red=[9]), [0x00, 0x11, 0x00, 0x00, 0x00]),
        (_leds(blue=[4, 8]), [0x00, 0x00, 0x00, 0x88, 0x00]),
        (_leds(red=[11, 12], green=[3, 4]), [0x00, 0xCC, 0x00, 0x00, 0x00]),
        # §12 uses the same bit layout for blink: green 7,8,11,12 + blue 9,10
        (_leds(green=[7, 8, 11, 12], blue=[9, 10]), [0x00, 0x00, 0xCC, 0x00, 0x03]),
    ],
)
def test_led_examples(colors, payload):
    assert keypad.encode_leds(colors) == payload


def test_led_colors_are_one_bit_per_channel():
    # §11: each LED channel is a single on/off bit, so only 7 colors + off exist
    colors = [value for name, value in vars(Color).items() if not name.startswith("_")]
    assert all(set(rgb) <= {0, 1} for rgb in colors)


# §25 heartbeat states: 00h Boot-up, 04h Stop, 05h Operational, 7Fh Pre-operational
@pytest.mark.parametrize(
    "byte, state",
    [
        (0x00, NodeState.BOOT_UP),
        (0x04, NodeState.STOPPED),
        (0x05, NodeState.OPERATIONAL),
        (0x7F, NodeState.PRE_OPERATIONAL),
    ],
)
def test_heartbeat_states(byte, state):
    pad = keypad.Keypad()
    pad.on_heartbeat(bytes([byte]))
    assert pad.state == state
