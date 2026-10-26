# Product

<!-- impeccable:product-schema 1 -->

## Platform

Native Linux desktop application, currently Python/Tk with SDL2 controller input.
Steam Deck Desktop Mode and Gaming Mode are the development priorities.

## Users

Players who own Crusader: No Remorse and want to play with a controller,
particularly on Steam Deck.

## Product Purpose

Import an owned game, launch it with the modified ScummVM engine, and make
independent stick movement and aiming easy to configure and understand.

## Operating Context

Local tools and live application previews are preferred. The application must
work independently of neighboring development checkouts. Private game files,
artwork, saves and test fixtures remain in ignored directories.

## Capabilities and Constraints

The launcher imports a supported GOG installer or complete game folder, keeps
saves separate, configures twin-stick controls and thresholds, displays a
controller reference, and opens ScummVM's button remapper. The user selected a
controller-first hub with Play, Controller layout and Settings destinations;
secondary pages return to the hub with restored focus. Normal launches show
the original main menu; explicit save loads may bypass it. Opening movies are
skipped by default with an option to show them. Mission movies remain available.

The user is open to changing the UI toolkit. Existing Python/Tk functionality
and the self-contained portable Linux bundle provide the current baseline.
New enhancements should preserve classic controls and existing saves.

## Brand Commitments

Crusader: No Remorse is the game identity. The user requested a red, orange and
black palette and supplied game artwork. Do not invent official endorsement or
ship proprietary artwork with source or releases.

## Evidence on Hand

The tracked launcher, controller diagram, engine patch and test drivers describe
the current implementation. The build script fetches the pinned ScummVM source.
Owned resources and player-supplied saves permit isolated gameplay checks; they
are not supplied with the checkout. The public decompiled engine is an optional
reference, not a runtime dependency. Actual Gaming Mode and full-campaign
verification remain open.

## Product Principles

- Make launching the game the primary task.
- Keep controller configuration readable on Steam Deck.
- Preserve player saves, custom mappings and original resources.
- Keep the application local and portable.

## Open Decisions

The user has been asked whether new optional gameplay enhancements should be
opt-in or enabled by default. No answer has been recorded yet.
