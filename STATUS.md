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
- `menus/` -- titlescreen, level select, competition mode: all S3K content
- Blue Sphere special stage, competition mode, Knuckles-specific cutscene

## Scaffolded, not yet built
- `level/01_ehz/`, `objects/01_ehz/` -- empty, this is milestone 1
- `oxygenproject.json` -- ROM checksum is a placeholder; fill in once you've
  verified your own dump

## Not yet checked
- Whether `main_oxygen.lemon` / `standalone/mainmenu/` compile cleanly with
  no menu scripts present (likely needs edits to boot straight into a
  debug/single-zone mode rather than a title screen)
- The `layout_actN.bin` binary format Oxygen's object-spawning system
  expects, vs. s2disasm's native object layout table format -- next
  concrete task, needed before Emerald Hill's object placement can be
  authored

## Milestone 1 target
Emerald Hill Zone Act 1, fully playable: player physics ported from
s2disasm, tile collision, rings, one spring, one monitor type, one enemy
(Buzzer), zone boundary. Proves or disproves the whole approach.
