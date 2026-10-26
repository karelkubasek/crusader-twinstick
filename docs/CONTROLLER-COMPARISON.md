# Decompiled engine comparison

Reference: [crusader-no-remorse-decomp at ec7193218f9a0e590916331f02f6c76891f51fa9](https://github.com/sebsebseb1982/crusader-no-remorse-decomp/tree/ec7193218f9a0e590916331f02f6c76891f51fa9),
inspected and exercised locally on 2026-10-25. It is a separate C++20/SDL2
engine implementation. This project continues to build and run independently
of that checkout.

| Area | Reference implementation | This project |
| --- | --- | --- |
| Movement | Left stick holds one of eight keypad directions; original animations drive movement | Continuous screen-space movement with collision handling; in-place animation compensates its authored sprite-origin shifts |
| Direction stability | Keeps a movement sector until the stick crosses a 30-degree boundary around it | Radial deadzones plus angular pose hysteresis; continuous movement and projectile aim remain independent |
| Aiming | Right stick drives the native crosshair; turning respects the actor's busy state | Independent aiming and movement, including strafing, projectile direction and target height |
| Menus | Fixed A confirm and B/Start cancel; stick moves the cursor | D-pad selection and A confirmation in the original main/difficulty menus; A/Y skip movies and B/Y cancel menus; mouse controls and ScummVM dialogs remain available |
| Remapping | Remembers the key sent on press so its matching release survives context changes | ScummVM keymapper plus movement resets on modal input, focus loss and controller changes |

The relevant upstream sources are [the SDL gamepad adapter][ref-gamepad],
[game orchestration][ref-game], [avatar movement][ref-mover] and
[aim mode][ref-aim]. Reference file/function names below refer to that pinned
public source tree, rather than files expected in this checkout.

## Runtime observations

The reference built using the existing Homebrew compiler and SDL2. GCC 16
required the build-only flag `-include utility` because `movie_player.cpp`
uses `std::exchange` without including its header. Its source was left alone.

All six data-independent suites passed: core, kernel, audio, world, usecode and input. A private copy of our imported resources ran the US
new-game scenario without usecode faults or unbound intrinsics. The US suite
reported one failure: its version-detection assertion expects the original DOS
executable, which our imported runtime resources do not contain.

A scripted test sent SDL controller events through the
reference's `Gamepad` class and fed its resulting keys into `Game`. Diagonal
movement advanced the actor both unarmed and after drawing a weapon. Holding
right-stick aim during the armed movement test kept playing combat-stand
animations and did not advance the actor. This is a specific tested input
pattern, and needs hands-on confirmation before adopting its aiming behavior.

## Movement investigation and correction

The first investigation enabled position interpolation and removed extra gait
holds. A capture showed more distinct frames, but that did not establish smooth
motion: the player reported worse judder, especially with the weapon holstered.
That earlier metric missed motion relative to the camera.

The 2026-10-26 investigation reproduced backward jumps in an isolated copy of the
player's new latest save. Physics moved steadily right, while the drawn avatar
oscillated across four screen pixels. Crusader's `SnapProcess` creates cameras
from simulation positions; smoothing only the avatar put the two in different
phases. Process order also left the camera one movement tick behind at times.

When twin-stick mode follows the player, the camera now renders the avatar's
centre using the same interpolated transform. Simulation camera positions,
walking speed, collisions and save serialization are unchanged. The correction
is bypassed for fixed cameras, scripted pans, stasis, remote actors and classic
controls; camera shake is still applied afterwards.

Rendered-coordinate traces from the same save showed a constant avatar anchor
in all four cardinal directions, both holstered and armed, after the initial
transition. The fixed-camera case retained actual movement across the view.
The player still saw pronounced judder, including in the comparison video.
Those traces measured the physical anchor, not the visible Silencer, and did
not establish that the walking sprite was smooth.
The persistent animation probe now checks avatar/camera alignment as well as
gait cadence; counting changing frames alone cannot catch this regression.
The current regression lives in the tracked
[animation probe](../scripts/probes/probe-twin-animation.py); it does not read
the private investigation captures.

### Sprite-origin correction

The subsequent comparison read the original animation and shape data, exercised
the decompiled port through its SDL gamepad adapter, and ran its windowed game
with an isolated resource copy. No additional game files were needed. A native
reference save was created at the corresponding map position; ScummVM saves
were not passed to the other engine. The reference run reported no usecode
faults or unbound intrinsic calls in this scenario.

Unarmed walking/running has eight sprite directions; combat locomotion can have
sixteen. The original crosshair angle turns in smaller increments than those
body directions. The reference controller's directional mode holds one of eight
keypad directions, and the animation supplies movement. Our continuous movement
instead discards each frame's authored planar travel while playing its sprite.

That matters because the sprite origins shift considerably during the gait.
For right-facing walking, consecutive authored distances include 6, 4, 1, 2 and
2; the corresponding sprite origins counter those unequal steps. Constant-speed
in-place playback exposes the origin shifts, even when the stick points exactly
left or right. Direction snapping alone cannot remove that case.

The renderer now registers the Silencer's upper-body position along the
animation's authored travel axis, using the opaque helmet pixels in the top ten
rows of its locomotion frames. The final frame supplies the reference position;
mirrored frames and sideways animations use their own direction and flip data.
Perpendicular gait bobbing remains. The offset affects the rendered sprite,
weapon overlay and sprite hit testing; world collision bounds, movement speed,
projectile simulation, camera coordinates and save serialization remain as before.
The correction is restricted to the player Silencer's owned twin-stick gait.

A first prototype restored only the authored stride variation. In the same
latest-save capture, that reduced the largest measured horizontal helmet jump
from about 8.8 to 3.4 native pixels, but still left visible shifts. Registering
the sprite itself reduced the largest horizontal step to about 2.0 pixels and
the horizontal range from 12 pixels to about 2 pixels in that capture. The
persistent animation probe now checks actual sprite pixels at the display-list
location as well as the physical camera anchor. To check the current build,
prepare the private fixtures described in
[the testing guide](TESTING.md#private-gameplay-probes), then run:

```sh
./scripts/test_engine.sh animation
```

The measurements above describe historical Desktop/X11 captures, which are not
distributed. The tracked probe reproduces the regression check with player-supplied
game resources and a suitable save. The player's judgement of the resulting
movement remains important.

## Review scope and adoption decisions

The reference contains about 28,000 implementation lines across core resources,
platform adapters, the engine and game orchestration, plus about 7,500 test
lines. This review followed the implementation and test paths for controller
routing, native menus, movement/animation, aiming/projectiles, cameras,
rendering/scaling, resource import, saves, autosave triggers, usecode and audio.
It is a source/runtime comparison of those paths, not a claim that every
instruction is equivalent or that either engine has completed a campaign.

| Area and reference sources | Assessment and action here |
| --- | --- |
| Pose stability: `sdl_gamepad.cpp::update_move` | Adopted the sector-hold principle for body poses: 30° from an eight-way axis, 15° for sixteen-way poses. Kept continuous aim and movement math. This avoids animation restarts caused by tiny boundary oscillations. |
| Native menus: `sdl_gamepad.cpp::press_slot`, `engine/ui/main_menu.cpp` | Adopted D-pad selection and A confirmation in the original main menu and difficulty screen. Main-menu focus uses the original bright frame 1, as in the reference, sharing one selection across controller, keyboard and mouse hover. The extra selection outline is removed; the original outer border remains. Startup navigation and mouse hover skip unavailable Save. B joins Y as a cancel default; explicit GUI remaps remain respected. A also skips movies. Physical mouse clicks remain clicks. |
| Context changes: `press_slot`, `set_menu`, `release_all` | The reference remembers the action pressed so release uses the same action. Our engine already clears movement on modal input, focus loss and device changes; those checks remain. The launcher now gates held controls until neutral after a page/focus/process change, and confirm uses a press edge rather than auto-repeat. |
| Script input reset: `game.cpp::reset_world`, original address `13E8:00A8` | Adopted the previously missing input-reset intrinsic in the known No Remorse tables. It clears movement/aim sticks and pending mouse clicks without synthesizing clicks or changing the camera. This replaces an unhandled intrinsic, rather than suppressing its warning with a no-op. |
| Device selection: `sdl_gamepad.cpp::init/open` | Adopted searching for the first SDL-mapped controller for launcher input, instead of assuming joystick zero is a controller. Hotplug reconnection is throttled; input polling is more responsive. |
| Follow camera: `world.cpp::track_camera_target/update_follow_camera` | ScummVM already has player following and camera interpolation. The mismatched phase in its twin-stick follow path is now corrected. The reference additionally eases toward the player, with special rounding to avoid jitter; that changes responsiveness and has not replaced the existing camera or scripted pans. |
| Native view/zoom: `game.cpp::draw`, `game.hpp::ui_x/ui_y`, `main.cpp`, `sdl_presenter.cpp` | The reference automatically expands the world view at integer pixel scales while centring original menus. ScummVM already has configurable render dimensions, aspect correction and scaling, but not this exact adaptive layout. This remains a distinct optional feature: widening the view also changes visibility, mouse bounds and fast-area activation, and requires gameplay/UI validation beyond a scaler toggle. |
| Event autosaves: `game.cpp::autosave/request_autosave`, `npc_intrinsics.cpp`, `engine/world/inventory.cpp` | A useful addition beyond ScummVM's timed autosaves: keycards, successful codes, mission starts and cutscene completion. Its save format, slot and hooks differ from ScummVM. Directly saving inside ScummVM's usecode callbacks would risk capturing a partial operation. Adoption needs deferred safe-point saves, existing manual-slot protection and an explicit enable/default decision; it is not enabled silently. |
| Run toggle and pad remapping: `game_config.hpp`, `engine/ui/gamepad_screen.cpp` | Reference toggle-to-run may help accessibility, but is a behavior preference. ScummVM already provides remapping and this launcher already persists custom mappings and independent stick thresholds. Keep those existing facilities; a toggle-to-run option remains a separate feature. |
| Save compatibility: `game.cpp::load_save/save_game` | The reference reads and writes original DOS-style FLEX saves. ScummVM serializes its own processes and object state. These formats cannot be copied interchangeably. Current player saves were tested through the existing ScummVM path and are preserved. A DOS-save importer would need a separate conversion project. |
| Resource import: `core/iso_image.cpp`, `main.cpp` | The reference imports ISO images and supports its documented FR 1.08/US 1.23 data. Our verified GOG importer checks hashes, excludes unrelated files, rejects symlinks, supports cancellation and rolls back failed replacements. Retain that transactional importer; do not relax its supported edition based on the reference's version guesses. |
| Usecode/physics/gameplay: `engine/usecode/*`, `engine/world/*` | The reference's original addresses and tests are valuable evidence for specific missing behaviors, not proof its whole VM/world is preferable. Intrinsic indices differ by edition: `I_isReleaseBuild` is already bound in our table, and its redraw intrinsic is explicitly a no-op in the reference. No blanket intrinsic renumbering, collision replacement or warning suppression was adopted. |
| Audio/movies: `engine/audio/*`, `core/avi_movie.cpp`, `movie_player.cpp` | Both use original resources. ScummVM already supplies movie decoding/subtitles, mixing and music state handling. No demonstrated audio/decoder improvement justified replacing these. The startup and mission-movie paths are exercised separately here. |
| Diagnostics/testing: `tests/*`, `e2e/*`, `src/tools/*` | Built and ran all six unit suites and US data scenarios during the historical comparison. Reference save-dependent campaign cases require its DOS-format fixtures, so their existence is not counted as a passed comparison. Current project checks use the tracked probes and fixture requirements in the testing guide. |

The new changes are independently implemented in this project's ScummVM patch
and launcher. The reference checkout remains unmodified and is never opened by
the application or its build scripts. No game data, screenshots or reference
executables are distributed. Its GPL-3.0-or-later code is license-compatible;
any future copied implementation should retain its attribution and provenance.

[ref-gamepad]: https://github.com/sebsebseb1982/crusader-no-remorse-decomp/blob/ec7193218f9a0e590916331f02f6c76891f51fa9/src/platform/sdl_gamepad.cpp
[ref-game]: https://github.com/sebsebseb1982/crusader-no-remorse-decomp/blob/ec7193218f9a0e590916331f02f6c76891f51fa9/src/game/game.cpp
[ref-mover]: https://github.com/sebsebseb1982/crusader-no-remorse-decomp/blob/ec7193218f9a0e590916331f02f6c76891f51fa9/src/engine/world/avatar_mover.cpp
[ref-aim]: https://github.com/sebsebseb1982/crusader-no-remorse-decomp/blob/ec7193218f9a0e590916331f02f6c76891f51fa9/src/engine/world/aim_mode.cpp
