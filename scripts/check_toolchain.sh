#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
CRUSADER_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$CRUSADER_ROOT/scripts/dev-env.sh"
mkdir -p "$CRUSADER_ROOT/build/toolchain-check"
read -r -a CRUSADER_LIBRARY_FLAGS <<< "$(pkg-config --cflags --libs sdl2 freetype2 libpng zlib)"
"$CC" -std=c17 -g -O1 -Wall -Wextra -Werror "$CRUSADER_ROOT/scripts/probes/toolchain-smoke.c" \
    -o "$CRUSADER_ROOT/build/toolchain-check/c-smoke"
"$CXX" -std=c++11 -g -O1 -Wall -Wextra -Werror -pthread \
    "$CRUSADER_ROOT/scripts/probes/toolchain-smoke.cpp" "${CRUSADER_LIBRARY_FLAGS[@]}" \
    -o "$CRUSADER_ROOT/build/toolchain-check/cpp-smoke"
"$CRUSADER_ROOT/build/toolchain-check/c-smoke"
"$CRUSADER_ROOT/build/toolchain-check/cpp-smoke"
