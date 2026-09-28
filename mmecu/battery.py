"""Tesla HV bus voltage to a servo state-of-charge gauge."""

from mmecu import log

# BO_ 294 DI_hvBusStatus: 3 VEH
#   SG_ DI_voltage : 0|10@1+ (0.5,0) [0|500] "V"
#   SG_ DI_current : 10|11@1+ (1,0) [0|2047] "A"
HV_BUS_STATUS_ID = 0x126

# TODO: calibrate against the real pack
EMPTY_VOLTS = 325
FULL_VOLTS = 400


def decode_hv_bus_voltage(data):
    """DI_voltage in volts; None if the payload is short."""
    if len(data) < 2:
        return None
    return (data[0] | (data[1] & 0x03) << 8) * 0.5


def charge_fraction(volts):
    """State of charge in [0, 1], clamped so the gauge can never leave its range."""
    fraction = (volts - EMPTY_VOLTS) / (FULL_VOLTS - EMPTY_VOLTS)
    return min(max(fraction, 0.0), 1.0)


class BatteryGauge:
    """Servo needle. Moves on the first reading, then every UPDATE_EVERY readings to avoid jitter."""

    MIN_ANGLE = 57
    MAX_ANGLE = 119
    UPDATE_EVERY = 100

    def __init__(self, servo):
        self._servo = servo
        self._servo.angle = (self.MAX_ANGLE + self.MIN_ANGLE) / 2
        self._readings = self.UPDATE_EVERY - 1

    def show(self, fraction):
        self._readings += 1
        if self._readings >= self.UPDATE_EVERY:
            angle = self.MAX_ANGLE * fraction
            self._servo.angle = angle
            log.event("gauge", fraction=f"{fraction:.3f}", angle=f"{angle:.1f}")
            self._readings = 0
