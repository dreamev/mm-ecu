"""Deploying to / restoring the CIRCUITPY drive, using a temp dir as the drive."""

import os
import subprocess

import pytest

from tools import circuitpy
from tools.circuitpy import DriveError


def _write(root, rel, data):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _read(root, rel):
    with open(os.path.join(root, rel), "rb") as f:
        return f.read()


def _snapshot(root):
    return {rel: _read(root, rel) for rel in circuitpy.walk_files(root)}


def _git_show(ref, path):
    return subprocess.run(
        ["git", "-C", circuitpy.REPO, "show", f"{ref}:{path}"], capture_output=True, check=True
    ).stdout


@pytest.fixture
def v1():
    try:
        _git_show("v1.0.0", "code.py")
    except subprocess.CalledProcessError:
        pytest.skip("v1.0.0 tag not fetched (git fetch --tags)")
    return "v1.0.0"


def test_default_restore_target_is_the_v1_tag_not_a_moving_branch(v1):
    assert v1 == circuitpy.RESTORE_REF
    subprocess.run(["git", "-C", circuitpy.REPO, "rev-parse", "--verify", f"refs/tags/{v1}"], check=True)


@pytest.fixture
def drive(tmp_path):
    """A CIRCUITPY drive with board-owned, OS and client files."""
    root = str(tmp_path / "CIRCUITPY")
    _write(root, "boot_out.txt", b"Adafruit CircuitPython 7.0.0 on 2021-09-20; Adafruit Feather M4 CAN\n")
    _write(root, "code.py", b"# whatever the board runs today\n")
    _write(root, "notes.txt", b"client notes")
    _write(root, ".fseventsd/fseventsd-uuid", b"os")
    return root


def test_deploy_working_tree_installs_and_verifies(drive):
    written = circuitpy.deploy(drive)
    assert written[-1] == "code.py"
    assert _read(drive, "code.py") == _read(circuitpy.REPO, "code.py")
    assert os.path.isfile(os.path.join(drive, "mmecu", "app.py"))
    assert os.path.isfile(os.path.join(drive, "lib", "adafruit_motor", "servo.mpy"))


def test_restore_v1_puts_back_the_single_file_firmware(drive, v1):
    circuitpy.deploy(drive)
    circuitpy.deploy_ref(drive, v1)
    assert _read(drive, "code.py") == _git_show(v1, "code.py")
    assert b"class Application" in _read(drive, "code.py")
    assert not os.path.exists(os.path.join(drive, "mmecu"))
    assert os.path.isfile(os.path.join(drive, "lib", "adafruit_motor", "servo.mpy"))


def test_deploy_after_restore_brings_the_package_back(drive, v1):
    circuitpy.deploy_ref(drive, v1)
    circuitpy.deploy(drive)
    assert os.path.isfile(os.path.join(drive, "mmecu", "app.py"))


def test_deploying_a_ref_matches_that_commit_exactly(drive):
    circuitpy.deploy_ref(drive, "HEAD")
    for rel in ("code.py", "mmecu/app.py", "mmecu/keypad.py"):
        assert _read(drive, rel) == _git_show("HEAD", rel)


def test_other_drive_files_are_left_alone(drive, v1):
    circuitpy.deploy(drive)
    circuitpy.deploy_ref(drive, v1)
    assert _read(drive, "notes.txt") == b"client notes"
    assert _read(drive, ".fseventsd/fseventsd-uuid") == b"os"
    assert b"CircuitPython 7.0.0" in _read(drive, "boot_out.txt")


def test_stale_package_modules_are_removed(drive):
    _write(drive, "mmecu/old_module.py", b"stale")
    circuitpy.deploy(drive)
    assert not os.path.exists(os.path.join(drive, "mmecu", "old_module.py"))


def test_unknown_ref_fails_before_touching_the_drive(drive):
    before = _snapshot(drive)
    with pytest.raises(DriveError, match="cannot read git ref"):
        circuitpy.deploy_ref(drive, "no-such-branch")
    assert _snapshot(drive) == before


@pytest.mark.parametrize("operation", ["deploy", "deploy_ref"])
def test_never_touches_a_directory_that_is_not_a_circuitpy_drive(tmp_path, operation):
    not_a_drive = str(tmp_path / "home")
    _write(not_a_drive, "important.txt", b"keep me")
    with pytest.raises(DriveError, match="boot_out.txt"):
        getattr(circuitpy, operation)(not_a_drive, *(["HEAD"] if operation == "deploy_ref" else []))
    assert _snapshot(not_a_drive) == {"important.txt": b"keep me"}


def test_code_py_is_written_last(monkeypatch, drive):
    written = []
    real_copy = circuitpy._copy
    monkeypatch.setattr(circuitpy, "_copy", lambda source, target: (written.append(target), real_copy(source, target)))
    circuitpy.deploy(drive)
    assert os.path.basename(written[-1]) == "code.py"
    assert sum(os.path.basename(path) == "code.py" for path in written) == 1


def test_a_bad_write_is_reported(monkeypatch, drive):
    monkeypatch.setattr(
        circuitpy, "_copy", lambda source, target: _write(os.path.dirname(target), os.path.basename(target), b"x")
    )
    with pytest.raises(DriveError, match="board unchanged"):
        circuitpy.deploy(drive)


def test_explicit_drive_is_never_swapped_for_an_auto_detected_one(monkeypatch, tmp_path, drive):
    monkeypatch.setattr(circuitpy, "AUTO_DETECT_PATHS", [drive])  # a drive is available to auto-detect...
    monkeypatch.delenv("CIRCUITPY", raising=False)
    with pytest.raises(DriveError, match="not found"):
        circuitpy.find_drive(str(tmp_path / "typo"))  # ...but the caller asked for this one
    monkeypatch.setenv("CIRCUITPY", str(tmp_path / "typo"))
    with pytest.raises(DriveError, match="not found"):
        circuitpy.find_drive()
    monkeypatch.delenv("CIRCUITPY")
    assert circuitpy.find_drive() == drive


def test_cli_restore_and_deploy(drive, v1, capsys):
    assert circuitpy.main(["--drive", drive, "deploy"]) == 0
    assert circuitpy.main(["--drive", drive, "restore", "--yes"]) == 0
    assert "Restored git 'v1.0.0'" in capsys.readouterr().out
    assert not os.path.exists(os.path.join(drive, "mmecu"))


def test_cli_restore_asks_first(monkeypatch, drive, v1):
    before = _snapshot(drive)
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    assert circuitpy.main(["--drive", drive, "restore"]) == 1
    assert _snapshot(drive) == before


def test_cli_reports_errors_without_traceback(tmp_path, capsys):
    assert circuitpy.main(["--drive", str(tmp_path), "deploy"]) == 2
    assert "refusing" in capsys.readouterr().err


# --- staged deploy (Copilot review r4126150691) ---
def _fail_copy_of(monkeypatch, name):
    real_copy = circuitpy._copy

    def flaky(source, target):
        if os.path.basename(target) == name:
            raise OSError(28, "No space left on device")
        real_copy(source, target)

    monkeypatch.setattr(circuitpy, "_copy", flaky)


def test_interrupted_deploy_leaves_the_running_firmware_untouched(monkeypatch, drive):
    circuitpy.deploy(drive)  # the board runs the package firmware
    before = _snapshot(drive)
    _fail_copy_of(monkeypatch, "keypad.py")
    with pytest.raises(OSError):
        circuitpy.deploy(drive)
    assert _snapshot(drive) == before
    assert not os.path.exists(os.path.join(drive, circuitpy.STAGING))


def test_interrupted_restore_leaves_the_running_firmware_untouched(monkeypatch, drive, v1):
    circuitpy.deploy(drive)
    before = _snapshot(drive)
    _fail_copy_of(monkeypatch, "code.py")
    with pytest.raises(OSError):
        circuitpy.deploy_ref(drive, v1)
    assert _snapshot(drive) == before


def test_bad_staged_copy_leaves_the_board_untouched(monkeypatch, drive):
    circuitpy.deploy(drive)
    before = _snapshot(drive)
    real_copy = circuitpy._copy
    monkeypatch.setattr(
        circuitpy,
        "_copy",
        lambda s, t: _write(os.path.dirname(t), os.path.basename(t), b"x") if t.endswith(".py") else real_copy(s, t),
    )
    with pytest.raises(DriveError, match="board unchanged"):
        circuitpy.deploy(drive)
    assert _snapshot(drive) == before


def test_leftover_staging_from_an_earlier_failure_is_cleaned_up(drive):
    _write(drive, circuitpy.STAGING + "/mmecu/junk.py", b"stale")
    circuitpy.deploy(drive)
    assert not os.path.exists(os.path.join(drive, circuitpy.STAGING))
    assert not os.path.exists(os.path.join(drive, "mmecu", "junk.py"))


def test_restore_replaces_code_py_before_removing_the_package(monkeypatch, drive, v1):
    circuitpy.deploy(drive)
    seen = []
    real_remove = circuitpy._remove_tree

    def spy(path):
        if os.path.basename(path) == "mmecu":
            seen.append(_read(drive, "code.py"))
        real_remove(path)

    monkeypatch.setattr(circuitpy, "_remove_tree", spy)
    circuitpy.deploy_ref(drive, v1)
    assert seen == [_git_show(v1, "code.py")]  # never a code.py importing a missing mmecu/


def test_swap_installs_lib_then_package_then_code_py_last(monkeypatch, drive):
    circuitpy.deploy(drive)
    moves = []
    real_replace, real_rename = os.replace, os.rename

    def spy(real):
        def move(source, target):
            if not os.path.relpath(target, drive).startswith(circuitpy.STAGING):
                moves.append(os.path.relpath(target, drive).replace(os.sep, "/"))
            real(source, target)

        return move

    monkeypatch.setattr(circuitpy.os, "replace", spy(real_replace))
    monkeypatch.setattr(circuitpy.os, "rename", spy(real_rename))
    circuitpy.deploy(drive)
    assert moves[-1] == "code.py"
    assert moves[-2] == "mmecu"
    assert all(move.startswith("lib/") for move in moves[:-2])
