# Crusader Twin Stick

An unofficial Linux launcher for **Crusader: No Remorse**, with independent
left-stick movement, right-stick aiming, and a configurable gamepad layout.
Powered by a locally modified ScummVM engine.

Version **1.0.0** is the first stable release. See the [release notes](CHANGELOG.md)
for features, supported platforms and testing limits. Run `./start.sh --version`
to check the launcher version.

## Play

Unpack a complete portable release and run `start.sh`. The first build targets
Linux x86_64 with glibc 2.38 or newer and a working desktop graphics/audio stack.
Python/Tk, SDL, the game runtime and import tools are bundled.

The hub accepts either your GOG offline installer or an existing complete
game folder. It checks the supported GOG English 1.21 data and installs a private
copy, leaving your source files alone. Once installed, choose **Play Crusader**,
**Controller layout** or **Settings**. Controller layout provides the diagram,
button remapping and SVG export; Settings provides independent stick deadzones
and the live preview. Fullscreen and opening-movie choices stay on the hub.

Play opens Crusader's original main menu, where you can choose **New Game**
or **Load Game**. New Game opens difficulty selection. **Skip opening movies**
is checked by default beside Fullscreen; uncheck it to watch the startup movies.
Press **Y** to skip a movie while it is playing. Mission cutscenes remain enabled.

Twin-stick movement smooths rendered positions between simulation frames and
keeps walking cycles continuous with the weapon drawn or holstered.

The Silencer portrait is extracted from your GOG icon when available. Game
files and artwork are not included in this repository or release archives.
A private PNG at `user-data/artwork/launcher.png` overrides that portrait (under
`CRUSADER_TWINSTICK_HOME` when set). The launcher fits the complete image into
the artwork panel, preserving its proportions and keeping logos and heads visible.

In Steam Deck Desktop Mode, hold **≡ Menu** to select the Gamepad action set.
For Gaming Mode, add `start.sh` as a non-Steam game with a Gamepad layout and
Proton disabled. The launcher also works with ordinary Linux gamepads.
The Desktop Mode hint is hidden for explicitly identified Gamescope sessions;
it remains visible in desktop sessions and when the session cannot be identified.

In the launcher, use **D-pad** to move focus, **A** to select, **B** to go back,
and **LB/RB** to switch pages. Left/right adjusts a focused stick setting;
the sticks remain available for the live preview in Settings.
Controller input waits for neutral after returning from the game or changing
pages, so a held button cannot select an action in the new screen.

In the original game menu, use the **D-pad** and **A** to choose an entry or
difficulty. The focused main-menu option uses the original brightened artwork,
with the same selection shared by controller, keyboard and mouse hover.
**B/Y** or **Escape** returns from difficulty selection to the main
menu. The quit confirmation starts on **No**; select **Yes** with the
**D-pad**, then press **A** to quit. **B/Y** cancels menus; **A/Y** skips movies. These are GUI defaults
and respect explicit ScummVM GUI remaps. Body poses have a small direction
buffer to avoid jitter near animation-sector boundaries; projectile aim stays
continuous. The following camera and avatar share position interpolation
between simulation frames. The walking sprites
also compensate their original frame-origin changes along the gait direction,
retaining normal bobbing. Unarmed sprites have eight facings and armed poses can
have sixteen; movement and aiming remain continuous. The [reference-engine comparison](docs/CONTROLLER-COMPARISON.md)
records the source review, runtime results and remaining feature decisions.

## Local files

By default, personal files are kept beside the app under `user-data/`:

| Path | Purpose |
| --- | --- |
| `user-data/installation/game-data/` | Imported, verified game resources |
| `user-data/installation/artwork/` | Artwork extracted from your copy |
| `user-data/scummvm.ini` | Settings and custom bindings |
| `user-data/saves/` | Player saves |
| `user-data/logs/` | Installation and game logs |

Set `CRUSADER_TWINSTICK_HOME` to use a different personal-data directory.
Reinstalling game files keeps saves and settings. An unsuccessful or cancelled
import leaves a working installation in place.

## Develop

The source launcher uses Python 3.11+ with Tk and SDL2. Installer import needs
`innoextract`; importing a GOG installation with `GAME.GOG` needs `bsdtar`.
Complete portable releases bundle these dependencies.

```sh
./start.sh
/usr/bin/python3 -m unittest discover -s tests -v
./start.sh --install /path/to/setup_crusader_no_remorse.exe
./start.sh --status
./start.sh --play
```

The runtime is generated under `runtime-engine/` and is deliberately ignored
by Git. The complete engine patch is under `patches/`, pinned to ScummVM commit
`a822b48a2ddd1bcdf742935f89ee94942e49539b`.

Build and stage the engine inside this repository:

```sh
./scripts/build_engine.sh
python3 scripts/stage_runtime.py
```

This checks the source revision and patch before copying the executable and
its ScummVM support resources. It does not copy commercial game data.
A source checkout without a staged runtime can display the UI and import data,
but cannot play until the runtime has been built or supplied.

Engine sources live in ignored `vendor/scummvm/` and builds in ignored
`build/scummvm/`. See [testing instructions](docs/TESTING.md) for native tests,
controller/gameplay probes, and the portable release smoke test. Private game
data, installers and save fixtures stay in ignored local directories.

## Portable artifacts

The release builder produces these ignored local artifacts:

- `dist/CrusaderTwinStick-linux-x86_64.tar.gz`: the player bundle, without game files.
- `dist/CrusaderTwinStick-source.tar.gz`: matching source and dependency sources.
- `dist/SHA256SUMS`: archive checksums.

See [build instructions](docs/BUILDING.md). Before publishing, run
`python3 scripts/check_repository.py` and the unit tests. The complete bundle
has also been exercised from a moved folder with spaces in its path, a clean
home directory and Homebrew removed from PATH. Game import, fullscreen launch,
controller remapping and return to the launcher were checked using X11.
Other Linux distributions and Steam Deck Gaming Mode still need release tests.

## Licensing and source

Launcher code and engine modifications are licensed under **GPL-3.0-or-later**;
see `LICENSE`. ScummVM retains its upstream copyright notices and licenses.
`NOTICE.md` and `licenses/` record third-party material. Binary releases must be
accompanied by their matching source release and dependency notices.

Crusader: No Remorse and its artwork remain the property of their original
rights holders. This project is unofficial and does not include those assets.
The file inventory under `assets/` contains only names, sizes and checksums.

## Repository boundaries

Development follows Git flow: `develop` is the integration branch and `main`
is the protected, stable default branch. See the [workflow guide](docs/WORKFLOW.md)
for feature branches, releases and hotfixes.

Game files, installers, extracted art, saves, generated runtimes, build outputs
and release archives are ignored. Release builders use an explicit allowlist;
they do not package the whole working directory. No GitHub remote is required
to develop or run the application.

Assisted-by: Codex:GPT-6. The engine patch is a local modification; no upstream
ScummVM commit or pull request has been submitted.
