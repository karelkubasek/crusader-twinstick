# SPDX-License-Identifier: GPL-3.0-or-later
"""Import user-owned game resources without modifying the source or user saves."""
from dataclasses import dataclass
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import uuid

from . import core

CATALOG_PATH = core.ROOT / "assets/game-data-manifest.json"
GAME_DIRS = {"STATIC", "USECODE", "SOUND", "FLICS", "IDATA"}


class InstallCancelled(Exception):
    pass


@dataclass(frozen=True)
class InstallStatus:
    ready: bool
    message: str
    edition: str = ""
    artwork: Path | None = None


def catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def installation_status(installation=None):
    installation = Path(installation or core.DATA.parent)
    try:
        receipt = json.loads((installation / "install.json").read_text())
        if (receipt.get("schema") != 1 or receipt.get("edition") != catalog()["edition"] or
                receipt.get("catalog_sha256") != hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()):
            raise ValueError("Unrecognized installation")
        for entry in catalog()["files"]:
            target = installation / "game-data" / entry["path"]
            if not target.is_file() or target.stat().st_size != entry["size"]:
                return InstallStatus(False, "Game files are missing or incomplete. Import your copy again.")
        art = installation / "artwork/silencer.png"
        return InstallStatus(True, "Game files installed", receipt["edition"], art if art.is_file() else None)
    except (OSError, ValueError, KeyError, TypeError):
        return InstallStatus(False, "Choose your GOG installer or an existing No Remorse folder to begin.")


def _cancelled(cancel):
    if cancel.is_set():
        raise InstallCancelled("Installation cancelled. Your existing files are unchanged.")


def _tool(name):
    bundled = core.ROOT / "runtime-tools/bin" / name
    result = str(bundled) if bundled.is_file() else shutil.which(name)
    if not result:
        raise RuntimeError(f"The importer needs {name}. Use the complete release bundle or install this tool for source development.")
    return result


def _run(command, cancel, log):
    with log.open("ab") as output:
        with subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT) as process:
            while process.poll() is None:
                if cancel.wait(.1):
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise InstallCancelled("Installation cancelled. Your existing files are unchanged.")
            if process.returncode:
                raise RuntimeError(f"Could not extract these files. Check the selected source and the installation log: {log}")


def _inventory(folder):
    """Normalize names, but reject ambiguous case variants and symbolic links."""
    result = {}
    for path in folder.rglob("*"):
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(folder)
        key = relative.as_posix().upper()
        if relative.parts[0].upper() not in GAME_DIRS:
            continue
        if key in result:
            raise ValueError(f"Ambiguous game files: {key}")
        result[key] = path
    return result


def find_game_root(folder):
    folder = Path(folder).expanduser().resolve()
    candidates = [folder, folder / "app", folder / "game-data", folder / "data"]
    for candidate in candidates:
        if candidate.is_dir():
            names = {p.name.upper() for p in candidate.iterdir() if p.is_dir()}
            if {"STATIC", "USECODE"} <= names:
                return candidate
    raise ValueError("This folder does not contain No Remorse game data. Select the folder containing STATIC and USECODE.")


def embedded_portrait(icon):
    """Return an existing PNG payload from a GOG ICO; no artwork is shipped."""
    data = Path(icon).read_bytes()
    if len(data) < 6 or len(data) > 4 * 1024 * 1024:
        return None
    reserved, kind, count = struct.unpack_from("<HHH", data)
    if reserved or kind != 1 or count > 64 or 6 + count * 16 > len(data):
        return None
    candidates = []
    for index in range(count):
        width, height, _, _, _, _, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * index)
        if offset + size > len(data):
            continue
        payload = data[offset:offset + size]
        if payload.startswith(b"\x89PNG\r\n\x1a\n") and len(payload) >= 24:
            png_width, png_height = struct.unpack_from(">II", payload, 16)
            if 0 < png_width <= 512 and 0 < png_height <= 512:
                candidates.append((png_width * png_height, payload))
    return max(candidates, default=(0, None), key=lambda pair: pair[0])[1]


def _copy_verified(source, target, entry, cancel):
    if source.stat().st_size != entry["size"]:
        raise ValueError(f"Unsupported or damaged game file: {entry['path']}. This release supports GOG English 1.21.")
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as src, target.open("wb") as dst:
        while block := src.read(1024 * 1024):
            _cancelled(cancel)
            digest.update(block)
            dst.write(block)
    if digest.hexdigest() != entry["sha256"]:
        raise ValueError(f"Unsupported or damaged game file: {entry['path']}. Your previous installation has been kept.")


def import_game(source, progress=None, cancel=None, installation=None):
    """Verify in staging, then replace game data as one installation transaction."""
    progress = progress or (lambda percent, message: None)
    cancel = cancel or threading.Event()
    installation = Path(installation or core.DATA.parent).resolve()
    state = installation.parent
    source = Path(source).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)
    log = state / "logs/install.log"
    log.parent.mkdir(exist_ok=True)
    lock = (state / ".install.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError("Another installation is running. Close it before importing again.") from None
    try:
        with tempfile.TemporaryDirectory(prefix=".install-", dir=state) as temporary:
            staging = Path(temporary)
            progress(1, "Checking your game files…")
            _cancelled(cancel)
            if source.is_file():
                if source.suffix.lower() != ".exe":
                    raise ValueError("Select the GOG offline installer (.exe), or choose an existing game folder.")
                extracted = staging / "gog"
                extracted.mkdir()
                progress(5, "Extracting the GOG installer…")
                _run([_tool("innoextract"), "--extract", "--exclude-temp", "--output-dir", str(extracted), str(source)], cancel, log)
                source_root = find_game_root(extracted)
            elif source.is_dir():
                source_root = find_game_root(source)
            else:
                raise ValueError("The selected installer or folder no longer exists.")

            inventory = {}
            image = next((p for p in source_root.iterdir() if p.name.upper() == "GAME.GOG" and p.is_file()), None)
            if image:
                cd = staging / "cd"
                cd.mkdir()
                progress(15, "Preparing CD resources…")
                _run([_tool("bsdtar"), "-xf", str(image), "-C", str(cd), "--no-same-owner", "--no-same-permissions"], cancel, log)
                inventory.update(_inventory(cd))
            inventory.update(_inventory(source_root))
            expected = catalog()
            missing = [entry["path"] for entry in expected["files"] if entry["path"] not in inventory]
            if missing:
                raise ValueError(f"Incomplete game data: missing {missing[0]}. Select the complete GOG installation including GAME.GOG, or a complete ScummVM data folder.")

            package = staging / "installation"
            data = package / "game-data"
            for index, entry in enumerate(expected["files"]):
                _cancelled(cancel)
                progress(25 + int(65 * index / len(expected["files"])), f"Verifying {entry['path']}…")
                _copy_verified(inventory[entry["path"]], data / entry["path"], entry, cancel)
            portrait = None
            icon = source_root / "goggame-1207658933.ico"
            if icon.is_file():
                portrait = embedded_portrait(icon)
            old_portrait = installation / "artwork/silencer.png"
            if portrait is None and old_portrait.is_file():
                portrait = old_portrait.read_bytes()
            if portrait:
                (package / "artwork").mkdir()
                (package / "artwork/silencer.png").write_bytes(portrait)
            receipt = {"schema": 1, "edition": expected["edition"], "game_id": "remorse", "installed_at": time.time(),
                       "catalog_sha256": hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()}
            (package / "install.json").write_text(json.dumps(receipt, indent=2) + "\n")
            _cancelled(cancel)
            previous = state / (".previous-" + uuid.uuid4().hex)
            if installation.exists():
                installation.rename(previous)
            try:
                package.rename(installation)
            except OSError:
                if previous.exists():
                    previous.rename(installation)
                raise
            if previous.exists():
                shutil.rmtree(previous, ignore_errors=True)
            progress(100, "Installed. Twin-stick controls are ready.")
            return installation_status(installation)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
