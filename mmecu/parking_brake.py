"""Parking brake: two position sensors, two level-held trigger outputs."""

from mmecu import log


class ParkingBrake:
    def __init__(self, engaged_sensor, disengaged_sensor, engage_out, disengage_out):
        self._engaged_sensor = engaged_sensor
        self._disengaged_sensor = disengaged_sensor
        self._engage_out = engage_out
        self._disengage_out = disengage_out
        self.engaged = False
        self._sync_with_sensors()

    def _sync_with_sensors(self):
        if self._engaged_sensor.value:
            self.engage()
        elif self._disengaged_sensor.value:
            self.disengage()
        else:
            log.error("parking brake sensors report neither engaged nor disengaged")

    def engage(self):
        if not self.engaged:
            self._disengage_out.value = False
            self._engage_out.value = True
            self.engaged = True
            log.event("brake", engaged=1)

    def disengage(self):
        if self.engaged:
            self._engage_out.value = False
            self._disengage_out.value = True
            self.engaged = False
            log.event("brake", engaged=0)
