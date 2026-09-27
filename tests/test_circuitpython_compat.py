"""Static guard: firmware must stay inside the CircuitPython 7 language/library subset."""

import ast
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.join(ROOT, "mmecu")
FIRMWARE = [os.path.join(ROOT, "code.py")] + [
    os.path.join(PACKAGE, name) for name in sorted(os.listdir(PACKAGE)) if name.endswith(".py")
]
ALLOWED_MODULES = {"time", "board", "canio", "digitalio", "pwmio", "adafruit_motor", "micropython", "mmecu"}
HARDWARE_MODULES = {"board", "canio", "digitalio", "pwmio", "adafruit_motor"}
HARDWARE_ALLOWED_IN = {"code.py", "hardware.py"}


def _tree(path):
    with open(path) as f:
        return ast.parse(f.read(), path)


def _imported_roots(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            yield node.module.split(".")[0]


@pytest.mark.parametrize("path", FIRMWARE, ids=os.path.basename)
def test_only_circuitpython_modules_are_imported(path):
    assert set(_imported_roots(_tree(path))) <= ALLOWED_MODULES


@pytest.mark.parametrize("path", FIRMWARE, ids=os.path.basename)
def test_hardware_modules_only_imported_at_the_edge(path):
    if os.path.basename(path) not in HARDWARE_ALLOWED_IN:
        assert not set(_imported_roots(_tree(path))) & HARDWARE_MODULES


@pytest.mark.parametrize("path", FIRMWARE, ids=os.path.basename)
def test_no_unsupported_syntax(path):
    for node in ast.walk(_tree(path)):
        assert not isinstance(node, (ast.AnnAssign, ast.NamedExpr, ast.Match)), f"{path}:{node.lineno}"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args.args + node.args.kwonlyargs + node.args.posonlyargs
            assert node.returns is None and all(a.annotation is None for a in args), f"{path}:{node.lineno}"
