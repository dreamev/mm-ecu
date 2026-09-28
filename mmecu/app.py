"""Main-loop orchestration: CAN in, dispatch, keypad lifecycle, CAN out."""

from mmecu import battery, keypad, log
from mmecu.can import Outbox

LISTEN_IDS = (battery.HV_BUS_STATUS_ID, keypad.HEARTBEAT_ID, keypad.KEY_STATE_ID)


class Application:
    """One `tick()` per main-loop iteration: receive at most one frame, send at most one."""

    def __init__(self, bus, pad, controller, gauge):
        self.bus = bus
        self.pad = pad
        self.controller = controller
        self.gauge = gauge
        self.outbox = Outbox()
        self._pad_started = False
        self._bus_state = None
        self._handlers = {
            keypad.HEARTBEAT_ID: self._on_heartbeat,
            keypad.KEY_STATE_ID: self._on_key_state,
            battery.HV_BUS_STATUS_ID: self._on_hv_bus_status,
        }

    def tick(self):
        self._watch_bus_state()
        message = self.bus.receive()
        if message is not None:
            self._dispatch(message)
        self._ensure_pad_started()
        if self.pad.leds_dirty:
            self.outbox.push(keypad.LED_ID, self.pad.led_payload())
        frame = self.outbox.pop()
        if frame is not None:
            self.bus.send(*frame)

    def _watch_bus_state(self):
        state = self.bus.state
        if state != self._bus_state:
            log.info(f"CAN bus state: {state}")
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
        self.outbox.push(keypad.NMT_ID, keypad.NMT_START_ALL_NODES)
        self.pad.mark_started()
        self.controller.keypad_restarted()
        self._pad_started = True

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
