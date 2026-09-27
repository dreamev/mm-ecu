"""HV bus voltage (0x126) to servo gauge."""

import pytest

from tests.sim import Sim


def test_gauge_centers_at_boot():
    sim = Sim().boot()
    assert sim.gauge.angle == 88


def test_first_reading_moves_gauge_immediately():
    sim = Sim().boot()
    sim.hv_bus(362.5)  # half way between 325 V and 400 V
    assert sim.gauge.angle == pytest.approx(59.5)


def test_gauge_then_moves_only_every_hundredth_reading():
    sim = Sim().boot()
    sim.hv_bus(362.5)
    sim.hv_bus(400, count=99)
    assert sim.gauge.angle == pytest.approx(59.5)
    sim.hv_bus(400)
    assert sim.gauge.angle == pytest.approx(119)


def test_voltage_below_range_pins_gauge_to_empty():
    sim = Sim().boot()
    sim.hv_bus(300)
    assert sim.gauge.angle == 0


def test_voltage_above_range_pins_gauge_to_full():
    sim = Sim().boot()
    sim.hv_bus(480)
    assert sim.gauge.angle == pytest.approx(119)


def test_short_hv_bus_payload_is_ignored():
    sim = Sim().boot()
    sim.receive(0x126, [0x10])
    sim.tick()
    assert sim.gauge.angle == 88
