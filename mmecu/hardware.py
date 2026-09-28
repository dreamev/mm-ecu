"""Feather M4 CAN wiring: the only module besides code.py that touches hardware."""

import time

import board
import canio
import digitalio
import pwmio
from adafruit_motor import servo

from mmecu import log
from mmecu.actions import VehicleActions
from mmecu.app import LISTEN_IDS, Application
from mmecu.battery import BatteryGauge
from mmecu.controller import VehicleController
from mmecu.drivetrain import DriveState, Shifter
from mmecu.keypad import Keypad
from mmecu.parking_brake import ParkingBrake

CAN_BAUDRATE = 500_000
CAN_LISTEN_TIMEOUT = 0.1

SHIFT_RELAY_PINS = {
    DriveState.REVERSE: board.D11,
    DriveState.NEUTRAL: board.D12,
    DriveState.DRIVE: board.D13,
}
BRAKE_ENGAGED_SENSOR_PIN = board.D10
BRAKE_DISENGAGED_SENSOR_PIN = board.D9
BRAKE_ENGAGE_PIN = board.D6
BRAKE_DISENGAGE_PIN = board.D5
GAUGE_PIN = board.A1


class CanBus:
    """canio.CAN plus a filtered listener, speaking (can_id, payload)."""

    def __init__(self, listen_ids):
        self._can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=CAN_BAUDRATE, auto_restart=True)
        self._listener = self._can.listen(
            matches=[canio.Match(can_id) for can_id in listen_ids], timeout=CAN_LISTEN_TIMEOUT
        )

    @property
    def state(self):
        return self._can.state

    def receive(self):
        return self._listener.receive()

    def send(self, can_id, data):
        log.debug(f"sending CAN 0x{can_id:03x}: {data}")
        self._can.send(canio.Message(id=can_id, data=data))


def output_pin(pin, value=False):
    io = digitalio.DigitalInOut(pin)
    io.switch_to_output(value=value)
    return io


def input_pin(pin, pull=digitalio.Pull.UP):
    io = digitalio.DigitalInOut(pin)
    io.switch_to_input(pull=pull)
    return io


def enable_can_transceiver():
    """Wake the CAN transceiver; returns the pins so they stay referenced."""
    pins = []
    if hasattr(board, "CAN_STANDBY"):
        pins.append(output_pin(board.CAN_STANDBY, False))
    if hasattr(board, "BOOST_ENABLE"):
        pins.append(output_pin(board.BOOST_ENABLE, True))
    return pins


def build_gauge_servo():
    pwm = pwmio.PWMOut(GAUGE_PIN, duty_cycle=2**15, frequency=50)
    return servo.Servo(pwm, min_pulse=500, max_pulse=2500)


def build_application(sleep=time.sleep, clock=time.monotonic, actions=None):
    pad = Keypad()
    shifter = Shifter({state: output_pin(pin) for state, pin in SHIFT_RELAY_PINS.items()}, sleep)
    parking_brake = ParkingBrake(
        input_pin(BRAKE_ENGAGED_SENSOR_PIN),
        input_pin(BRAKE_DISENGAGED_SENSOR_PIN),
        output_pin(BRAKE_ENGAGE_PIN),
        output_pin(BRAKE_DISENGAGE_PIN),
    )
    controller = VehicleController(pad, shifter, parking_brake, actions or VehicleActions(), clock)
    gauge = BatteryGauge(build_gauge_servo())
    return Application(CanBus(LISTEN_IDS), pad, controller, gauge)
