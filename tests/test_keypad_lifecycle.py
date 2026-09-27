"""Keypad node management: activation, heartbeats, LED restoration."""

import pytest

from tests.sim import LED_ID, NMT_ID, Sim


def test_first_tick_sends_nmt_start_before_anything_else():
    sim = Sim()
    sim.tick()
    assert sim.sent() == [(NMT_ID, [0x01, 0, 0, 0, 0, 0, 0, 0])]


def test_boot_with_brake_engaged_lights_park_and_neutral():
    sim = Sim(brake="engaged").boot()
    assert sim.lit() == {"PARK": "blue", "NEUTRAL": "blue"}
    assert sim.sent(LED_ID)[-1] == (LED_ID, [0, 0, 0, 0x0A, 0, 0, 0, 0])


def test_boot_with_brake_disengaged_lights_only_neutral():
    sim = Sim(brake="disengaged").boot()
    assert sim.lit() == {"NEUTRAL": "blue"}


def test_every_frame_is_eight_bytes():
    sim = Sim().boot()
    sim.press("DRIVE")
    sim.press("F1")
    assert sim.sent()
    assert all(len(data) == 8 for _, data in sim.sent())


def test_operational_heartbeat_is_ignored():
    sim = Sim().boot()
    before = len(sim.sent())
    sim.heartbeat("operational")
    assert len(sim.sent()) == before


def test_pad_reboot_restarts_node_and_restores_leds():
    sim = Sim().boot()
    sim.press("F1")
    nmt_before = len(sim.sent(NMT_ID))
    sim.heartbeat("boot_up")
    assert len(sim.sent(NMT_ID)) == nmt_before + 1
    assert sim.lit() == {"PARK": "blue", "NEUTRAL": "blue", "F1": "cyan"}


def test_pad_reboot_redraws_boot_drive_leds_not_current_selection():
    # Current behavior (see lode open question 1): a pad reboot redraws the boot
    # drive LEDs, not the selected drive state.
    sim = Sim(brake="disengaged").boot()
    sim.press("DRIVE")
    sim.heartbeat("boot_up")
    assert sim.lit() == {"NEUTRAL": "blue"}


@pytest.mark.xfail(strict=True, reason="bug: pre-operational heartbeat raises AttributeError")
def test_pre_operational_heartbeat_restarts_node():
    sim = Sim().boot()
    nmt_before = len(sim.sent(NMT_ID))
    sim.heartbeat("pre_operational")
    assert len(sim.sent(NMT_ID)) == nmt_before + 1
    assert sim.lit() == {"PARK": "blue", "NEUTRAL": "blue"}
