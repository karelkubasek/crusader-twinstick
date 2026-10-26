# Testing

Run all commands from this repository. A fresh checkout contains source and test
drivers. Build outputs are created by the commands below; game resources,
installers and save fixtures must come from your own copy. A separate development
workspace or previous investigation archive is not required.

## Inputs and generated files

Ignored paths in this guide describe generated outputs or private inputs, rather
than files supplied with the checkout:

| Path | How it is supplied |
| --- | --- |
| `vendor/scummvm/`, `build/scummvm/` | `scripts/build_engine.sh` fetches the pinned engine source and builds it |
| `build/toolchain-check/` | `scripts/check_toolchain.sh` and `scripts/test_engine.sh` compile the tracked smoke/probe sources |
| `runtime-engine/` | `scripts/stage_runtime.py` stages the built engine and its support resources |
| `dist/` | `scripts/build_portable.py` creates the player bundle, matching source and checksums |
| `runtime/` | The tracked engine and portable test drivers create working configs, fixture copies, logs and reports |
| `user-data/installation/` | `start.sh --install SOURCE` imports the player's supported game copy |
| `user-data/test-fixtures/` | The player supplies the save states described below; `--fixtures` accepts another location |
| `installers/` | An optional location for an owned installer; `--installer` accepts an explicit file elsewhere |

Pure Python and native engine unit tests do not require commercial game data.
Gameplay probes and the portable smoke flow require the private inputs described
in their sections. The test drivers create their own output directories.

The [reference-engine comparison](CONTROLLER-COMPARISON.md) records the shared
findings and implementation decisions. Its upstream references are pinned public
source links; a local reference-engine installation is optional. Historical
captures, one-off helpers and private review reports are not part of the shared
instructions. When reusing your own evidence, verify its save, configuration,
source revision and executable, preserve the original results, and use fresh
outputs. An old passing result does not validate the current build.

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

These fixtures are not included. Create equivalent saves in your own supported
game copy and copy them into the layout above, or pass `--fixtures` with a folder
containing that layout. The mission-start fixture can be made with a new game
and a quicksave; the camera/robot case additionally requires the stated objects
to be present. They contain game-derived data and must never be committed or
included in release archives.

With a graphical X11/XWayland session and an SDL-mapped controller connected:

```sh
./scripts/test_engine.sh
./scripts/test_engine.sh movement
./scripts/test_engine.sh animation
./scripts/test_engine.sh save-load
./scripts/test_engine.sh gameplay
./scripts/test_engine.sh startup
```

The runner copies fixtures to ignored working save directories under `runtime/`
and generates configs using the current repository paths. Player saves and
settings are not used or changed. `--fixtures /another/private/folder` selects
another fixture collection. The save/load group always saves before loading.

The startup group checks both movie preferences, the first Y press without
opening a ScummVM dialog, classic controls, the original main menu with a
previous save present, bright menu focus and mouse/controller handoff, Save
availability before and after loading, controller quit confirmation (default No, selecting both
answers, cancel, and confirming Yes exits cleanly), New Game and difficulty
selection, cancelling difficulty with B or Escape and reopening it, mission cutscenes,
and an explicit save load. It uses the first-mission fixture and isolated
configs under `runtime/startup/`. Normal Crusader launches ignore `lastSave`
and show the menu; an explicit engine `--save-slot` still loads directly.

The animation group measures walking with the weapon drawn and holstered,
including frame cadence across stride boundaries, continuous movement, render
interpolation and alignment between the physical avatar anchor and following camera,
weapon changes while walking, and scripted animation handoffs. It also checks that
classic rendering keeps its existing setting and that paused scenes remain
still. The holstered case walks horizontally and measures the opaque helmet pixels
at their actual display-list position, rejecting frame-origin jumps above two
native pixels. A stable physical anchor alone cannot pass this check.
Like the other groups, it uses
private fixture copies rather than player saves.

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

## Test inventory and overlap audit

The Python suite contains 42 test methods: two duplicate configuration tests
were consolidated, and three controller-navigation behavior tests were added.
The native runner contains 454 upstream ScummVM tests
and 13 project-specific input/math tests; the upstream suites are retained.
Engine reports count assertions inside launched scenarios, rather than separate
tests: the current matrix has 16 scenarios. The portable smoke test is one
end-to-end scenario with multiple checkpoints. Report these counts separately.

The 2026-10-25 audit covered the project-owned Python tests, native controller
suites, GDB probes and portable smoke driver. It consolidated the duplicate
binding-ownership loop and deadzone validation, removed unused projectile/save
breakpoints from persistence probes, and changed animation process identity
into a diagnostic. Visible cadence and seamless animation handoffs are the
requirements; keeping one process ID is not. The pause/interpolation check
runs once with twin-stick enabled instead of repeating an invariant in all
three animation scenarios.

Some overlap is intentional: pure direction math cannot detect broken SDL
mapping; configuration persistence cannot prove movies skip in the engine;
importer transaction tests cannot prove a relocated bundle works. Armed and
holstered gait, item versus actor damage, direct versus menu-driven loading,
and classic versus twin-stick input exercise different paths and remain.
Startup scenarios repeat some menu assertions; their distinct first-input
and movie-preference paths justify keeping them together for now.

During development, run the Python suite plus the engine group affected by
the change. Run the full engine matrix and portable smoke test before a
release or changes spanning startup, input and packaging. Avoid repeating the
full GUI matrix after documentation-only edits.
