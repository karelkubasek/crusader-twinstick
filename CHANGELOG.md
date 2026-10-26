# Changelog

## 1.0.0 — 2026-10-26

The first stable release of Crusader Twin Stick, an unofficial Linux launcher
and modified ScummVM engine for Crusader: No Remorse.

### Launcher

- A controller-first hub with Play, Controller layout and Settings pages.
- D-pad navigation, A to select, B to return and LB/RB to change pages.
  Held inputs wait for neutral after page changes, focus changes or returning
  from the game. Controller reconnection is supported.
- Visible focus indicators, including the Fullscreen and Skip opening movies
  checkboxes, and a live stick preview with independent movement/aim deadzones.
- Configurable gamepad bindings, a controller diagram and SVG export.
- Import from an owned GOG offline installer or a complete game folder, with
  verified resources, cancellation and recovery from failed replacements.
  Saves and settings are preserved when replacing game files or moving the app.
- Optional artwork from the player's local installation or a private image.
- A bundled Linux runtime, matching source archive, dependency notices and
  checksums. `--version` and `BUILD-INFO.json` identify the launcher release.

### Game and controller support

- Independent, continuous left-stick movement and right-stick aiming, with
  configurable deadzones and a direction buffer for sprite poses.
- Smoother walking with the weapon drawn or holstered: continuous gait cycles,
  aligned camera interpolation and compensation for authored sprite-origin
  shifts. Movement and projectile aiming remain continuous; the original
  sprites retain their eight unarmed or sixteen armed facings.
- Normal launches open the original main menu even when a previous save exists.
  Explicit save loading still goes directly into the selected save.
- The main menu uses the original brightened selection artwork for controller,
  keyboard and mouse focus, retaining its original red outer border.
- Controller support for quit confirmation, with No selected initially, and
  cancellation from difficulty selection back to the main menu.
- Opening movies are skipped by default and can be enabled in the launcher.
  Movies accept the first skip input without first opening the ScummVM menu.
  Mission cutscenes remain enabled.
- Regression coverage for movement, animation, collision, aiming, combat,
  save/load and startup, plus a relocated portable-bundle smoke test.

### Support and limits

- Linux x86_64 with glibc 2.38 or newer and desktop graphics/audio support.
  Development and runtime checks use Steam Deck Desktop Mode through X11/XWayland.
- Supported game data: GOG English 1.21. Game files, artwork, installers and
  player saves are supplied privately and excluded from releases.
- Steam Deck Gaming Mode setup is documented, but it has not received the same
  release testing. Other Linux distributions, suspend/resume and a complete
  campaign playthrough remain unverified.
- Saves use ScummVM's format; original DOS and decompiled-engine saves are not
  interchangeable with them.
- The decompiled engine is an optional comparison tool. Playing and building
  this project do not require it or the former sibling workspace.
