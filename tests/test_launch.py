# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from modern import core


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "runtime").mkdir()
        binary = root / "scummvm"
        binary.touch()
        for name, value in (("ROOT", root), ("CONFIG", root / "runtime/twin.ini"), ("SAVES", root / "saves"),
                            ("BINARY", binary), ("LOG", root / "runtime/scummvm.log")):
            active = patch.object(core, name, value)
            active.start()
            self.addCleanup(active.stop)
        active = patch.object(core, "prepare_data")
        active.start()
        self.addCleanup(active.stop)

    def test_play_preserves_saved_bindings_and_applies_display_choice(self):
        core.save_settings({**core.DEFAULTS, "fullscreen": False})
        config = core.read_config()
        config[core.TARGET]["keymap_remorse_ATTACK"] = "SPACE JOY_Y"
        with core.CONFIG.open("w") as stream:
            config.write(stream)
        original = core.CONFIG.read_bytes()
        with patch.object(core.subprocess, "Popen") as popen:
            core.launch()
        command = popen.call_args.args[0]
        self.assertEqual(command[-1], "remorse-twin-stick")
        self.assertIn("--no-fullscreen", command)
        self.assertIn("--config=" + str(core.CONFIG), command)
        self.assertEqual(core.CONFIG.read_bytes(), original)

    def test_fresh_launch_enables_twin_stick_fullscreen_and_child_controller_driver(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(core.subprocess, "Popen") as popen:
            core.launch()
            self.assertNotIn("SDL_JOYSTICK_LINUX_CLASSIC", os.environ)
        self.assertIn("--fullscreen", popen.call_args.args[0])
        self.assertEqual(popen.call_args.kwargs["env"]["SDL_JOYSTICK_LINUX_CLASSIC"], "1")
        section = core.read_config()[core.TARGET]
        self.assertEqual(section["crusader_modern_controls"], "true")
        self.assertEqual(section["crusader_twin_stick"], "true")
        self.assertEqual(section["savepath"], str(core.SAVES))

    def test_remapper_keeps_existing_sdl_driver_and_opens_launcher(self):
        with patch.dict(os.environ, {"SDL_JOYSTICK_LINUX_CLASSIC": "0"}), patch.object(core.subprocess, "Popen") as popen:
            core.launch(launcher=True)
        self.assertNotIn(core.TARGET, popen.call_args.args[0])
        self.assertEqual(popen.call_args.kwargs["env"]["SDL_JOYSTICK_LINUX_CLASSIC"], "0")

    def test_relocation_rebinds_paths_without_resetting_controls(self):
        core.save_settings({**core.DEFAULTS, "deadzone": 23, "fullscreen": False})
        config = core.read_config()
        config[core.TARGET]["path"] = "/old/location/game-data"
        config[core.TARGET]["keymap_remorse_ATTACK"] = "SPACE JOY_Y"
        config["scummvm"]["themepath"] = "/old/location/themes"
        with core.CONFIG.open("w") as stream:
            config.write(stream)
        with patch.object(core.subprocess, "Popen"):
            core.launch()
        config = core.read_config()
        self.assertEqual(config[core.TARGET]["path"], str(core.DATA))
        self.assertEqual(config["scummvm"]["themepath"], str(core.THEMES))
        self.assertEqual(config[core.TARGET]["keymap_remorse_ATTACK"], "SPACE JOY_Y")
        self.assertEqual(core.load_settings()["deadzone"], 23)
        self.assertFalse(core.load_settings()["fullscreen"])


if __name__ == "__main__":
    unittest.main()
