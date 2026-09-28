"""code.py boots the transceiver, builds the app and ticks it forever."""

import os
import runpy

import digitalio
import pytest

from mmecu import hardware

CODE_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code.py")


class _StopLoop(Exception):
    pass


def test_code_py_wakes_transceiver_and_ticks_application(monkeypatch):
    ticks = []

    class App:
        def tick(self):
            ticks.append(1)
            if len(ticks) == 3:
                raise _StopLoop

    monkeypatch.setattr(hardware, "build_application", lambda: App())
    with pytest.raises(_StopLoop):
        runpy.run_path(CODE_PY, run_name="__main__")
    assert len(ticks) == 3
    assert digitalio.pins["CAN_STANDBY"].value is False
    assert digitalio.pins["BOOST_ENABLE"].value is True


def test_real_application_builds_and_ticks_with_fake_hardware():
    app = hardware.build_application(sleep=lambda seconds: None)
    app.tick()


def test_default_actions_are_logging_stubs_for_every_key():
    from tests.sim import KEYS, key_state_payload

    app = hardware.build_application(sleep=lambda seconds: None)
    for name in KEYS:
        for payload in (key_state_payload(name), [0, 0]):
            app.bus._listener.inbox.append(canio_message(payload))
            app.tick()


def canio_message(payload):
    import canio

    return canio.Message(0x195, bytes(payload))
