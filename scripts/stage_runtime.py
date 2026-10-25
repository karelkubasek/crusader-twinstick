#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stage a verified development engine; generated binaries never enter Git."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
BASE = "a822b48a2ddd1bcdf742935f89ee94942e49539b"


def source_directory(workspace):
    expanded = workspace / "scummvm"
    return expanded if (expanded / "configure").is_file() else workspace / "vendor/scummvm"


def stage(workspace=ROOT):
    workspace = Path(workspace).resolve()
    source = source_directory(workspace)
    binary = workspace / "build/scummvm/scummvm"
    patch = ROOT / "patches/scummvm-crusader-twin-stick.patch"
    environment = {key: value for key, value in os.environ.items() if key not in ("GIT_DIR", "GIT_WORK_TREE")}
    environment["GIT_CEILING_DIRECTORIES"] = str(source.parent)
    if (source / ".git").exists():
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, env=environment, text=True).strip()
    else:
        revision = (workspace / "SCUMMVM-REVISION").read_text().strip()
    if revision != BASE:
        raise RuntimeError("Unexpected ScummVM source revision")
    subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=source, env=environment, check=True)
    destination = ROOT / "runtime-engine"
    (destination / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, destination / "bin/scummvm.bin")
    wrapper = destination / "bin/scummvm"
    wrapper.write_text('''#!/bin/sh
set -eu
CRUSADER_ENGINE_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
CRUSADER_RUNTIME_DIR="$CRUSADER_ENGINE_DIR/../runtime"
if [ -f "$CRUSADER_RUNTIME_DIR/lib/ld-linux-x86-64.so.2" ]; then
    exec "$CRUSADER_RUNTIME_DIR/lib/ld-linux-x86-64.so.2" --library-path "$CRUSADER_RUNTIME_DIR/lib" "$CRUSADER_ENGINE_DIR/bin/scummvm.bin" "$@"
fi
exec "$CRUSADER_ENGINE_DIR/bin/scummvm.bin" "$@"
''')
    wrapper.chmod(0o755)
    for name in ("engine-data", "themes"):
        target = destination / "share" / name
        target.mkdir(parents=True, exist_ok=True)
        if name == "engine-data":
            for filename in ("ultima8.dat", "encoding.dat"):
                shutil.copy2(source / "dists/engine-data" / filename, target / filename)
        else:
            shutil.copytree(source / "gui/themes", target, dirs_exist_ok=True)
    licenses = destination / "licenses"
    licenses.mkdir(exist_ok=True)
    for name in ("COPYING", "AUTHORS", "COPYRIGHT"):
        shutil.copy2(source / name, licenses / name)
    shutil.copytree(source / "LICENSES", licenses / "LICENSES", dirs_exist_ok=True)
    metadata = {"source_revision": BASE, "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
                "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
    (destination / "build.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path, nargs="?", default=ROOT)
    args = parser.parse_args()
    print(json.dumps(stage(args.workspace), indent=2))
