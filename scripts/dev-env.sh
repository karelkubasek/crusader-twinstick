# Source this file from Bash: source ./dev-env.sh
# Keep compiler aliases within this workspace; leave the system compiler alone.
CRUSADER_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CRUSADER_BREW_PREFIX="$(brew --prefix)"
CRUSADER_GCC_PREFIX="$(brew --prefix gcc)"
CRUSADER_CXX=""
for CRUSADER_CANDIDATE in "$CRUSADER_GCC_PREFIX"/bin/g++-[0-9]*; do
    if [ -x "$CRUSADER_CANDIDATE" ]; then
        CRUSADER_CXX="$CRUSADER_CANDIDATE"
    fi
done
if [ -z "$CRUSADER_CXX" ]; then
    printf '%s\n' 'Homebrew GCC is missing. Install gcc and run brew postinstall gcc.' >&2
    return 1
fi
CRUSADER_GCC_MAJOR="${CRUSADER_CXX##*-}"
export CXX="$CRUSADER_CXX"
export CC="$CRUSADER_GCC_PREFIX/bin/gcc-$CRUSADER_GCC_MAJOR"
mkdir -p "$CRUSADER_ROOT/build/toolchain-bin"
ln -sf "$CC" "$CRUSADER_ROOT/build/toolchain-bin/gcc"
ln -sf "$CC" "$CRUSADER_ROOT/build/toolchain-bin/cc"
ln -sf "$CXX" "$CRUSADER_ROOT/build/toolchain-bin/g++"
ln -sf "$CXX" "$CRUSADER_ROOT/build/toolchain-bin/c++"
export PATH="$CRUSADER_ROOT/build/toolchain-bin:$CRUSADER_BREW_PREFIX/bin:$PATH"
export PKG_CONFIG="$CRUSADER_BREW_PREFIX/bin/pkg-config"
export PKG_CONFIG_PATH="$CRUSADER_BREW_PREFIX/lib/pkgconfig:$CRUSADER_BREW_PREFIX/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export SDL_CONFIG="$CRUSADER_BREW_PREFIX/opt/sdl2-compat/bin/sdl2-config"
