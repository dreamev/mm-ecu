"""Fake `adafruit_motor.servo` that fails the way the real library does."""

instances = []


def reset():
    instances.clear()


class Servo:
    def __init__(self, pwm_out, *, actuation_range=180, min_pulse=750, max_pulse=2250):
        self.pwm_out = pwm_out
        self.actuation_range = actuation_range
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self._angle = None
        self.history = []
        instances.append(self)

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, new_angle):
        if new_angle is not None and (new_angle < 0 or new_angle > self.actuation_range):
            raise ValueError("Angle out of range")
        self._angle = new_angle
        self.history.append(new_angle)
