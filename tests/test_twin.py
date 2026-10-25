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

    def test_default_target_uses_twin_stick_and_has_unique_bindings(self):
        self.assertEqual(core.TARGET, "remorse-twin-stick")
        core.save_settings(core.DEFAULTS)
        self.assertEqual(core.load_settings(), core.DEFAULTS)
        saved = core.read_config()[core.TARGET]
        self.assertEqual(saved["crusader_twin_stick"], "true")
        self.assertEqual(core.controller_labels()["JOY_LEFT_STICK_X-"], ["Move"])
        self.assertEqual(core.controller_labels()["JOY_RIGHT_STICK_X-"], ["Aim"])
        owners = {}
        for action, values in saved.items():
            if not action.startswith("keymap_"):
                continue
            for token in values.split():
                if token.startswith("JOY_"):
                    self.assertNotIn(token, owners)
                    owners[token] = action

    def test_movement_and_aim_deadzones_validate_independently(self):
        settings = {**core.DEFAULTS, "deadzone": 60, "aim_deadzone": 20}
        core.save_settings(settings)
        self.assertEqual(core.load_settings(), settings)
        for values in ({"aim_deadzone": 0}, {"aim_deadzone": 99}, {"aim_deadzone": 5}, {"deadzone": 99}):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    core.save_settings({**core.DEFAULTS, **values})

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
