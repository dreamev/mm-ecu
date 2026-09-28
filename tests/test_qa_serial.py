"""SerialConsole over a pseudo-terminal, standing in for the Feather's USB serial port."""

import os
import sys

import pytest

pytest.importorskip("serial")
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pty")


@pytest.fixture
def board():
    import pty

    from qa.console import SerialConsole

    controller, device = pty.openpty()
    console = SerialConsole(os.ttyname(device))
    yield controller, console
    console.close()
    os.close(controller)
    os.close(device)


def test_reads_complete_lines_and_keeps_partial_ones(board):
    controller, console = board
    os.write(controller, b"EVT key_down key=5\r\nEVT rel")
    assert [line.strip() for line in console.read_lines(1.0)] == ["EVT key_down key=5"]
    os.write(controller, b"ay state=DRIVE\r\n")
    assert [line.strip() for line in console.read_lines(1.0)] == ["EVT relay state=DRIVE"]


def test_read_times_out_with_no_output(board):
    _, console = board
    assert console.read_lines(0.1) == []


def test_reset_sends_ctrl_c_then_ctrl_d(board):
    controller, console = board
    console.reset_board()
    assert os.read(controller, 16) == b"\x03\x03\x04"
