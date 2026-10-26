# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from modern.session import detect_session, SessionMode


class SessionTests(unittest.TestCase):
    def test_explicit_gamescope_sessions_are_gaming_mode(self):
        for key, value in (("XDG_CURRENT_DESKTOP", "gamescope"),
                           ("XDG_SESSION_DESKTOP", "Gamescope"),
                           ("DESKTOP_SESSION", "gamescope-session-steam")):
            with self.subTest(key=key, value=value):
                self.assertIs(detect_session({key: value}), SessionMode.GAMING)

    def test_desktop_session_is_recognized_even_when_launched_by_steam(self):
        environment = {"XDG_CURRENT_DESKTOP": "KDE", "DESKTOP_SESSION": "plasma",
                       "SteamDeck": "1", "SteamGamepadUI": "1", "XDG_SESSION_TYPE": "wayland"}
        self.assertIs(detect_session(environment), SessionMode.DESKTOP)
        self.assertIs(detect_session({"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"}), SessionMode.DESKTOP)

    def test_generic_steam_and_display_flags_do_not_identify_a_session(self):
        for environment in ({}, {"SteamDeck": "1"}, {"SteamGamepadUI": "1"},
                            {"XDG_SESSION_TYPE": "wayland", "GAMESCOPE_WAYLAND_DISPLAY": "gamescope-0"}):
            with self.subTest(environment=environment):
                self.assertIs(detect_session(environment), SessionMode.UNKNOWN)

    def test_conflicting_session_labels_use_the_unknown_fallback(self):
        self.assertIs(detect_session({"XDG_CURRENT_DESKTOP": "gamescope", "DESKTOP_SESSION": "plasma"}),
                      SessionMode.UNKNOWN)
