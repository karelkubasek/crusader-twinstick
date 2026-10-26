# Building and source releases

The launcher is Python source. The game runtime is ScummVM at commit
`a822b48a2ddd1bcdf742935f89ee94942e49539b`, with the complete local patch applied.
No proprietary game files are required to compile it.

The verified development toolchain uses Homebrew GCC 16, glibc headers,
Make, pkgconf, SDL2-compat/SDL3, libpng and FreeType. On this SteamOS machine:

```sh
brew install gcc glibc make pkgconf sdl2-compat libpng freetype patchelf innoextract
brew postinstall gcc
./scripts/build_engine.sh
python3 scripts/stage_runtime.py
/usr/bin/python3 -m unittest discover -s tests -v
```

The build script fetches only the pinned open-source ScummVM source. A full
source release already contains the patched tree under `scummvm/`; the script
uses it directly. The split-debug development configuration matches the tested
engine; debug packages need not be included in player releases.

`stage_runtime.py` checks the revision and reverse-applicability of the exact
patch before accepting a development runtime. It copies the executable, theme
resources, required engine support data, upstream notices and build provenance.
It copies no Crusader resources.

To produce the portable Linux x86_64 distribution and matching source archive:

```sh
/usr/bin/python3 scripts/build_portable.py
```

The workspace defaults to this repository, with the Git checkout under
`vendor/scummvm` and the executable at `build/scummvm/scummvm`. An optional
workspace argument supports a separate build;
no neighboring project directory is required. This builder currently runs on the
verified SteamOS/Homebrew development host. It collects Python/Tk, SDL, the
import tools and their native dependencies, removes host-specific ELF paths
with patchelf, records exact components, gathers notices and downloads verified
upstream component source archives. It excludes the system C library and
platform graphics/audio drivers. `BUILD-INFO.json` records the required glibc
version and the launcher release version from `modern/__init__.py`.
Linux x86_64 with a graphical session is the supported release target.

The builder writes under ignored `dist/` and `build/` directories. The player
archive must be offered together with `CrusaderTwinStick-source.tar.gz` and
`SHA256SUMS`. The source archive contains the complete patched ScummVM tree,
launcher source, build scripts, notices and component source archives.
Do not publish an archive from a build that failed to finish these steps.

Game input is supplied only at runtime. The installation catalog contains file
identities, not game contents. Release content comes from an explicit source
allowlist plus generated runtime components, never from `user-data/`.

The portable runtime is verified on this host and by launching from a moved
folder with a clean environment. Additional Linux distributions and Steam Deck
Gaming Mode still need release testing. Packaging does not establish wider
platform compatibility by itself.

See [TESTING.md](TESTING.md) for the native suite and private gameplay fixtures.
