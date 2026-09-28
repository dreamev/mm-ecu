"""Main-loop orchestration: CAN in, dispatch, keypad lifecycle, CAN out."""

from mmecu import battery, keypad, log
from mmecu.can import Outbox
from mmecu.drivetrain import DriveState

LISTEN_IDS = (battery.HV_BUS_STATUS_ID, keypad.HEARTBEAT_ID, keypad.KEY_STATE_ID, keypad.SDO_RESPONSE_ID)
# How long to wait for the keypad's SDO key-state reply before trusting key frames alone
BASELINE_TIMEOUT_SECONDS = 1.0


class Application:
    """One `tick()` per main-loop iteration: receive at most one frame, send at most one."""

    def __init__(self, bus, pad, controller, gauge, clock):
        self.bus = bus
        self.clock = clock
        self._baseline_deadline = None
        self.pad = pad
        self.controller = controller
        self.gauge = gauge
        self.outbox = Outbox()
        self._pad_started = False
        self._bus_state = None
        self._handlers = {
            keypad.HEARTBEAT_ID: self._on_heartbeat,
            keypad.KEY_STATE_ID: self._on_key_state,
            keypad.SDO_RESPONSE_ID: self._on_sdo_response,
            battery.HV_BUS_STATUS_ID: self._on_hv_bus_status,
        }

    def tick(self):
        self._watch_bus_state()
        message = self.bus.receive()
        if message is not None:
            self._dispatch(message)
        self._ensure_pad_started()
        self._check_baseline_timeout()
        if self.pad.leds_dirty:
            payload = self.pad.led_payload()
            self.outbox.push(keypad.LED_ID, payload)
            log.event("leds", payload="".join(f"{byte:02x}" for byte in payload))
        frame = self.outbox.pop()
        if frame is not None:
            self.bus.send(*frame)

    def _watch_bus_state(self):
        state = self.bus.state
        if state != self._bus_state:
            log.event("can_bus", state=state)
            self._bus_state = state

    def _dispatch(self, message):
        handler = self._handlers.get(message.id)
        if handler is None:
            log.info(f"unexpected CAN message 0x{message.id:03x}: {message.data}")
        else:
            handler(message.data)

    def _ensure_pad_started(self):
        # Always start once at boot: after an ECU-only reset the pad is still
        # Operational but showing LEDs from before the reset.
        if self._pad_started and not self.pad.needs_start():
            return
        if not self._pad_started:
            log.event(
                "ecu_start",
                drive=DriveState.NAMES[self.controller.drive_state],
                brake=int(self.controller.parking_brake.engaged),
            )
        log.event("keypad_start", reason=self.pad.state)
        self.outbox.push(keypad.NMT_ID, keypad.NMT_START_ALL_NODES)
        self.outbox.push(keypad.SDO_REQUEST_ID, keypad.SDO_READ_KEY_STATE)
        self._baseline_deadline = self.clock() + BASELINE_TIMEOUT_SECONDS
        self.pad.mark_started()
        self.controller.keypad_restarted()
        self._pad_started = True

    def _check_baseline_timeout(self):
        if self.pad.baseline_pending and self._baseline_deadline is not None and self.clock() > self._baseline_deadline:
            log.warning("keypad did not answer the key-state SDO read; baseline from key frames instead")
            self._baseline_deadline = None
            self.pad.baseline_timed_out()

    def _on_sdo_response(self, data):
        held = keypad.decode_key_state_reply(data)
        if held is not None and self.pad.baseline_pending:
            self.pad.set_baseline(held, "sdo")

    def _on_heartbeat(self, data):
        self.pad.on_heartbeat(data)

    def _on_key_state(self, data):
        held = keypad.decode_pressed_keys(data)
        if held is None:
            log.warning(f"short key-state payload: {data}")
            return
        pressed, released = self.pad.key_edges(held)
        for key in released:
            self.controller.key_released(key)
        for key in pressed:
            self.controller.key_pressed(key)

    def _on_hv_bus_status(self, data):
        volts = battery.decode_hv_bus_voltage(data)
        if volts is None:
            log.warning(f"short HV bus payload: {data}")
            return
        self.gauge.show(battery.charge_fraction(volts))
