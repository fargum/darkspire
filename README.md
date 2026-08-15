# DARKSPIRE: Depths of the Mad Archon

A Wizardry-inspired party-based dungeon crawler built with Python.
I created this as a way of testing out the capabilities and cost of Claude Fable.
I worked with the AI in coming up with a plan for building this complete game.
And allowed it to implement the plan. full cost for the finished and polished version
was around £58. We took about 2-3 hours working together to produce it.

Create a roster of
adventurers, form a party of six, and descend the ten-level Darkspire to
take the stolen Everflame back from Vexis, the Mad Archon.

See `DESIGN.md` for the full design document.

## Run (from source)

```
.venv\Scripts\python main.py
```

## Run (packaged)

```
dist\Darkspire\Darkspire.exe
```

Saves are written to a `saves\` folder next to the exe (or the project root
when running from source).

## Controls

- Menus: arrow keys / WASD move · Enter selects · Esc backs out
- Stat allocation: ◄ ► adjust the selected stat · R rerolls the bonus pool
- Maze: ↑ forward · ◄ ► turn · ↓ about-face · C or Esc opens camp

## Development

```
.venv\Scripts\python -m pytest tests\ -q        # test suite
.venv\Scripts\python tools\gen_levels.py        # regenerate maze levels
.venv\Scripts\python tools\balance_sim.py 100   # headless balance delves
.venv\Scripts\pyinstaller Darkspire.spec        # rebuild the exe
```

All game content — races, classes, spells, items, monsters, encounter and
loot tables, rumors, and the ten maze levels — lives in `data/` as JSON.
The `game/` package is a pure-Python rules library (no pygame) covered by
the test suite; scenes and rendering sit on top.

## About

Darkspire is a non-commercial fan homage to the classic 1981 dungeon
crawler *Wizardry: Proving Grounds of the Mad Overlord*. It is not
affiliated with, endorsed by, or connected to the Wizardry rights holders.
All code, maps, story, characters, monsters, art, and audio are original;
the spell names are used in tribute to the genre's roots. Code is released
under the MIT License (see `LICENSE`).
