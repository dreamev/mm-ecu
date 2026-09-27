"""Hazard, exhaust, F1/F2 and not-yet-implemented keys."""

import pytest

from tests.sim import Sim

BOOT_LEDS = {"PARK": "blue", "NEUTRAL": "blue"}


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


@pytest.mark.parametrize("key", ["REGEN", "AUTOPILOT_ON", "AUTOPILOT_SPEED_UP", "AUTOPILOT_SPEED_DOWN"])
def test_unimplemented_keys_do_nothing(key):
    sim = Sim().boot()
    before = len(sim.sent())
    sim.press(key)
    assert len(sim.sent()) == before
    assert sim.pulses() == []


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
