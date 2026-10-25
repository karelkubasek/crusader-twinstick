#!/bin/bash
set -eu
CRUSADER_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$CRUSADER_ROOT/scripts/dev-env.sh"
CRUSADER_SOURCE="$CRUSADER_ROOT/vendor/scummvm"
if [ -x "$CRUSADER_ROOT/scummvm/configure" ]; then
    CRUSADER_SOURCE="$CRUSADER_ROOT/scummvm"
fi
if [ ! -x "$CRUSADER_SOURCE/configure" ]; then
    mkdir -p "$CRUSADER_ROOT/vendor"
    git init "$CRUSADER_SOURCE"
    git -C "$CRUSADER_SOURCE" remote add origin https://github.com/scummvm/scummvm.git
    git -C "$CRUSADER_SOURCE" fetch --depth=1 origin a822b48a2ddd1bcdf742935f89ee94942e49539b
    git -C "$CRUSADER_SOURCE" checkout --detach FETCH_HEAD
    git -C "$CRUSADER_SOURCE" apply "$CRUSADER_ROOT/patches/scummvm-crusader-twin-stick.patch"
fi
mkdir -p "$CRUSADER_ROOT/build/scummvm"
cd -- "$CRUSADER_ROOT/build/scummvm"
"$CRUSADER_SOURCE/configure" \
    --disable-all-engines --enable-engine=ultima8 --disable-detection-full \
    --enable-debug --disable-release \
    --with-sdl-prefix="$CRUSADER_BREW_PREFIX/opt/sdl2-compat"
make -j"${CRUSADER_BUILD_JOBS:-3}" "$@"
