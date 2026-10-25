#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the private first-mission regression fixtures against the local engine."""
import argparse
import configparser
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from modern import core
from scripts.stage_runtime import source_directory


def write_config(path, target, saves):
    source = source_directory(ROOT)
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config["scummvm"] = {"themepath": str(source / "gui/themes")}
    config[target] = {
        "gameid": "remorse", "engineid": "ultima", "path": str(core.DATA),
        "extrapath": str(source / "dists/engine-data"), "savepath": str(saves),
        "joystick_num": "0", "fullscreen": "false", "skip_intro": "true",
        "crusader_modern_controls": "true", "crusader_twin_stick": "true",
        "crusader_stick_deadzone": "15", "crusader_aim_deadzone": "15",
        "crusader_stick_hysteresis": "5",
        **{"keymap_remorse_" + key: value for key, value in core.KEYS.items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as output:
        config.write(output, space_around_delimiters=False)


def prepare_fixtures(fixtures, group):
    copies = []
    if group in ("movement", "save-load", "all"):
        copies.append((fixtures / "twin-integration-saves/remorse-twin-stick.001",
                       ROOT / "runtime/twin-integration-saves/remorse-twin-stick.001"))
    if group in ("gameplay", "all"):
        for slot in ("000", "001"):
            copies.append((fixtures / f"opening-saves/remorse-opening-probe.{slot}",
                           ROOT / f"runtime/opening-investigation/saves/remorse-opening-probe.{slot}"))
    for source, _ in copies:
        if not source.is_file():
            raise FileNotFoundError(f"Missing private save fixture: {source}. See docs/TESTING.md.")
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def run_probe(script, config, slot, target, report, environment, safe_path):
    report.unlink(missing_ok=True)
    command = ["gdb", "-q", "-batch", "-iex", "add-auto-load-safe-path " + str(safe_path),
               "-x", str(ROOT / "scripts/probes" / script), "--args",
               str(ROOT / "build/scummvm/scummvm"), "--config=" + str(config),
               "--save-slot=" + str(slot), target]
    log = report.with_suffix(".log")
    with log.open("w") as output:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            result = process.wait(timeout=300)
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
    if result or not report.is_file() or json.loads(report.read_text()).get("passed") is not True:
        raise RuntimeError(f"Probe failed: {script}; inspect {log}")
    checks = len(json.loads(report.read_text())["results"])
    print(f"{report.name}: {checks} checks passed", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", nargs="?", choices=("movement", "save-load", "gameplay", "all"), default="all")
    parser.add_argument("--fixtures", type=Path, default=core.STATE / "test-fixtures")
    args = parser.parse_args()
    core.prepare_data()
    for name in ("build/scummvm/scummvm", "build/scummvm/scummvm.dwp",
                 "build/toolchain-check/probe-modern-sdl.so"):
        if not (ROOT / name).is_file():
            raise FileNotFoundError(f"Missing {name}; build the engine and run scripts/test_engine.sh.")
    prepare_fixtures(args.fixtures.expanduser().resolve(), args.group)
    movement_config = ROOT / "runtime/scummvm-twin-probe.ini"
    opening_config = ROOT / "runtime/opening-investigation/twin.ini"
    write_config(movement_config, "remorse-twin-stick", ROOT / "runtime/twin-integration-saves")
    write_config(opening_config, "remorse-opening-probe", ROOT / "runtime/opening-investigation/saves")
    prefix = Path(subprocess.check_output(["brew", "--prefix"], text=True).strip())
    safe_path = (prefix / "opt/glibc/lib/libthread_db.so.1").resolve()
    environment = {**os.environ, "SDL_JOYSTICK_LINUX_CLASSIC": "1", "SDL_VIDEODRIVER": "x11",
                   "SDL_AUDIODRIVER": "dummy", "CRUSADER_BUILD_LABEL": "fixed"}
    jobs = []
    if args.group in ("movement", "all"):
        jobs.append(("probe-twin-stick.py", movement_config, 1, "remorse-twin-stick",
                     ROOT / "runtime/twin-integration-results.json"))
    if args.group in ("save-load", "all"):
        for action, slot in (("save", 1), ("load", 2)):
            jobs.append((f"probe-twin-{action}.py", movement_config, slot, "remorse-twin-stick",
                         ROOT / f"runtime/twin-{action}-results.json"))
    for job in jobs:
        run_probe(*job, environment, safe_path)
    if args.group in ("gameplay", "all"):
        for scenario in ("opening_downright", "opening_upstep", "opening_right", "camera", "robot"):
            report = ROOT / f"runtime/opening-investigation/fixed-{scenario}.json"
            run_probe("probe-twin-gameplay.py", opening_config, 0 if scenario in ("camera", "robot") else 1,
                      "remorse-opening-probe", report, {**environment, "CRUSADER_SCENARIO": scenario}, safe_path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
