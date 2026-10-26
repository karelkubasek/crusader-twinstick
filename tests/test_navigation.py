# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from modern.navigation import Navigation


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.nav = Navigation()
        self.update()
        self.update()

    def update(self, buttons=(), axes=(0, 0), context="game", now=0):
        return self.nav.update(buttons, axes, context, now)

    def test_confirm_is_an_edge_and_directions_repeat_after_a_delay(self):
        self.assertEqual(self.update((0, 12)), ["confirm", "down"])
        self.assertEqual(self.update((0, 12), now=0.2), [])
        self.assertEqual(self.update((0, 12), now=0.4), ["down"])
        self.assertEqual(self.update((0, 12), now=0.45), [])
        self.assertEqual(self.update((0, 12), now=0.53), ["down"])
        self.update(now=0.6)
        self.assertEqual(self.update((0,), now=0.7), ["confirm"])

    def test_page_and_focus_changes_require_neutral_before_new_actions(self):
        self.assertEqual(self.update((0,)), ["confirm"])
        for context in ("controls", None, "game"):
            with self.subTest(context=context):
                self.assertEqual(self.update((0, 12), axes=(0, 1), context=context), [])
                self.assertEqual(self.update((0, 12), axes=(0, 1), context=context, now=4), [])
        self.assertEqual(self.update(axes=(0, 0.5)), [])
        self.assertEqual(self.update(), [])
        self.assertEqual(self.update((0,)), ["confirm"])

    def test_stick_uses_threshold_buffer_and_dpad_has_priority(self):
        self.assertEqual(self.update(axes=(0, -0.59)), [])
        self.assertEqual(self.update(axes=(0, -0.61)), ["up"])
        self.assertEqual(self.update(axes=(0, -0.5), now=0.4), ["up"])
        self.assertEqual(self.update(axes=(0, -0.39), now=0.5), [])
        self.assertEqual(self.update((14,), axes=(0, -1), now=0.6), ["right"])
        self.assertEqual(self.update((1, 9), now=0.7), ["back", "previous_page"])


if __name__ == "__main__":
    unittest.main()
