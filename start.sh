#!/bin/sh
set -eu
CRUSADER_APP_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
cd -- "$CRUSADER_APP_DIR"
if [ -x "$CRUSADER_APP_DIR/runtime/bin/python3" ]; then
    export PYTHONHOME="$CRUSADER_APP_DIR/runtime/python"
    export TCL_LIBRARY="$CRUSADER_APP_DIR/runtime/tcl/tcl8.6"
    export TK_LIBRARY="$CRUSADER_APP_DIR/runtime/tcl/tk8.6"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="$CRUSADER_APP_DIR"
    export SDL_JOYSTICK_LINUX_CLASSIC="${SDL_JOYSTICK_LINUX_CLASSIC:-1}"
    export LD_LIBRARY_PATH="$CRUSADER_APP_DIR/runtime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    exec "$CRUSADER_APP_DIR/runtime/bin/python3-loader" -m modern.app "$@"
fi
exec /usr/bin/python3 -m modern.app "$@"
