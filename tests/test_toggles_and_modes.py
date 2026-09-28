"""Hazard, exhaust, F1/F2 and not-yet-implemented keys."""

import pytest

from tests.sim import Sim

BOOT_LEDS = {"PARK": "blue"}


def test_f1_lights_cyan_and_clears_f2():
    sim = Sim().boot()
    sim.press("F2")
    sim.press("F1")
    assert sim.lit() == {**BOOT_LEDS, "F1": "cyan"}


def test_f2_lights_yellow_and_clears_f1():
    sim = Sim().boot()
    sim.press("F1")
    sim.press("F2")
    assert sim.lit() == {**BOOT_LEDS, "F2": "yellow"}


def test_keys_in_one_frame_are_handled_in_key_order():
    sim = Sim().boot()
    sim.press("F2", "F1")
    assert sim.lit() == {**BOOT_LEDS, "F2": "yellow"}


def test_key_release_frame_does_nothing():
    sim = Sim().boot()
    before = len(sim.sent())
    sim.release()
    assert len(sim.sent()) == before


def test_hazard_toggles_on_and_off():
    sim = Sim().boot()
    sim.press("HAZARD")
    assert sim.lit() == {**BOOT_LEDS, "HAZARD": "yellow"}
    sim.press("HAZARD")
    assert sim.lit() == BOOT_LEDS


def test_exhaust_sound_toggles_on_and_off():
    sim = Sim().boot()
    sim.press("EXHAUST_SOUND")
    assert sim.lit() == {**BOOT_LEDS, "EXHAUST_SOUND": "yellow"}
    sim.press("EXHAUST_SOUND")
    assert sim.lit() == BOOT_LEDS


def test_short_key_state_payload_is_ignored():
    sim = Sim().boot()
    before = len(sim.sent())
    sim.receive(0x195, [0x10])
    sim.settle()
    assert len(sim.sent()) == before


def test_held_key_is_not_retriggered_when_another_key_changes():
    # Manual §10: the frame carries the level of every key and is sent on any change.
    sim = Sim().boot()
    sim.hold("DRIVE")
    sim.hold("DRIVE", "F1")
    sim.hold("DRIVE")
    sim.release()
    assert sim.pulses() == [("DRIVE", 0.5)]
    assert sim.lit() == {"DRIVE": "blue", "F1": "cyan"}


def test_periodic_state_frames_do_not_retrigger_a_held_key():
    # Object 1800h sub 5 can make the pad repeat the key-state frame while held.
    sim = Sim().boot()
    for _ in range(2):
        sim.hold("HAZARD")
    sim.release()
    assert sim.lit() == {**BOOT_LEDS, "HAZARD": "yellow"}


def test_key_pressed_again_after_release_triggers_again():
    sim = Sim().boot()
    sim.hold("HAZARD")
    sim.release()
    sim.hold("HAZARD")
    assert sim.lit() == BOOT_LEDS


def test_every_key_has_a_press_handler():
    from mmecu.keypad import Key

    sim = Sim()
    assert set(sim.app.controller._on_press) == set(Key.ALL)


@pytest.mark.parametrize(
    "key, color, action",
    [
        ("HAZARD", "yellow", "set_hazard"),
        ("EXHAUST_SOUND", "yellow", "set_exhaust_sound"),
        ("REGEN", "white", "set_regen"),
        ("AUTOPILOT_ON", "blue", "set_cruise"),
    ],
)
def test_toggle_keys_light_and_call_their_action(key, color, action):
    sim = Sim().boot()
    sim.press(key)
    assert sim.lit() == {**BOOT_LEDS, key: color}
    sim.press(key)
    assert sim.lit() == BOOT_LEDS
    assert sim.actions.calls == [(action, True), (action, False)]


def test_power_mode_keys_call_set_power_mode():
    sim = Sim().boot()
    sim.press("F1")
    sim.press("F2")
    assert sim.actions.calls == [("set_power_mode", "low"), ("set_power_mode", "high")]


@pytest.mark.parametrize(
    "key, color, direction",
    [("AUTOPILOT_SPEED_UP", "green", 1), ("AUTOPILOT_SPEED_DOWN", "red", -1)],
)
def test_cruise_speed_keys_light_while_held_and_report_hold_time(key, color, direction):
    sim = Sim().boot()
    sim.hold(key)
    assert sim.lit() == {**BOOT_LEDS, key: color}
    assert sim.actions.calls == []
    sim.wait(1.5)
    sim.release()
    assert sim.lit() == BOOT_LEDS
    assert sim.actions.calls == [("adjust_cruise_speed", direction, 1.5)]


def test_pad_reboot_mid_hold_cancels_the_hold():
    sim = Sim().boot()
    sim.hold("AUTOPILOT_SPEED_UP")
    sim.heartbeat("boot_up")
    assert sim.lit() == BOOT_LEDS
    sim.release()
    assert sim.actions.calls == []
