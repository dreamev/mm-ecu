VENV := .venv
BIN := $(VENV)/bin

.PHONY: help setup test lint fmt check deploy watch console qa

help:  ## list targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

$(BIN)/pytest:
	python3 -m venv $(VENV)
	$(BIN)/pip install -q pytest ruff pyserial

setup: $(BIN)/pytest  ## create the local venv with pytest, ruff, pyserial

test: setup  ## run the test suite against fake hardware
	$(BIN)/pytest

lint: setup  ## lint and check formatting
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

fmt: setup  ## autofix lint and format
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

check: test lint  ## everything CI would run

deploy: check  ## test, then copy firmware to the CIRCUITPY drive
	./sync.sh

watch:  ## redeploy on every file change (no tests)
	./sync.sh --watch

console:  ## serial console (override PORT=/dev/...)
	screen $${PORT:-$$(ls /dev/tty.usbmodem* /dev/ttyACM* 2>/dev/null | head -1)} 115200

qa: setup  ## guided hardware QA on the real keypad (ARGS="--only drive -v", PORT=/dev/...)
	$(BIN)/python -m qa $${PORT:+--port $$PORT} $(ARGS)
