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


def test_stopped_heartbeat_restarts_node():
    # Manual §25: 04h = Stopped. A stopped pad sends no key frames, so restart it.
    sim = Sim().boot()
    nmt_before = len(sim.sent(NMT_ID))
    sim.heartbeat("stopped")
    assert len(sim.sent(NMT_ID)) == nmt_before + 1
    assert sim.lit() == {"PARK": "blue"}


# --- keys held through a restart (Copilot review finding; manual §15 SDO baseline) ---
def test_every_keypad_start_reads_the_current_key_levels():
    from tests.sim import SDO_READ_KEY_STATE, SDO_REQUEST_ID

    sim = Sim().boot()
    sim.heartbeat("boot_up")
    reads = sim.sent(SDO_REQUEST_ID)
    assert len(reads) == 2
    assert all(data == SDO_READ_KEY_STATE + [0, 0, 0, 0] for _, data in reads)


def test_key_held_through_ecu_reset_does_not_fire_when_another_key_changes():
    sim = Sim(brake="engaged", held=["DRIVE"]).boot()  # DRIVE was down before the ECU reset
    sim.hold("DRIVE", "F1")
    sim.hold("DRIVE")
    sim.release()
    assert sim.pulses() == []
    assert sim.brake_outputs() == {"engage": True, "disengage": False}
    assert sim.lit() == {"PARK": "blue", "F1": "cyan"}


def test_key_held_through_keypad_reboot_does_not_fire():
    sim = Sim(brake="engaged").boot()
    sim.hold("DRIVE")
    sim.clear_events()
    sim.heartbeat("boot_up")
    sim.hold("DRIVE", "F1")
    assert sim.pulses() == []


def test_periodic_frame_of_a_held_key_at_startup_does_not_fire():
    sim = Sim(brake="engaged", held=["DRIVE"])
    sim.receive(0x195, [0x10, 0x00])  # periodic key-state frame arrives on the first tick
    sim.settle()
    assert sim.pulses() == []


def test_first_press_after_startup_still_works():
    sim = Sim(brake="engaged").boot()
    sim.press("DRIVE")
    assert sim.pulses() == [("DRIVE", 0.5)]


def test_without_an_sdo_reply_keys_are_ignored_until_the_timeout_then_work():
    sim = Sim(brake="engaged", held=["DRIVE"], sdo_replies=False).boot()
    sim.hold("DRIVE", "F1")  # before the timeout: only updates the baseline
    assert sim.pulses() == [] and "F1" not in sim.lit()
    sim.wait(1.5)
    sim.tick()
    sim.hold("DRIVE", "F1", "F2")  # after the timeout, F2 is a new press; DRIVE stays held
    assert sim.pulses() == []
    assert sim.lit()["F2"] == "yellow"
