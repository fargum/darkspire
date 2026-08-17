"""Tests for M7: deep levels, illusions, null zones, sp drain, the finale."""

import random

from game import combat, creation, data, maze, spells
from game.character import STATS


def _char(name, cls="warrior", level=8, **overrides):
    stats = {s: 14 for s in STATS}
    stats.update(overrides)
    c = creation.create_character(name, "human", "gray", cls, stats,
                                  random.Random(1))
    c.level = level
    c.max_hp = c.hp = 60
    return c


def _groups(*specs):
    return [
        {"key": key, "members": [{"hp": hp, "status": "OK"} for hp in hps]}
        for key, hps in specs
    ]


def test_endgame_monster_data():
    monsters = data.load("monsters")
    assert len(monsters) == 48
    vexis = monsters["vexis"]
    assert vexis["caster"] and vexis["drain"] and vexis["xp"] == 100000
    for depth in range(1, 11):
        assert str(depth) in data.load("encounters")
        assert str(depth) in data.load("loot")


def test_illusory_walls():
    l10 = maze.load_level(10)
    # the sanctum's only entrance is an illusion at (10,5)->(10,4)... via edge north of (10,6)
    found = any(
        l10.edge(x, y, f) == maze.ILLUSION
        for x in range(20) for y in range(20) for f in range(4)
    )
    assert found
    # illusions are passable
    for x in range(20):
        for y in range(20):
            for f in range(4):
                if l10.edge(x, y, f) == maze.ILLUSION:
                    assert l10.passable(x, y, f)


def test_null_zones():
    l8 = maze.load_level(8)
    assert l8.null_at(10, 10)      # the Seraph's cell
    assert not l8.null_at(16, 3)   # arrival landing
    l9 = maze.load_level(9)
    assert l9.null_at(10, 5)
    assert l9.dark_at(10, 16)


def test_null_blocks_monster_casting():
    party = [_char("Tank")]
    for seed in range(30):
        fight = combat.Combat(party, _groups(("archon_echo", [20, 20])),
                              random.Random(seed))
        fight.surprise = None
        fight.null = True
        party[0].hp = party[0].max_hp
        lines = fight.resolve({0: ("parry",)})
        assert not any("casts" in t for _, t in lines)


def test_sp_drain_eats_points():
    caster = _char("Wisp", cls="mage", level=9)
    spells.restore(caster)
    total_before = sum(caster.sp["mage"])
    drained = False
    for seed in range(60):
        fight = combat.Combat([caster], _groups(("null_stalker", [30])),
                              random.Random(seed))
        fight.surprise = None
        caster.hp = caster.max_hp
        caster.status = "OK"
        for _ in range(6):
            if fight.result:
                break
            fight.resolve({0: ("parry",)})
        if sum(caster.sp["mage"]) < total_before:
            drained = True
            break
    assert drained


def test_quest_specials_l7_to_l10():
    l7 = maze.load_level(7)
    amalgam = next(s for s in l7.specials.values() if s["type"] == "encounter")
    assert amalgam["grant"] == "black_key"
    down7 = next(s for s in l7.specials.values() if s["type"] == "stairs_down")
    assert down7["requires"] == "black_key"

    l8 = maze.load_level(8)
    seraph = next(s for s in l8.specials.values()
                  if s["type"] == "quest_item")
    assert seraph["grant"] == "seraph_blessing"

    l9 = maze.load_level(9)
    lens = next(s for s in l9.specials.values() if s["type"] == "quest_item")
    assert lens["grant"] == "void_lens"
    down9 = next(s for s in l9.specials.values() if s["type"] == "stairs_down")
    assert down9["requires"] == "wardlantern"
    elev = next(s for s in l9.specials.values() if s["type"] == "elevator")
    assert elev["floors"] == [4, 9] and elev["requires"] == "black_key"

    l10 = maze.load_level(10)
    vexis = next(s for s in l10.specials.values()
                 if s["type"] == "encounter" and s["id"] == "vexis")
    assert vexis["grant"] == "everflame_taken"
    portal = next(s for s in l10.specials.values() if s["type"] == "portal")
    assert portal["requires"] == "everflame_taken"


def test_second_elevator_on_both_ends():
    for depth in (4, 9):
        lvl = maze.load_level(depth)
        shafts = [(p, s) for p, s in lvl.specials.items()
                  if s["type"] == "elevator" and s["floors"] == [4, 9]]
        assert len(shafts) == 1
        assert shafts[0][0] == (18, 18)


def test_rumors_shape():
    rumors = data.load("rumors")
    assert isinstance(rumors["main"], list) and len(rumors["main"]) >= 15
    assert isinstance(rumors["postgame"], list) and rumors["postgame"]
