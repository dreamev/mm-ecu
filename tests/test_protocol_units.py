"""Pure protocol/encoding functions, checked against the spec helpers in sim.py."""

import pytest

from mmecu import battery, can, keypad
from mmecu.keypad import Color, Key
from tests.sim import COLOR_NAMES, KEYS, decode_leds, hv_bus_payload, key_state_payload

ALL_COLORS = list(COLOR_NAMES)


@pytest.mark.parametrize("key", Key.ALL)
@pytest.mark.parametrize("color", ALL_COLORS)
def test_led_encoding_matches_spec_for_every_key_and_color(key, color):
    colors = [Color.BLACK] * keypad.KEY_COUNT
    colors[key - 1] = color
    expected = dict.fromkeys(KEYS, "black")
    expected[KEYS[key - 1]] = COLOR_NAMES[color]
    assert decode_leds(keypad.encode_leds(colors)) == expected


def test_led_encoding_all_white_sets_all_36_bits():
    assert keypad.encode_leds([Color.WHITE] * 12) == [0xFF, 0xFF, 0xFF, 0xFF, 0x0F]


@pytest.mark.parametrize("key", Key.ALL)
def test_decode_single_key(key):
    assert keypad.decode_pressed_keys(key_state_payload(KEYS[key - 1])) == [key]


def test_decode_multiple_keys_in_key_order():
    assert keypad.decode_pressed_keys(key_state_payload("F2", "HAZARD", "AUTOPILOT_SPEED_DOWN")) == [1, 9, 12]


def test_decode_ignores_unused_high_bits():
    assert keypad.decode_pressed_keys([0x00, 0xF0]) == []


def test_decode_short_payload_is_none():
    assert keypad.decode_pressed_keys(b"\x01") is None


@pytest.mark.parametrize(
    "data, expected",
    [
        ([0x01], b"\x01" + bytes(7)),
        (list(range(10)), bytes(range(8))),
        ((), bytes(8)),
        (b"\xaa\xbb", b"\xaa\xbb" + bytes(6)),
    ],
)
def test_frame_data_is_always_eight_bytes(data, expected):
    assert can.frame_data(data) == expected


def test_outbox_is_fifo():
    outbox = can.Outbox()
    outbox.push(1, [1])
    outbox.push(2, [2])
    assert [outbox.pop()[0], outbox.pop()[0], outbox.pop()] == [1, 2, None]


@pytest.mark.parametrize("volts", [0, 325, 362.5, 400, 511.5])
def test_hv_bus_voltage_round_trip(volts):
    assert battery.decode_hv_bus_voltage(hv_bus_payload(volts)) == volts


def test_hv_bus_voltage_ignores_current_bits():
    assert battery.decode_hv_bus_voltage([0x00, 0xFC, 0xFF]) == 0


@pytest.mark.parametrize("volts, fraction", [(300, 0.0), (325, 0.0), (362.5, 0.5), (400, 1.0), (480, 1.0)])
def test_charge_fraction_is_clamped(volts, fraction):
    assert battery.charge_fraction(volts) == pytest.approx(fraction)


@pytest.mark.parametrize(
    "data, state",
    [
        (b"\x00", keypad.NodeState.BOOT_UP),
        (b"\x7f", keypad.NodeState.PRE_OPERATIONAL),
        (b"\x05", keypad.NodeState.OPERATIONAL),
        (b"\x42", keypad.NodeState.UNKNOWN),
        (b"", keypad.NodeState.UNKNOWN),
    ],
)
def test_heartbeat_states(data, state):
    pad = keypad.Keypad()
    pad.on_heartbeat(data)
    assert pad.state == state
