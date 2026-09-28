"""Vehicle actions the keypad can request that are not wired to hardware yet.

Each method is a stub that only logs. Implement one by sending the CAN frame or
driving the pin it needs; key handling and LEDs in controller.py already call it.
See lode/keypad/button-behaviors.md.
"""

from mmecu import log


class PowerMode:
    LOW = "low"  # F1: slow mode, low power and regen
    HIGH = "high"  # F2: fast mode, high power and regen


class VehicleActions:
    def set_hazard(self, on):
        log.info(f"TODO set_hazard({on})")

    def set_exhaust_sound(self, on):
        log.info(f"TODO set_exhaust_sound({on})")

    def set_power_mode(self, mode):
        """PowerMode.LOW or PowerMode.HIGH: sets both drive power and regen level."""
        log.info(f"TODO set_power_mode({mode})")

    def set_regen(self, on):
        log.info(f"TODO set_regen({on})")

    def set_cruise(self, on):
        """Engage/disengage cruise (openpilot)."""
        log.info(f"TODO set_cruise({on})")

    def adjust_cruise_speed(self, direction, held_seconds):
        """direction +1 (speed up) or -1 (slow down); held_seconds is how long the key was held."""
        log.info(f"TODO adjust_cruise_speed({direction}, {held_seconds})")
