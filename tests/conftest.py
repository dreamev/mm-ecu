import code  # noqa: F401  stdlib; bind it before the repo root (with its code.py) is on sys.path
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
# Appended, never prepended: the firmware's code.py must not shadow stdlib `code`.
for path in (os.path.join(HERE, "fakes"), os.path.dirname(HERE)):
    if path not in sys.path:
        sys.path.append(path)

import canio  # noqa: E402  fake, from tests/fakes
import digitalio  # noqa: E402
from adafruit_motor import servo  # noqa: E402

from mmecu import log  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_fake_hardware():
    canio.reset()
    digitalio.reset()
    servo.reset()
    yield
    log.set_event_sink(print)
