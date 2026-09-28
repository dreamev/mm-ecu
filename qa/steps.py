"""The QA script: what to ask the tester, and which firmware events prove it worked.

Each Step carries:
- `instruction` for the human,
- `do`, the same actions in machine form (the test suite replays them on the simulator,
  so this script cannot drift from firmware behavior; `reset_ecu` is performed by the
  harness itself on real hardware),
- `expect`, checks against the events and the running context,
- `confirm`, a yes/no question for what only a human can observe.
"""

from qa.spec import DRIVE_KEYS, KEY_NUMBER, decode_leds


# --- actions (`do`) -----------------------------------------------------------
def reset_ecu():
    return ("reset_ecu",)


def hold(*keys):
    return ("hold",) + keys


def release():
    return ("release",)


def wait(seconds):
    return ("wait", seconds)


def reboot_pad():
    return ("reboot_pad",)


def hv_bus(volts):
    return ("hv_bus", volts)


def tap(key):
    return [hold(key), release()]


# --- expectations -------------------------------------------------------------
class Expect:
    final = False  # True: only judged once the step has settled (counts, end state)

    def met(self, events, ctx):
        raise NotImplementedError


def _matches(event, name, fields):
    if event.name != name:
        return False
    for key, want in fields.items():
        have = event.fields.get(key)
        if have is None or not (want(have) if callable(want) else have == str(want)):
            return False
    return True


class Saw(Expect):
    """Some event with this name and field values (a value may be a predicate)."""

    def __init__(self, name, **fields):
        self.name, self.fields = name, fields

    def met(self, events, ctx):
        return any(_matches(event, self.name, self.fields) for event in events)

    def __str__(self):
        return f"event {self.name} {self.fields}" if self.fields else f"event {self.name}"


class Count(Expect):
    """Exactly `n` matching events during the step."""

    final = True

    def __init__(self, n, name, **fields):
        self.n, self.name, self.fields = n, name, fields

    def met(self, events, ctx):
        return sum(_matches(event, self.name, self.fields) for event in events) == self.n

    def __str__(self):
        return f"exactly {self.n} x {self.name} {self.fields}"


class Leds(Expect):
    """The latest LED frame sent to the pad (in any step) shows these colors.

    `colors` may be a function of the context. A step that changes nothing sends no
    frame, so this judges the pad's current state rather than frames in the step.
    """

    final = True

    def __init__(self, colors):
        self.colors = colors

    def expected(self, ctx):
        return self.colors(ctx) if callable(self.colors) else self.colors

    def met(self, events, ctx):
        if "leds" not in ctx:
            return False
        shown = decode_leds(bytes.fromhex(ctx["leds"]))
        return all(shown[key] == color for key, color in self.expected(ctx).items())

    def __str__(self):
        return f"LED frame shows {self.colors if not callable(self.colors) else 'drive state'}"


class State(Expect):
    """The context (built from events) has these values at the end of the step."""

    final = True

    def __init__(self, **values):
        self.values = values

    def met(self, events, ctx):
        return all(ctx.get(key) == str(value) for key, value in self.values.items())

    def __str__(self):
        return f"state {self.values}"


def at_least(minimum):
    return lambda value: float(value) >= minimum


def only_drive_lit(key):
    return {name: "blue" if name == key else "black" for name in DRIVE_KEYS}


def current_drive_lit(ctx):
    return only_drive_lit(ctx.get("drive", "PARK"))


def update_context(ctx, event):
    """Running knowledge of the vehicle, used by ctx-dependent expectations and prompts."""
    if event.name == "ecu_start":
        ctx["drive"], ctx["brake"] = event.fields["drive"], event.fields["brake"]
    elif event.name == "drive":
        ctx["drive"] = event.fields["state"]
    elif event.name == "brake":
        ctx["brake"] = event.fields["engaged"]
    elif event.name == "leds":
        ctx["leds"] = event.fields["payload"]


# --- the script ---------------------------------------------------------------
class Step:
    def __init__(self, id, group, instruction, do, expect, confirm=None, timeout=20, optional=False, ready=None):
        self.id = id
        self.ready = ready  # asked before `do` runs, e.g. "Holding HAZARD?" before an automated reset
        self.group = group
        self.instruction = instruction
        self.do = do
        self.expect = expect
        self.confirm = confirm
        self.timeout = timeout
        self.optional = optional  # a timeout means "not testable here" (SKIP), not FAIL


def _drive_step(key, relay, brake, id=None):
    expect = [Saw("key_down", key=KEY_NUMBER[key]), Leds(only_drive_lit(key)), State(drive=key)]
    expect.append(Count(1, "relay", state=key) if relay else Count(0, "relay"))
    if brake is not None:
        expect.append(State(brake=brake))
    checks = ["only " + key + " lit blue among P/R/N/D"]
    if relay:
        checks.append(f"the {key} shift relay clicked once")
    if brake == 0:
        checks.append("the parking brake is released")
    if brake == 1:
        checks.append("the parking brake is engaged")
    return Step(
        id or f"drive-{key.lower()}",
        "drive",
        f"Tap {key}.",
        tap(key),
        expect,
        confirm="Confirm: " + ", ".join(checks) + ".",
    )


def _toggle_steps(key, event, color, label):
    steps = []
    for on, color_now in ((1, color), (0, "black")):
        state = "on" if on else "off"
        steps.append(
            Step(
                f"{event}-{state}",
                "toggles",
                f"Tap {key} to turn {label} {state}.",
                tap(key),
                [Saw(event, on=on), Leds({key: color_now})],
                confirm=f"Confirm: {key} is {'lit ' + color if on else 'dark'}.",
            )
        )
    return steps


def _hold_step(key, direction, color):
    return Step(
        f"cruise-{'up' if direction > 0 else 'down'}",
        "cruise",
        f"Press and HOLD {key} for about 2 seconds, then release it.",
        [hold(key), wait(2), release()],
        [
            Saw("key_down", key=KEY_NUMBER[key]),
            Saw("key_up", key=KEY_NUMBER[key], held=at_least(1.0)),
            Saw("cruise_adjust", direction=direction, held=at_least(1.0)),
            Leds({key: "black"}),
        ],
        confirm=f"Confirm: {key} was lit {color} while held and went dark on release.",
        timeout=30,
    )


STEPS = (
    [
        Step(
            "startup",
            "startup",
            "Resetting the ECU over USB. Leave the keypad powered.",
            [reset_ecu()],
            [Saw("ecu_start"), Saw("keypad_start"), Saw("keypad_baseline", source="sdo"), Leds(current_drive_lit)],
            confirm="Confirm: the keypad shows only {drive} lit blue among P/R/N/D (brake engaged={brake}).",
            timeout=15,
        ),
        _drive_step("NEUTRAL", relay=True, brake=None),
        _drive_step("DRIVE", relay=True, brake=0),
        _drive_step("REVERSE", relay=True, brake=0),
        _drive_step("PARK", relay=False, brake=1),
    ]
    + _toggle_steps("HAZARD", "hazard", "yellow", "hazard")
    + _toggle_steps("EXHAUST_SOUND", "exhaust_sound", "yellow", "exhaust sound")
    + _toggle_steps("REGEN", "regen", "white", "regen")
    + _toggle_steps("AUTOPILOT_ON", "cruise", "blue", "cruise")
    + [
        Step(
            "power-f2",
            "modes",
            "Tap F2.",
            tap("F2"),
            [Saw("power_mode", mode="high"), Leds({"F2": "yellow", "F1": "black"})],
            confirm="Confirm: F2 is lit yellow and F1 is dark.",
        ),
        Step(
            "power-f1",
            "modes",
            "Tap F1.",
            tap("F1"),
            [Saw("power_mode", mode="low"), Leds({"F1": "cyan", "F2": "black"})],
            confirm="Confirm: F1 is lit cyan and F2 is dark.",
        ),
        _hold_step("AUTOPILOT_SPEED_UP", 1, "green"),
        _hold_step("AUTOPILOT_SPEED_DOWN", -1, "red"),
        Step(
            "held-key-not-retriggered",
            "edges",
            "Press and HOLD DRIVE. While still holding it, tap F2. Then release DRIVE.",
            [hold("DRIVE"), hold("DRIVE", "F2"), hold("DRIVE"), release()],
            [
                Saw("power_mode", mode="high"),
                Saw("key_up", key=KEY_NUMBER["DRIVE"]),
                Count(1, "relay", state="DRIVE"),
                Count(1, "key_down", key=KEY_NUMBER["DRIVE"]),
                State(drive="DRIVE"),
            ],
            confirm="Confirm: the DRIVE relay clicked only once.",
            timeout=30,
        ),
        _drive_step("PARK", relay=False, brake=1, id="drive-park-again"),
        Step(
            "held-through-reset",
            "edges",
            "Press and HOLD HAZARD, and keep holding it. The harness will then reset the ECU.",
            [hold("HAZARD"), reset_ecu()],
            [Saw("ecu_start"), Saw("keypad_baseline", source="sdo", keys=KEY_NUMBER["HAZARD"])],
            ready="Are you holding HAZARD down now?",
            timeout=15,
        ),
        Step(
            "held-key-ignored-after-reset",
            "edges",
            "Still holding HAZARD, tap F2. Then release HAZARD.",
            [hold("HAZARD", "F2"), hold("HAZARD"), release()],
            # HAZARD is in the baseline, so it was never "pressed" and emits no key_up either
            [Saw("power_mode", mode="high"), Count(0, "hazard")],
            confirm="Confirm: HAZARD stayed dark the whole time (a key held through a reset must not fire).",
            timeout=30,
        ),
        Step(
            "keypad-reboot",
            "keypad",
            "Disconnect the keypad's power for ~3 seconds, then reconnect it.",
            [reboot_pad()],
            [Saw("keypad_state", state="Boot-up"), Saw("keypad_start"), Leds(current_drive_lit)],
            confirm="Confirm: after the keypad's start-up light show, only {drive} is lit among P/R/N/D.",
            timeout=60,
        ),
        Step(
            "gauge",
            "gauge",
            "Make sure the drive unit is powered and broadcasting 0x126. Waiting for a gauge update...",
            [hv_bus(362.5)],
            [Saw("gauge")],
            confirm="Confirm: the gauge needle matches the pack's charge.",
            timeout=30,
            optional=True,
        ),
    ]
)

GROUPS = []
for _step in STEPS:
    if _step.group not in GROUPS:
        GROUPS.append(_step.group)
