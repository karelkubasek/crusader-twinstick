# SPDX-License-Identifier: GPL-3.0-or-later
"""Read the controller used by the settings preview through SDL2."""
import ctypes as C
import ctypes.util


class Gamepad:
    def __init__(self):
        self.sdl = C.CDLL(C.util.find_library("SDL2-2.0") or "libSDL2-2.0.so.0")
        signatures = {
            "SDL_InitSubSystem": (C.c_int, [C.c_uint32]),
            "SDL_QuitSubSystem": (None, [C.c_uint32]),
            "SDL_SetHint": (C.c_int, [C.c_char_p, C.c_char_p]),
            "SDL_GetError": (C.c_char_p, []),
            "SDL_NumJoysticks": (C.c_int, []),
            "SDL_JoystickOpen": (C.c_void_p, [C.c_int]),
            "SDL_JoystickClose": (None, [C.c_void_p]),
            "SDL_JoystickName": (C.c_char_p, [C.c_void_p]),
            "SDL_JoystickUpdate": (None, []),
        }
        for name, (result, args) in signatures.items():
            function = getattr(self.sdl, name)
            function.restype, function.argtypes = result, args
        self.handle = None
        self.flags = 0x200 | 0x2000  # joystick and gamecontroller
        self.sdl.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
        if self.sdl.SDL_InitSubSystem(self.flags) < 0:
            raise RuntimeError(self.sdl.SDL_GetError().decode(errors="replace"))
        self.refresh()

    def refresh(self):
        if self.handle:
            self.sdl.SDL_JoystickClose(self.handle)
            self.handle = None
        self.sdl.SDL_JoystickUpdate()
        self.count = self.sdl.SDL_NumJoysticks()
        self.name = "No controller detected"
        if self.count:
            self.handle = self.sdl.SDL_JoystickOpen(0)
            if self.handle:
                name = self.sdl.SDL_JoystickName(self.handle)
                self.name = name.decode(errors="replace") if name else "Controller 1"

    def close(self):
        if self.handle:
            self.sdl.SDL_JoystickClose(self.handle)
            self.handle = None
        self.sdl.SDL_QuitSubSystem(self.flags)
