"""Deploy this repo's firmware, from the working tree or any git ref, to a CIRCUITPY drive.

    python -m tools.circuitpy deploy                 # working tree
    python -m tools.circuitpy deploy --ref v1.0.0    # any commit/branch/tag
    python -m tools.circuitpy restore [--ref v1.0.0] [--yes]

"Restore" is a deploy of a known-good release tag (default: v1.0.0, the original
single-file firmware). Always a tag, never a branch: branches move. The board
only ever runs what is in this repo, so git is the backup. Nothing is written
to a directory that does not look like a CircuitPython drive (no boot_out.txt).
Standard library only.
"""

import argparse
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVE_MARKER = "boot_out.txt"  # written by CircuitPython at every boot
FIRMWARE_PACKAGE = "mmecu"
STAGING = ".mmecu-staging"  # hidden: ignored by walk_files, never imported by CircuitPython
RESTORE_REF = "v1.0.0"  # a release tag, never a branch (master moves on merge)
SYSTEM_NAMES = {"System Volume Information", "$RECYCLE.BIN"}
_USER = os.environ.get("USER", "")
AUTO_DETECT_PATHS = ["/Volumes/CIRCUITPY", f"/run/media/{_USER}/CIRCUITPY", f"/media/{_USER}/CIRCUITPY"]


class DriveError(Exception):
    pass


# --- drive --------------------------------------------------------------------
def find_drive(explicit=None):
    """The drive given by --drive or $CIRCUITPY (never swapped for another), else auto-detected."""
    chosen = explicit or os.environ.get("CIRCUITPY")
    if chosen:
        if not os.path.isdir(chosen):
            raise DriveError(f"{chosen} not found; is the board mounted?")
        return require_drive(chosen)
    for candidate in AUTO_DETECT_PATHS:
        if os.path.isdir(candidate):
            return require_drive(candidate)
    raise DriveError("CIRCUITPY drive not found; mount the board or set CIRCUITPY=/path")


def require_drive(path):
    if not os.path.isfile(os.path.join(path, DRIVE_MARKER)):
        raise DriveError(f"{path} has no {DRIVE_MARKER}; refusing to treat it as a CIRCUITPY drive")
    return path


def _ignored(name):
    return name.startswith(".") or name in SYSTEM_NAMES or name == "__pycache__"


def walk_files(root):
    """Relative paths of all user files under root, skipping hidden/system/cache entries."""
    found = []
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = sorted(d for d in subdirs if not _ignored(d))
        for name in sorted(files):
            if not _ignored(name):
                found.append(os.path.relpath(os.path.join(directory, name), root).replace(os.sep, "/"))
    return found


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _copy(source, target):
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    shutil.copyfile(source, target)


# --- firmware sources -----------------------------------------------------------
def export_ref(ref, destination, repo=REPO):
    """Extract the committed tree of a git ref (branch, tag, sha) into destination."""
    try:
        archive = subprocess.run(
            ["git", "-C", repo, "archive", "--format=tar", ref], capture_output=True, check=True
        ).stdout
    except subprocess.CalledProcessError as error:
        raise DriveError(f"cannot read git ref {ref!r}: {error.stderr.decode().strip()}") from error
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        if hasattr(tarfile, "data_filter"):  # Python >= 3.12 (and recent 3.8-3.11 patches)
            tar.extractall(destination, filter="data")
        else:  # our own repo's archive, so the unfiltered path is acceptable on old Pythons
            tar.extractall(destination)


def firmware_files(source):
    """(source path, drive-relative path) for what goes on the board; code.py last.

    Works for both layouts: the original single-file code.py and code.py + mmecu/.
    """
    if not os.path.isfile(os.path.join(source, "code.py")):
        raise DriveError(f"{source} has no code.py; not a firmware tree")
    pairs = [(os.path.join(source, "lib", rel), "lib/" + rel) for rel in walk_files(os.path.join(source, "lib"))]
    package = os.path.join(source, FIRMWARE_PACKAGE)
    if os.path.isdir(package):
        pairs += [
            (os.path.join(package, name), f"{FIRMWARE_PACKAGE}/{name}")
            for name in sorted(os.listdir(package))
            if name.endswith(".py")
        ]
    pairs.append((os.path.join(source, "code.py"), "code.py"))
    return pairs


# --- deploy -------------------------------------------------------------------
def _remove_tree(path):
    shutil.rmtree(path)


def _flush():
    if hasattr(os, "sync"):
        os.sync()


RETIRED = "retired-" + FIRMWARE_PACKAGE  # previous package, parked inside staging during the swap


def repair_interrupted_swap(drive):
    """Put the previous package back if a swap died between its two renames.

    The only unbootable state a swap can leave is: code.py importing mmecu/, no mmecu/,
    and the previous package parked in staging. Returns True if it repaired that.
    """
    package = os.path.join(drive, FIRMWARE_PACKAGE)
    retired = os.path.join(drive, STAGING, RETIRED)
    if os.path.isdir(package) or not os.path.isdir(retired):
        return False
    os.rename(retired, package)
    _flush()
    return True


def deploy(drive, source=REPO):
    """Install the firmware tree at `source` on the drive without ever leaving it unbootable.

    1. Copy everything into a hidden staging folder on the drive and verify it. Any
       failure here leaves the running firmware untouched (staging is removed).
    2. Swap in by renames: lib/ files, then the mmecu/ directory, then code.py last.
       A source without mmecu/ (the legacy layout) gets code.py first, and mmecu/ is
       removed only afterwards, so no code.py ever imports a missing package.
    3. Verify the installed files.

    CircuitPython auto-reloads after any write to the drive; during staging a reload
    just restarts the old, intact firmware. Other files on the drive are left alone.
    """
    require_drive(drive)
    files = firmware_files(source)
    repair_interrupted_swap(drive)
    staging = os.path.join(drive, STAGING)
    if os.path.isdir(staging):
        _remove_tree(staging)  # left over from an earlier interrupted deploy
    try:
        for source_path, rel in files:
            _copy(source_path, os.path.join(staging, rel))
        _flush()
        for source_path, rel in files:
            staged = os.path.join(staging, rel)
            if not os.path.isfile(staged) or sha256(staged) != sha256(source_path):
                raise DriveError(f"{rel} did not copy correctly; board unchanged, run the command again")
    except BaseException:
        if os.path.isdir(staging):
            _remove_tree(staging)
        raise

    for _, rel in files:
        if rel.startswith("lib/"):
            os.makedirs(os.path.dirname(os.path.join(drive, rel)), exist_ok=True)
            os.replace(os.path.join(staging, rel), os.path.join(drive, rel))
    package = os.path.join(drive, FIRMWARE_PACKAGE)
    staged_package = os.path.join(staging, FIRMWARE_PACKAGE)
    source_has_package = os.path.isdir(staged_package)  # decided before the swap moves it
    if source_has_package:
        if os.path.isdir(package):
            os.rename(package, os.path.join(staging, RETIRED))
        try:
            os.rename(staged_package, package)
        except OSError as error:
            if repair_interrupted_swap(drive):
                raise DriveError(f"swap failed ({error}); previous firmware restored, run the command again") from error
            raise
    os.replace(os.path.join(staging, "code.py"), os.path.join(drive, "code.py"))
    if not source_has_package and os.path.isdir(package):
        _remove_tree(package)  # legacy firmware: its code.py is already in place
    _remove_tree(staging)
    _flush()

    for source_path, rel in files:
        target = os.path.join(drive, rel)
        if not os.path.isfile(target) or sha256(target) != sha256(source_path):
            raise DriveError(f"{rel} is wrong after install; run the command again")
    return [rel for _, rel in files]


def deploy_ref(drive, ref, repo=REPO):
    require_drive(drive)
    with tempfile.TemporaryDirectory() as tree:
        export_ref(ref, tree, repo)
        return deploy(drive, tree)


# --- CLI ----------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m tools.circuitpy", description=__doc__.split("\n\n")[0])
    parser.add_argument("--drive", help="CIRCUITPY mount point (default: $CIRCUITPY or auto-detect)")
    commands = parser.add_subparsers(dest="command", required=True)
    deploy_cmd = commands.add_parser("deploy", help="install firmware from the working tree or a git ref")
    deploy_cmd.add_argument("--ref", help="git ref to deploy instead of the working tree")
    restore_cmd = commands.add_parser("restore", help=f"deploy a known-good git ref (default {RESTORE_REF})")
    restore_cmd.add_argument("--ref", default=RESTORE_REF)
    restore_cmd.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = parser.parse_args(argv)

    try:
        drive = find_drive(args.drive)
        if repair_interrupted_swap(drive):
            print("Found an interrupted deploy; put the previous firmware back in place first.")
        if args.command == "restore":
            if not args.yes:
                answer = input(f"Replace the firmware on {drive} with git '{args.ref}'? [yes/no] ")
                if answer.strip().lower() != "yes":
                    print("Nothing changed.")
                    return 1
            deploy_ref(drive, args.ref)
            print(f"Restored git '{args.ref}' to {drive} and verified. The board reloads by itself.")
        elif args.ref:
            deploy_ref(drive, args.ref)
            print(f"Deployed git '{args.ref}' to {drive} and verified.")
        else:
            deploy(drive)
            print(f"Deployed the working tree to {drive} and verified. Undo with: make restore")
    except (DriveError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
