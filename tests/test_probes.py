# SPDX-License-Identifier: GPL-3.0-or-later
import configparser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_engine_probes


class ProbeSetupTests(unittest.TestCase):
    def test_config_uses_current_workspace_and_private_save_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "user-data/installation/game-data"
            saves = root / "runtime/twin-integration-saves"
            config_path = root / "runtime/probe.ini"
            with patch.object(run_engine_probes, "ROOT", root), patch.object(run_engine_probes.core, "DATA", data):
                run_engine_probes.write_config(config_path, "probe", saves)
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(config_path)
            self.assertEqual(config["probe"]["path"], str(data))
            self.assertEqual(config["probe"]["savepath"], str(saves))
            self.assertEqual(config["probe"]["extrapath"], str(root / "vendor/scummvm/dists/engine-data"))
            self.assertEqual(config["scummvm"]["themepath"], str(root / "vendor/scummvm/gui/themes"))
            self.assertEqual(config["probe"]["keymap_remorse_ATTACK"], "SPACE KP0 JOY_RIGHT_TRIGGER")
            self.assertFalse((root / "user-data/scummvm.ini").exists())

    def test_probe_working_save_is_an_independent_copy_of_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixtures = root / "private-fixtures"
            original = fixtures / "twin-integration-saves/remorse-twin-stick.001"
            original.parent.mkdir(parents=True)
            original.write_bytes(b"pristine mission")
            with patch.object(run_engine_probes, "ROOT", root):
                run_engine_probes.prepare_fixtures(fixtures, "save-load")
            working = root / "runtime/twin-integration-saves/remorse-twin-stick.001"
            working.write_bytes(b"saved during movement")
            self.assertEqual(original.read_bytes(), b"pristine mission")

    def test_missing_fixture_fails_before_replacing_any_working_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixtures = root / "private-fixtures"
            original = fixtures / "twin-integration-saves/remorse-twin-stick.001"
            original.parent.mkdir(parents=True)
            original.write_bytes(b"pristine mission")
            working = root / "runtime/twin-integration-saves/remorse-twin-stick.001"
            working.parent.mkdir(parents=True)
            working.write_bytes(b"previous working save")
            with patch.object(run_engine_probes, "ROOT", root), self.assertRaisesRegex(FileNotFoundError, "private save fixture"):
                run_engine_probes.prepare_fixtures(fixtures, "all")
            self.assertEqual(working.read_bytes(), b"previous working save")
