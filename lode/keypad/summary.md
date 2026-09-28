# Keypad domain

The Blink Marine PKP-2600-SI is the driver's only input device. The ECU keeps
the keypad Operational, turns key-state frames into vehicle actions, and owns the
LED model (the pad has no memory of colors across reboots).

```mermaid
flowchart LR
  HB[0x715 heartbeat] --> NS[node state machine]
  NS -->|needs start| NMT[0x000 NMT start + LED refresh]
  KS[0x195 key state] --> Dispatch --> LED[LED model] --> RP[0x215 LED frame]
```

- Wire protocol, bit layouts, node state machine: [can-protocol.md](can-protocol.md)
- Per-key behavior and requirement gaps: [button-behaviors.md](button-behaviors.md)
- Vendor manual digest, defaults, required keypad config: [spec-reference.md](spec-reference.md)
