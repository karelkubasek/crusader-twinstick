# SPDX-License-Identifier: GPL-3.0-or-later
import configparser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from modern import core


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name, value in (("CONFIG", root / "twin.ini"), ("SAVES", root / "saves")):
            active = patch.object(core, name, value)
            active.start()
            self.addCleanup(active.stop)

    def test_settings_roundtrip_and_isolated_game_paths(self):
        value = {**core.DEFAULTS, "deadzone": 20, "aim_deadzone": 60, "hysteresis": 8}
        core.save_settings(value)
        self.assertEqual(core.load_settings(), value)
        config = core.read_config()[core.TARGET]
        self.assertEqual(config["path"], str(core.DATA))
        self.assertEqual(config["savepath"], str(core.SAVES))
        self.assertNotIn("SAVEGAME", config["savepath"])
        self.assertEqual(config["crusader_modern_controls"], "true")

    def test_saving_thresholds_preserves_button_remapping(self):
        core.save_settings(core.DEFAULTS)
        config = core.read_config()
        config[core.TARGET]["keymap_remorse_ATTACK"] = "SPACE JOY_Y"
        with core.CONFIG.open("w") as stream:
            config.write(stream)
        core.save_settings({**core.DEFAULTS, "aim_deadzone": 55})
        self.assertEqual(core.read_config()[core.TARGET]["keymap_remorse_ATTACK"], "SPACE JOY_Y")

    def test_default_gamepad_mappings_have_one_owner(self):
        core.save_settings(core.DEFAULTS)
        owners = {}
        for action, value in core.read_config()[core.TARGET].items():
            if not action.startswith("keymap_"):
                continue
            for token in value.split():
                if token.startswith("JOY_"):
                    self.assertNotIn(token, owners, f"{token} duplicated by {action}")
                    owners[token] = action
        self.assertEqual(owners["JOY_RIGHT"], "keymap_remorse_NEXT_INVENTORY")
        self.assertEqual(owners["JOY_LEFT_STICK_X-"], "keymap_remorse_STICK_LEFT")

    def test_disabling_restores_native_defaults_and_preserves_custom_bindings(self):
        core.save_settings(core.DEFAULTS)
        config = core.read_config()
        config[core.TARGET]["keymap_remorse_ATTACK"] = "SPACE JOY_Y"
        with core.CONFIG.open("w") as stream:
            config.write(stream)
        core.save_settings({**core.DEFAULTS, "enabled": False})
        section = core.read_config()[core.TARGET]
        self.assertEqual(section["keymap_remorse_ATTACK"], "SPACE JOY_Y")
        self.assertNotIn("keymap_remorse_MOVE_RUN", section)
        self.assertNotIn("keymap_remorse_STICK_LEFT", section)
        core.save_settings(core.DEFAULTS)
        section = core.read_config()[core.TARGET]
        self.assertEqual(section["keymap_remorse_ATTACK"], "SPACE JOY_Y")
        self.assertEqual(section["keymap_remorse_STICK_LEFT"], "JOY_LEFT_STICK_X-")

    def test_invalid_thresholds_do_not_replace_saved_config(self):
        core.save_settings(core.DEFAULTS)
        saved = core.CONFIG.read_bytes()
        for changes in ({"deadzone": 0}, {"deadzone": 99}, {"aim_deadzone": 101},
                        {"aim_deadzone": 0}, {"hysteresis": 15}, {"deadzone": "15"}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    core.save_settings({**core.DEFAULTS, **changes})
                self.assertEqual(core.CONFIG.read_bytes(), saved)

    def test_diagram_labels_distinguish_each_dpad_direction(self):
        core.save_settings(core.DEFAULTS)
        labels = core.controller_labels()
        self.assertEqual(labels["JOY_UP"], ["Medikit"])
        self.assertEqual(labels["JOY_DOWN"], ["Energy cube"])
        self.assertEqual(labels["JOY_LEFT"], ["Pick up items"])
        self.assertEqual(labels["JOY_RIGHT"], ["Next item"])

    def test_diagram_uses_saved_remaps_and_falls_back_to_native_defaults(self):
        core.save_settings(core.DEFAULTS)
        config = core.read_config()
        config[core.TARGET]["keymap_remorse_ATTACK"] = "SPACE JOY_A"
        config[core.TARGET]["keymap_remorse_USE_SELECTION"] = "RETURN"
        config[core.TARGET]["keymap_remorse_QUICKSAVE"] = "F1 JOY_BACK"
        del config[core.TARGET]["keymap_remorse_USE_MEDIKIT"]
        with core.CONFIG.open("w") as stream:
            config.write(stream)
        labels = core.controller_labels()
        self.assertEqual(labels["JOY_A"], ["Fire"])
        self.assertNotIn("JOY_RIGHT_TRIGGER", labels)
        self.assertEqual(labels["JOY_UP"], ["Medikit"])
        self.assertEqual(labels["JOY_BACK"], ["Use item", "Quicksave"])
        core.save_settings({**core.DEFAULTS, "enabled": False})
        labels = core.controller_labels()
        self.assertEqual(labels["JOY_UP"], ["Move up"])
        self.assertEqual(labels["JOY_A"], ["Left click", "Fire"])


if __name__ == "__main__":
    unittest.main()
