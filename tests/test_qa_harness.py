"""The hardware QA script, replayed against the simulator.

A virtual tester performs each step's `do` actions on a Sim, so if the firmware's
behavior or events drift from what the QA script expects, this fails here instead
of on the bench.
"""

import pytest

from qa.runner import FAIL, PASS, SKIP, Runner, report_markdown
from qa.steps import STEPS, Saw, Step, hold, release
from tests.sim import Sim


class SimActor:
    """A virtual tester: does exactly what each step instructs, on the simulator."""

    def __init__(self, brake):
        self.brake = brake
        self.sim = None

    def perform(self, step):
        for action in step.do:
            kind, args = action[0], action[1:]
            if kind == "reset_ecu":
                # the keypad stays powered: keys physically held survive the ECU reset
                held = self.sim.physical_held if self.sim else []
                self.sim = Sim(brake=self.brake, held=held).boot()
            elif kind == "hold":
                self.sim.hold(*args)
            elif kind == "release":
                self.sim.release()
            elif kind == "wait":
                self.sim.wait(args[0])
            elif kind == "reboot_pad":
                self.sim.heartbeat("boot_up")
            elif kind == "hv_bus":
                self.sim.hv_bus(args[0])
            else:
                raise AssertionError(f"unknown QA action {kind}")


class SimConsole:
    """The simulator's event lines as if read from the serial port."""

    def __init__(self, actor):
        self.actor = actor
        self.injected = []
        self._sim, self._index = None, 0

    def read_lines(self, timeout):
        lines, self.injected = self.injected, []
        if self.actor.sim is not self._sim:
            self._sim, self._index = self.actor.sim, 0
        if self._sim is not None:
            lines += self._sim.event_lines[self._index :]
            self._index = len(self._sim.event_lines)
        return lines

    def reset_board(self):
        raise AssertionError("the SimActor performs resets")


class AutoUI:
    def __init__(self, answers=None):
        self.answers = answers or {}
        self.said = []

    def say(self, text, style=None):
        self.said.append(text)

    def ask(self, question, choices):
        for prefix, answer in self.answers.items():
            if question.startswith(prefix):
                return answer
        return next(iter(choices))


def _runner(brake="engaged", ui=None, actor=None):
    actor = actor or SimActor(brake)
    return Runner(SimConsole(actor), actor, ui or AutoUI(), settle=0)


@pytest.mark.parametrize("brake", ["engaged", "disengaged"])
def test_full_qa_script_passes_on_simulated_hardware(brake):
    results = _runner(brake).run(STEPS)
    failures = [(r.step.id, r.notes) for r in results if r.status != PASS]
    assert failures == []
    assert len(results) == len(STEPS)


def test_step_ids_are_unique():
    ids = [step.id for step in STEPS]
    assert len(ids) == len(set(ids))


def test_every_key_is_exercised():
    from qa.spec import KEYS

    held = {key for step in STEPS for action in step.do if action[0] == "hold" for key in action[1:]}
    assert held == set(KEYS)


def test_safety_gate_aborts_before_any_step():
    ui = AutoUI({"Is the vehicle safe": "no"})
    runner = _runner(ui=ui)
    assert runner.run(STEPS) == []
    assert runner.actor.sim is None


def _startup_then(step):
    runner = _runner(ui=AutoUI({"Step failed": "c"}))
    runner.run([STEPS[0], step])
    return runner.results[-1]


def test_missing_event_fails_the_step():
    step = Step("never", "t", "Tap F1.", [hold("F1"), release()], [Saw("regen", on=1)], timeout=0.2)
    result = _startup_then(step)
    assert result.status == FAIL and "regen" in result.notes


def test_optional_step_without_events_is_skipped():
    step = Step("gauge", "t", "Wait.", [], [Saw("gauge")], timeout=0.2, optional=True)
    assert _startup_then(step).status == SKIP


def test_tester_rejection_fails_the_step():
    ui = AutoUI({"Confirm": "n", "Step failed": "c"})
    runner = _runner(ui=ui)
    runner.run(STEPS[:1])
    assert runner.results[0].status == FAIL


def test_firmware_traceback_fails_the_step():
    actor = SimActor("engaged")
    runner = _runner(actor=actor, ui=AutoUI({"Step failed": "c"}))
    runner.console.injected = ["Traceback (most recent call last):"]
    runner.run(STEPS[:1])
    assert runner.results[0].status == FAIL
    assert "Traceback" in runner.results[0].notes


def test_quit_stops_the_run_and_keeps_the_failure():
    ui = AutoUI({"Confirm": "n", "Step failed": "q"})
    runner = _runner(ui=ui)
    runner.run(STEPS)
    assert [r.status for r in runner.results] == [FAIL]


def test_report_lists_every_step():
    runner = _runner()
    runner.run(STEPS)
    report = report_markdown(runner.results, "2026-09-28 10:00:00")
    assert f"PASS {len(STEPS)} / FAIL 0 / SKIP 0" in report
    assert all(f"| {step.id} |" in report for step in STEPS)


class ScriptedUI(AutoUI):
    """Answers each prompt from a script, in order (the safety gate is always 'yes')."""

    def __init__(self, answers):
        super().__init__()
        self.script = list(answers)

    def ask(self, question, choices):
        if question.startswith("Is the vehicle safe"):
            return "yes"
        answer = self.script.pop(0)
        assert answer in choices, (question, answer)
        return answer


@pytest.mark.parametrize("step_id, key, color", [("hazard-on", "HAZARD", "yellow"), ("regen-on", "REGEN", "white")])
def test_retrying_a_toggle_step_after_a_rejected_confirmation_does_not_toggle_back(step_id, key, color):
    step = next(s for s in STEPS if s.id == step_id)
    actor = SimActor("engaged")
    ui = ScriptedUI(["y", "n", "r", "y"])  # startup ok; tester rejects, retries, then confirms
    runner = Runner(SimConsole(actor), actor, ui, settle=0)
    runner.run([STEPS[0], step])
    assert [r.status for r in runner.results] == [PASS, PASS]
    assert actor.sim.lit()[key] == color
    assert len(actor.sim.events(step.target and next(iter(step.target)))) == 1  # toggled exactly once
    assert any("already" in line for line in ui.said)


# --- exit status of `python -m qa` (Copilot review: aborted runs must not look like passes) ---
class _NullConsole:
    def __init__(self, port):
        pass

    def read_lines(self, timeout):
        return []

    def reset_board(self):
        pass

    def close(self):
        pass


def _run_main(monkeypatch, tmp_path, ui, run=None):
    import qa.__main__ as cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "SerialConsole", _NullConsole)
    monkeypatch.setattr(cli, "TerminalUI", lambda verbose: ui)
    if run is not None:
        monkeypatch.setattr(cli.Runner, "run", run)
    code = cli.main(["--port", "/dev/fake"])
    (report,) = (tmp_path / "qa-reports").iterdir()
    return code, report.read_text()


def test_declining_the_safety_gate_exits_nonzero(monkeypatch, tmp_path):
    code, report = _run_main(monkeypatch, tmp_path, AutoUI({"Is the vehicle safe": "no"}))
    assert code == 1
    assert "INCOMPLETE" in report


def test_interrupted_run_with_only_passes_exits_nonzero(monkeypatch, tmp_path):
    from qa.runner import Result

    def run(self, steps):
        self.results.append(Result(steps[0], PASS, ""))
        raise KeyboardInterrupt

    code, report = _run_main(monkeypatch, tmp_path, AutoUI(), run)
    assert code == 1
    assert f"INCOMPLETE: 1 of {len(STEPS)} steps run" in report


def test_complete_run_outcomes():
    from qa.runner import Result, run_outcome

    steps = STEPS[:2]
    assert run_outcome([Result(s, PASS, "") for s in steps], steps) == "PASS"
    assert run_outcome([Result(steps[0], PASS, ""), Result(steps[1], SKIP, "")], steps) == "PASS"
    assert run_outcome([Result(steps[0], PASS, ""), Result(steps[1], FAIL, "")], steps) == "FAIL"
    assert run_outcome([Result(steps[0], PASS, "")], steps) == "INCOMPLETE"
