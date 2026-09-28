"""Drive-state selection via pulsed shift relays."""

from mmecu import log

PULSE_SECONDS = 0.5


class DriveState:
    PARK = 0
    REVERSE = 1
    NEUTRAL = 2
    DRIVE = 3

    NAMES = ("PARK", "REVERSE", "NEUTRAL", "DRIVE")


class Shifter:
    """Requests REVERSE/NEUTRAL/DRIVE from the drive unit by pulsing one relay.

    The pulse blocks on purpose: two relays must never be high at once, and a
    blocking pulse makes overlapping requests impossible.
    """

    def __init__(self, relays, sleep):
        self._relays = relays
        self._sleep = sleep

    def pulse(self, state):
        relay = self._relays.get(state)
        if relay is None:
            log.info(f"no shift relay for drive state {state}")
            return
        relay.value = True
        self._sleep(PULSE_SECONDS)
        relay.value = False
        log.event("relay", state=DriveState.NAMES[state])
