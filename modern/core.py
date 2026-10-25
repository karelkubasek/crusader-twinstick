# SPDX-License-Identifier: GPL-3.0-or-later
import configparser
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get("CRUSADER_TWINSTICK_HOME", ROOT / "user-data")).expanduser().resolve()
CONFIG = STATE / "scummvm.ini"
DATA = STATE / "installation/game-data"
SAVES = STATE / "saves"
BINARY = ROOT / "runtime-engine/bin/scummvm"
EXTRA = ROOT / "runtime-engine/share/engine-data"
THEMES = ROOT / "runtime-engine/share/themes"
LOG = STATE / "logs/scummvm.log"
TARGET = "remorse-twin-stick"

DEFAULTS = {"enabled": True, "deadzone": 15, "aim_deadzone": 15, "hysteresis": 5, "fullscreen": True}
KEYS = {
    "LCLK": "MOUSE_LEFT", "RCLK": "MOUSE_RIGHT",
    "COMBAT": "c JOY_RIGHT_STICK", "MENU": "ESCAPE JOY_START",
    "MOVE_UP": "", "MOVE_DOWN": "", "MOVE_LEFT": "", "MOVE_RIGHT": "",
    "MOVE_RUN": "LSHIFT JOY_LEFT_TRIGGER", "MOVE_STEP": "LALT",
    "USE_SELECTION": "RETURN KP_ENTER JOY_A", "SHORT_JUMP": "TAB j JOY_B",
    "SELECT_ITEM": "s KP_PLUS JOY_X", "NEXT_WEAPON": "w KP_MULTIPLY JOY_Y",
    "USE_INVENTORY": "u KP_PERIOD JOY_BACK", "ATTACK": "SPACE KP0 JOY_RIGHT_TRIGGER",
    "ROLL_LEFT": "INSERT KP1 JOY_LEFT_SHOULDER", "ROLL_RIGHT": "PAGEUP KP3 JOY_RIGHT_SHOULDER",
    "TOGGLE_CROUCH": "KP5 JOY_LEFT_STICK", "USE_MEDIKIT": "m JOY_UP",
    "USE_ENERGYCUBE": "e JOY_DOWN", "NEXT_INVENTORY": "o KP_MINUS JOY_RIGHT",
    "GRAB_ITEM": "g JOY_LEFT", "MOVE_BACK": "DOWN",
    "STICK_LEFT": "JOY_LEFT_STICK_X-", "STICK_RIGHT": "JOY_LEFT_STICK_X+",
    "STICK_UP": "JOY_LEFT_STICK_Y-", "STICK_DOWN": "JOY_LEFT_STICK_Y+",
    "AIM_LEFT": "JOY_RIGHT_STICK_X-", "AIM_RIGHT": "JOY_RIGHT_STICK_X+",
    "AIM_UP": "JOY_RIGHT_STICK_Y-", "AIM_DOWN": "JOY_RIGHT_STICK_Y+",
}


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

ACTION_LABELS = {
    "LCLK": "Left click", "RCLK": "Right click", "COMBAT": "Draw / holster",
    "MENU": "Game menu", "MOVE_UP": "Move up", "MOVE_DOWN": "Move down",
    "MOVE_LEFT": "Move left", "MOVE_RIGHT": "Move right", "MOVE_RUN": "Run",
    "MOVE_STEP": "Side step", "USE_SELECTION": "Use selection", "SHORT_JUMP": "Jump",
    "SELECT_ITEM": "Search", "NEXT_WEAPON": "Next weapon", "USE_INVENTORY": "Use item",
    "ATTACK": "Fire", "ROLL_LEFT": "Roll left", "ROLL_RIGHT": "Roll right",
    "TOGGLE_CROUCH": "Crouch", "USE_MEDIKIT": "Medikit", "USE_ENERGYCUBE": "Energy cube",
    "NEXT_INVENTORY": "Next item", "GRAB_ITEM": "Pick up items", "MOVE_BACK": "Move back",
    "STICK_LEFT": "Move", "STICK_RIGHT": "Move",
    "STICK_UP": "Move", "STICK_DOWN": "Move",
    "AIM_LEFT": "Aim", "AIM_RIGHT": "Aim", "AIM_UP": "Aim", "AIM_DOWN": "Aim",
}

NATIVE_KEYS = {
    **{key: value for key, value in KEYS.items() if not key.startswith(("STICK_", "AIM_"))},
    "LCLK": "MOUSE_LEFT JOY_A", "RCLK": "MOUSE_RIGHT JOY_B",
    "COMBAT": "c JOY_X", "MENU": "ESCAPE JOY_Y",
    "MOVE_UP": "JOY_UP", "MOVE_DOWN": "JOY_DOWN", "MOVE_LEFT": "JOY_LEFT", "MOVE_RIGHT": "JOY_RIGHT",
    "MOVE_RUN": "LSHIFT JOY_RIGHT_TRIGGER", "MOVE_STEP": "LALT JOY_RIGHT_SHOULDER",
    "USE_SELECTION": "RETURN KP_ENTER", "SHORT_JUMP": "TAB j", "SELECT_ITEM": "s KP_PLUS",
    "NEXT_WEAPON": "w KP_MULTIPLY", "USE_INVENTORY": "u KP_PERIOD", "ATTACK": "SPACE KP0",
    "ROLL_LEFT": "INSERT KP1", "ROLL_RIGHT": "PAGEUP KP3", "TOGGLE_CROUCH": "KP5",
    "USE_MEDIKIT": "m", "USE_ENERGYCUBE": "e", "NEXT_INVENTORY": "i KP_MINUS", "GRAB_ITEM": "g",
}


def controller_labels():
    """Describe saved gamepad mappings, including native defaults for omitted keys."""
    config = read_config()
    section = config[TARGET] if config.has_section(TARGET) else {}
    enabled = section.get("crusader_modern_controls", "true").lower() in ("true", "yes", "on", "1")
    defaults = KEYS if enabled else NATIVE_KEYS
    labels = {}
    custom_actions = [key[len("keymap_remorse_"):] for key in section if key.startswith("keymap_remorse_")]
    for action in dict.fromkeys((*defaults, *ACTION_LABELS, *custom_actions)):
        if not enabled and action.startswith(("STICK_", "AIM_")):
            continue
        binding = section.get("keymap_remorse_" + action, defaults.get(action, ""))
        description = ACTION_LABELS.get(action, action.replace("_", " ").capitalize())
        for token in binding.split():
            if token.startswith("JOY_"):
                labels.setdefault(token, [])
                if description not in labels[token]:
                    labels[token].append(description)
    return labels

def read_config():
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    if CONFIG.exists():
        config.read(CONFIG)
    return config

def load_settings():
    config = read_config()
    if not config.has_section(TARGET):
        return dict(DEFAULTS)
    section = config[TARGET]
    settings = {
        "enabled": section.getboolean("crusader_modern_controls", True),
        "deadzone": section.getint("crusader_stick_deadzone", 15),
        "aim_deadzone": section.getint("crusader_aim_deadzone", 15),
        "hysteresis": section.getint("crusader_stick_hysteresis", 5),
        "fullscreen": section.getboolean("fullscreen", DEFAULTS["fullscreen"]),
    }
    return validate(settings)

def validate(settings):
    if type(settings["enabled"]) is not bool or type(settings["fullscreen"]) is not bool:
        raise ValueError("Enabled and fullscreen must be true or false")
    integer_keys = ("deadzone", "hysteresis", "aim_deadzone")
    if any(type(settings[k]) is not int for k in integer_keys):
        raise ValueError("Thresholds must be whole percentages")
    if not 1 <= settings["deadzone"] <= 98 or not 1 <= settings["aim_deadzone"] <= 98:
        raise ValueError("Choose movement and aiming deadzones between 1% and 98%")
    if not 0 <= settings["hysteresis"] < min(settings["deadzone"], settings["aim_deadzone"]):
        raise ValueError("The boundary cushion must be smaller than both deadzones")
    return settings

def save_settings(settings):
    validate(settings)
    config = read_config()
    if not config.has_section("scummvm"):
        config.add_section("scummvm")
    config["scummvm"]["themepath"] = str(THEMES)
    if not config.has_section(TARGET):
        config.add_section(TARGET)
    section = config[TARGET]
    description = "Crusader: No Remorse - Twin Stick"
    section.update({"gameid": "remorse", "engineid": "ultima", "description": description,
                    "path": str(DATA), "extrapath": str(EXTRA), "savepath": str(SAVES), "joystick_num": "0",
                    "fullscreen": str(settings["fullscreen"]).lower(), "crusader_modern_controls": str(settings["enabled"]).lower(),
                    "crusader_stick_deadzone": str(settings["deadzone"]),
                    "crusader_stick_hysteresis": str(settings["hysteresis"])})
    section["crusader_twin_stick"] = "true"
    section["crusader_aim_deadzone"] = str(settings["aim_deadzone"])
    section.pop("crusader_walk_threshold", None)
    for action, binding in KEYS.items():
        key = "keymap_remorse_" + action
        if not settings["enabled"]:
            if section.get(key) == binding:
                del section[key]
        elif key not in section:
            section[key] = binding
    SAVES.mkdir(parents=True, exist_ok=True)
    output = io.StringIO()
    config.write(output, space_around_delimiters=False)
    atomic_write(CONFIG, output.getvalue())

def prepare_data():
    from .install import installation_status
    status = installation_status(DATA.parent)
    if not status.ready:
        raise RuntimeError(status.message)


def launch(launcher=False):
    if not BINARY.exists():
        raise FileNotFoundError("The twin-stick runtime is missing. Use a complete release bundle or follow the source-build instructions.")
    prepare_data()
    config = read_config()
    section = config[TARGET] if config.has_section(TARGET) else {}
    if any(section.get(key) != str(value) for key, value in
           (("path", DATA), ("savepath", SAVES), ("extrapath", EXTRA))):
        save_settings(load_settings())
    command = [str(BINARY), "--config=" + str(CONFIG), "--extrapath=" + str(EXTRA)]
    if not launcher:
        command.append("--fullscreen" if load_settings()["fullscreen"] else "--no-fullscreen")
        command.append(TARGET)
    environment = os.environ.copy()
    # Homebrew SDL's evdev driver misses this Deck's Steam virtual controller.
    environment.setdefault("SDL_JOYSTICK_LINUX_CLASSIC", "1")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("w") as log:
        return subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
