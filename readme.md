# mm-ecu

CircuitPython firmware for an Adafruit Feather M4 CAN acting as the auxiliary ECU
of an EV conversion. It runs the Blink Marine 12-key CAN keypad, drive
selection (shift relays + parking brake) and a servo battery gauge fed from the
Tesla drive unit. Behavior per key: [REQUIREMENTS.md](REQUIREMENTS.md).

## Layout
```
code.py          entrypoint CircuitPython runs at boot (boot + main loop only)
mmecu/           firmware logic; only mmecu/hardware.py touches pins/CAN
lib/             vendored CircuitPython libraries (adafruit_motor)
tests/           pytest suite running the firmware against fake hardware
tools/           host-side deploy/restore tool (python3 stdlib only)
qa/              host-side hardware QA harness (make qa); not deployed
lode/            project knowledge base (protocols, wiring, design notes)
```

## Development
```
make test        # full suite on CPython, no board needed (~0.1 s)
make lint        # ruff
make deploy      # test + copy firmware to the mounted CIRCUITPY drive (verified); REF=<tag> for a release
make restore     # put the known-good firmware back: deploys tag v1.0.0 (REF=... for another)
make watch       # redeploy on every save (needs fswatch)
make console     # serial console, 115200 baud (PORT=/dev/... to override)
make qa          # guided hardware QA: press what it says, it checks the firmware's events
```
`make qa` walks through every key, the relays, the parking brake, a keypad reboot
and the gauge on the real hardware, and writes a report to `qa-reports/`. It moves the
shift relays and brake, so only run it with the vehicle secured.
The CIRCUITPY drive is auto-detected on macOS and Linux; set `CIRCUITPY=/path`
otherwise. Firmware code must stay within the CircuitPython 7 subset (no
`typing`, `dataclasses`, `enum`, annotations); `make test` enforces this.

## Links
- Adafruit Feather M4 CAN: https://www.adafruit.com/product/4759
- CircuitPython drivers: https://circuitpython.readthedocs.io/projects/bundle/en/latest/drivers.html
- Blink Marine PKP-2600-SI keypad
  - datasheet: https://ss-usa.s3.amazonaws.com/c/308474458/media/1417060ec085e997cc28740285766947/PKP-2600-SI%20Datasheet.pdf
  - CANopen manual: https://ss-usa.s3.amazonaws.com/c/308474458/media/30755e6bc22cc0b7e94093360556784/PKP-2600-SI_CANOpen_UM_REV1.1.pdf
- Serial console on macOS/Linux: https://learn.adafruit.com/adafruit-feather-m4-express-atsamd51/advanced-serial-console-on-mac-and-linux
