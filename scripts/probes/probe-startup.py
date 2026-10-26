# SPDX-License-Identifier: GPL-3.0-or-later
"""Check real startup movies, menu transitions and SDL controller input in GDB."""
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import traceback

import gdb

gdb.execute("set pagination off")
gdb.execute("set confirm off")
gdb.execute("set debuginfod enabled off")
gdb.execute("set print thread-events off")
scenario = os.environ["CRUSADER_STARTUP_SCENARIO"]
root = Path("runtime/startup")
report = {"scenario": scenario, "results": [], "movies_started": 0, "movies_closed": 0, "scummvm_dialogs": 0}


class Frame(gdb.Breakpoint):
    def __init__(self):
        super().__init__("Ultima::Ultima8::Ultima8Engine::handleDelayedEvents", internal=True)
        self.silent = True


class Observe(gdb.Breakpoint):
    def __init__(self, function, counter):
        super().__init__(function, internal=True)
        self.counter = counter

    def stop(self):
        report[self.counter] += 1
        return False


class Actions(gdb.Breakpoint):
    def __init__(self):
        super().__init__("Ultima::Ultima8::Ultima8Engine::handleActionDown", internal=True)

    def stop(self):
        report.setdefault("actions", []).append(str(gdb.selected_frame().read_var("action")))
        return False


def engine():
    return gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance")


def modal():
    value = gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance->getModalGump()")
    return str(value.dynamic_type) if int(value) else ""


def ticks(count=1):
    for _ in range(count):
        gdb.execute("continue", to_string=True)


def wait_for(predicate, description, count=600):
    for _ in range(count):
        if predicate():
            return
        ticks()
    raise AssertionError("Timed out: " + description + "; focused gump: " + modal())


def check(condition, name, details=None):
    report["results"].append({"test": name, "passed": bool(condition), "details": details})
    print(name, "passed:", bool(condition), flush=True)
    if not condition:
        raise AssertionError(name)


def event(function, *args):
    queued = gdb.parse_and_eval("(int)crusader_probe_%s(%s)" % (function, ",".join(map(str, args))))
    if int(queued) != 1:
        raise AssertionError("SDL event was not queued: " + function)


def press(function, number):
    event(function, number, 1)
    ticks(8)
    event(function, number, 0)
    ticks(8)


def menu_entries():
    menu = gdb.parse_and_eval("(Ultima::Ultima8::CruMenuGump*)Ultima::Ultima8::Ultima8Engine::_instance->getModalGump()")
    anchor = menu["_children"]["_anchor"]
    node = anchor["_next"]
    node_type = gdb.lookup_type("Common::ListInternal::Node<Ultima::Ultima8::Gump*>").pointer()
    entries = {}
    while int(node) != int(anchor.address):
        child = node.cast(node_type)["_data"]
        index = int(child["_index"])
        if 1 <= index <= 6:
            entries[index] = child
        node = node["_next"]
    return menu, entries


def bright_entry(expected):
    menu, entries = menu_entries()
    frames = {index: int(child["_frameNum"]) for index, child in entries.items()}
    return len(frames) == 6 and int(menu["_highlighted"]) == expected and all(
        frame == (1 if index == expected else 0) for index, frame in frames.items())


def hover_entry(index):
    menu, entries = menu_entries()
    child = entries[index]
    dims = child["_dims"]
    x = int(menu["_x"]) + int(child["_x"]) + (int(dims["left"]) + int(dims["right"])) // 2
    y = int(menu["_y"]) + int(child["_y"]) + (int(dims["top"]) + int(dims["bottom"])) // 2
    event("mouse", x, y)
    ticks(16)


def mission_running():
    pointer = engine()["_objectManager"]["_objects"]["_storage"][1]
    if not int(pointer):
        return False
    actor = pointer.cast(gdb.lookup_type("Ultima::Ultima8::MainActor").pointer())
    return int(actor["_mapNum"]) == 1 and int(actor["_x"]) > 1000 and not bool(engine()["_avatarInStasis"])


def screenshot(name):
    if not os.environ.get("CRUSADER_PROBE_SCREENSHOTS"):
        return
    windows = subprocess.run(["xdotool", "search", "--pid", str(gdb.selected_inferior().pid),
                              "--class", "scummvm"], capture_output=True, text=True, check=True)
    subprocess.run(["imlib2_grab", "-id", windows.stdout.splitlines()[-1],
                    str(root / (scenario + "-" + name + ".png"))], capture_output=True, check=True)


def choose_save(window):
    try:
        time.sleep(2)
        subprocess.run(["xdotool", "windowactivate", "--sync", window], capture_output=True, check=True)
        subprocess.run(["xdotool", "key", "Home", "Down", "Return"], capture_output=True, check=True)
        time.sleep(1)
        subprocess.run(["xdotool", "key", "Return"], capture_output=True, check=True)
    except Exception as error:
        report["dialog_driver_error"] = str(error)


frame = Frame()
Observe("Ultima::Ultima8::MovieGump::InitGump", "movies_started")
Observe("Ultima::Ultima8::MovieGump::Close", "movies_closed")
Observe("GUI::GuiManager::runLoop", "scummvm_dialogs")
Actions()

try:
    gdb.execute("run", to_string=True)
    library = Path("build/toolchain-check/probe-modern-sdl.so").resolve()
    gdb.parse_and_eval("(void*)dlopen(%s,2)" % json.dumps(str(library)))
    if scenario in ("load", "menu-load"):
        if scenario == "menu-load":
            wait_for(lambda: "CruMenuGump" in modal(), "original main menu before load")
            windows = subprocess.check_output(["xdotool", "search", "--pid", str(gdb.selected_inferior().pid),
                                               "--class", "scummvm"], text=True)
            driver = threading.Thread(target=choose_save, args=(windows.splitlines()[-1],), daemon=True)
            driver.start()
            press("key", 31)  # SDL scancode 2: Load Game
            driver.join(timeout=5)
        wait_for(mission_running, "explicit save load", 2400)
        check(report["movies_started"] == 0, "explicit_save_load_honors_skip_movies")
        check("MenuGump" not in modal() and "DifficultyGump" not in modal(),
              "explicit_save_load_bypasses_startup_menu_and_difficulty")
    else:
        if scenario in ("movies", "classic"):
            wait_for(lambda: "MovieGump" in modal(), "first opening movie")
            check(report["scummvm_dialogs"] == 0, "no_scummvm_dialog_needed_before_controller_input")
            press("button", 3)  # SDL controller Y
            check(report["movies_closed"] == 1, "first_y_press_skips_first_movie", report["movies_closed"])
            wait_for(lambda: report["movies_started"] == 2, "second opening movie")
            press("button", 3)
            check(report["movies_closed"] == 2, "y_skips_second_movie")
        wait_for(lambda: "CruMenuGump" in modal(), "original main menu")
        check(report["movies_started"] == (2 if scenario in ("movies", "classic") else 0),
              "movie_preference_controls_startup_only", report["movies_started"])
        check(not mission_running(), "normal_launch_waits_at_menu_despite_last_save")
        ticks(8)
        screenshot("menu")
        press("button", 3)
        check("CruMenuGump" in modal(), "startup_menu_cannot_be_dismissed_into_unstarted_game")
        press("key", 32)  # SDL scancode 3: Save
        check("CruMenuGump" in modal() and report["scummvm_dialogs"] == 0,
              "cannot_save_before_starting_or_loading_a_game")
        before_new_game = report["movies_started"]
        if scenario == "skip":
            check(bright_entry(1), "initial_menu_focus_uses_original_bright_artwork")
            hover_entry(2)
            check(bright_entry(2), "mouse_hover_brightens_only_the_focused_option")
            screenshot("mouse-focus")
            press("button", 12)  # Skip Save, leaving the mouse over Load
            check(bright_entry(4), "controller_focus_moves_brightness_away_from_stationary_mouse")
            screenshot("controller-focus")
            hover_entry(3)
            check(bright_entry(4), "unavailable_save_cannot_steal_startup_focus")
            press("button", 11)
            press("button", 11)
            press("button", 11)  # D-pad Up wraps from New Game to Quit
            press("button", 0)
            wait_for(lambda: "QuitGump" in modal(), "quit confirmation")
            def quit_selection():
                return bool(gdb.parse_and_eval("((Ultima::Ultima8::QuitGump*)Ultima::Ultima8::Ultima8Engine::_instance->getModalGump())->_yesSelected"))
            check(not quit_selection(), "quit_confirmation_defaults_to_no")
            ticks(8)
            screenshot("quit-no")
            press("button", 13)  # D-pad Left: Yes
            check(quit_selection(), "controller_selects_quit_yes")
            screenshot("quit-yes")
            press("button", 14)  # D-pad Right: No
            check(not quit_selection(), "controller_selects_quit_no")
            press("button", 0)
            check("CruMenuGump" in modal(), "controller_a_confirms_no_and_returns_to_menu")
            press("button", 0)  # Quit remains selected in the main menu
            wait_for(lambda: "QuitGump" in modal(), "controller reopens quit confirmation")
            press("button", 1)
            check("CruMenuGump" in modal(), "controller_b_cancels_quit_confirmation")
            press("button", 12)  # Wrap back to New Game
            press("button", 12)  # D-pad Down: Load
            press("button", 12)  # Skip unavailable Save: Options
            menu = engine()["_desktopGump"]["_focusChild"].cast(gdb.lookup_type("Ultima::Ultima8::CruMenuGump").pointer())
            check(int(menu["_highlighted"]) == 4, "controller_navigation_skips_unavailable_save")
            press("button", 11)
            press("button", 11)
            press("button", 0)  # A confirms New Game, independently of mouse position
        else:
            press("key", 30)  # SDL scancode 1: New Game
        wait_for(lambda: "DifficultyGump" in modal(), "new game difficulty")
        check(report["movies_started"] == before_new_game, "new_game_does_not_repeat_opening_movies_or_main_menu")
        ticks(8)
        screenshot("difficulty")
        if scenario in ("skip", "classic"):
            if scenario == "skip":
                press("button", 1)  # B
            else:
                windows = subprocess.check_output(["xdotool", "search", "--pid", str(gdb.selected_inferior().pid),
                                                   "--class", "scummvm"], text=True)
                subprocess.run(["xdotool", "windowactivate", "--sync", windows.splitlines()[-1]],
                               capture_output=True, check=True)
                subprocess.run(["xdotool", "key", "--clearmodifiers", "Escape"],
                               capture_output=True, check=True)
                ticks(16)
            wait_for(lambda: "CruMenuGump" in modal(), "return from difficulty to main menu")
            ticks(60)
            check("CruMenuGump" in modal() and not mission_running() and
                  report["movies_started"] == before_new_game,
                  "cancel_difficulty_returns_to_menu_without_starting_game_or_replaying_movies")
            screenshot("difficulty-back")
            if scenario == "skip":
                press("button", 0)
            else:
                press("key", 30)
            wait_for(lambda: "DifficultyGump" in modal(), "difficulty can reopen after cancelling")
            check(True, "new_game_can_be_selected_again_after_cancel")
        if scenario == "skip":
            press("button", 12)  # D-pad Down selects another difficulty
            press("button", 0)   # A confirms it
            check(int(engine()["_world"]["_difficulty"]) == 4,
                  "confirmed_difficulty_is_applied_after_cancelling_and_reopening")
        else:
            press("key", 40)  # SDL Return: default difficulty
        wait_for(lambda: "MovieGump" in modal() or mission_running(), "first mission cutscene", 2400)
        check("MovieGump" in modal(), "mission_cutscene_still_plays_when_openings_are_skipped")
        press("button", 3)
        wait_for(mission_running, "new first mission", 2400)
        check(True, "new_game_reaches_first_mission")
    ticks(8)
    manager = engine()["_eventMan"]
    manager = manager.cast(manager.dynamic_type)
    mode = str(manager["_keymapper"]["_enabledKeymapType"])
    check(mode.endswith("kKeymapTypeGame"), "game_keymap_restored_after_modal_closes", mode)
    if scenario in ("load", "menu-load"):
        report["before_game_menu"] = {"cru_stasis": bool(engine()["_cruStasis"]),
                                       "avatar_stasis": bool(engine()["_avatarInStasis"]),
                                       "controlled_npc": int(engine()["_world"]["_controlledNPCNum"])}
        press("button", 6)  # SDL Menu: native game menu
        wait_for(lambda: "CruMenuGump" in modal(), "in-game menu")
        if scenario == "load":
            hover_entry(3)
            check(bright_entry(3), "save_can_be_highlighted_once_a_game_is_running")
        press("button", 1)  # B cancels the native menu
        wait_for(lambda: "CruMenuGump" not in modal(), "return from in-game menu")
        check(mission_running(), "in_game_menu_still_closes_back_to_game")
    check(report["scummvm_dialogs"] == (1 if scenario == "menu-load" else 0),
          "only_explicit_load_dialog_uses_scummvm_gui", report["scummvm_dialogs"])
    if scenario == "skip":
        press("button", 6)
        wait_for(lambda: "CruMenuGump" in modal(), "in-game menu before quit")
        press("key", 35)
        wait_for(lambda: "QuitGump" in modal(), "in-game quit confirmation")
        press("button", 13)
        exit_codes = []
        gdb.events.exited.connect(lambda event: exit_codes.append(getattr(event, "exit_code", None)))
        event("button", 0, 1)
        frame.enabled = False
        gdb.execute("continue", to_string=True)
        check(exit_codes == [0], "controller_a_confirms_yes_and_exits_cleanly", exit_codes)
    report["passed"] = True
except Exception as error:
    report["passed"] = False
    report["error"] = str(error)
    traceback.print_exc()
finally:
    path = root / (scenario + ".json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("Startup probe:", path, "passed:", report.get("passed"), "error:", report.get("error"))
    try:
        gdb.execute("kill", to_string=True)
    except gdb.error:
        pass
    gdb.execute("quit %d" % (0 if report.get("passed") else 1))
