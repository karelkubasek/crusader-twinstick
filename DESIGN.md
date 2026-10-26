---
name: Crusader Twin Stick
description: A native controller launcher in warm black, red, orange, and cream.
colors:
  background: "#15100f"
  surface: "#231917"
  border: "#65473d"
  text: "#f5e9df"
  muted: "#c6b0a3"
  focus-orange: "#ff8a3d"
  move-coral: "#df8067"
  play-red: "#a73928"
  play-red-active: "#bd4932"
  button-brown: "#3d2923"
  button-brown-active: "#59382c"
  action-ink: "#1a100c"
  action-orange-active: "#ffa764"
  action-disabled: "#603c29"
  button-disabled-text: "#a38c7e"
  scale-trough: "#432b24"
  scale-disabled: "#8f6b58"
  error: "#ffb2a5"
  artwork-black: "#000000"
typography:
  display:
    fontFamily: "Noto Sans"
    fontSize: "42pt"
    fontWeight: 700
  headline:
    fontFamily: "Noto Sans"
    fontSize: "26pt"
    fontWeight: 400
  display-compact:
    fontFamily: "Noto Sans"
    fontSize: "30pt"
    fontWeight: 700
  headline-compact:
    fontFamily: "Noto Sans"
    fontSize: "18pt"
    fontWeight: 400
  title:
    fontFamily: "Noto Sans"
    fontSize: "12pt"
    fontWeight: 700
  hub-primary:
    fontFamily: "Noto Sans"
    fontSize: "16pt"
    fontWeight: 700
  hub-action:
    fontFamily: "Noto Sans"
    fontSize: "14pt"
    fontWeight: 700
  body:
    fontFamily: "Noto Sans"
    fontSize: "10pt"
    fontWeight: 400
  body-secondary:
    fontFamily: "Noto Sans"
    fontSize: "11pt"
    fontWeight: 400
  label:
    fontFamily: "Noto Sans"
    fontSize: "10pt"
    fontWeight: 700
  label-small:
    fontFamily: "Noto Sans"
    fontSize: "9pt"
    fontWeight: 400
  diagram-label:
    fontFamily: "Noto Sans, DejaVu Sans, sans-serif"
    fontSize: "16px"
    fontWeight: 400
rounded:
  native: "0px"
  diagram-label: "6px"
spacing:
  compact: "4px"
  tight: "6px"
  small: "8px"
  gap: "10px"
  control: "12px"
  button: "14px"
  section: "18px"
  major: "20px"
  hub-control: "23px"
  window-inline: "26px"
  hero-inline: "28px"
components:
  hub-play:
    backgroundColor: "{colors.play-red}"
    textColor: "{colors.text}"
    typography: "{typography.hub-primary}"
    rounded: "{rounded.native}"
    padding: "23px 18px"
  hub-play-active:
    backgroundColor: "{colors.play-red-active}"
  hub-play-disabled:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
  hub-destination:
    backgroundColor: "{colors.button-brown}"
    textColor: "{colors.text}"
    typography: "{typography.hub-action}"
    rounded: "{rounded.native}"
    padding: "23px 18px"
  button-action:
    backgroundColor: "{colors.focus-orange}"
    textColor: "{colors.action-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.native}"
    padding: "11px 23px"
  button-action-active:
    backgroundColor: "{colors.action-orange-active}"
  button-action-disabled:
    backgroundColor: "{colors.action-disabled}"
    textColor: "{colors.muted}"
  button-secondary:
    backgroundColor: "{colors.button-brown}"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.native}"
    padding: "13px 14px"
  button-secondary-active:
    backgroundColor: "{colors.button-brown-active}"
  button-secondary-disabled:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.button-disabled-text}"
  button-quiet:
    backgroundColor: "{colors.background}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.native}"
    padding: "12px 10px"
  numeric-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.native}"
    padding: "12px 6px"
  checkbox:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text}"
    typography: "{typography.body-secondary}"
    padding: "12px 6px"
  tuning-scale:
    backgroundColor: "{colors.scale-trough}"
    rounded: "{rounded.native}"
  status-badge:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.focus-orange}"
    typography: "{typography.label}"
    padding: "6px 12px"
  hero:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.native}"
    padding: "18px 22px 18px 28px"
  artwork-pane:
    backgroundColor: "{colors.artwork-black}"
    width: "250px"
---

# Design System: Crusader Twin Stick

## Overview

**Creative North Star: "Controller-first hub"**

The launcher carries Crusader: No Remorse through warm black and brown surfaces, a red Play destination, orange interaction cues, and cream Noto Sans text. Its character comes from the player's original cover and large, readable controls. The interface is a local tool for playing and configuring an owned game.

This is a native Linux desktop application built with Python/Tk, the ttk clam theme, and SDL2 controller input. Tokens describe that implementation: positive Tk font sizes are points, widget padding is in pixels, and the exported controller diagram has its own scalable pixel coordinates. Native geometry and keyboard behavior define the interface.

**Key Characteristics:**

- Warm dark surfaces with cream text and restrained tonal separation.
- Red identifies the hub's Play destination; orange identifies actions, focus, and live aiming.
- Real buttons, checkboxes, numeric fields, and scales support keyboard, mouse, and controller input.
- Privately supplied artwork remains whole and local; the source and release contain no shipped raster asset.

The record derives from [the Tk interface](modern/ui.py), [the hub](modern/home.py), [the controller diagram](modern/diagram.py), [navigation](modern/navigation.py), and [controller input](modern/gamepad.py). Layout and interaction checks covered the documented window sizes in Desktop Mode. Simulating the Gaming layout on a desktop does not establish actual Steam Deck Gaming Mode compatibility; that validation remains open.

## Colors

The palette stays warm from background to text; brown outlines separate controls without introducing a second visual world.

### Primary

- **Play Red** (`play-red`): the large Play Crusader destination. Its active variant brightens on interaction.
- **Focus Orange** (`focus-orange`): ordinary primary actions, focused hub and tuning borders, checked indicators, state badges, ready text, and independent aiming feedback.
- **Action Ink** (`action-ink`): dark text and native focus detail on orange action buttons.

### Secondary

- **Movement Coral** (`move-coral`): left-stick movement feedback and the diagram's directional labels. The source constant is historically named `TEAL`; its actual color is coral.
- **Error Peach** (`error`): validation, save, launch, and process failure text in the persistent footer. Error meaning also appears in words.

### Neutral

- **Warm Black** (`background`): the window, page canvas, and quiet utility actions.
- **Brown Black** (`surface`): the title band, badge, notice, numeric fields, and disabled secondary surfaces.
- **Button Brown** (`button-brown`): native secondary buttons and hub destinations; its active variant adds tonal feedback.
- **Burnished Border** (`border`): hub destinations and numeric-field boundaries.
- **Cream** (`text`): primary reading and control text. **Muted Sand** (`muted`) carries secondary explanations, status, and disabled primary text.
- **Disabled Brown**, **Disabled Sand**, and **Disabled Scale** (`action-disabled`, `button-disabled-text`, `scale-disabled`): explicit unavailable-control states.
- **Scale Trough** (`scale-trough`): the track behind the orange slider. **Artwork Black** (`artwork-black`) preserves the cover's black surround.

**The Visible Focus Rule.** Keep keyboard and controller focus visible on the control that will activate. Hub buttons, scales, and numeric fields use the orange border; other native controls retain the clam focus treatment. Focus must survive page, import, and dialog transitions.

## Typography

**Display Font:** Noto Sans. **Body Font:** Noto Sans. Tk requests this family directly; any unavailable-font substitution is platform behavior. The SVG export declares DejaVu Sans and sans-serif fallbacks.

**Character:** bold destination labels and headings establish hierarchy; regular subtitles and explanations keep the interface readable without simulated game HUD typography. Line height and tracking are native defaults, not separately configured tokens.

### Hierarchy

- **Display / Headline:** the game name and subtitle in the ready title band. Compact variants make room for first-run, import, progress, and explanatory messages.
- **Title:** the window page title, preview heading, tuning labels, and preview state.
- **Hub Primary / Hub Action:** large bold labels distinguish Play and the two internal-page destinations.
- **Body / Body Secondary:** normal status and field text; larger secondary text for hero explanations and checkboxes.
- **Label / Label Small:** bold ordinary buttons and badges; smaller help and controller instructions. The Desktop notice uses the small size in bold.
- **Diagram Label:** labels begin at the documented logical size, shrink for long assignments, and scale with the vector scene. Tk clamps rendered diagram text to a minimum of 11 pixels. This is separate from the window's point-based ramp.

## Layout

The native window starts at 1080×720 and has a 940×680 minimum. The outer frame uses 26 pixels horizontally and 18 vertically. Header, flexible page content, optional session notice, and persistent footer form four rows. The footer wraps status to its available width and places save/play actions at the right; the controller help stays below.

The implemented home surface places a wide title band above a single row of Play Crusader, Controller layout, and Settings. Their grid weights are 4:4:3 with 10-pixel gaps. Launch checkboxes follow, then quieter import and About actions. The title band receives remaining vertical space, with a minimum row height of 180 pixels. Its artwork pane stays 250 pixels wide; title-band text has its own internal padding. When importing or displaying a message, the title and subtitle switch to compact roles.

At 940×680, 1080×720, and 1280×800 the same native structure fits without a CSS breakpoint or alternate mobile layout. The flexible title band grows with height; wrapping follows available width. The controller reference scales one 1120×454 vector scene to fit its canvas. Settings uses side-by-side preview and tuning columns with weights 5:6, preserving both live-stick preview and numeric adjustment at the minimum window size.

Native tuning and action targets retain a minimum target intent of 44 pixels. The reviewed 940×680 capture measured the tuning scale at 46 pixels high and the numeric field at 47; ordinary reviewed buttons were 45–47 pixels high and the hub actions 80–84. These are measured results under the reviewed Tk scaling, not fixed cross-platform widget dimensions. Preserve the target floor when changing fonts, scaling, or density.

**The Whole Cover Rule.** Center the original portrait in the black artwork pane and fit its entire width and height. The implementation downsamples by an integer factor to leave a 12-pixel margin on each side; it does not crop or upscale the cover. A text-based fallback carries the game identity when no usable private image is present.

## Elevation & Depth

The shipped interface has no decorative shadows or animated elevation. Depth comes from warm tonal layering, native control boundaries, and focused or active states. The title band and Desktop notice use the same surface color; the red destination supplies the strongest mass. State changes are immediate. Controller hold-repeat timing is functional input behavior, not a visual animation system.

## Shapes

Window surfaces, title band, buttons, and fields are rectangular with square corners. The native clam theme supplies its button and checkbox details. The controller reference uses rounded hardware contours, circular sticks, and small rounded callout backgrounds; those illustration geometries do not change the rectangular widget language. The stick preview uses circles and dashed boundaries to explain thresholds.

## Components

### Buttons

Buttons are solid native controls with direct action labels. The hub's red Play uses the largest label; the two brown destinations share its generous padding. Focus changes their 2-pixel border to orange and keeps a native inner focus indicator. Ordinary primary actions use orange with dark ink; secondary actions use brown with cream; import and About utilities use muted text on the window background. Active and disabled colors are recorded as sibling variants in the frontmatter. Focus and pointer states must remain distinct from disabled states.

### Cards / Containers

The title band is a broad, flat rectangular surface containing a black artwork pane and game information. The compact variant serves import and feedback states. Other surface containers are functional: the state badge and session notice. There is no general grid of decorative cards.

Artwork provenance is private and user supplied: the original Crusader cover belongs to its original rights holders. Runtime lookup first uses the player's optional `user-data/artwork/launcher.png` (or the equivalent under `CRUSADER_TWINSTICK_HOME`), then artwork imported from their game copy. No proprietary raster is embedded in this design record, source bundle or release.

### Inputs / Fields

Native checkboxes control fullscreen, skipping opening movies, and enabling twin-stick controls. Their labels and padding create the target, rather than enlarging the small native indicator alone. Keyboard and controller focus draws an orange dotted rectangle around the label, whether checked or unchecked. Fullscreen and skip-intro remain saved preferences; the default skip-intro behavior is preserved.

Each movement setting pairs a labeled explanation, horizontal orange scale, centered percentage spinbox, and percent suffix. Numeric fields use the surface fill and brown outline, changing their border to orange on focus. Scale geometry uses a 44-pixel arrow size and 38-pixel slider length. On a focused scale or spinbox, controller left/right changes the value; up/down continues navigation. Invalid whole percentages or threshold relationships put a written error in the footer, disable save/play, and retain the last valid stick preview.

### Navigation

The three home destinations lead to separate internal pages; the notebook's tab strip is hidden. Controller layout and Settings show a clear header Back action and a footer Play action. Returning home restores focus to the destination that opened the page. The controller page offers Remap buttons and Export SVG; the settings page keeps both movement and aim preview modes.

D-pad navigation follows native focus order; A activates only visible, enabled buttons or checkboxes; B closes About, cancels an active import, returns from an internal page, or leaves the optional import view. LB/RB cycles pages. The left stick can also navigate outside Settings; Settings reserves both sticks for the preview. Keyboard navigation uses native Tk behavior, with Ctrl+S to save. About closes with Return or Escape and restores focus to its visible opener. System file dialogs retain native behavior.

**The One Back Rule.** Every internal page has one clear route home and restores the corresponding destination focus. Held input belongs to its previous context: require neutral after a window/page transition or child-process return before accepting a fresh controller action.

### Status and import

State appears in the badge and written footer, with additional copy beside import progress. A clean configuration reads Saved; a valid edit reads Unsaved changes and enables Save changes. Secondary-page Play becomes Save & play while dirty and saves before launching. The hub retains its Play Crusader label and follows the same save-before-launch behavior.

Running and installing states disable editable settings and launch/remap actions. Import distinguishes Installing, Cancelling, Import failed, Cancelled, and Installed; progress and Cancel installation replace source/install actions while busy. Failure and cancellation results persist through refresh, and completion returns to the ready hub. Existing saves and controller settings stay separate from replacement files. Closing during installation requests cancellation and waits for cleanup.

### Controller reference and preview

The controller is a generated vector illustration shared by Tk canvas rendering and SVG export. Every assignment follows saved mappings; unassigned controls say Unassigned. Physical A/B/X/Y colors identify hardware controls within the illustration and do not become extra application accents. The preview combines labeled state, movement coral, aiming orange, threshold circles, and a draggable dot. It remains available with mouse input when SDL2 or a controller is unavailable.

## Do's and Don'ts

### Do:

- **Do** use the warm dark palette, cream Noto Sans text, and native rectangular controls.
- **Do** preserve visible focus, destination focus restoration, and neutral input after context changes.
- **Do** keep tuning and action targets at least 44 pixels at the supported native window sizes.
- **Do** pair status color with written saved, dirty, busy, import, or error feedback.
- **Do** keep the privately supplied cover whole, local, and outside source and release assets.
- **Do** check the minimum window alongside 1080×720 and 1280×800 when extending the interface.

### Don't:

- **Don't** add rounded cards, shadows, button icons or web typography without reviewing their fit with the native interface.
- **Don't** crop the cover or package proprietary artwork, private screenshots, game files, or saves.
- **Don't** replace real Tk buttons and checkboxes with decorative game HUD controls or invented status.
- **Don't** consume movement-stick preview input for page navigation on Settings.
- **Don't** describe the Desktop Gaming-layout simulation or scoped finish review as actual Gaming Mode validation.
