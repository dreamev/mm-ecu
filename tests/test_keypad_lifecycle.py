"""Keypad node management: activation, heartbeats, LED restoration."""

from tests.sim import LED_ID, NMT_ID, Sim


def test_first_tick_sends_nmt_start_before_anything_else():
    sim = Sim()
    sim.tick()
    assert sim.sent() == [(NMT_ID, [0x01, 0, 0, 0, 0, 0, 0, 0])]


def test_boot_with_brake_engaged_lights_only_park():
    sim = Sim(brake="engaged").boot()
    assert sim.lit() == {"PARK": "blue"}
    assert sim.sent(LED_ID)[-1] == (LED_ID, [0, 0, 0, 0x02, 0, 0, 0, 0])


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
    assert sim.lit() == {"PARK": "blue", "F1": "cyan"}


def test_pad_reboot_redraws_current_drive_selection():
    sim = Sim(brake="disengaged").boot()
    sim.press("DRIVE")
    sim.heartbeat("boot_up")
    assert sim.lit() == {"DRIVE": "blue"}


def test_pad_reboot_in_neutral_with_brake_engaged_keeps_neutral():
    sim = Sim(brake="engaged").boot()
    sim.press("NEUTRAL")
    sim.heartbeat("boot_up")
    assert sim.lit() == {"NEUTRAL": "blue"}


def test_pre_operational_heartbeat_restarts_node():
    sim = Sim().boot()
    nmt_before = len(sim.sent(NMT_ID))
    sim.heartbeat("pre_operational")
    assert len(sim.sent(NMT_ID)) == nmt_before + 1
    assert sim.lit() == {"PARK": "blue"}


def test_ecu_reset_with_pad_already_operational_still_activates_and_draws_leds():
    # The pad kept power while the ECU rebooted: its first heartbeat says
    # Operational, but its LEDs still show the pre-reset state.
    sim = Sim(brake="engaged")
    sim.heartbeat("operational")
    assert sim.sent(NMT_ID)
    assert sim.lit() == {"PARK": "blue"}
