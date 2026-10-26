# SPDX-License-Identifier: GPL-3.0-or-later
"""Identify desktop and Gamescope sessions without guessing from device flags."""
from enum import Enum
import os
import re


class SessionMode(Enum):
    DESKTOP = "desktop"
    GAMING = "gaming"
    UNKNOWN = "unknown"


def detect_session(environment=None):
    environment = os.environ if environment is None else environment
    labels = {
        label for key in ("XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION")
        for label in re.split(r"[:;\s]+", environment.get(key, "").casefold()) if label
    }
    gaming = any(label == "gamescope" or label.startswith("gamescope-session") for label in labels)
    desktop_names = {
        "kde", "gnome", "xfce", "xfce4", "lxqt", "lxde", "cinnamon", "mate",
        "budgie", "cosmic", "sway", "hyprland",
    }
    desktop = any(label in desktop_names or label.startswith("plasma") for label in labels)
    if gaming and not desktop:
        return SessionMode.GAMING
    if desktop and not gaming:
        return SessionMode.DESKTOP
    return SessionMode.UNKNOWN
