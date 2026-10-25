#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
CRUSADER_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$CRUSADER_ROOT/scripts/dev-env.sh"
cd -- "$CRUSADER_ROOT"
mkdir -p build/toolchain-check
read -r -a CRUSADER_SDL_FLAGS <<< "$(pkg-config --cflags --libs sdl2)"
"$CC" -std=c17 -g -Wall -Wextra -Werror -shared -fPIC \
    scripts/probes/probe-modern-sdl.c "${CRUSADER_SDL_FLAGS[@]}" \
    -o build/toolchain-check/probe-modern-sdl.so
exec /usr/bin/python3 scripts/run_engine_probes.py "$@"
