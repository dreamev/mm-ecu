"""The firmware's structured event stream, which the QA harness depends on."""

from qa.events import Event, is_firmware_error, parse_line
from qa.spec import decode_leds
from tests.sim import Sim


def test_parse_line():
    assert parse_line("EVT key_up key=6 held=1.50\r\n") == Event("key_up", {"key": "6", "held": "1.50"})
    assert parse_line('level=4 message="x"') is None
    assert parse_line("EVT") is None


def test_firmware_error_lines():
    assert is_firmware_error("Traceback (most recent call last):")
    assert is_firmware_error('level=3 message="parking brake sensors ..."')
    assert not is_firmware_error("EVT leds payload=0000000200")


def test_boot_emits_ecu_start_keypad_start_and_leds():
    sim = Sim(brake="engaged").boot()
    names = [event.name for event in sim.events()]
    assert names.index("ecu_start") < names.index("keypad_start") < names.index("leds")
    assert sim.events("ecu_start")[0].fields == {"drive": "PARK", "brake": "1"}
    assert decode_leds(bytes.fromhex(sim.events("leds")[-1].fields["payload"]))["PARK"] == "blue"


def test_leds_event_matches_the_frame_on_the_bus():
    sim = Sim().boot()
    sim.press("F1")
    assert decode_leds(bytes.fromhex(sim.events("leds")[-1].fields["payload"])) == sim.leds()


def test_drive_press_events():
    sim = Sim(brake="engaged").boot()
    sim.press("DRIVE")
    names = [event.name for event in sim.events()]
    for name in ("key_down", "brake", "drive", "relay", "key_up"):
        assert name in names
    assert sim.events("relay")[-1].fields == {"state": "DRIVE"}
    assert sim.events("brake")[-1].fields == {"engaged": "0"}


def test_hold_events_carry_hold_time():
    sim = Sim().boot()
    sim.hold("AUTOPILOT_SPEED_UP")
    sim.wait(2)
    sim.release()
    assert sim.events("key_up")[-1].fields == {"key": "6", "held": "2.00"}
    assert sim.events("cruise_adjust")[-1].fields == {"direction": "1", "held": "2.00"}


def test_event_values_never_contain_spaces():
    sim = Sim().boot()
    for key in ("HAZARD", "F1", "REGEN", "AUTOPILOT_ON", "DRIVE", "PARK"):
        sim.press(key)
    sim.heartbeat("boot_up")
    sim.hv_bus(362.5)
    for line in sim.event_lines:
        event = parse_line(line)
        assert all(" " not in value and value for value in event.fields.values()), line
