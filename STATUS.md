# Sonic 2 Oxygen -- Status

## What this is
A new Oxygen Engine project, sibling to `sonic3air`, built by keeping S3AIR's
shared engine layer (physics, collision, camera, HUD scaffolding, object
spawning, rendering, save system -- ~39k lines, GPLv3) and replacing all
Sonic 3 & Knuckles-specific *content* (zones, objects, enemies, bosses,
menus) with Sonic 2 content, authored against the public `s2disasm`
disassembly as a logic reference.

Requires the player's own legally-dumped Sonic 2 ROM. No Sonic 3 ROM is
referenced anywhere -- the ROM requirement in `oxygenproject.json` is pure
per-project config, not hardcoded into the engine.

## Design principle: S3K-exclusive features are opt-in toggles, not cut
Decided explicitly (not a default-strip-everything-S3K approach): anything
from S3K that's genuinely desirable content -- Super Flickies, elemental
shields, etc. -- stays in the project and should eventually become a
player-facing settings toggle, not get deleted. The whole point of this
project is giving modders more than RSDK ever could, not recreating RSDK's
limits under a new engine.

The ONLY category that gets removed outright is stuff with literally no
Sonic 2 equivalent to toggle on top of -- e.g. `giantring.lemon` (Giant
Ring special-stage portal: S2 enters special stages via a ring-count
checkpoint, there's no level object to attach a toggle to in the first
place, nothing to turn on).

IMPORTANT DISTINCTION -- "kept" != "toggle exists yet":
Currently, kept S3K features (superflickies.lemon, shields.lemon's
elemental part, capsule.lemon) are DORMANT: the code compiles but nothing
in S2's object layouts ever triggers it, since no setting/menu exists yet
to turn it on. Making one an actual player-facing toggle requires three
real pieces of work, not yet done for any feature:
  1. A setting definition (defines_settings.lemon is copied over, ready)
  2. Logic that checks the setting and conditionally spawns/enables the
     feature (e.g. Super form spawning flickies only if enabled)
  3. An actual menu entry exposing it (menus/ for structure; the visual
     rendering of that entry is C++, not lemon -- unexplored so far)
This is real, separately-scoped work per feature, to be done as its own
task list, not something that happens automatically by leaving files in.

## Kept as-is from S3AIR (reused wholesale)
- `_defines/`, `utility/`, `general/` (minus Blue Sphere)
- `maingame/` incl. `character/`, `hud/` (minus Knuckles cutscene, minus outro)
- `objects/basics`, `objects/effects`, `objects/misc` (rings, springs,
  monitors, signposts -- near-identical across S2/S3K, may need minor tuning)
- `standalone/` (app-level glue, rendering, resources)
- `level/level_*.lemon` (shared per-frame level update logic)

## Deliberately stripped (S3K-only content, not reusable)
- All 14 S3K zone folders under `level/` and `objects/`
- `enemies/`, `bosses/` -- every file is a specific S3K creature/boss
- Blue Sphere special stage, competition mode, Knuckles-specific cutscene

## CORRECTED: menus/ is kept whole, not stripped
Originally dropped as "S3K content." Wrong -- confirmed by the user (an
existing S3AIR modder): the menu/title flow is load-bearing, the game does
not boot without it. Kept all of `menus/` (titlescreen, dataselect,
levelselect, actselect, continuescreen, competition_menus, titlescreen_sk)
for now. Trimming the genuinely S3K-only pieces (competition_menus.lemon,
titlescreen_sk.lemon's S&K lock-on screen) is deferred until we can
test-compile, not guessed at blind.

Separately, and important for later: the menu *theme/rendering* (fonts,
layout, visual skin) lives in the C++ engine layer, not lemonscript. Writing
a Sonic 2-themed menu means touching `oxygenengine`/`sonic3air`'s C++ UI
code too, not just scripts. Not yet investigated where.

## Scaffolded, not yet built
- `level/01_ehz/`, `objects/01_ehz/` -- empty, this is milestone 1
- `oxygenproject.json` -- ROM checksum is a placeholder; fill in once you've
  verified your own dump

## RESOLVED: object layout conversion pipeline works
`tools/convert_object_layout.py` parses s2disasm's native 6-byte object
layout format (verified against the real ChkLoadObj decoder at s2.asm
~line 33650, not guessed from wiki docs) and emits
`LevelObjectTableBuilder.addObject(...)` calls -- the same human-authored
format S3AIR itself uses for its standalone build (see
`scripts/standalone/resources/level_objects/levelobjects_01_aiz.lemon` for
the original). Turns out we didn't need to reverse-engineer the
`data/rawdata/*/layout_actN.bin` ROM-injection format at all -- that's a
different, ROM-compatibility-mode path we don't need for the standalone
build.

Ran it for real: `scripts/standalone/resources/level_objects_converted/`
has `levelobjects_01_ehz_act1_RAW.lemon` (135 objects) and
`..._act2_RAW.lemon` (165 objects), converted from s2disasm's actual
`EHZ_1.bin` / `EHZ_2.bin`. All object IDs resolved to real names (Ring,
Monitor, Buzzer, Masher, Coconuts, Spring, Spikes, EHZWaterfall, etc.) with
zero unknowns.

**"RAW" means**: x/y/id/subtype/flip-flags are correct and real. What's
NOT done yet: these numeric IDs (e.g. `0x4b` = Buzzer) don't correspond to
any object *behavior* script yet -- there's no `objects/01_ehz/buzzer.lemon`
for the engine to dispatch to. That's the next layer of work, zone by zone,
object by object -- not a data problem anymore, a "write the object's
actual lemonscript logic" problem.

## Not yet checked
- Whether `main_oxygen.lemon` / `standalone/mainmenu/` compile cleanly as-is
  (likely needs edits to boot straight into a debug/single-zone mode rather
  than a full title screen flow, since zone-select content is still S3K's)
- Ring layout conversion (separate from object layout -- s2disasm stores
  rings in their own table, same general idea, not yet looked at)

## MAJOR FINDING: core player physics are already correct, byte-for-byte
Started porting Sonic's physics from s2disasm into character.lemon, as
planned. Before writing anything, checked each constant against s2disasm's
real values to know what actually needs changing. Result: the core numbers
are already identical, not approximately close -- verified independently
from both sides of the code, not assumed:

| Constant                          | s2disasm (s2.asm)         | character.lemon (S3AIR)      |
|------------------------------------|----------------------------|-------------------------------|
| Top speed (normal)                | `0x600` (line 36232)       | `0x600` (debugmode.lemon fallback) |
| Acceleration (normal)             | `0xC` (line 36233)         | `0xC` (debugmode.lemon fallback)   |
| Deceleration (normal)             | `0x80` (line 36234)        | `0x80` (debugmode.lemon fallback)  |
| Gravity (per-frame)                | `0x38` (ObjectMoveAndFall) | `0x38` (character.lemon:1461) |
| Jump launch accel (normal)        | `0x680` (Sonic_Jump)       | `0x680` (character.lemon:2122)|
| Jump launch accel (Super)         | `0x800`                    | `0x800` (character.lemon:2122)|
| Jump launch accel (underwater)    | `0x380`                    | `0x380` (character.lemon:2122)|
| Variable jump height cap (normal) | `-0x400` (Sonic_JumpHeight)| `-0x400` (character.lemon:2740)|
| Variable jump height cap (water)  | `-0x200`                   | `-0x200` (character.lemon:2740)|
| Jump headroom check                | `>= 6px` (CalcRoomOverHead)| `>= 6` (character.lemon:2105) |

Both also use the same angle-based sine/cosine jump vector math (for
jumping while on slopes), the same post-jump flag sequence, and the same
"charging a spindash disables the upward-velocity cap" exception.

**What this means for scope**: the base running/jumping physics (the thing
that actually defines "does this feel like Sonic 2") require ZERO porting
work. S3K's engine inherited these values unchanged from S1/S2's shared
lineage (consistent with what the user originally suspected about a shared
engine ancestry -- confirmed true specifically for base movement, even
though the broader "same engine" claim wasn't right for object/boss code).

**Rolling physics -- also checked, also exact matches:**

| Constant                            | s2disasm (Sonic_RollSpeed)        | character.lemon                  |
|--------------------------------------|-------------------------------------|------------------------------------|
| Roll top speed                      | `Sonic_top_speed << 1` = `0xC00`   | `u16[A4] << 1` (line 4329)        |
| Natural roll deceleration            | `Sonic_acceleration >> 1` = `6`    | `u16[A4+2] >> 1` (line 4330)      |
| Controlled roll deceleration (input) | `0x20`                              | `0x20` (line 4339)                |

**Hitbox dimensions -- also checked, also exact matches:**

| Dimension          | s2disasm        | character.lemon (defines_character.lemon) |
|---------------------|-------------------|----------------------------------------------|
| Standing height/width | `0x13` / `9`   | `UPRIGHT` = `19` / `9`                       |
| Rolling height/width  | `0xE` / `7`    | `ROLLING` = `14` / `7`                       |

That's 4 for 4 independently-checked categories (run physics, jump
physics, roll physics, hitboxes) with zero discrepancies found. At this
point the evidence strongly supports: Sonic's core movement in S3K's
Oxygen port IS Sonic 1/2's original movement code, carried forward
unchanged, not just "similar."

**What's NOT yet checked, and may genuinely differ** (verify before
assuming, same discipline as above -- don't skip this, but expect more
matches given the pattern so far):
- Spin-dash charge/release values -- S2 uses the original (not Sonic 1.5
  style) spindash; S3K's spindash is also original-style, likely a match,
  not yet pulled
- Character-specific stats for Tails (separate constant set,
  `Tails_top_speed` etc. -- not yet pulled, but Tails' physics in both
  games are known to mirror Sonic's almost exactly)
- Underwater deceleration/friction modifiers beyond the two water-specific
  values already confirmed above
- Slope/rotation-angle collision sampling (the 8-direction floor sensor
  system) -- structurally complex, worth a dedicated pass rather than a
  quick grep-and-compare like the above

**Practical conclusion**: milestone 1 does not need a physics "port" in
the sense originally planned -- it needs a verification pass over the
remaining unchecked constants above, with corrections only where real
differences turn up. This meaningfully de-scopes the hardest part of the
original plan.

## Milestone 1 target
Emerald Hill Zone Act 1, fully playable: player physics ported from
s2disasm, tile collision, rings, one spring, one monitor type, one enemy
(Buzzer), zone boundary. Proves or disproves the whole approach.
