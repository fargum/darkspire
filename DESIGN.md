# DARKSPIRE: Depths of the Mad Archon
### A Wizardry-inspired party-based dungeon crawler — Design & Implementation Plan

*(Working title — easy to rename. Everything below is our own content: original classes, spells,
monsters, and maze, built on the classic Wizardry I mechanical skeleton.)*

---

## 1. Vision

A single-player, party-based, first-person dungeon crawler in the spirit of *Wizardry: Proving
Grounds of the Mad Overlord* (1981). The player creates a roster of adventurers in the town of
**Aldenmoor**, assembles a party of six at the tavern, and descends the ten-level **Darkspire**
beneath the castle to recover the **Everflame** — the living fire that fuels the town's protective
wards, stolen by the **Mad Archon Vexis**. Every day it burns in his sanctum, Aldenmoor's wards
grow dimmer and the things in the deep climb higher.

- **Platform:** Windows PC, Python 3.12+, `pygame-ce` (plus `numpy` for sound synthesis)
- **View:** classic first-person wireframe maze, one step at a time
- **Difficulty:** classic with softer edges — death and failed resurrections matter, but no
  character is ever lost forever, and you can save freely at the castle
- **Art:** procedurally generated pixel-art monster portraits (swappable for hand-drawn art later)
- **Audio:** procedurally synthesized retro bleeps and effects
- **Quest:** one classic main quest gated by key items across 10 maze levels

---

## 2. Game Structure

A scene/state machine drives everything:

```
Title ─► Castle (hub)
           ├── Training Grounds .. create/inspect/change class/delete characters
           ├── Gilded Griffin Tavern .. form party, divvy gold, hear rumors
           ├── Adventurer's Rest (Inn) .. rest to heal, level up, (save)
           ├── Boltac-style Trading Post → "The Iron Ledger" .. buy/sell/identify/uncurse
           ├── Temple of the Dawnmother .. heal, cure, resurrect
           └── Edge of Town ─► Maze Entrance ─► THE DARKSPIRE (10 levels)
                                                   ├── Exploration (first-person)
                                                   ├── Camp (spells, items, reorder, equip)
                                                   └── Combat (turn-based)
```

**Saving:** automatic + manual save at the castle. Entering the maze snapshots the party; if the
program is closed mid-maze, the party is marked *"lost in the maze"* and can be recovered at the
Training Grounds (they walk out with a small gold penalty — softer than the original's corpse
retrieval, but leaving the maze still isn't free).

**Party wipe:** bodies remain where they fell. Any new party can find them and carry them out, or
pay the Temple to mount a recovery expedition (costs scale with depth).

---

## 3. Characters

### 3.1 Attributes (3–18 at creation, racial mins/maxes, cap 20)

| Attribute | Governs |
|---|---|
| **Might** | melee damage, carry capacity |
| **Agility** | initiative, AC bonus, trap disarm, flee chance |
| **Vitality** | HP per level, resurrection survival, poison resist |
| **Intellect** | arcane spell learning, spell points, identify chance |
| **Faith** | divine spell learning, spell points, curse resist |
| **Luck** | criticals, treasure quality, saving throws |

Creation follows the classic ritual: pick race → roll a **bonus pool** (7–15, rare big rolls up to
25+) → distribute onto racial base stats → eligible classes light up → pick class and alignment.

### 3.2 Races

The classic five:

| Race | Statistical lean |
|---|---|
| **Human** | balanced baseline |
| **Elf** | +Int/+Faith, −Vit |
| **Dwarf** | +Might/+Vit, −Agi |
| **Gnome** | +Faith/+Agi, −Luck |
| **Halfling** | +Agi/+Luck, −Might |

### 3.3 Alignment

**Light / Gray / Shadow.** Light and Shadow characters won't share a party (Gray goes with
either). Some classes and items are alignment-locked. Alignment can drift from in-maze choices
(sparing fleeing monsters, robbing shrines).

### 3.4 Classes — 4 base + 4 elite

| Class | Requirements | Role |
|---|---|---|
| **Warrior** | Might 11 | front-line damage/tank, best weapons & armor |
| **Mage** | Int 11 | mage spells (7 levels), fragile |
| **Priest** | Faith 11 | priest spells (7 levels), maces, medium armor |
| **Rogue** | Agi 11 | traps, locks, hide-and-backstab, best chest work |
| **Spellblade** | Might 13, Int 12, not Light | warrior + mage spells levels 1–4, slow learner |
| **Templar** | Might 13, Faith 12, Light only | warrior + priest spells levels 1–4, can *Lay Hands* |
| **Sage** | Int 12, Faith 12 | both schools (slowly), master identifier of items |
| **Shadowdancer** | Agi 15, Luck 14, Shadow only | elite rogue, chance of instant-kill strikes, hides in combat |

Class change is allowed at the Training Grounds (resets level to 1, keeps stats/spells known —
the classic long-game build path).

### 3.5 Progression

- Per-class XP tables (elite classes ~1.6× base cost)
- Level up **only at the Inn** (classic): HP roll (Vitality-modified), chance of ±1 stat swings,
  new spell levels/points, elite abilities at milestones
- **No aging system** (softer edge) — resting costs gold, not years

---

## 4. Magic

Two schools, 7 levels each, **spell points per level** (not a shared mana pool), restored by
resting at the Inn or (partially) camping with rations.

**We use the original Wizardry I spell lists verbatim** — same names, same effects (50 spells):

| Lvl | Mage spells | Priest spells |
|---|---|---|
| 1 | HALITO · MOGREF · KATINO · DUMAPIC | KALKI · DIOS · BADIOS · MILWA · PORFIC |
| 2 | DILTO · SOPIC | MATU · CALFO · MANIFO · MONTINO |
| 3 | MAHALITO · MOLITO | LOMILWA · DIALKO · LATUMAPIC · BAMATU |
| 4 | MORLIS · DALTO · LAHALITO | DIAL · BADIAL · LATUMOFIS · MAPORFIC |
| 5 | MAMORLIS · MAKANITO · MADALTO | DIALMA · BADIALMA · LITOKAN · KANDI · DI · BADI |
| 6 | LAKANITO · ZILWAN · MASOPIC · HAMAN | LORTO · MADI · MABADI · LOKTOFEIT |
| 7 | MALOR · MAHAMAN · TILTOWAIT | MALIKTO · KADORTO |

Casting in the maze from the Camp menu (healing, MILWA/LOMILWA light, DUMAPIC location, MALOR
teleport) is fully supported. MALOR into solid rock = party deposited at the maze entrance, badly
hurt (softened from the original's instant party loss). LOKTOFEIT remains the desperate
everything-but-your-gear escape it always was.

---

## 5. The Darkspire — 10 Levels

Hand-authored 20×20 grids, **walls/doors on cell edges** (true Wizardry style), stored as JSON.
Fixed encounters, messages, and specials are authored per level; random encounters roll from
per-level tables.

**Special squares:** darkness zones, spinners, teleporters, chutes (one-way down), pressure-plate
traps, elevators (L1↔L4, L4↔L9 once unlocked), message/riddle squares, locked doors, healing
fonts (rare), anti-magic zones (deep levels).

| Lvl | Theme | Gate / quest beat |
|---|---|---|
| 1 | The Undercroft — crypts, vermin, rogue apprentices | learn of the **Bronze Sigil** |
| 2 | Flooded Cisterns — slimes, drowned dead | find **Bronze Sigil** (opens L3 stair) |
| 3 | The Foundry — animated armor, fire vents | mini-boss: **Forge Warden** → **Iron Key** |
| 4 | Fungal Warrens — myconids, poison everywhere | elevator hub; riddle of the Pale Court |
| 5 | The Pale Court — undead nobility, level-drain wraiths (soft drain: recoverable at Temple) | **Ivory Crown** — tribute to pass L6 |
| 6 | Shifting Halls — heavy spinners/teleporters, mimics | map fragments reveal L7 route |
| 7 | The Menagerie — Vexis's failed experiments, chimeras | mini-boss: **The Amalgam** → **Black Key** |
| 8 | Ember Gaol — demons, fire theme, anti-magic cells | free the **Bound Seraph** (blessing: +1 all saves) |
| 9 | The Null Ward — darkness + anti-magic labyrinth | **Void Lens** needed to see L10's true doors |
| 10 | The Archon's Sanctum — elite guard, illusory walls | **VEXIS, the Mad Archon** and the stolen **Everflame** |

**Endgame:** defeating Vexis breaks his hold on the **Everflame**, which the party captures in the
**Wardlantern** (given to them at the Temple when they first reach level 9 — carrying it into the
Sanctum is part of the quest). The lantern is a powerful invokable relic on the journey out, and
bearing the flame opens a one-way ceremonial portal to the castle. Restoring the Everflame to
Aldenmoor's ward-brazier earns the party a title, a large XP/gold award, and new tavern rumors
(post-game superboss hook we can add later).

---

## 6. Combat

Turn-based, party of 6 (front 3 melee-capable rows vs monster **up to 4 groups**, 1–9 each).

- **Unidentified monsters** show vague names ("a shambling figure") until identified by sight
  (Sage/level check) or LATUMAPIC
- **Round flow:** all combatants declare → initiative order (Agility + class + d10) → resolve
- **Actions:** Fight, Parry (+AC), Cast, Use item, Hide (rogues), Dispel (Templar vs undead),
  Run (party-wide, Agility-checked; failure = free enemy round)
- **Surprise:** either side can get a free round; Shadowdancers strike from hiding for instant-kill chances
- **Status effects:** sleep, poison, paralysis, silence, fear, stone, drain (recoverable)
- **Monster AI:** simple per-monster weights (aggressive / caster / breath / call-for-help / flee-at-low-HP)
- **Friendly encounters:** some groups offer to leave — attacking Light-aligned wanderers drifts
  the party toward Shadow

**Bestiary:** ~60 original monsters across the 10 levels — e.g. Gutter Wisp, Bonepicker, Rust
Slime, Hollow Knight, Pale Countess, Cinder Fiend, Null Stalker, Archon's Echo… each with a
procedurally generated pixel portrait (deterministic from monster id, so art is stable).

---

## 7. Items & Economy

- ~80 items in tiers: mundane → fine → enchanted → relic; class & alignment restrictions
- **Unidentified drops** ("?Sword") — identify at the Iron Ledger (fee) or via a Sage (free, small
  mishap chance of triggering a curse)
- **Cursed items** weld themselves on until Temple uncursing
- **Invokable items** (charges, may crumble): wands, the quest relics, the Wardlantern itself
- **Chests** guard fixed/boss treasure: Rogue inspects (or Priest casts CALFO) → disarm by naming
  the trap —
  original trap list: *Needle, Gas Bloom, Screamer (summons), Mind Jar, Rust Mist, Null Spark,
  Trapdoor (chute!), Glyph of Ash*
- Gold is per-character with **Pool Gold** at shops; Inn rooms from cot (cheap) to royal suite
  (fast spell-point recovery)

---

## 8. Presentation

### 8.1 Wireframe renderer
- 640×400 logical resolution (integer-scaled to window), classic layout: maze viewport top-left,
  party roster bottom, message log right
- Perspective wireframe: draws wall edges/doors for cells up to 4 deep in the facing direction,
  nested trapezoid projection — solid dark fills with bright edge lines (CGA-meets-amber aesthetic,
  one accent palette per dungeon theme)
- MILWA/LOMILWA extend draw distance; darkness zones collapse it to 1
- **Automap** deliberately absent — but DUMAPIC gives coordinates + facing as in the original,
  honoring the graph-paper tradition without pure cruelty *(if it stings in playtesting, we add an
  earned automap item late-game)*

### 8.2 Pixel art
- Monster portraits: 64×64, generated by a seeded procedural sprite tool (silhouette + palette +
  detail passes per monster "family"), cached to `assets/gen/`
- UI: 8×8 bitmap font (embedded), simple bordered panels

### 8.3 Audio
- `numpy`-synthesized: square/noise-channel effects for steps, doors, hits, spells, chest traps,
  level-up fanfare, death knell — generated once at startup, cached as WAV

---

## 9. Technical Architecture

```
darkspire/
├── main.py                  # entry point
├── engine/                  # scene manager, input map, UI widgets, font, palette
├── game/                    # rules layer — PURE PYTHON, no pygame imports
│   ├── character.py, party.py, items.py, spells.py, monsters.py
│   ├── combat.py            # full combat resolution, deterministic w/ seeded RNG
│   ├── maze.py              # grid model, movement, specials, encounters
│   └── save.py              # JSON save/load, roster + game state
├── scenes/                  # title, castle, training, tavern, inn, shop, temple,
│                            # maze_explore, camp, combat, endgame
├── render/                  # wireframe renderer, portrait generator, panels
├── audio/                   # synth + sound bank
├── data/                    # JSON: races, classes, spells, items, monsters,
│                            # levels/level01.json … level10.json, encounter tables
└── tests/                   # pytest over game/ (combat math, leveling, traps, saves)
```

**Key principle:** `game/` is a pure rules library with injected RNG — fully unit-testable and
UI-independent. Scenes are thin controllers; `render/` and `audio/` are dumb outputs. All content
lives in JSON data files so balancing never touches code.

---

## 10. Implementation Milestones

Each milestone ends **playable and testable**.

| # | Milestone | Delivers |
|---|---|---|
| **M0** | Skeleton | pygame window, scene manager, bitmap font, palette, input map, title screen |
| **M1** | Characters | data files (races/classes), full Training Grounds creation flow, roster save/load |
| **M2** | Castle hub | tavern party formation, inn rest/level-up, shop buy/sell, temple heal — economy loop works |
| **M3** | Into the maze | wireframe renderer, movement/turning, doors/stairs, Level 1 map, camp menu, kick-the-door random encounter *stub*, return to castle |
| **M4** | Combat | full combat system, monsters for L1–L2, XP/gold awards, death & temple resurrection chain |
| **M5** | Magic & loot | both spell schools end-to-end, equipment effects, chests + trap minigame, identify/curse flow |
| **M6** | Mid-game | levels 3–6 content, all special square types, elevators, quest items, mini-boss 1, tavern rumors |
| **M7** | Endgame | levels 7–10, Vexis boss fight, amulet, victory sequence |
| **M8** | Polish | audio pass, portrait generator upgrade, balance sweep (scripted auto-play sims), Windows packaging via PyInstaller |

Suggested order of attack: M0–M2 are quick wins; M3 (renderer) and M4 (combat) are the two big
engineering lifts; M5+ is mostly content authoring on finished systems.

---

## 11. Testing & Balance

- `pytest` suite over `game/`: character creation legality, XP tables, combat resolution with
  seeded RNG, trap/chest outcomes, save round-trips, maze movement vs. wall data
- **Headless balance sims:** scripted parties auto-fight level encounter tables thousands of times
  to tune monster stats before human playtesting
- Data validation script: every level JSON checked for unreachable cells, doors without walls,
  stairs that match between levels
