# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with GDB -x against the development executable and a mission save.

Queues SDL controller events through the real backend and keymapper.
"""
import json
import math
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
                shot = {key: int(frame.read_var(key)) for key in ("sx", "sy", "sz", "dx", "dy", "dz", "firetype", "target")}
                shot["actor"] = state()
                if shot["target"]:
                    target = gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance->_objectManager->_objects._storage[%d]" % shot["target"])
                    target = target.cast(gdb.lookup_type("Ultima::Ultima8::Item").pointer())
                    shot["target_location"] = {key: int(target["_" + key]) for key in ("x", "y", "z")}
                shots.append(shot)
        except gdb.error:
            pass
        return False
ShotCapture("Ultima::Ultima8::SuperSpriteProcess::SuperSpriteProcess")

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
    ticks(10)
    library = Path("build/toolchain-check/probe-modern-sdl.so").resolve()
    handle = gdb.parse_and_eval("(void*)dlopen(%s, 2)" % json.dumps(str(library)))
    if not int(handle):
        raise AssertionError("Could not load SDL input probe")
    gdb.execute("call (int)crusader_probe_controllers()", to_string=True)
    initial = state()
    for name, direction, angle in (("LEFT", 10, 22500), ("RIGHT", 2, 4500), ("UP", 14, 31500), ("DOWN", 6, 13500)):
        aim(name, 9000)
        ticks(10)
        current = state()
        current["aim_angle"] = int(gdb.parse_and_eval("$probe_mover->_avatarAngle"))
        check(position(initial) == position(current) and current["direction"] == direction and current["aim_angle"] == angle,
              "right_stick_%s_aims_without_moving" % name.lower(), initial, current)
        aim(name, 0)
        ticks(2)

    before = state()
    axis("DOWN", 7000)
    ticks(30)
    moved = state()
    check(screen(moved)[1] > screen(before)[1] and moved["direction"] == 6,
          "left_stick_moves_immediately_above_deadzone", before, moved)
    axis("DOWN", 0)
    ticks(4)

    before = state()
    aim("RIGHT", 24000)
    axis("LEFT", 18000)
    ticks(20)
    moved = state()
    check(screen(moved)[0] < screen(before)[0] and moved["direction"] == 2,
          "walk_left_while_aiming_right", before, moved)
    aim("RIGHT", 0)
    ticks(5)
    current = state()
    check(current["direction"] == 10,
          "releasing_aim_follows_left_stick_movement", moved, current)
    axis("LEFT", 0)
    ticks(4)
    stopped = state()
    ticks(15)
    check(position(stopped) == position(state()), "centering_left_stick_stops_movement", stopped, state())

    before = state()
    aim("UP", 18000)
    ticks(8)
    current = state()
    check(position(before) == position(current) and current["direction"] == 14,
          "stationary_right_stick_aim_still_works_after_walking", before, current)
    aim("UP", 0)
    ticks(3)

    axis("RIGHT", 18000)
    ticks(45)
    axis("RIGHT", 0)
    ticks(3)
    aim("UP", 18000)
    ticks(4)
    aim("UP", 0)
    before = state()
    aim("RIGHT", 24000)
    axis("LEFT", 18000)
    raw_axis(5, 26000)  # Right trigger: fire.
    fire_motion = []
    previous = before
    for _ in range(30):
        ticks(1)
        point = state()
        if point["animation"] == 7 and position(point) != position(previous):
            fire_motion.append(point)
        previous = point
    current = state()
    raw_axis(5, 0)
    axis("LEFT", 0)
    ticks(10)
    check(screen(current)[0] < screen(before)[0] and len(shots) > 0,
          "fire_projectiles_while_moving_opposite_aim", before, current)
    check(bool(fire_motion), "movement_continues_during_firing_animation", before, {"samples": fire_motion})
    def aimed_right(shot):
        if not shot["target"]:
            return (shot["dx"]-shot["sx"])-(shot["dy"]-shot["sy"]) > 300 and \
                abs((shot["dx"]-shot["sx"])+(shot["dy"]-shot["sy"])) < 5
        target, source = shot["target_location"], shot["actor"]
        angle = math.degrees(math.atan2(target["x"]-source["x"], source["y"]-target["y"])) % 360
        return abs(angle - 45) <= 11.25 and shot["dx"]-shot["sx"] > shot["dy"]-shot["sy"]
    check(all(aimed_right(shot) for shot in shots),
          "free_shots_and_assisted_targets_follow_right_aim_while_moving_left", {"shots": shots}, state())
    check(any(not shot["target"] for shot in shots), "free_aim_projectile_vector_is_exercised", {"shots": shots}, state())
    report["shots"] = shots
    aim("RIGHT", 0)
    ticks(2)

    before = state()
    button(14, 1)
    ticks(4)
    button(14, 0)
    ticks(8)
    check(position(before) == position(state()) and before["direction"] == state()["direction"],
          "dpad_right_only_changes_inventory", before, state())

    axis("RIGHT", 18000)
    aim("LEFT", 18000)
    ticks(8)
    gdb.parse_and_eval("(int)crusader_probe_focus_lost()")
    ticks(4)
    stopped = state()
    ticks(18)
    check(position(stopped) == position(state()), "focus_loss_clears_both_sticks", stopped, state())
    axis("RIGHT", 0)
    aim("LEFT", 0)
    ticks(3)

    for name, number, animation in (("jump", 1, "jumpForward"), ("roll", 9, "combatRollLeft")):
        expected = int(gdb.parse_and_eval("Ultima::Ultima8::Animation::" + animation))
        button(number, 1)
        ticks(1)
        button(number, 0)
        for _ in range(90):
            if state()["animation"] == expected:
                break
            ticks(1)
        else:
            raise AssertionError(name + " did not start")
        before = state()
        aim("UP", 24000)
        axis("DOWN", 24000)
        ticks(1)
        current = state()
        check(current["animation"] == expected and current["direction"] == before["direction"],
              "twin_sticks_do_not_interrupt_" + name, before, current)
        aim("UP", 0)
        axis("DOWN", 0)
        ticks(60)

    before = state()
    aim("RIGHT", 18000)
    raw_axis(3, -18000)
    ticks(8)
    current = state()
    current["aim_angle"] = int(gdb.parse_and_eval("$probe_mover->_avatarAngle"))
    check(position(before) == position(current) and current["aim_angle"] == 34157,
          "diagonal_aim_matches_isometric_screen_coordinates", before, current)
    aim("RIGHT", 0)
    raw_axis(3, 0)
    ticks(2)

    axis("UP", 24000)
    valid_positions = 0
    for _ in range(80):
        ticks(1)
        state()
        valid = bool(gdb.parse_and_eval("Ultima::Ultima8::World::_world->_currentMap->getPositionInfo("
            "$probe_actor->getWorldBox(), $probe_actor->getWorldBox(), $probe_actor->getShapeInfo()->_flags, 1).valid"))
        valid_positions += valid
    check(valid_positions == 80, "movement_and_wall_sliding_keep_collision_positions_valid",
          {"samples": 80}, {"valid_positions": valid_positions, "actor": state()})
    axis("UP", 0)
    ticks(4)

    report["passed"] = True
except Exception as error:
    report["passed"] = False
    report["error"] = str(error)
finally:
    if save_fixture.exists() and save_fixture.read_bytes() != original_fixture:
        save_fixture.with_suffix(".002").write_bytes(save_fixture.read_bytes())
        save_fixture.write_bytes(original_fixture)
        report["resume_fixture"] = "runtime/twin-integration-saves/remorse-twin-stick.002"
    Path("runtime/twin-integration-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    try:
        gdb.execute("kill", to_string=True)
    except gdb.error:
        pass
    gdb.execute("quit %d" % (0 if report.get("passed") else 1))
