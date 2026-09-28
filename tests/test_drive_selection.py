"""PRND radio group, shift relay pulses and parking brake."""

from tests.sim import Sim


def test_drive_releases_brake_pulses_relay_and_lights_drive():
    sim = Sim(brake="engaged").boot()
    sim.press("DRIVE")
    assert sim.pulses() == [("DRIVE", 0.5)]
    assert sim.brake_outputs() == {"engage": False, "disengage": True}
    assert sim.lit() == {"DRIVE": "blue"}


def test_reverse_releases_brake_and_pulses_reverse_relay():
    sim = Sim().boot()
    sim.press("REVERSE")
    assert sim.pulses() == [("REVERSE", 0.5)]
    assert sim.brake_outputs() == {"engage": False, "disengage": True}
    assert sim.lit() == {"REVERSE": "blue"}


def test_neutral_pulses_relay_and_leaves_brake_alone():
    sim = Sim(brake="engaged").boot()
    sim.press("NEUTRAL")
    assert sim.pulses() == [("NEUTRAL", 0.5)]
    assert sim.brake_outputs() == {"engage": True, "disengage": False}
    assert sim.lit() == {"NEUTRAL": "blue"}


def test_park_engages_brake_without_relay_pulse():
    sim = Sim().boot()
    sim.press("DRIVE")
    sim.clear_events()
    sim.press("PARK")
    assert sim.pulses() == []
    assert sim.brake_outputs() == {"engage": True, "disengage": False}
    assert sim.lit() == {"PARK": "blue"}


def test_repeated_selection_pulses_relay_again():
    sim = Sim().boot()
    sim.press("DRIVE")
    sim.press("DRIVE")
    assert sim.pulses() == [("DRIVE", 0.5), ("DRIVE", 0.5)]
    assert sim.lit() == {"DRIVE": "blue"}


def test_park_at_boot_with_brake_disengaged_engages_brake_and_lights_park():
    sim = Sim(brake="disengaged").boot()
    sim.press("PARK")
    assert sim.brake_outputs() == {"engage": True, "disengage": False}
    assert sim.lit() == {"PARK": "blue"}


def test_boot_with_brake_disengaged_pulses_no_relay():
    # NEUTRAL at boot is a display state only; nothing is actuated.
    sim = Sim(brake="disengaged").boot()
    assert sim.pulses() == []


def test_invalid_brake_sensors_leave_triggers_low():
    sim = Sim(brake="invalid").boot()
    assert sim.brake_outputs() == {"engage": False, "disengage": False}
    assert sim.lit() == {"NEUTRAL": "blue"}


def test_both_brake_sensors_high_treated_as_engaged():
    sim = Sim(brake="both").boot()
    assert sim.brake_outputs() == {"engage": True, "disengage": False}
    assert sim.lit() == {"PARK": "blue"}
