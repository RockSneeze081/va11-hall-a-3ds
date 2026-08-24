# Patches against Cinnamon

Six small patches against
[Project-Sunshine-Native/cinnamon](https://github.com/Project-Sunshine-Native/cinnamon)
(`UNDERTALE-3DS` branch), applied on top of each other in order. The first
three aren't VA-11 Hall-A-specific — they'd affect any GameMaker game with a
resolution/audio profile different from Undertale/Deltarune/Pizza Tower.
Patch 04 adds generic mouse/touch and timer support to the engine, plus one
VA-11 Hall-A-specific workaround (matched by GML object name). Patch 05 is
VA-11 Hall-A-specific (matched by room name). Patch 06 is generic (any room
with an in-room camera view).

**Real-hardware status (unverified as of this writing):** everything above
was tested in the Azahar emulator only. A first real-3DS test reported
touch/buttons not working and "weird resolution" with illegible text —
still open, not yet diagnosed, likely something that behaves differently on
real hardware vs. the emulator rather than anything patch 06 addresses (see
its own note below). Leading theory: `C3D_Init`/`C2D_Init` failing on real
hardware and silently falling back to the tiny built-in text-console path
(`consoleInit` branch in `src/n3ds/main.c`'s `main()`), which would produce
exactly this symptom set. Unconfirmed — waiting on a photo/video from real
hardware to actually diagnose rather than guessing further.

Apply with `git apply patches/01-*.patch` etc. from the root of a fresh
`cinnamon` clone (branch `UNDERTALE-3DS`), or just read them — each is small.

## [01 — sound bank duration cap](patches/01-sound-bank-duration-cap.patch)

`tools/n3ds-preprocess/main.c`. The packed SFX sound bank is loaded fully
into memory at boot. Cinnamon's music/SFX classifier is a filename-pattern
heuristic and can misclassify long background tracks as short effects,
which get decoded to raw PCM and blow past a real 3DS's ~124–178MB of
application memory. Adds a 20-second cutoff — longer "effects" are skipped
with a log message instead of being packed. Fixed an 872MB sound bank down
to 8MB on this game.

## [02 — report PS Vita as os_type](patches/02-report-psvita-os-type.patch)

`src/vm_builtins.c`. One line. The GML-visible `os_type` builtin now always
returns `OS_PSVITA` instead of the engine's real `runner->osType`, which
stays `OS_3DS` for every one of Cinnamon's own internal checks. Games
originally released on PS Vita generally ship a gamepad-navigable control
path in their own code (Vita has no mouse) — this makes that path activate,
without touching any of Cinnamon's real 3DS-specific rendering/GUI logic.

## [03 — debug logging, Space/Enter mapping, language-select auto-skip](patches/03-debug-log-input-mapping-autoskip.patch)

`src/n3ds/main.c`. Three related changes:

- `N3DS_debugLog()`: appends to `sdmc:/3ds/cinnamon/debug.txt`. Plain
  `fprintf(stderr, ...)` has nowhere to go once citro2d owns the screen (no
  active `consoleInit()` console), so it silently produces nothing — this
  was the only way to get real proof of which buttons were reaching the
  engine, and it logs room transitions too.
- Adds `VK_SPACE` (3DS-A) and `VK_ENTER` (3DS-B) to the existing
  Undertale-tuned `Z`/`X`/`C` keyboard simulation. Space/Enter turned out to
  be this game's actual dialogue-advance keys.
- A narrow, generic one-time auto-skip: the first time the current room is
  named exactly `languageselect`, look up its position in the game's own
  declared room order and jump to whatever comes next. That specific room
  never responds to any button (tested exhaustively — see the main
  [README](README.md#4-no-input-reaches-the-game-at-all--except-it-does-just-not-everywhere)).
  The real intro narration plays correctly afterward; the title screen turned
  out to have its own separate bug, fixed in patch 04.

## [04 — mouse/touch input, title screen loop fix, real get_timer/delta_time](patches/04-mouse-touch-input-and-title-screen-loop-fix.patch)

`src/n3ds/main.c`, `src/runner.h`, `src/vm_builtins.{c,h}`, `CMakeLists.txt`.
VA-11 Hall-A is mouse-driven, and none of GameMaker's mouse API existed in
Cinnamon at all — any script calling `mouse_check_button()` or reading
`mouse_x`/`mouse_y` silently got back `undefined` (Cinnamon's generic
unknown-function fallback). Four changes:

- Wires `hidTouchRead()` into the main loop and implements
  `mouse_x`/`mouse_y`/`mb_left`/etc. and
  `mouse_check_button`/`_pressed`/`_released` for real, mapping the 3DS touch
  panel to the single "mouse button" a touch panel can express.
- **The title screen bug**: with real mouse support in place, the title
  screen still weirdly cycled back into the intro every ~0.7 seconds
  regardless of input. Traced (via temporary call-site tracing on every
  `room_goto`-family builtin, and on `mouse_check_button*` itself) to a GML
  object literally named `out_to_splash`, whose Step event unconditionally
  forces `room_goto` back to the publisher splash screens ~21 steps after
  `title_screen` loads — every time, with no observed dependency on any input
  state. This is presumably a very-long idle/attract-mode timeout on real
  hardware; on this port it fires almost immediately. Rather than reverse
  the exact timer/threshold value it reads, `room_goto()` now just no-ops
  when the calling script's name contains `out_to_splash`, so the title
  screen holds until the player clicks — this is the one part of this patch
  that's specific to this game rather than to Cinnamon in general.
- Implements `get_timer()` and `delta_time` for real — both were previously
  stubbed to always return `0`, so any GML code computing elapsed time
  against either of them (`alpha = (get_timer() - startTime) / duration`)
  would get stuck at `0` forever. Mirrors the existing `current_time`
  builtin's platform-branched monotonic-clock pattern.
- A `SELECT+R` debug shortcut to warp straight to the title screen (skips the
  ~90-second splash/intro replay on every single boot while testing), and a
  `freopen()` of `stderr` to `sdmc:/3ds/cinnamon/stderr.txt` so Cinnamon's own
  existing `fprintf(stderr, ...)` unknown-function warnings — previously
  invisible on-device — become readable.

**Known remaining issue**: the title screen currently renders fully black on
both screens (no crash — the room loads, instances exist, and clicks are
confirmed reaching the room's own click-to-play objects (`title_to_room`,
`cursor_obj`) — but nothing visible is drawn). A deep dive tracing the full
draw pipeline (`Renderer_drawSelf` → `N3DSRenderer_drawSprite` → the
direct-mapped/fragmented-atlas paths → `transformScreenRect`) confirmed
`title_screen`'s sprites are valid data (correct dimensions, resolved
texture-page indices) and the transform math checks out on paper, but
capped, targeted logging at each stage never actually fired for at least one
plainly-valid sprite (`cursor_spr`) — meaning it's taking a code path this
investigation didn't reach yet, not a data problem. Every earlier room
(splash screens, intro narration) renders correctly, so this is specific to
something about how `title_screen` in particular gets drawn. Not
root-caused; worked around in patch 05 by skipping the room entirely rather
than blocking on it further.

## [05 — auto-skip title_screen into real gameplay](patches/05-auto-skip-title-screen-into-gameplay.patch)

`src/n3ds/main.c`. Since the title screen can't currently be seen or
interacted with, it's now auto-skipped the same way `languageselect` already
was: the first time `title_screen` is entered, look up its position in the
game's own room order and jump to whatever comes right after. That lands on
`jill_room` — the game's actual first gameplay scene — which renders
correctly with real art, dialogue, and a working menu (confirmed by
screenshot, not just room-name logging). This is a workaround for the
still-unfixed issue in patch 04, not a fix for it, and is matched by room
name (`title_screen`), so it's specific to this game.

## [06 — touch coordinates respect the active room view](patches/06-touch-mapping-respects-active-view.patch)

`src/n3ds/main.c`. The touch-to-`mouse_x`/`mouse_y` mapping from patch 04
scaled `hidTouchRead()`'s panel coordinates directly against the full
`gameW`x`gameH` logical canvas. Rooms with their own in-room camera view —
a sub-rectangle of that canvas — only show and accept input for that
sub-rectangle, so on such a room only the fraction of the touch panel
proportional to the view's position/size would ever land on anything
visible (e.g. a top-left-anchored sub-view means only the top-left of the
panel does anything). Now reads `runner->drawViewX/Y/Width/Height` (falling
back to the full canvas when no custom view is active) and maps the touch
panel onto whatever room-space rectangle is actually on screen. Generic —
applies to any room with a camera view, not VA-11 Hall-A-specific.

Verified in Azahar against `title_screen` (which does have a 640×360 view)
and `jill_room` (which turned out to use the full canvas, no custom view) —
correct in both cases. Does **not** by itself explain the touch/button
problems reported on real hardware (see the real-hardware status note
above); `jill_room`, where those were reported, isn't the kind of room this
patch changes anything for.
