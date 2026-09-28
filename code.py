# mm-ecu entry point. CircuitPython runs this file at boot; all logic is in mmecu/.
# Hardware references (datasheets, serial console) are in readme.md.

from mmecu import hardware, log

log.set_level(log.WARNING)
log.info("INIT: starting Feather M4")
can_transceiver_pins = hardware.enable_can_transceiver()
application = hardware.build_application()

while True:
    application.tick()
