# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise opening geometry and real projectile damage in an isolated save copy."""
import json
import math
import os
from pathlib import Path
import subprocess
import gdb

gdb.execute("set pagination off")
gdb.execute("set confirm off")
gdb.execute("set debuginfod enabled off")
gdb.execute("set print thread-events off")
gdb.Breakpoint("Ultima::Ultima8::CruAvatarMoverProcess::run")
scenario = os.environ.get("CRUSADER_SCENARIO", "camera")
label = os.environ.get("CRUSADER_BUILD_LABEL", "fixed")
report = {"scenario": scenario, "build": label, "shots": [], "hits": [], "impacts": [], "results": []}
root = Path("runtime/opening-investigation")


def actor():
    value = gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance->_objectManager->_objects._storage[1]")
    value = value.cast(gdb.lookup_type("Ultima::Ultima8::MainActor").pointer())
    gdb.set_convenience_variable("hero", value)
    return value


def item(number):
    return gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance->_objectManager->_objects._storage[%d]" % number)


def state(pointer):
    if not int(pointer):
        return None
    pointer = pointer.cast(gdb.lookup_type("Ultima::Ultima8::Item").pointer())
    result = {key: int(pointer["_" + key]) for key in ("objId", "shape", "frame", "x", "y", "z", "flags", "damagePoints")}
    if "Actor" in str(pointer.dynamic_type):
        value = pointer.cast(gdb.lookup_type("Ultima::Ultima8::Actor").pointer())
        result.update(hp=int(value["_hitPoints"]), actor_flags=int(value["_actorFlags"]))
    return result


def ticks(count):
    for _ in range(count):
        gdb.execute("continue", to_string=True)
    actor()
    gdb.set_convenience_variable("mover", gdb.selected_frame().read_var("this"))


def axis(number, value):
    if int(gdb.parse_and_eval("(int)crusader_probe_axis(%d,%d)" % (number, value))) != 1:
        raise AssertionError("SDL axis was not queued")


def check(condition, name, details):
    report["results"].append({"test": name, "passed": bool(condition), "details": details})
    if not condition:
        raise AssertionError(name)


def screenshot(name):
    pid = gdb.selected_inferior().pid
    windows = subprocess.run(["xdotool", "search", "--pid", str(pid), "--class", "scummvm"], capture_output=True, text=True)
    if windows.returncode == 0:
        window = windows.stdout.splitlines()[-1]
        subprocess.run(["imlib2_grab", "-id", window, str(root / name)], capture_output=True)


class Shot(gdb.Breakpoint):
    def stop(self):
        frame = gdb.selected_frame()
        try:
            if int(frame.read_var("source")) == 1:
                report["shots"].append({key: int(frame.read_var(key)) for key in
                                        ("sx", "sy", "sz", "dx", "dy", "dz", "target", "firetype", "damage")})
        except gdb.error:
            pass
        return False


class Hit(gdb.Breakpoint):
    def stop(self):
        frame = gdb.selected_frame()
        pointer = frame.read_var("this")
        hit = {"item": state(pointer), "damage": int(frame.read_var("damage")),
               "type": int(frame.read_var("type" if "Item" in str(pointer.type) else "damage_type"))}
        report["impacts"].append(hit)
        if int(pointer["_objId"]) in (9424, 5):
            report["hits"].append(hit)
        return False


try:
    gdb.execute("run", to_string=True)
    for _ in range(1200):
        if int(actor()["_mapNum"]) == 1 and int(actor()["_x"]) > 1000:
            break
        ticks(1)
    ticks(12)
    library = Path("build/toolchain-check/probe-modern-sdl.so").resolve()
    gdb.parse_and_eval("(void*)dlopen(%s,2)" % json.dumps(str(library)))
    report["loaded"] = state(actor())
    if scenario.startswith("opening"):
        gdb.execute("set $empty = (Ultima::Ultima8::Box*)calloc(1,sizeof(Ultima::Ultima8::Box))", to_string=True)
        axis(0, 24000)
        if scenario != "opening_right":
            axis(1, 24000)
        samples = []
        valid = []
        for _ in range(30 if scenario == "opening_upstep" else 90):
            ticks(1)
            samples.append(state(actor()))
            valid.append(bool(gdb.parse_and_eval("Ultima::Ultima8::World::_world->_currentMap->getPositionInfo("
                "$hero->getWorldBox(), *$empty, $hero->getShapeInfo()->_flags, 1).valid")))
        axis(0, 0)
        axis(1, 0)
        report["samples"] = samples
        check(all(valid), "opening_route_does_not_overlap_solid_geometry", {"valid": sum(valid), "total": len(valid)})
        if scenario == "opening_right":
            before = state(actor())
            axis(0, 24000)
            ticks(20)
            after = state(actor())
            check(before["x"] == after["x"] and before["y"] == after["y"], "nearby_wall_still_blocks_movement", after)
        else:
            check(any(s["x"] > 60850 and s["z"] == 8 for s in samples),
                  "cross_opening_floor_step_without_jumping", samples[-1])
        if scenario == "opening_upstep":
            axis(0, -24000)
            axis(1, -24000)
            ticks(30)
            after = state(actor())
            check(after["x"] < 60750 and after["z"] == 16, "step_back_up_to_opening_platform", after)
        gdb.parse_and_eval("(void)free($empty)")
    else:
        number = 9424 if scenario == "camera" else 5
        target = item(number).cast(gdb.lookup_type("Ultima::Ultima8::Item").pointer())
        gdb.set_convenience_variable("target", target)
        report["target_before"] = state(target)
        # Find supported, unblocked positions around the unmodified world object.
        gdb.execute("set $box = (Ultima::Ultima8::Box*)malloc(sizeof(Ultima::Ultima8::Box))", to_string=True)
        candidates = []
        for z in (96, 128, 64, 0):
            for dx, dy in ((256, 512), (0, 512), (512, 256), (-256, 512), (512, 0),
                           (512, -256), (-512, 256), (256, -512), (-512, 0), (0, -512)):
                x, y = int(target["_x"]) + dx, int(target["_y"]) + dy
                gdb.execute("set *$box = $hero->getWorldBox()", to_string=True)
                for key, value in (("x", x), ("y", y), ("z", z)):
                    gdb.execute("set $box->_%s = %d" % (key, value), to_string=True)
                info = gdb.parse_and_eval("Ultima::Ultima8::World::_world->_currentMap->getPositionInfo("
                                         "*$box, $hero->getWorldBox(), $hero->getShapeInfo()->_flags, 1)")
                if bool(info["valid"]) and bool(info["supported"]):
                    candidates.append([x, y, z])
        report["candidate_positions"] = candidates
        gdb.parse_and_eval("(void)free($box)")
        if not candidates:
            raise AssertionError("No supported firing position near target")
        # Camera shots start below its base; robot shots start above its top.
        positions = [p for p in candidates if (p[2] + 40 < int(target["_z"]) if scenario == "camera" else p[2] == 0)]
        if not positions:
            raise AssertionError("No supported position with the requested height difference")
        position = positions[0] if scenario == "camera" else next(
            p for p in positions if p[0] == int(target["_x"]) - 512 and p[1] == int(target["_y"]))
        gdb.execute("call $mover->resetMovementFlags()", to_string=True)
        gdb.execute("call $hero->move(%d,%d,%d)" % tuple(position), to_string=True)
        ticks(12)
        report["firing_position"] = state(actor())
        x, y = int(target["_x"]) - int(actor()["_x"]), int(target["_y"]) - int(actor()["_y"])
        sx, sy = (x - y) / 4, (x + y) / 8
        length = math.hypot(sx, sy)
        axis(2, round(sx / length * 25000))
        axis(3, round(sy / length * 25000))
        ticks(12)
        if label == "baseline":
            # Refresh the old reticle once; its two-second delay is unrelated
            # to the baseline projectile-height failure this comparison tests.
            gdb.execute("call Ultima::Ultima8::TargetReticleProcess::_instance->findTargetItem()", to_string=True)
        report["marker"] = int(gdb.parse_and_eval("Ultima::Ultima8::TargetReticleProcess::_instance->_lastTargetItem"))
        screenshot(label + "-" + scenario + "-aim.png")
        check(report["marker"] == number, "stick_aim_marks_expected_target", {"marker": report["marker"], "expected": number})
        Shot("Ultima::Ultima8::SuperSpriteProcess::SuperSpriteProcess", internal=True)
        Hit("Ultima::Ultima8::Item::receiveHitCru", internal=True)
        Hit("Ultima::Ultima8::Actor::receiveHitCru", internal=True)
        axis(5, 26000)
        for _ in range(240):
            ticks(1)
            current = state(item(number))
            if current is None or current["flags"] & 0x8000 or current.get("actor_flags", 0) & 0x1000:
                break
        axis(5, 0)
        report["target_after"] = state(item(number))
        report["final_actor"] = state(actor())
        check(bool(report["shots"]), "trigger_emits_projectiles", report["shots"])
        check(any(s["target"] == number and (s["dz"] > s["sz"] if scenario == "camera" else s["dz"] < s["sz"])
                  for s in report["shots"]), "projectiles_use_target_height", report["shots"])
        check(bool(report["hits"]), "projectiles_actually_hit_target", report["hits"])
        after = report["target_after"]
        check(after is None or after["shape"] != report["target_before"]["shape"] or
              (after.get("hp", 1) < report["target_before"].get("hp", 1)) or
              bool(gdb.parse_and_eval("$target->hasFlags(Ultima::Ultima8::Item::FLG_BROKEN)")),
              "target_takes_damage_or_is_destroyed", after)
        screenshot(label + "-" + scenario + "-after.png")
    report["passed"] = True
except Exception as error:
    report["passed"] = False
    report["error"] = str(error)
finally:
    path = root / (label + "-" + scenario + ".json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("Gameplay probe:", path, "passed:", report.get("passed"), "error:", report.get("error"))
    try:
        gdb.execute("kill", to_string=True)
    except gdb.error:
        pass
    gdb.execute("quit %d" % (0 if report.get("passed") else 1))
