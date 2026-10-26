# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure gait continuity and rendered movement using the private mission save."""
import itertools
import json
import os
from pathlib import Path
import traceback

import gdb

gdb.execute("set pagination off")
gdb.execute("set confirm off")
gdb.execute("set debuginfod enabled off")
gdb.execute("set print thread-events off")
stance = os.environ["CRUSADER_ANIMATION_CASE"]
report = {"stance": stance, "results": [], "samples": [], "render_factors": {}, "passed": False}
phase = None
queued_animation = 0


class Tick(gdb.Breakpoint):
    def __init__(self):
        super().__init__("Ultima::Ultima8::Kernel::runProcesses", internal=True)
        self.silent = True


class Render(gdb.Breakpoint):
    def __init__(self):
        super().__init__("Ultima::Ultima8::Ultima8Engine::paint", internal=True)

    def stop(self):
        if phase:
            report["render_factors"].setdefault(phase, []).append(int(engine()["_lerpFactor"]))
        return False


class QueuedAnimation(gdb.Breakpoint):
    def __init__(self):
        super().__init__("Ultima::Ultima8::ActorAnimProcess::init", internal=True)

    def stop(self):
        if queued_animation and int(gdb.selected_frame().read_var("this")["_pid"]) == queued_animation:
            report["queued_animation_started"] = True
        return False


class RenderedAvatar(gdb.Breakpoint):
    def __init__(self):
        super().__init__("Ultima::Ultima8::ItemSorter::PaintDisplayList", internal=True)
        self.sprite = None
        self.heads = {}

    def stop(self):
        if phase == "moving":
            value = actor()
            sorter = gdb.selected_frame().read_var("this")
            x = int(value["_ix"])
            y = int(value["_iy"])
            z = int(value["_iz"])
            report.setdefault("rendered_avatar", []).append([
                int((x-y)/4) - int(sorter["_camSx"]),
                int((x+y)/8) - z - int(sorter["_camSy"])])
            if stance == "holstered":
                if self.sprite is None or not int(self.sprite) or int(self.sprite["_itemNum"]) != 1 or int(self.sprite["_order"]) != -1:
                    self.sprite = sorter["_items"]
                    while int(self.sprite) and int(self.sprite["_itemNum"]) != 1:
                        self.sprite = self.sprite["_next"]
                if int(self.sprite):
                    sprite = self.sprite
                    number = int(sprite["_frame"])
                    frame = sprite["_shape"]["_frames"]["_storage"][number]
                    if number not in self.heads:
                        surface = frame["_surface"]
                        width, height, pitch = (int(surface[key]) for key in ("w", "h", "pitch"))
                        pixels = gdb.selected_inferior().read_memory(int(surface["pixels"]), pitch * min(height, 10)).tobytes()
                        opaque = [(x, y) for y in range(min(height, 10)) for x in range(width)
                                  if pixels[y * pitch + x] != int(frame["_keycolor"])]
                        self.heads[number] = [sum(point[axis] for point in opaque) / len(opaque) for axis in (0, 1)]
                    hx, hy = self.heads[number]
                    head_x = int(frame["_xoff"]) - 1 - hx if int(sprite["_flags"]) & 0x20 else hx - int(frame["_xoff"])
                    report.setdefault("rendered_head", []).append([
                        int(sprite["_sxBot"]) + head_x, int(sprite["_syBot"]) - int(frame["_yoff"]) + hy])
        return False


class InputReset(gdb.Breakpoint):
    def __init__(self):
        super().__init__("Ultima::Ultima8::CruAvatarMoverProcess::resetStick", internal=True)

    def stop(self):
        if phase == "moving":
            caller = gdb.selected_frame().older()
            report.setdefault("input_resets", []).append({"caller": caller.name(),
                "stasis": bool(engine()["_avatarInStasis"])})
        return False


def engine():
    return gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance")


def actor():
    return engine()["_objectManager"]["_objects"]["_storage"][1].cast(
        gdb.lookup_type("Ultima::Ultima8::MainActor").pointer())


def ticks(count):
    for _ in range(count):
        gdb.execute("continue", to_string=True)


def axis(number, value):
    if int(gdb.parse_and_eval("(int)crusader_probe_axis(%d,%d)" % (number, value))) != 1:
        raise AssertionError("SDL axis was not queued")


def sample():
    value = actor()
    state = {name: int(value["_" + name]) for name in ("x", "y", "z", "frame", "animFrame")}
    mover = engine()["_avatarMoverProcess"].cast(gdb.lookup_type("Ultima::Ultima8::CruAvatarMoverProcess").pointer())
    state["pid"] = int(mover["_modernAnimation"])
    if state["pid"]:
        process = gdb.parse_and_eval("Ultima::Ultima8::Ultima8Engine::_instance->_kernel->getProcess(%d)" % state["pid"])
        if int(process):
            process = process.cast(gdb.lookup_type("Ultima::Ultima8::ActorAnimProcess").pointer())
            tracker = process["_tracker"]
            if int(tracker):
                state["index"] = int(tracker["_currentFrame"])
                state["data_action"] = int(tracker["_animAction"]["_action"])
                state["ticks_per_frame"] = int(tracker["_animAction"]["_frameRepeat"]) + 1
    return state


def check(condition, name, details=None):
    report["results"].append({"test": name, "passed": bool(condition), "details": details})
    if not condition:
        raise AssertionError(name)


Tick()
Render()
QueuedAnimation()
RenderedAvatar()
InputReset()
try:
    gdb.execute("run", to_string=True)
    for _ in range(2400):
        if int(actor()["_mapNum"]) == 1 and int(actor()["_x"]) > 1000 and not bool(engine()["_avatarInStasis"]):
            break
        ticks(1)
    else:
        raise AssertionError("Mission save did not load")
    library = Path("build/toolchain-check/probe-modern-sdl.so").resolve()
    gdb.parse_and_eval("(void*)dlopen(%s,2)" % json.dumps(str(library)))
    gdb.set_convenience_variable("hero", actor())
    gdb.parse_and_eval("(void)$hero->" + ("clearInCombat()" if stance == "holstered" else "setInCombat(0)"))
    ticks(40)
    phase = "moving"
    if stance != "classic":
        axis(0, 24000)
        axis(1, 0 if stance == "holstered" else 24000)
        ticks(4)
        for _ in range(160):
            ticks(1)
            report["samples"].append(sample())
        samples = report["samples"]
        check(all("index" in s for s in samples), "walking_animation_stays_live_between_strides")
        # Process identity helps debugging; a seamless handoff is also valid.
        report["walking_process_ids"] = sorted({s["pid"] for s in samples})
        holds = [(key, len(list(group))) for key, group in itertools.groupby(samples, key=lambda s: s["index"])]
        interval = samples[0]["ticks_per_frame"]
        check(len(holds) > 20 and all(count == interval for _, count in holds[1:-1]),
              "stride_boundaries_keep_the_data_frame_cadence", holds)
        check(len({s["frame"] for s in samples}) >= 6, "walking_visits_the_full_gait")
        check(samples[-1]["x"] != samples[0]["x"] or samples[-1]["y"] != samples[0]["y"],
              "gait_runs_alongside_real_movement")
        projected = report.get("rendered_avatar", [])[8:50]
        spread = [max(point[axis] for point in projected) - min(point[axis] for point in projected)
                  for axis in (0, 1)] if projected else []
        check(len(projected) >= 10 and all(value <= 1 for value in spread),
              "following_camera_keeps_physics_anchor_stable", spread)
        if stance == "holstered":
            heads = report.get("rendered_head", [])[8:85]
            largest_step = max((abs(after[0] - before[0]) for before, after in zip(heads, heads[1:])), default=999)
            check(len(heads) >= 32 and largest_step <= 2,
                  "visible_walking_sprite_has_no_large_horizontal_origin_jumps", largest_step)
        if stance == "drawn":
            weapon = gdb.parse_and_eval("(Ultima::Ultima8::Item*)Ultima::Ultima8::ItemFactory::createItem(0x332,0,0,0,0,1,0,true)")
            gdb.set_convenience_variable("weapon", weapon)
            gdb.parse_and_eval("(int)$hero->addItemCru($weapon,false)")
            for small, name in ((False, "large"), (True, "small")):
                gdb.parse_and_eval("(int)crusader_probe_button(3,1)")
                ticks(2)
                gdb.parse_and_eval("(int)crusader_probe_button(3,0)")
                ticks(24)
                expected = int(gdb.parse_and_eval("Ultima::Ultima8::AnimDat::getActionNumberForSequence("
                                                  "Ultima::Ultima8::Animation::advance,$hero)"))
                is_small = bool(gdb.parse_and_eval("$hero->activeWeaponIsSmall()"))
                check(is_small is small and sample().get("data_action") == expected,
                      name + "_weapon_change_updates_walking_pose", {"expected": expected, "sample": sample()})
        walking_pid = sample()["pid"]
        queued_animation = int(gdb.parse_and_eval("$hero->doAnimAfter(Ultima::Ultima8::Animation::stand,"
                                                  "Ultima::Ultima8::dir_current,%d)" % walking_pid))
        for _ in range(80):
            ticks(1)
            if report.get("queued_animation_started"):
                break
        check(report.get("queued_animation_started"), "scripted_animation_can_follow_a_walking_stride")
        ticks(12)
        check("index" in sample(), "walking_resumes_after_the_scripted_animation")
        axis(0, 0)
        axis(1, 0)
    else:
        ticks(40)
    factors = report["render_factors"]["moving"]
    if stance == "classic":
        check(all(factor == 256 for factor in factors), "classic_rendering_keeps_its_existing_setting")
    else:
        check(len(set(factor for factor in factors if 0 < factor < 256)) > 2,
              "movement_renders_between_simulation_frames", sorted(set(factors)))
    if stance == "holstered":
        phase = "paused"
        gdb.parse_and_eval("(void)Ultima::Ultima8::Ultima8Engine::_instance->_kernel->pause()")
        ticks(10)
        check(report["render_factors"].get("paused") and all(factor == 256 for factor in report["render_factors"]["paused"]),
              "paused_world_does_not_interpolate")
        gdb.parse_and_eval("(void)Ultima::Ultima8::Ultima8Engine::_instance->_kernel->unpause()")
    report["passed"] = True
except Exception as error:
    report["error"] = str(error)
    traceback.print_exc()
finally:
    path = Path("runtime/animation-" + stance + ".json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("Animation probe:", path, "passed:", report["passed"], "error:", report.get("error"))
    try:
        gdb.execute("kill", to_string=True)
    except gdb.error:
        pass
    gdb.execute("quit %d" % (0 if report["passed"] else 1))
