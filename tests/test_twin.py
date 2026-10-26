# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from modern import core


class TwinConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = patch.object(core, "CONFIG", Path(self.temp.name) / "twin.ini")
        self.saves = patch.object(core, "SAVES", Path(self.temp.name) / "saves")
        self.config.start()
        self.saves.start()
        self.addCleanup(self.config.stop)
        self.addCleanup(self.saves.stop)

    def test_opening_movies_default_to_skipped_for_existing_configs(self):
        core.CONFIG.write_text(f"[{core.TARGET}]\ncrusader_modern_controls=true\n")
        self.assertTrue(core.load_settings()["skip_intro"])
        core.save_settings(core.load_settings())
        self.assertTrue(core.read_config()[core.TARGET].getboolean("skip_intro"))

    def test_movie_preference_survives_other_settings_changes(self):
        core.save_settings({**core.DEFAULTS, "skip_intro": False})
        settings = core.load_settings()
        self.assertFalse(settings["skip_intro"])
        core.save_settings({**settings, "deadzone": 25, "enabled": False})
        self.assertFalse(core.read_config()[core.TARGET].getboolean("skip_intro"))

    def test_movie_preference_requires_a_boolean(self):
        for value in (1, "true", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.save_settings({**core.DEFAULTS, "skip_intro": value})

    def test_twin_remapping_survives_threshold_updates(self):
        core.save_settings(core.DEFAULTS)
        config = core.read_config()
        config[core.TARGET]["keymap_remorse_AIM_UP"] = "JOY_RIGHT_STICK_Y+"
        with core.CONFIG.open("w") as stream:
            config.write(stream)
        core.save_settings({**core.DEFAULTS, "aim_deadzone": 25})
        self.assertEqual(core.read_config()[core.TARGET]["keymap_remorse_AIM_UP"], "JOY_RIGHT_STICK_Y+")
        core.save_settings({**core.DEFAULTS, "enabled": False})
        self.assertNotIn("JOY_RIGHT_STICK_Y+", core.controller_labels())
        self.assertEqual(core.read_config()[core.TARGET]["keymap_remorse_AIM_UP"], "JOY_RIGHT_STICK_Y+")


if __name__ == "__main__":
    unittest.main()
