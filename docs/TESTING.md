# Testing

Run all commands from this repository. Source, builds and private test inputs
live here; a separate development workspace is not required.

## Launcher and toolchain

```sh
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 scripts/check_repository.py
./scripts/check_toolchain.sh
```

The toolchain check compiles and runs C and C++ smoke tests with the same
Homebrew environment used by the engine. It checks threads, exceptions, SDL2,
FreeType, PNG and zlib without changing the system compiler.

## Native engine tests

```sh
./scripts/build_engine.sh
./scripts/build_engine.sh test
```

The native test runner must run from `build/scummvm` so its encoding resources
are found. The Make `test` target does this. To run one suite after building:

```sh
(cd build/scummvm && ./test/runner CruTwinStickMathTestSuite)
```

Use the default build target after engine changes to refresh `scummvm.dwp`
along with the executable before using GDB.

## Private gameplay probes

Import your game using `start.sh` or its `--install` option. The probes use the
verified resources under `user-data/installation/game-data`, or the location
selected by `CRUSADER_TWINSTICK_HOME`.

Private fixture inputs belong under `user-data/test-fixtures/`:

| File | Required state |
| --- | --- |
| `twin-integration-saves/remorse-twin-stick.001` | Pristine first-mission quicksave |
| `opening-saves/remorse-opening-probe.001` | The same mission-start state, under the gameplay target name |
| `opening-saves/remorse-opening-probe.000` | First-mission save containing camera item 9424 and robot actor 5 |

These local fixtures have been preserved for development. New checkouts must
supply equivalent saves from their own game. They contain game-derived data
and must never be committed or included in release archives.

With a graphical X11/XWayland session and an SDL-mapped controller connected:

```sh
./scripts/test_engine.sh
./scripts/test_engine.sh movement
./scripts/test_engine.sh save-load
./scripts/test_engine.sh gameplay
```

The runner copies fixtures to ignored working save directories under `runtime/`
and generates configs using the current repository paths. Player saves and
settings are not used or changed. `--fixtures /another/private/folder` selects
another fixture collection. The save/load group always saves before loading.

The GDB probes queue SDL events inside their own game process and check actor
positions, aiming, projectile vectors, collisions, target damage, focus loss,
and save/load behavior. GDB starts the game rather than attaching to it.
Only the matching Homebrew thread helper is added to GDB's auto-load safe path.
Logs and JSON results are written under `runtime/`; gameplay reports are under
`runtime/opening-investigation/`. Optional screenshots need `xdotool` and
`imlib2_grab`. These probes cover the X11 backend; they do not establish
Steam Deck Gaming Mode, suspend/resume or full-campaign compatibility.

## Portable release smoke test

Build the release with `python3 scripts/build_portable.py`, then run:

```sh
/usr/bin/python3 scripts/test_portable.py --installer /path/to/owned-installer.exe
```

Without `--installer`, the test uses the single No Remorse GOG installer under
ignored `installers/`. It imports into a temporary bundle, moves it to a path
with spaces, and checks the launcher, fullscreen game, remapper and return to
the launcher with a clean home and Homebrew removed from PATH. This interactive
X11/XWayland test needs `xdotool`, `xprop` and `imlib2_grab`; run it without
interacting with its windows. Results and logs remain under ignored `runtime/`.
