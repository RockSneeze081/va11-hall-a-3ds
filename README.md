# VA-11 Hall-A on 3DS

Getting *VA-11 Hall-A: Cyberpunk Bartender Action* running on Nintendo 3DS
homebrew, via [Cinnamon](https://github.com/Project-Sunshine-Native/cinnamon),
an open-source reimplementation of the GameMaker: Studio runtime for 3DS and
Wii U. The result: the game boots, has working audio, and real mouse/touch
input (buttons *and* the touch panel) correctly drives the intro, publisher
logo, and title screen, which now holds still instead of forcing itself back
into the intro every ~0.7 seconds. The title screen currently renders as a
black screen — game logic and input both work, the art just isn't drawing —
see problem #5 below; it's the one open item standing between this and
actual gameplay.

**This repo contains no game data.** Like ScummVM, RPCS3, or Citra, this is
tooling that runs *your own* legally-purchased copy of the game — you supply
the data file yourself. Nothing extracted from the game is committed here.

## Why this is possible at all

GameMaker: Studio compiles games to portable bytecode (unless the developer
opts into YYC, which compiles to native machine code instead) — the same
bytecode runs on any platform with a compatible runner. That's the whole
premise behind [Droidtale](https://github.com/pcysl5edgo/Droidtale) (Undertale
on Android) and behind Cinnamon itself, which already ports Undertale and
Deltarune to 3DS/Wii U. VA-11 Hall-A happens to be built in GameMaker too — its
prologue was Ren'Py, but the full release was rewritten in GameMaker, per
[GameMaker's own showcase page](https://gamemaker.io/en/showcase/va-11-hall-a-cyberpunk-bartender-action)
for it.

The catch: Cinnamon was built entirely around Undertale, Deltarune, and Pizza
Tower — three keyboard/gamepad-driven games with small, boxy resolutions close
to the 3DS's own screens. VA-11 Hall-A is a 1280×720 mouse-driven visual
novel. Getting it running meant finding and fixing several real gaps that
those games never exercised.

## What was actually wrong, and how each was found

Every fix below was reached by building a small tool or adding real
diagnostics to get ground truth, rather than guessing — details in the repo's
[commit history](../../commits/main) and in `cinnamon`'s own local commits.

### 1. Sourcing clean, compatible game data

The data file (`data.win` / `game.unx` / `game.win` depending on platform) had
to actually be usable: not encrypted, not compiled with YYC (native code has
no bytecode for a reimplemented runner to interpret), and on a bytecode
version Cinnamon's VM understands.

- A PS Vita backup's `game.win` turned out to be genuinely encrypted (verified
  by entropy analysis and a systematic known-plaintext XOR sweep across every
  repeat-period from 1–256 bytes — none produced a plausible chunk length).
  Research into the wider "GameMaker on Vita/3DS" homebrew scene confirmed
  this wasn't bad luck: the community's own established workflow for this
  ([Rinnegatamante's yoyoloader_vita](https://github.com/Rinnegatamante/yoyoloader_vita)
  and its [asset-swap guide](https://gist.github.com/CatoTheYounger97/fa47e7eef92f772e4004d4dac22f9bdb))
  universally sources from PC builds, never console-native exports.
- A GOG offline Linux installer (a self-extracting `makeself`/`mojosetup`
  script) turned out to contain a clean copy. It was extracted **without
  running the installer** — the embedded `data.zip` was located by finding the
  real end of the first gzip stream via `zlib.decompressobj`, not by trusting
  the installer's own (incorrect) `--dumpconf` offset.
- That file turned out to be **bytecode version 15** — one version older than
  Cinnamon's documented "16/17 only" support. Reading `vm.c` directly showed
  the VM's actual opcode dispatch only ever distinguishes "version 17 or
  higher" from "everything else" — nothing in the real code path separates
  v15 from v16. The stricter documented requirement never actually mattered.

`tools/scan_gm_data.py` — a small dependency-free script that finds a
GameMaker data file by byte signature (not filename) and reports its bytecode
version and YYC status — was built and verified against synthetic test data
before being trusted on the real file.

### 2. Missing `data.win` in the packaged romfs

`n3ds-preprocess` (Cinnamon's asset-conversion tool) only ever writes
converted textures and audio — never the data file itself. But the runtime
(`chooseDataWinPath()` in `src/n3ds/main.c`) still needs the *original*
`data.win` bundled at `romfs:/data.win` to read game logic (code, objects,
rooms, strings) at boot; the preprocessor only converts graphics and audio.
Without it, `DataWin_parse()` hits a failed `fopen()` and calls `exit(1)`
directly — a silent, clean process exit, no on-screen error, no crash report.
**Fix:** copy the real data file into `resources/3ds/romfs/data.win` before
building.

### 3. An unbounded, always-resident sound bank

With #2 fixed, the app crashed one step later loading audio. The packed sound
bank was 872MB. Cinnamon's SFX/music classifier (`soundLooksLikeMusic()`,
a filename-pattern heuristic) misclassified roughly 48 multi-minute
background music tracks as short sound effects, so they were being decoded
to raw PCM and loaded entirely into memory at boot — a real 3DS has roughly
124–178MB of total application memory, so this was never going to fit,
regardless of whether the file lived in the app bundle or on the SD card.

**Fix:** added a duration cap (`N3DS_SOUND_BANK_MAX_DURATION_SECONDS`, 20s) to
`tools/n3ds-preprocess/main.c`'s sound-bank packer — anything longer is
skipped with a clear log message instead of silently exhausting memory.
Result: 8.0MB for the ~40 real sound effects, instead of 872MB. (The excluded
long tracks are currently just silent — a known, cosmetic gap, not a
blocker.)

### 4. No input reaches the game at all — except it does, just not everywhere

With the first two fixed, the game booted and rendered correctly, but nothing
responded to input. Rather than keep guessing blindly, real file-based debug
logging was added directly to Cinnamon (`N3DS_debugLog()` — plain
`fprintf(stderr, ...)` goes nowhere once the game owns the screen via
citro2d, since there's no active `consoleInit()` console to receive it; this
instead appends to a file on the SD card). That logging proved, with repeated
confirmed entries, that **button presses do reach the engine correctly** —
but the game's very first interactive screen, a language-select menu, never
responded to any of them.

Two more things came out of the same investigation:

- Cinnamon has no touch-screen input at all (`hidTouchRead()` is never
  called), and the GML builtins `mouse_x`/`mouse_y` don't exist in this VM —
  unsurprising, since none of Cinnamon's prior target games use a mouse.
  Building that properly would mean adding new interpreter builtins, not
  wiring up something that already exists (done in problem #5, below).
- The one screen that didn't respond to buttons turned out to be the *only*
  one that needed a mouse for this specific auto-skip to matter. Once
  auto-skipped past it, the real intro narration and publisher logo played
  correctly. The title screen looked like it worked too — buttons visibly
  cycled it — but that turned out to be a second, unrelated bug making it
  loop regardless of input at all; see #5.

**Fixes:**
- Reused Cinnamon's own existing debug room-warp mechanism (already present
  for an Undertale-specific developer shortcut) to add a generic one-time
  auto-skip: the first time the current room is named exactly
  `languageselect`, jump to whatever room comes next in the game's own
  declared room order.
- Added `VK_SPACE`/`VK_ENTER` to the existing 3DS-button-to-keyboard
  simulation (previously only `Z`/`X`/`C`, tuned for Undertale) — Space and
  Enter turned out to be VA-11 Hall-A's actual dialogue-advance keys, the
  standard PC visual-novel convention.
- Also changed what the game's own GML code sees when it asks `os_type`:
  it now reports PS Vita specifically (a real platform Cinnamon already
  defines), while every one of Cinnamon's own internal checks that gate real
  3DS-specific rendering behavior still see `OS_3DS` as before — a
  one-line, fully decoupled change. The reasoning: the Vita release of this
  same game needs a gamepad-navigable control scheme since Vita has no
  mouse, and that logic is very likely still present as a platform-gated
  branch in the shared bytecode. Whether this specific change is what made
  buttons work in the main game, versus the Space/Enter mapping alone being
  sufficient, wasn't isolated — both were verified working together, not
  independently.

### 5. Real mouse/touch input, and a title screen that quietly forced itself to loop

Buttons alone got far enough to look finished — the title screen appeared,
buttons visibly cycled through it — but a second play session immediately
after publishing to GitHub surfaced a real problem: the intro kept repeating
forever instead of ever reaching gameplay. First instinct was that this was
just a side effect of a rapid `repeat: 15-20`-button-press test method
landing on "New Game" over and over. A follow-up test with **zero input at
all** ruled that out: the loop happened regardless, proving it wasn't
input-driven at all.

Two problems were tangled together here, and both needed fixing:

**Mouse/touch didn't exist yet.** VA-11 Hall-A is mouse-driven; the button
mapping in problem #4 was papering over that with keyboard simulation.
`hidTouchRead()` was wired into the main loop, and GameMaker's real mouse API
(`mouse_x`, `mouse_y`, `mb_left`/`mb_right`/`mb_middle`, and
`mouse_check_button`/`_pressed`/`_released`) was implemented in the VM for
the first time — previously, any script calling these got back `undefined`
from Cinnamon's generic unknown-function fallback, silently. A real touch
now correctly reaches the game: confirmed directly by adding temporary
call-site tracing and watching specific in-game objects (`title_to_room`,
`cursor_obj`) see a real `mouse_check_button_pressed(1) = true` follow an
actual touch on the 3DS touch panel.

**The title screen was looping on a fixed timer, not on input.** With mouse
support in place, the title screen *still* cycled back into the intro every
~0.7 seconds. The same call-site tracing that confirmed mouse input worked
also caught the actual culprit red-handed: a GML object literally named
`out_to_splash`, whose Step event unconditionally calls `room_goto()` back to
the publisher splash screens roughly 21 steps after `title_screen` loads —
every single time, with no observed dependency on any input state. This is
presumably a very-long idle/attract-mode timeout in the original PC game;
whatever value or clock it's actually reading, on this port it resolves to
~0.7 seconds instead. Two Cinnamon builtins were suspects and got fixed
regardless, since they were flatly broken either way — `get_timer()` and
`delta_time` were both stubbed to always return `0`, which would permanently
freeze any GML code that times something against them — but neither turned
out to be what `out_to_splash` reads. Rather than keep reverse-engineering
the exact mechanism, `room_goto()` now just no-ops when the calling script's
name contains `out_to_splash`. The title screen now holds indefinitely under
zero input, confirmed over multiple runs at both normal speed and an
artificially slowed frame rate used while diagnosing this.

**Known remaining issue, not yet fixed:** the title screen currently renders
as a fully black screen on both the top and bottom 3DS displays. This is not
a crash — the room loads normally (14 instances), the game loop keeps
running at a steady 30 FPS, and input demonstrably reaches the room's own
objects, as above. Every room before it (splash screens, intro narration —
all with real character art and backgrounds) renders correctly, which points
at something specific to `title_screen`'s own instances rather than a
general rendering regression. Not yet root-caused; a real GML
decompiler/disassembler would help here far more than further blind
hypothesis-testing against individual builtin functions.

## Building it yourself

You need your own legally-obtained copy of the game's data file (any
platform's GameMaker export — Windows, Mac, Linux, etc.). This repo does not
provide one.

```bash
# 1. Find and check your data file
python3 tools/scan_gm_data.py /path/to/extracted/game/files
# Looking for: "COMPATIBLE (probable)" with CODE present, not YYC

# 2. Get Cinnamon (the UNDERTALE-3DS branch has the asset-conversion tool
#    that `main` is missing) and a devkitPro 3DS environment
git clone --branch UNDERTALE-3DS https://github.com/Project-Sunshine-Native/cinnamon.git
# devkitPro: https://devkitpro.org/wiki/Getting_Started

# 3. Copy your data file in as both the preprocessor input and the runtime copy
cp /path/to/data.win cinnamon/resources/3ds/romfs/data.win

# 4. Build and run the preprocessor (needs tex3ds from devkitPro)
cmake -S cinnamon/tools/n3ds-preprocess -B build/n3ds-preprocess -DCMAKE_BUILD_TYPE=Release
cmake --build build/n3ds-preprocess
build/n3ds-preprocess/n3ds-preprocess /path/to/data.win cinnamon/resources/3ds/romfs

# 5. Build Cinnamon itself
cmake -S cinnamon -B build/n3ds -DPLATFORM=n3ds \
  -DCMAKE_TOOLCHAIN_FILE="$DEVKITPRO/cmake/3DS.cmake" -DCMAKE_BUILD_TYPE=Release
cmake --build build/n3ds
# -> build/n3ds/cinnamon.3dsx
```

Run it on real hardware via the Homebrew Launcher, or in an emulator like
[Azahar](https://github.com/azahar-emu/azahar) — use its **Load File**
option specifically; launching the `.3dsx` as a bare command-line argument
opens the library but does not boot it.

## Repo layout

- `tools/scan_gm_data.py` — standalone GameMaker data-file scanner/validator
  (finds the file by byte signature, reports bytecode version and YYC
  status). No dependencies beyond the Python standard library.
- `cinnamon/`, `pkg2zip/` — not included in this repo (see `.gitignore`);
  clone them fresh per the build steps above. All patches described here are
  small, self-contained diffs against upstream, listed in
  [`PATCHES.md`](PATCHES.md).
- `extracted/`, `dist/*.3dsx` — also gitignored. Both would contain the
  actual game's copyrighted assets, which don't belong in a public repo.

## Credits

- [Cinnamon](https://github.com/Project-Sunshine-Native/cinnamon) and
  [Butterscotch](https://github.com/MrPowerGamerBR/Butterscotch) — the actual
  GameMaker runtime reimplementation this all runs on. All credit for the 3DS
  port working *at all* belongs to Project Sunshine and Butterscotch's
  authors.
- [pkg2zip](https://github.com/mmozeiko/pkg2zip) by mmozeiko — used early on
  for PS Vita package extraction.
- Sukeban Games — VA-11 Hall-A itself. Go buy it if you haven't:
  [sukeban.moe](https://sukeban.moe).
