/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <SDL.h>
#include <stdio.h>

int crusader_probe_controllers(void) {
    int count = SDL_NumJoysticks();
    fprintf(stderr, "Probe: %d joysticks, SDL error: %s\n", count, SDL_GetError());
    for (int i = 0; i < count; ++i)
        fprintf(stderr, "Probe: device %d: %s, controller=%d\n", i,
                SDL_JoystickNameForIndex(i), SDL_IsGameController(i));
    return count;
}

static SDL_JoystickID controller_id(void) {
    SDL_GameController *controller = SDL_GameControllerOpen(0);
    if (!controller)
        return -1;
    SDL_JoystickID id = SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(controller));
    SDL_GameControllerClose(controller);
    return id;
}

int crusader_probe_axis(int axis, int value) {
    SDL_JoystickID id = controller_id();
    if (id < 0)
        return -1;
    SDL_Event event = {0};
    event.type = SDL_CONTROLLERAXISMOTION;
    event.caxis.which = id;
    event.caxis.axis = axis;
    event.caxis.value = value;
    return SDL_PushEvent(&event);
}

int crusader_probe_button(int button, int down) {
    SDL_JoystickID id = controller_id();
    if (id < 0)
        return -1;
    SDL_Event event = {0};
    event.type = down ? SDL_CONTROLLERBUTTONDOWN : SDL_CONTROLLERBUTTONUP;
    event.cbutton.which = id;
    event.cbutton.button = button;
    event.cbutton.state = down ? SDL_PRESSED : SDL_RELEASED;
    return SDL_PushEvent(&event);
}

int crusader_probe_focus_lost(void) {
    SDL_Window *window = SDL_GetKeyboardFocus();
    for (Uint32 id = 1; !window && id < 64; ++id)
        window = SDL_GetWindowFromID(id);
    if (!window)
        return -1;
    SDL_Event event = {0};
    event.type = SDL_WINDOWEVENT;
    event.window.event = SDL_WINDOWEVENT_FOCUS_LOST;
    event.window.windowID = SDL_GetWindowID(window);
    return SDL_PushEvent(&event);
}

int crusader_probe_key(int scancode, int down) {
    SDL_Window *window = SDL_GetKeyboardFocus();
    for (Uint32 id = 1; !window && id < 64; ++id)
        window = SDL_GetWindowFromID(id);
    SDL_Event event = {0};
    event.type = down ? SDL_KEYDOWN : SDL_KEYUP;
    event.key.state = down ? SDL_PRESSED : SDL_RELEASED;
    event.key.windowID = window ? SDL_GetWindowID(window) : 0;
    event.key.keysym.scancode = scancode;
    event.key.keysym.sym = SDL_GetKeyFromScancode(scancode);
    return SDL_PushEvent(&event);
}
