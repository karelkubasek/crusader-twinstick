# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import json
import subprocess
import sys

from . import __version__, core
from .install import import_game, installation_status

def gui():
    from .ui import gui as show_gui
    show_gui()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=f"Crusader Twin Stick {__version__}")
    parser.add_argument("--play", action="store_true")
    parser.add_argument("--install", metavar="SOURCE", help="Import a GOG installer or complete game folder")
    parser.add_argument("--status", action="store_true", help="Report installation readiness")
    args = parser.parse_args()
    try:
        if args.install:
            import_game(args.install, lambda percent, message: print(f"{percent:3}% {message}", flush=True))
            core.save_settings(core.load_settings())
        if args.status:
            status = installation_status()
            print(json.dumps({"installed": status.ready, "message": status.message,
                              "edition": status.edition, "runtime_available": core.BINARY.is_file()}))
            return 0 if status.ready else 1
        if args.play:
            return core.launch().wait()
        elif not args.install:
            gui()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
