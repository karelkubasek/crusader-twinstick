# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic resources exercise import transactions without game assets."""
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch

from modern import install


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.destination = self.root / "state/installation"
        self.files = {"STATIC/SHAPES.FLX": b"shapes", "USECODE/EUSECODE.FLX": b"scripts",
                      "SOUND/SOUND.FLX": b"sound", "FLICS/INTRO.AVI": b"video", "IDATA/ICONS.DAT": b"icons"}
        self.catalog = self.root / "catalog.json"
        self.catalog.write_text(json.dumps({"edition": "GOG English 1.21", "files": [
            {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in self.files.items()]}))
        active = patch.object(install, "CATALOG_PATH", self.catalog)
        active.start()
        self.addCleanup(active.stop)
        self.write_files(self.source)

    def write_files(self, root):
        for name, data in self.files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def do_import(self, source=None, **kwargs):
        return install.import_game(source or self.source, installation=self.destination, **kwargs)

    def snapshot(self):
        return {str(p.relative_to(self.destination)): p.read_bytes() for p in self.destination.rglob("*") if p.is_file()}

    def test_success_copies_only_whitelisted_files_and_keeps_source(self):
        (self.source / "manual.pdf").write_bytes(b"never copy this")
        status = self.do_import()
        self.assertTrue(status.ready)
        for name, data in self.files.items():
            self.assertEqual((self.source / name).read_bytes(), data)
            self.assertEqual((self.destination / "game-data" / name).read_bytes(), data)
        self.assertFalse((self.destination / "game-data/manual.pdf").exists())

    def test_incomplete_and_damaged_imports_preserve_working_install_and_saves(self):
        self.do_import()
        before = self.snapshot()
        saves = self.destination.parent / "saves/player.001"
        saves.parent.mkdir()
        saves.write_bytes(b"player save")
        bad = self.root / "bad"
        self.write_files(bad)
        (bad / "USECODE/EUSECODE.FLX").write_bytes(b"CORRUPT")
        with self.assertRaisesRegex(ValueError, "Unsupported or damaged"):
            self.do_import(bad)
        self.assertEqual(before, self.snapshot())
        (bad / "SOUND/SOUND.FLX").unlink()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.do_import(bad)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(saves.read_bytes(), b"player save")

    def test_cancellation_keeps_previous_install_and_removes_staging(self):
        self.do_import()
        before = self.snapshot()
        cancel = threading.Event()
        def progress(percent, _message):
            if percent >= 25:
                cancel.set()
        with self.assertRaises(install.InstallCancelled):
            self.do_import(progress=progress, cancel=cancel)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(list(self.destination.parent.glob(".install-*")), [])

    def test_failed_atomic_switch_rolls_back_previous_install(self):
        self.do_import()
        before = self.snapshot()
        rename = Path.rename
        def fail_switch(path, target):
            if path.name == "installation" and path.parent.name.startswith(".install-"):
                raise OSError("Simulated disk failure")
            return rename(path, target)
        with patch.object(Path, "rename", fail_switch), self.assertRaisesRegex(OSError, "disk failure"):
            self.do_import()
        self.assertEqual(before, self.snapshot())

    def test_case_insensitive_folder_import(self):
        lower = self.root / "lower"
        for name, data in self.files.items():
            path = lower / name.lower()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.assertTrue(self.do_import(lower).ready)

    def test_ambiguous_names_and_symlinks_are_rejected(self):
        (self.source / "STATIC/shapes.flx").write_bytes(b"shapes")
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            self.do_import()
        (self.source / "STATIC/shapes.flx").unlink()
        shapes = self.source / "STATIC/SHAPES.FLX"
        shapes.unlink()
        shapes.symlink_to(self.catalog)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.do_import()

    def test_installer_is_extracted_without_executing_it(self):
        executable = self.root / "installer with spaces.exe"
        executable.write_bytes(b"not an executable")
        calls = []
        def extract(command, _cancel, _log):
            calls.append(command)
            target = Path(command[command.index("--output-dir") + 1])
            self.write_files(target)
        with patch.object(install, "_run", extract), patch.object(install, "_tool", return_value="innoextract"):
            self.assertTrue(self.do_import(executable).ready)
        self.assertEqual(calls[0][0], "innoextract")
        self.assertEqual(calls[0][-1], str(executable))

    def test_installed_files_override_older_cd_copies(self):
        (self.source / "GAME.GOG").write_bytes(b"disc")
        def extract(command, _cancel, _log):
            target = Path(command[command.index("-C") + 1])
            self.write_files(target)
            (target / "USECODE/EUSECODE.FLX").write_bytes(b"older!!")
        with patch.object(install, "_run", extract), patch.object(install, "_tool", return_value="bsdtar"):
            self.assertTrue(self.do_import().ready)
        self.assertEqual((self.destination / "game-data/USECODE/EUSECODE.FLX").read_bytes(), b"scripts")

    def test_missing_files_disable_readiness(self):
        self.do_import()
        (self.destination / "game-data/FLICS/INTRO.AVI").unlink()
        self.assertFalse(install.installation_status(self.destination).ready)

    def test_parallel_import_is_blocked_by_advisory_lock(self):
        self.destination.parent.mkdir(parents=True)
        with (self.destination.parent / ".install.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with self.assertRaisesRegex(RuntimeError, "Another installation"):
                self.do_import()

    def test_portrait_is_extracted_unchanged_from_local_icon(self):
        png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 256, 256)
        icon = self.source / "goggame-1207658933.ico"
        icon.write_bytes(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22) + png)
        self.assertEqual(install.embedded_portrait(icon), png)
        status = self.do_import()
        self.assertEqual(status.artwork.read_bytes(), png)
        self.assertTrue(icon.exists())


if __name__ == "__main__":
    unittest.main()
