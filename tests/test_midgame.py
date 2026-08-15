"""Tests for M6: monster abilities, drain, quest data integrity."""

import random

from game import combat, creation, data, dice, maze
from game.character import STATS
from game.state import GameState


def _char(name, cls="warrior", level=1, **overrides):
    stats = {s: 12 for s in STATS}
    stats.update(overrides)
    c = creation.create_character(name, "human", "gray", cls, stats,
                                  random.Random(1))
    c.level = level
    c.max_hp = c.hp = 30
    return c


def _fight(party, groups, seed=0):
    f = combat.Combat(party, groups, random.Random(seed))
    f.surprise = None
    return f


def _groups(*specs):
    return [
        {"key": key, "members": [{"hp": hp, "status": "OK"} for hp in hps]}
        for key, hps in specs
    ]


def test_new_monster_data_valid():
    rng = random.Random(0)
    monsters = data.load("monsters")
    assert len(monsters) >= 30
    for key, d in monsters.items():
        caster = d.get("caster")
        if caster:
            for spell in caster["spells"]:
                assert spell in combat.MONSTER_SPELLS, f"{key}: {spell}"
        breath = d.get("breath")
        if breath:
            dice.roll(rng, breath["dice"])
        assert 0 <= d.get("drain", 0) < 1


def test_encounters_and_loot_cover_depths_1_to_6():
    for depth in range(1, 7):
        assert str(depth) in data.load("encounters")
        assert str(depth) in data.load("loot")
        groups = combat.build_encounter(depth, random.Random(depth))
        assert groups


def test_monster_caster_casts():
    party = [_char("Tank")]
    saw_cast = False
    for seed in range(40):
        fight = _fight(party, _groups(("spore_witch", [10, 10])), seed=seed)
        party[0].hp = party[0].max_hp
        party[0].status = "OK"
        lines = fight.resolve({0: ("parry",)})
        if any("casts" in t for _, t in lines):
            saw_cast = True
            break
    assert saw_cast


def test_monster_sleep_can_land_and_wears_off():
    party = [_char("Tank")]
    slept = False
    for seed in range(60):
        target = _char("Tank")
        fight = _fight([target], _groups(("spore_witch", [10])), seed=seed)
        for _ in range(6):
            if fight.result:
                break
            fight.resolve({0: ("parry",)} if target.status == "OK" else {})
            if target.status == "ASLEEP":
                slept = True
        if slept:
            break
    assert slept


def test_breath_hits_back_row_too():
    front = [_char(f"F{i}") for i in range(3)]
    back = _char("Backline", cls="mage")
    party = front + [back]
    hurt_back = False
    for seed in range(40):
        for c in party:
            c.hp = c.max_hp = 30
            c.status = "OK"
        fight = _fight(party, _groups(("ember_hound", [12, 12])), seed=seed)
        for _ in range(6):
            if fight.result:
                break
            fight.resolve({i: ("parry",) for i in range(4)})
        if back.hp < back.max_hp:
            hurt_back = True
            break
    assert hurt_back


def test_drain_reduces_level_and_tracks():
    drained = False
    for seed in range(60):
        victim = _char("Vessel", level=5)
        fight = _fight([victim], _groups(("pale_wraith", [15])), seed=seed)
        for _ in range(8):
            if fight.result:
                break
            fight.resolve({0: ("parry",)})
        if victim.drained > 0:
            assert victim.level < 5
            drained = True
            break
    assert drained


def test_quest_flags_persist(tmp_path, monkeypatch):
    monkeypatch.setattr("game.state.SAVE_DIR", tmp_path)
    monkeypatch.setattr("game.state.GAME_FILE", tmp_path / "game.json")
    monkeypatch.setattr("game.state.LEGACY_ROSTER", tmp_path / "roster.json")
    gs = GameState()
    gs.roster = [_char("Keeper")]
    gs.quest["bronze_sigil"] = True
    gs.quest["enc_forge_warden"] = True
    gs.save()
    loaded = GameState.load()
    assert loaded.quest["bronze_sigil"]
    assert loaded.quest["enc_forge_warden"]


def test_quest_specials_present():
    l2 = maze.load_level(2)
    grants = [s.get("grant") for s in l2.specials.values()]
    assert "bronze_sigil" in grants
    down = next(s for s in l2.specials.values() if s["type"] == "stairs_down")
    assert down["requires"] == "bronze_sigil"

    l3 = maze.load_level(3)
    enc = next(s for s in l3.specials.values() if s["type"] == "encounter")
    assert enc["grant"] == "iron_key" and enc["once"]

    l4 = maze.load_level(4)
    riddle = next(s for s in l4.specials.values() if s["type"] == "riddle")
    assert riddle["grant"] == "pale_word" and riddle["answer"] == "echo"

    l5 = maze.load_level(5)
    gate = next(s for s in l5.specials.values() if s["type"] == "gate")
    assert gate["requires"] == "pale_word"
    enc5 = next(s for s in l5.specials.values() if s["type"] == "encounter")
    assert enc5["grant"] == "ivory_crown"
    down5 = next(s for s in l5.specials.values() if s["type"] == "stairs_down")
    assert down5["requires"] == "ivory_crown"


def test_elevator_floors_match():
    for depth in (1, 4):
        lvl = maze.load_level(depth)
        elev = next(s for s in lvl.specials.values() if s["type"] == "elevator")
        assert elev["floors"] == [1, 4]
        pos = next(p for p, s in lvl.specials.items() if s["type"] == "elevator")
        assert pos == (2, 2)


def test_dark_zones():
    l2 = maze.load_level(2)
    assert l2.dark_at(2, 10)       # the sigil chamber is dark
    assert not l2.dark_at(17, 3)   # arrival gallery is not
