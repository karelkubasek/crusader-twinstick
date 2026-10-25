#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build an allowlisted Linux bundle and matching ScummVM source archive."""
import argparse
import concurrent.futures
import ctypes.util
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.stage_runtime import BASE, stage

SYSTEM_LIBS = {"libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1", "libresolv.so.2",
               "ld-linux-x86-64.so.2", "ld.so"}
SOURCE_DIRS = {"modern": {".py"}, "assets": {".svg", ".json"}, "scripts": {".py", ".sh"},
               "patches": {".patch"}, "docs": {".md"}, "tests": {".py"}, "licenses": None}
SOURCE_FILES = ("README.md", "NOTICE.md", "LICENSE", ".gitignore", ".gitattributes", "start.sh")


def run(command, **kwargs):
    return subprocess.check_output([str(x) for x in command], text=True, **kwargs).strip()


def source_files():
    for name in SOURCE_FILES:
        yield ROOT / name
    for directory, extensions in SOURCE_DIRS.items():
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and (extensions is None or path.suffix in extensions):
                yield path


def copy_sources(destination):
    for path in source_files():
        target = destination / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def dependencies(path):
    output = run(["ldd", path], stderr=subprocess.STDOUT)
    if "not found" in output:
        raise RuntimeError(f"Unresolved library for {path}: {output}")
    result = []
    for name, filename in re.findall(r"^\s*(\S+)\s+=>\s+(/\S+)", output, re.M):
        if "/" in name:
            if Path(name).name in SYSTEM_LIBS:
                continue
            raise RuntimeError(f"Unsupported absolute library dependency: {name}")
        result.append((name, Path(filename)))
    return result


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        while data := file.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()


def python_runtime(destination):
    runtime = destination / "runtime"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "lib").mkdir()
    python = runtime / "bin/python3"
    shutil.copy2(sys.executable, python)
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    standard = runtime / "python/lib" / version
    shutil.copytree(sysconfig.get_path("stdlib"), standard,
                    ignore=shutil.ignore_patterns("site-packages", "__pycache__", "*.pyc", "test", "tests", "idlelib", "turtledemo", "ensurepip", "lib-dynload"))
    extensions = standard / "lib-dynload"
    extensions.mkdir()
    # Include native modules used by the UI, importer and CLI, without desktop packages.
    for name in ("modern.ui", "modern.app", "zlib", "bz2", "lzma", "_zstd", "binascii", "pyexpat", "_elementtree"):
        importlib.import_module(name)
    roots = [(Path(sys.executable), python)]
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", "") or ""
        if filename.endswith(".so") and "/lib-dynload/" in filename:
            original = Path(filename)
            target = extensions / original.name
            shutil.copy2(original, target)
            roots.append((original, target))
    for name in ("tcl8.6", "tk8.6"):
        original = Path("/usr/lib") / name
        if not original.is_dir():
            raise RuntimeError(f"Missing Tcl/Tk runtime: {original}")
        shutil.copytree(original, runtime / "tcl" / name)
    (runtime / "bin/python3-loader").write_text('''#!/bin/sh
set -eu
CRUSADER_RUNTIME_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
exec "$CRUSADER_RUNTIME_DIR/bin/python3" "$@"
''')
    (runtime / "bin/python3-loader").chmod(0o755)
    return roots


def collect_native(destination, roots):
    library_dir = destination / "runtime/lib"
    libraries = {target.name: source.resolve() for source, target in roots if target.parent == library_dir}
    queue = [source for source, _ in roots]
    visited = set()
    while queue:
        source = queue.pop()
        real = source.resolve()
        if real in visited:
            continue
        visited.add(real)
        for soname, dependency in dependencies(source):
            if soname in SYSTEM_LIBS:
                continue
            if soname not in libraries:
                target = library_dir / soname
                shutil.copy2(dependency.resolve(), target)
                libraries[soname] = dependency.resolve()
                queue.append(dependency)
    # Strip host-specific RPATHs and ELF interpreters only in generated copies.
    patchelf = shutil.which("patchelf")
    if not patchelf:
        raise RuntimeError("Install patchelf to build a portable runtime")
    for _, target in roots:
        target.chmod(target.stat().st_mode | 0o200)
        run([patchelf, "--set-rpath", "$ORIGIN/" + os.path.relpath(library_dir, target.parent), target])
        if target.parent.name == "bin":
            run([patchelf, "--set-interpreter", "/lib64/ld-linux-x86-64.so.2", target])
    for soname in libraries:
        target = library_dir / soname
        target.chmod(target.stat().st_mode | 0o200)
        run([patchelf, "--set-rpath", "$ORIGIN", target])
    requirements = set()
    for target in [t for _, t in roots] + list(library_dir.iterdir()):
        requirements.update(re.findall(r"GLIBC_(\d+\.\d+)", run(["readelf", "--version-info", target])))
    minimum = max(requirements, key=lambda version: tuple(map(int, version.split("."))))
    return libraries, minimum


def component_records(paths):
    brew = json.loads(run(["brew", "info", "--json=v2", "--installed"]))["formulae"]
    formulae = {f["name"]: f for f in brew}
    records = {}
    for path in paths:
        real = path.resolve()
        if "/Cellar/" in str(real):
            tail = str(real).split("/Cellar/", 1)[1].split("/")
            name, version = tail[:2]
            item = formulae[name]
            if version.split("_")[0] != item["versions"]["stable"]:
                raise RuntimeError(f"Source metadata differs from installed {name} {version}")
            key = "homebrew-" + name
            records[key] = {"name": name, "version": version, "license": item["license"],
                            "source": item["urls"]["stable"], "prefix": str(real).split("/Cellar/")[0] + "/Cellar/" + "/".join(tail[:2])}
        else:
            name = run(["pacman", "-Qoq", real])
            key = "system-" + name
            info = run(["pacman", "-Qi", name], env={**os.environ, "LC_ALL": "C"})
            version = re.search(r"^Version\s*:\s*(.+)$", info, re.M).group(1)
            license_name = re.search(r"^Licenses\s*:\s*(.+)$", info, re.M).group(1)
            records[key] = {"name": name, "version": version, "license": license_name}
    system_sources = {
        "acl": "https://download.savannah.nongnu.org/releases/acl/acl-{version}.tar.xz",
        "libarchive": "https://libarchive.org/downloads/libarchive-{version}.tar.xz",
        "zstd": "https://github.com/facebook/zstd/releases/download/v{version}/zstd-{version}.tar.gz",
        "lz4": "https://github.com/lz4/lz4/releases/download/v{version}/lz4-{version}.tar.gz",
        "xz": "https://github.com/tukaani-project/xz/releases/download/v{version}/xz-{version}.tar.xz",
        "util-linux-libs": "https://www.kernel.org/pub/linux/utils/util-linux/v{series}/util-linux-{version}.tar.xz",
    }
    for key, record in records.items():
        if key.startswith("system-") and record["name"] in system_sources:
            version = record["version"].rsplit("-", 1)[0].split(":")[-1]
            url = system_sources[record["name"]].format(version=version, series=".".join(version.split(".")[:2]))
            record["source"] = {"url": url, "checksum": None}
    return records


def download_source(key, record, cache):
    source = record.get("source")
    if not source:
        return None
    url = source["url"].replace("http://", "https://", 1)
    name = Path(url.split("?", 1)[0]).name
    target = cache / name
    checksum = source.get("checksum")
    if not target.is_file() or (checksum and digest(target) != checksum):
        print(f"Downloading corresponding source: {key}", flush=True)
        temporary = target.with_suffix(target.suffix + ".part")
        request = urllib.request.Request(url, headers={"User-Agent": "CrusaderTwinStick-source-builder/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        if checksum and digest(temporary) != checksum:
            temporary.unlink()
            raise RuntimeError(f"Source checksum mismatch: {key}")
        temporary.replace(target)
    source["checksum"] = digest(target)
    return target


def collect_notices(destination, records, sources):
    directory = destination / "licenses/components"
    directory.mkdir(parents=True)
    for key, record in records.items():
        target = directory / key
        target.mkdir()
        root = Path(record.get("prefix", "/usr/share/licenses/" + record["name"]))
        found = []
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() and path.stat().st_size < 300000 and re.search(r"(copying|license|copyright|notice)", path.name, re.I):
                    if "/include/" not in str(path) or "license" in path.name.lower():
                        found.append(path)
        for index, path in enumerate(found):
            shutil.copy2(path, target / f"{index}-{path.name}")
        recipe_dir = root / ".brew"
        if recipe_dir.is_dir():
            for recipe in recipe_dir.glob("*.rb"):
                shutil.copy2(recipe, target / ("build-recipe-" + recipe.name))
        if key in sources:
            with tarfile.open(sources[key]) as archive:
                for index, member in enumerate(archive.getmembers()):
                    if member.isfile() and member.size < 300000 and re.fullmatch(r"(COPYING.*|LICENSE.*|NOTICE.*|COPYRIGHT.*)", Path(member.name).name, re.I):
                        payload = archive.extractfile(member).read()
                        (target / f"source-{index}-{Path(member.name).name}").write_bytes(payload)
        if record["name"] == "python":
            shutil.copy2(Path(sysconfig.get_path("stdlib")) / "LICENSE.txt", target / "LICENSE.txt")
        if not list(target.iterdir()):
            raise RuntimeError(f"Missing original license notice for {key}")
        public = {k: v for k, v in record.items() if k != "prefix"}
        (target / "component.json").write_text(json.dumps(public, indent=2) + "\n")


def apply_engine_patch(engine, expected_source, patch):
    environment = {key: value for key, value in os.environ.items() if key not in ("GIT_DIR", "GIT_WORK_TREE")}
    environment["GIT_CEILING_DIRECTORIES"] = str(engine.parent)
    subprocess.run(["git", "apply", str(patch)], cwd=engine, env=environment, check=True)
    for relative in re.findall(r"^\+\+\+ b/(.+)$", patch.read_text(), re.M):
        if (engine / relative).read_bytes() != (expected_source / relative).read_bytes():
            raise RuntimeError(f"Exported engine source differs from the verified build: {relative}")


def make_source_archive(workspace, target, sources):
    source = workspace / "vendor/scummvm"
    with tempfile.TemporaryDirectory(prefix="source-release-", dir=ROOT / "build") as name:
        staging = Path(name) / "crusader-twinstick-source"
        staging.mkdir()
        copy_sources(staging)
        (staging / "SCUMMVM-REVISION").write_text(BASE + "\n")
        engine = staging / "scummvm"
        engine.mkdir()
        process = subprocess.Popen(["git", "archive", BASE], cwd=source, stdout=subprocess.PIPE)
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            archive.extractall(engine, filter="data")
        if process.wait():
            raise RuntimeError("Could not export pinned ScummVM source")
        apply_engine_patch(engine, source, ROOT / "patches/scummvm-crusader-twin-stick.patch")
        (staging / "dependency-sources").mkdir()
        for source_file in sources.values():
            shutil.copy2(source_file, staging / "dependency-sources" / source_file.name)
        shutil.copytree(ROOT / "dist/CrusaderTwinStick-linux-x86_64/licenses", staging / "licenses", dirs_exist_ok=True)
        with tarfile.open(target, "w:gz", compresslevel=3) as archive:
            archive.add(staging, arcname=staging.name)


def build(workspace):
    workspace = Path(workspace).resolve()
    stage(workspace)
    (ROOT / "build/source-downloads").mkdir(parents=True, exist_ok=True)
    destination = ROOT / "dist/CrusaderTwinStick-linux-x86_64"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    copy_sources(destination)
    shutil.copytree(ROOT / "runtime-engine", destination / "runtime-engine")
    roots = python_runtime(destination)
    roots.append((workspace / "build/scummvm/scummvm", destination / "runtime-engine/bin/scummvm.bin"))
    tools = destination / "runtime-tools/bin"
    tools.mkdir(parents=True)
    for name in ("innoextract", "bsdtar"):
        original = Path(shutil.which(name)).resolve()
        target = tools / name
        shutil.copy2(original, target)
        roots.append((original, target))
    # SDL2-compat resolves SDL3 dynamically, outside ldd's dependency list.
    sdl_prefix = Path(run(["brew", "--prefix", "sdl3"]))
    sdl3 = next((sdl_prefix / "lib").glob("libSDL3.so.0"))
    sdl_target = destination / "runtime/lib/libSDL3.so.0"
    shutil.copy2(sdl3.resolve(), sdl_target)
    roots.append((sdl3, sdl_target))
    sdl2 = Path(run(["brew", "--prefix", "sdl2-compat"])) / "lib/libSDL2-2.0.so.0"
    sdl2_target = destination / "runtime/lib/libSDL2-2.0.so.0"
    shutil.copy2(sdl2.resolve(), sdl2_target)
    roots.append((sdl2, sdl2_target))
    gcc_prefix = Path(run(["brew", "--prefix", "gcc"]))
    for name in ("libstdc++.so.6", "libgcc_s.so.1"):
        original = gcc_prefix / "lib/gcc/current" / name
        target = destination / "runtime/lib" / name
        shutil.copy2(original.resolve(), target)
        roots.append((original, target))
    libraries, minimum = collect_native(destination, roots)
    records = component_records([p for p, target in roots if target.name != "scummvm.bin"] + list(libraries.values()) +
                                [Path("/usr/lib/libtcl8.6.so"), Path("/usr/lib/libtk8.6.so")])
    sources = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        pending = {pool.submit(download_source, key, record, ROOT / "build/source-downloads"): key for key, record in records.items()}
        for result in concurrent.futures.as_completed(pending):
            key = pending[result]
            path = result.result()
            if path:
                sources[key] = path
    collect_notices(destination, records, sources)
    engine_info = json.loads((destination / "runtime-engine/build.json").read_text())
    engine_info["unpatched_binary_sha256"] = engine_info["binary_sha256"]
    engine_info["binary_sha256"] = digest(destination / "runtime-engine/bin/scummvm.bin")
    (destination / "runtime-engine/build.json").write_text(json.dumps(engine_info, indent=2) + "\n")
    metadata = {"platform": "Linux x86_64", "minimum_glibc": minimum, "engine": engine_info,
                "components": {k: {n: v for n, v in r.items() if n != "prefix"} for k, r in records.items()}}
    (destination / "BUILD-INFO.json").write_text(json.dumps(metadata, indent=2) + "\n")
    source_archive = ROOT / "dist/CrusaderTwinStick-source.tar.gz"
    make_source_archive(workspace, source_archive, sources)
    (destination / "SOURCE.txt").write_text("Matching source: CrusaderTwinStick-source.tar.gz\nDistribute this application together with that source download and the included license notices.\n")
    archive_path = ROOT / "dist/CrusaderTwinStick-linux-x86_64.tar.gz"
    with tarfile.open(archive_path, "w:gz", compresslevel=5) as archive:
        archive.add(destination, arcname=destination.name)
    (ROOT / "dist/SHA256SUMS").write_text("".join(f"{digest(p)}  {p.name}\n" for p in (archive_path, source_archive)))
    print(json.dumps({"bundle": str(archive_path), "source": str(source_archive), "minimum_glibc": minimum}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    build(parser.parse_args().workspace)
