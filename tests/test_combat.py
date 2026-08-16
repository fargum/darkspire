"""Tests for the combat engine."""

import random

import pygame
import pytest

from engine import palette
from engine.text import TextRenderer
from game import combat, creation, data, dice
from game.character import STATS
from scenes.combat import CombatScene


def _char(name, cls="warrior", **overrides):
    stats = {s: 12 for s in STATS}
    stats.update(overrides)
    align = "shadow" if cls == "shadowdancer" else "gray"
    c = creation.create_character(name, "human", align, cls, stats,
                                  random.Random(1))
    c.max_hp = c.hp = 12
    return c


def _groups(*specs):
    return [
        {"key": key, "members": [{"hp": hp} for hp in hps]}
        for key, hps in specs
    ]


def _combat(party, groups, seed=0, surprise=None):
    c = combat.Combat(party, groups, random.Random(seed))
    c.surprise = surprise
    return c


def test_dice():
    rng = random.Random(0)
    for _ in range(100):
        assert 2 <= dice.roll(rng, "2d4") <= 8
        assert 3 <= dice.roll(rng, "1d8+2") <= 10
    with pytest.raises(ValueError):
        dice.roll(rng, "d20")


def test_monster_data_valid():
    rng = random.Random(0)
    for key, d in data.load("monsters").items():
        dice.roll(rng, d["hp"])
        dice.roll(rng, d["gold"])
        for attack in d["attacks"]:
            dice.roll(rng, attack)
        assert d["level"] >= 1 and d["xp"] > 0
        assert d["name"] and d["plural"] and d["unknown"]


def test_encounter_tables_valid():
    rng = random.Random(0)
    monsters = data.load("monsters")
    for depth, table in data.load("encounters").items():
        for entry in table:
            assert entry["weight"] > 0
            for key, count in entry["groups"]:
                assert key in monsters
                assert dice.roll(rng, count) >= 1


def test_build_encounter():
    for seed in range(50):
        groups = combat.build_encounter(1, random.Random(seed))
        assert 1 <= len(groups) <= 2
        for g in groups:
            assert g["members"]
            assert all(m["hp"] >= 1 for m in g["members"])


def test_victory_and_rewards():
    party = [_char("Bruiser", might=18)]
    fight = _combat(party, _groups(("giant_rat", [1])), seed=3)
    for _ in range(30):
        if fight.result:
            break
        fight.resolve({0: ("fight", 0)})
    assert fight.result == "victory"
    assert fight.kills["giant_rat"] == 1
    xp_before = party[0].xp
    fight.distribute_rewards()
    assert party[0].xp == xp_before + 20


def test_defeat_marks_dead():
    weakling = _char("Frail", cls="mage", might=3)
    weakling.max_hp = weakling.hp = 1
    fight = _combat(weakling and [weakling],
                    _groups(("hollow_squire", [12, 12, 12])), seed=1)
    for _ in range(50):
        if fight.result:
            break
        fight.resolve({0: ("parry",)})
    assert fight.result == "defeat"
    assert weakling.status == "DEAD" and weakling.hp == 0


def test_fled_ends_combat():
    party = [_char("Sprinter", agility=18)]
    fled = False
    for seed in range(20):
        fight = _combat(party, _groups(("giant_rat", [2])), seed=seed)
        party[0].hp = party[0].max_hp
        fight.resolve({0: ("run",)})
        if fight.result == "fled":
            fled = True
            break
    assert fled


def test_back_row_protected_until_front_falls():
    front = [_char(f"F{i}") for i in range(3)]
    back = _char("Backline", cls="mage")
    party = front + [back]
    fight = _combat(party, _groups(("bonepicker", [5, 5])), seed=2)
    for _ in range(6):
        if fight.result:
            break
        fight.resolve({i: ("parry",) for i in range(4)})
    # while any front-liner stands, the back row is untouched
    if any(c.status != "DEAD" for c in front):
        assert back.hp == back.max_hp


def test_poison_applies():
    poisoned = False
    for seed in range(60):
        target = _char("Bitten")
        fight = _combat([target], _groups(("cellar_spider", [3])), seed=seed)
        for _ in range(10):
            if fight.result or target.status == "POISONED":
                break
            fight.resolve({0: ("parry",)})
        if target.status == "POISONED":
            poisoned = True
            break
    assert poisoned


def test_group_shifts_up_when_front_group_dies():
    party = [_char("Cleaver", might=18)]
    groups = _groups(("giant_rat", [1]), ("gutter_wisp", [1, 1]))
    fight = _combat(party, groups, seed=5)
    for _ in range(40):
        if fight.result:
            break
        fight.resolve({0: ("fight", 0)})
    assert fight.result == "victory"
    assert fight.kills["gutter_wisp"] == 2


def test_unidentified_then_identified():
    party = [_char("Scout")]
    fight = _combat(party, _groups(("giant_rat", [2, 2])), seed=7)
    assert "skittering" in fight.group_label(fight.groups[0])
    fight.resolve({0: ("parry",)})
    if fight.groups[0]["members"]:
        assert "Rat" in fight.group_label(fight.groups[0])


def test_combat_scene_staggers_result_lines():
    scene = CombatScene.__new__(CombatScene)
    scene.log = []
    scene.log_queue = []
    scene.state_ = "DECLARE"
    scene._pending_log_callback = None

    scene._queue_result_lines([("info", "one"), ("bad", "two")])

    assert scene.log == [("one", palette.TEXT)]
    assert scene.log_queue == [("bad", "two")]
    assert scene.state_ == "RESOLVING"

    scene._advance_result_log()

    assert scene.log == [("one", palette.TEXT), ("two", palette.BAD)]
    assert scene.log_queue == []


def test_combat_scene_draw_handles_resolving_state():
    pygame.init()
    scene = CombatScene.__new__(CombatScene)
    scene.app = type("App", (), {
        "text": TextRenderer(),
        "state": type("State", (), {"party": []})(),
    })()
    scene.fight = type("Fight", (), {
        "surprise": None,
        "alive_groups": lambda self: [],
    })()
    scene.log = [("one", palette.TEXT)]
    scene.state_ = "RESOLVING"
    scene.menu = None
    scene.target_menu = None
    scene.item_menu = None
    scene.spell_menu = None
    scene.chest_menu = None
    scene.draw(pygame.Surface((640, 400)))
