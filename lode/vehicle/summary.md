# Vehicle domain

The physical systems the ECU commands or observes.

```mermaid
flowchart LR
  Ctl[VehicleController] --> Shifter[shift relays] & Brake[parking brake]
  HV[0x126 HV bus] --> Gauge[battery gauge]
```

- [drive-selection.md](drive-selection.md): PRND radio group, relay pulses, parking brake
- [battery-gauge.md](battery-gauge.md): voltage decode, clamping, servo throttling
- [drive-unit-can.md](drive-unit-can.md): Tesla bus speed (500k), the abandoned CAN-shift attempt and why it likely failed
