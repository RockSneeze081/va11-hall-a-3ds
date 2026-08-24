# Patches against Cinnamon

Three small patches against
[Project-Sunshine-Native/cinnamon](https://github.com/Project-Sunshine-Native/cinnamon)
(`UNDERTALE-3DS` branch), applied on top of each other in order. None of
these are VA-11 Hall-A-specific — they'd affect any GameMaker game with a
resolution/audio profile different from Undertale/Deltarune/Pizza Tower.

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
  [README](README.md#4-no-input-reaches-the-game-at-all--except-it-does-just-not-everywhere));
  every other screen tested afterward, including the real intro narration
  and title screen, works correctly with buttons.
