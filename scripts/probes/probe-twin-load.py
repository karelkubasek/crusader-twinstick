# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with GDB -x against the development executable and a mission save.

Queues SDL controller events through the real backend and keymapper.
"""
import json
from pathlib import Path
import gdb

gdb.execute("set pagination off")
gdb.execute("set confirm off")
gdb.execute("set debuginfod enabled off")
gdb.execute("set print thread-events off")
breakpoint = gdb.Breakpoint("Ultima::Ultima8::CruAvatarMoverProcess::run")
results = []
save_fixture = Path("runtime/twin-integration-saves/remorse-twin-stick.001")
original_fixture = save_fixture.read_bytes()

def state():
    engine = gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance")
    actor = engine["_objectManager"]["_objects"]["_storage"][1].cast(
        gdb.lookup_type("Ultima::Ultima8::MainActor").pointer())
    gdb.set_convenience_variable("probe_actor", actor)
    return {key: int(actor[field]) for key, field in
            (("x", "_x"), ("y", "_y"), ("z", "_z"), ("direction", "_direction"),
             ("animation", "_lastAnim"), ("map", "_mapNum"))}

def ticks(count):
    for _ in range(count):
        gdb.execute("continue", to_string=True)
    gdb.set_convenience_variable("probe_mover", gdb.selected_frame().read_var("this"))

def axis(name, value):
    number = 0 if name in ("LEFT", "RIGHT") else 1
    signed = -value if name in ("LEFT", "UP") else value
    result = gdb.parse_and_eval("(int)crusader_probe_axis(%d, %d)" % (number, signed))
    if int(result) != 1:
        raise AssertionError("SDL axis event was not queued: result %s, error %s" % (
            result, gdb.parse_and_eval("(const char*)SDL_GetError()").string()))

def position(value):
    return value["x"], value["y"], value["z"]

def button(number, down):
    result = gdb.parse_and_eval("(int)crusader_probe_button(%d, %d)" % (number, down))
    if int(result) != 1:
        raise AssertionError("SDL button event was not queued")

def check(condition, name, before, after):
    results.append({"test": name, "passed": bool(condition), "before": before, "after": after})
    if not condition:
        raise AssertionError(name)


def raw_axis(number, value):
    if int(gdb.parse_and_eval("(int)crusader_probe_axis(%d, %d)" % (number, value))) != 1:
        raise AssertionError("SDL axis event was not queued")

def aim(name, value):
    number = 2 if name in ("LEFT", "RIGHT") else 3
    raw_axis(number, -value if name in ("LEFT", "UP") else value)

def screen(value):
    return (value["x"]-value["y"])/4, (value["x"]+value["y"])/8-value["z"]

shots = []
class ShotCapture(gdb.Breakpoint):
    def stop(self):
        frame = gdb.selected_frame()
        try:
            if int(frame.read_var("source")) == 1:
                shots.append({key: int(frame.read_var(key)) for key in ("sx", "sy", "sz", "dx", "dy", "dz", "firetype")})
        except gdb.error:
            pass
        return False
ShotCapture("Ultima::Ultima8::SuperSpriteProcess::SuperSpriteProcess")
saved_states = []
class SaveCapture(gdb.Breakpoint):
    def stop(self):
        saved_states.append(state())
        return False
SaveCapture("Ultima::Ultima8::Ultima8Engine::saveGameStream")

report = {"coverage": "Twin-stick first-mission probe; real SDL input, actor positions and projectile constructors", "results": results}
try:
    gdb.execute("run", to_string=True)
    for _ in range(1200):
        current = state()
        stasis = bool(gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance->_avatarInStasis"))
        if current["map"] == 1 and not stasis and current["x"] > 1000:
            break
        ticks(1)
    else:
        raise AssertionError("Mission did not become ready")
    loaded = state()
    expected = json.loads(Path("runtime/twin-save-results.json").read_text())["serialized_actor_state"]
    check(position(loaded) == position(expected), "load_restores_exact_saved_position", expected, loaded)
    ticks(10)
    library = Path("build/toolchain-check/probe-modern-sdl.so").resolve()
    handle = gdb.parse_and_eval("(void*)dlopen(%s, 2)" % json.dumps(str(library)))
    if not int(handle):
        raise AssertionError("Could not load SDL input probe")
    gdb.execute("call (int)crusader_probe_controllers()", to_string=True)
    initial = state()
    ticks(90)
    check(position(initial) == position(state()), "loaded_walk_does_not_drift_with_centered_sticks", initial, state())
    aim("RIGHT", 18000)
    ticks(8)
    check(position(initial) == position(state()) and state()["direction"] == 2,
          "independent_aim_works_after_loading", initial, state())
    axis("DOWN", 18000)
    ticks(20)
    current = state()
    check(position(initial) != position(current) and current["direction"] == 2,
          "independent_movement_works_after_loading", initial, current)
    report["passed"] = True
except Exception as error:
    report["passed"] = False
    report["error"] = str(error)
finally:
    if save_fixture.exists() and save_fixture.read_bytes() != original_fixture:
        save_fixture.with_suffix(".002").write_bytes(save_fixture.read_bytes())
        save_fixture.write_bytes(original_fixture)
        report["resume_fixture"] = "runtime/twin-integration-saves/remorse-twin-stick.002"
    Path("runtime/twin-load-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    try:
        gdb.execute("kill", to_string=True)
    except gdb.error:
        pass
    gdb.execute("quit %d" % (0 if report.get("passed") else 1))
