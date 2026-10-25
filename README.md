# Crusader Twin Stick

An unofficial Linux launcher for **Crusader: No Remorse**, with independent
left-stick movement, right-stick aiming, and a configurable gamepad layout.
Powered by a locally modified ScummVM engine.

## Play

Unpack a complete portable release and run `start.sh`. The first build targets
Linux x86_64 with glibc 2.38 or newer and a working desktop graphics/audio stack.
Python/Tk, SDL, the game runtime and import tools are bundled.

The default **Game** tab accepts either your GOG offline installer or an
existing complete game folder. It checks the supported GOG English 1.21 data,
installs a private copy, and then offers **Play Crusader**. Your source files
are left alone. The other tabs retain the controller diagram, button remapping,
fullscreen setting and independent stick deadzones.

The Silencer portrait is extracted from your GOG icon when available. Game
files and artwork are not included in this repository or release archives.

In Steam Deck Desktop Mode, hold **≡ Menu** to select the Gamepad action set.
For Gaming Mode, add `start.sh` as a non-Steam game with a Gamepad layout and
Proton disabled. The launcher also works with ordinary Linux gamepads.

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

To stage the verified engine from the existing development workspace:

```sh
python3 scripts/stage_runtime.py /path/to/crusader
```

This checks the source revision and patch before copying the executable and
its ScummVM support resources. It does not copy commercial game data.
A source checkout without a staged runtime can display the UI and import data,
but cannot play until the runtime has been built or supplied.

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
