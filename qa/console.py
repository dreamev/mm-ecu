"""USB serial console of the Feather (CircuitPython REPL port) and terminal UI."""

import glob
import sys
import time

ADAFRUIT_USB_VID = 0x239A


def find_port():
    """The first Adafruit CircuitPython serial port, else the first USB modem/ACM port."""
    try:
        from serial.tools import list_ports

        for port in list_ports.comports():
            if port.vid == ADAFRUIT_USB_VID:
                return port.device
    except ImportError:
        pass
    candidates = sorted(glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/ttyACM*"))
    return candidates[0] if candidates else None


class SerialConsole:
    def __init__(self, port, baudrate=115200):
        import serial  # host-only dependency (pyserial); see `make setup`

        self._serial = serial.Serial(port, baudrate, timeout=0.05)
        self._buffer = b""

    def read_lines(self, timeout):
        deadline = time.monotonic() + timeout
        lines = []
        while True:
            self._buffer += self._serial.read(self._serial.in_waiting or 1)
            while b"\n" in self._buffer:
                line, self._buffer = self._buffer.split(b"\n", 1)
                lines.append(line.decode("utf-8", errors="replace"))
            if lines or time.monotonic() >= deadline:
                return lines

    def reset_board(self):
        """Ctrl-C stops code.py, Ctrl-D soft-reloads it (CircuitPython REPL controls)."""
        for control in (b"\x03", b"\x03", b"\x04"):
            self._serial.write(control)
            time.sleep(0.3)

    def close(self):
        self._serial.close()


STYLES = {
    "title": "\033[1m",
    "warn": "\033[33m",
    "PASS": "\033[32m",
    "FAIL": "\033[31m",
    "SKIP": "\033[33m",
    "event": "\033[2m",
    "console": "\033[36m",
}


class TerminalUI:
    def __init__(self, verbose=False, stream=sys.stdout):
        self.verbose = verbose
        self.stream = stream
        self.color = stream.isatty()

    def say(self, text, style=None):
        if style in ("event", "console") and not self.verbose:
            return
        if self.color and style in STYLES:
            text = f"{STYLES[style]}{text}\033[0m"
        print(text, file=self.stream, flush=True)

    def ask(self, question, choices):
        options = "/".join(choices)
        labels = ", ".join(f"{key}={label}" for key, label in choices.items())
        while True:
            answer = input(f"{question} [{options}] ({labels}) ").strip().lower()
            if answer in choices:
                return answer
