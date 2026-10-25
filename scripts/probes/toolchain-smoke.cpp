/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <SDL.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include <png.h>
#include <zlib.h>

#include <iostream>
#include <numeric>
#include <stdexcept>
#include <thread>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3, 4};
    int total = 0;
    std::thread worker([&]() { total = std::accumulate(values.begin(), values.end(), 0); });
    worker.join();
    try {
        throw std::runtime_error("exception support");
    } catch (const std::runtime_error &) {
        if (total != 10)
            return 1;
    }
    if (SDL_Init(SDL_INIT_TIMER) != 0) {
        std::cerr << SDL_GetError() << '\n';
        return 1;
    }
    SDL_version sdl;
    SDL_GetVersion(&sdl);
    SDL_Quit();
    FT_Library font;
    if (FT_Init_FreeType(&font) != 0)
        return 1;
    FT_Done_FreeType(font);
    std::cout << "C++ exceptions, threads, STL: OK\nSDL: "
              << int(sdl.major) << '.' << int(sdl.minor) << '.' << int(sdl.patch)
              << "\nFreeType: OK\nlibpng: " << png_get_libpng_ver(nullptr)
              << "\nzlib: " << zlibVersion() << '\n';
    return 0;
}
