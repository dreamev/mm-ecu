"""`python -m qa`: interactive hardware QA against the physical keypad and vehicle I/O."""

import argparse
import datetime
import os
import sys

from qa.console import SerialConsole, TerminalUI, find_port
from qa.runner import PASS, HardwareActor, Runner, report_markdown, run_outcome
from qa.steps import GROUPS, STEPS

REPORT_DIR = "qa-reports"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m qa", description=__doc__)
    parser.add_argument("--port", help="serial port (default: auto-detect the Feather)")
    parser.add_argument("--only", help=f"comma-separated groups to run ({', '.join(GROUPS)}); startup always runs")
    parser.add_argument("--list", action="store_true", help="list steps and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="show every firmware event and console line")
    args = parser.parse_args(argv)

    steps = STEPS
    if args.only:
        groups = set(args.only.split(",")) | {"startup"}
        steps = [step for step in STEPS if step.group in groups]
    if args.list:
        for step in steps:
            print(f"{step.group:8} {step.id:26} {step.instruction}")
        return 0

    port = args.port or find_port()
    if port is None:
        print("No Feather serial port found; pass --port.", file=sys.stderr)
        return 2
    print(f"Using {port}. Close any other serial console (screen/make console) first.", flush=True)
    try:
        console = SerialConsole(port)
    except OSError as error:  # pyserial's SerialException is an OSError
        print(f"Cannot open {port}: {error}", file=sys.stderr)
        return 2
    ui = TerminalUI(verbose=args.verbose)
    runner = Runner(console, HardwareActor(console), ui)
    started_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        runner.run(steps)
    except KeyboardInterrupt:
        print("\nInterrupted; writing partial report.")
    finally:
        console.close()

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, "qa-" + started_at.replace(":", "").replace(" ", "-") + ".md")
    with open(path, "w") as report:
        report.write(report_markdown(runner.results, started_at, steps))
    outcome = run_outcome(runner.results, steps)
    print(f"\n{outcome}: {len(runner.results)} of {len(steps)} steps run. Report: {path}")
    return 0 if outcome == PASS else 1


if __name__ == "__main__":
    sys.exit(main())
