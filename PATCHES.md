# Patches against Cinnamon

Four small patches against
[Project-Sunshine-Native/cinnamon](https://github.com/Project-Sunshine-Native/cinnamon)
(`UNDERTALE-3DS` branch), applied on top of each other in order. The first
three aren't VA-11 Hall-A-specific — they'd affect any GameMaker game with a
resolution/audio profile different from Undertale/Deltarune/Pizza Tower.
Patch 04 adds generic mouse/touch and timer support to the engine, plus one
VA-11 Hall-A-specific workaround (matched by GML object name).

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
`cursor_obj`) — but nothing visible is drawn). Every earlier room (splash
screens, intro narration) renders correctly, so this looks specific to
whatever `title_screen`'s own instances do in their Draw step, not a general
rendering regression. Not yet root-caused.
