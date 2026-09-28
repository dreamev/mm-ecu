"""Runs QA steps: instructs the tester, watches firmware events, records results.

Pluggable parts: `console` (read_lines(timeout), reset_board()), `actor` (performs a
step's `do` actions; on hardware the human does, except the reset), and `ui`
(say(text, style), ask(question, choices) -> choice key).
"""

import time

from qa.events import is_firmware_error, parse_line
from qa.steps import update_context

SAFETY_WARNING = (
    "SAFETY: this test pulses the shift relays and moves the parking brake.\n"
    "Only continue if the vehicle cannot move: drive unit disabled, or drive wheels\n"
    "off the ground and the area clear."
)

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


class HardwareActor:
    """On the bench the tester performs every action; only the ECU reset is automated."""

    def __init__(self, console):
        self.console = console

    def perform(self, step):
        for action in step.do:
            if action[0] == "reset_ecu":
                self.console.reset_board()


class Result:
    def __init__(self, step, status, notes):
        self.step, self.status, self.notes = step, status, notes


class Runner:
    def __init__(self, console, actor, ui, settle=1.0, clock=time.monotonic):
        self.console = console
        self.actor = actor
        self.ui = ui
        self.settle = settle
        self.clock = clock
        self.ctx = {}
        self.results = []
        self._errors_between_steps = []

    def run(self, steps):
        self.ui.say(SAFETY_WARNING, "warn")
        if self.ui.ask("Is the vehicle safe to test?", {"yes": "safe, continue", "no": "abort"}) != "yes":
            self.ui.say("Aborted before any test.", "warn")
            return self.results
        for index, step in enumerate(steps, start=1):
            self.ui.say(f"\n[{index}/{len(steps)}] {step.id}", "title")
            result = self._run_with_retry(step)
            self.results.append(result)
            if result.status == "QUIT":
                result.status = FAIL
                break
        return self.results

    def _run_with_retry(self, step):
        while True:
            result = self.run_step(step)
            self.ui.say(f"{result.status}: {step.id}" + (f" ({result.notes})" if result.notes else ""), result.status)
            if result.status != FAIL:
                return result
            choice = self.ui.ask("Step failed.", {"c": "continue", "r": "retry", "q": "quit"})
            if choice == "c":
                return result
            if choice == "q":
                result.status = "QUIT"
                return result

    def run_step(self, step):
        self._read(0)  # drain leftovers into the context before this step starts
        # a crash while idle between steps still fails the next step
        events, errors = [], self._errors_between_steps
        self._errors_between_steps = []
        self.ui.say(step.instruction)
        if step.ready:
            self.ui.ask(step.ready, {"yes": "ready"})
        self.actor.perform(step)
        waiting_for = [check for check in step.expect if not check.final]
        deadline = self.clock() + step.timeout
        while not errors and self.clock() < deadline:
            self._read(0.1, events, errors)
            if all(check.met(events, self.ctx) for check in waiting_for):
                break
        settle_until = self.clock() + self.settle
        while not errors and self.clock() < settle_until:
            self._read(0.1, events, errors)

        if errors:
            return Result(step, FAIL, "firmware error: " + errors[0])
        missing = [str(check) for check in step.expect if not check.met(events, self.ctx)]
        if missing:
            if step.optional and not events:
                return Result(step, SKIP, "no events; not testable in this setup")
            for check in missing:
                self.ui.say(f"  missing: {check}", FAIL)
            return Result(step, FAIL, "missing: " + "; ".join(missing))
        if step.confirm:
            question = step.confirm.format(**self.ctx)
            answer = self.ui.ask(question, {"y": "yes", "n": "no", "s": "skip"})
            if answer == "n":
                return Result(step, FAIL, "tester: not as expected")
            if answer == "s":
                return Result(step, SKIP, "tester skipped")
        return Result(step, PASS, "")

    def _read(self, timeout, events=None, errors=None):
        for line in self.console.read_lines(timeout):
            event = parse_line(line)
            if event is not None:
                update_context(self.ctx, event)
                if events is not None:
                    events.append(event)
                self.ui.say(f"  {line.strip()}", "event")
            elif is_firmware_error(line):
                (self._errors_between_steps if errors is None else errors).append(line.strip())
                self.ui.say(f"  {line.strip()}", FAIL)
            elif line.strip():
                self.ui.say(f"  {line.strip()}", "console")


def report_markdown(results, started_at):
    counts = {status: sum(r.status == status for r in results) for status in (PASS, FAIL, SKIP)}
    lines = [
        f"# mm-ecu hardware QA {started_at}",
        "",
        f"PASS {counts[PASS]} / FAIL {counts[FAIL]} / SKIP {counts[SKIP]}",
        "",
        "| Step | Group | Result | Notes |",
        "|---|---|---|---|",
    ]
    for result in results:
        notes = result.notes.replace("|", "/")
        lines.append(f"| {result.step.id} | {result.step.group} | {result.status} | {notes} |")
    return "\n".join(lines) + "\n"
