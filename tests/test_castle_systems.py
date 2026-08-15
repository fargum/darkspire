"""Tests for M2 systems: state/party, items/equip, progression, temple."""

import random

from game import creation, items, progression, temple
from game.character import STATS
from game.state import GameState, PARTY_CAP


def _char(name, alignment="gray", cls="warrior", **stat_overrides):
    stats = {s: 12 for s in STATS}
    stats.update(stat_overrides)
    return creation.create_character(
        name, "human", alignment, cls, stats, random.Random(hash(name) % 10000)
    )


# ---- party rules ---------------------------------------------------------

def test_party_alignment_gate():
    gs = GameState()
    light = _char("Aldric", "light")
    shadow = _char("Vex", "shadow")
    gray = _char("Moss", "gray")
    gs.roster = [light, shadow, gray]
    assert gs.add_to_party(light)[0]
    assert gs.add_to_party(gray)[0]
    ok, reason = gs.add_to_party(shadow)
    assert not ok and "Shadow" in reason


def test_party_cap():
    gs = GameState()
    gs.roster = [_char(f"Grunt{i}") for i in range(8)]
    for c in gs.roster[:PARTY_CAP]:
        assert gs.add_to_party(c)[0]
    ok, reason = gs.add_to_party(gs.roster[PARTY_CAP])
    assert not ok and "full" in reason


def test_gold_pool_pay_divvy():
    gs = GameState()
    a, b, c = _char("A"), _char("B"), _char("C")
    a.gold, b.gold, c.gold = 100, 50, 10
    gs.roster = gs.party = [a, b, c]
    assert gs.party_gold() == 160
    assert gs.party_pay(120)
    assert gs.party_gold() == 40
    assert not gs.party_pay(1000)
    gs.pool_gold(c)
    assert c.gold == 40 and a.gold == 0
    gs.divvy_gold()
    assert sorted(x.gold for x in gs.party) == [13, 13, 14]


def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("game.state.SAVE_DIR", tmp_path)
    monkeypatch.setattr("game.state.GAME_FILE", tmp_path / "game.json")
    monkeypatch.setattr("game.state.LEGACY_ROSTER", tmp_path / "roster.json")
    gs = GameState()
    a, b = _char("Alpha"), _char("Beta")
    gs.roster = [a, b]
    gs.party = [b]
    gs.save()
    loaded = GameState.load()
    assert [c.name for c in loaded.roster] == ["Alpha", "Beta"]
    assert [c.name for c in loaded.party] == ["Beta"]
    assert loaded.party[0] is loaded.roster[1]  # same object, not a copy


# ---- items ---------------------------------------------------------------

def test_equip_and_ac():
    c = _char("Tank")
    items.add_item(c, "leather_armor")
    items.add_item(c, "buckler")
    ok, _ = items.equip(c, 0)
    assert ok and c.ac == 8
    ok, _ = items.equip(c, 1)
    assert ok and c.ac == 7
    items.equip(c, 0)  # unequip armor
    assert c.ac == 9


def test_equip_slot_conflict():
    c = _char("Tank")
    items.add_item(c, "leather_armor")
    items.add_item(c, "chain_mail")
    items.equip(c, 0)
    items.equip(c, 1)  # chain replaces leather
    assert not c.inventory[0]["equipped"]
    assert c.inventory[1]["equipped"]
    assert c.ac == 6


def test_class_restrictions():
    mage = _char("Wisp", cls="mage", intellect=14)
    items.add_item(mage, "battle_axe")
    ok, msg = items.equip(mage, 0)
    assert not ok and "cannot use" in msg
    assert items.can_use(mage, "dagger")


def test_inventory_cap():
    c = _char("Packrat")
    for _ in range(items.INVENTORY_CAP):
        assert items.add_item(c, "dagger")
    assert not items.add_item(c, "dagger")


# ---- progression ---------------------------------------------------------

def test_xp_curve_monotonic_and_elite_costs_more():
    prev = 0
    for level in range(2, 14):
        need = progression.xp_for_level("warrior", level)
        assert need > prev
        prev = need
    assert progression.xp_for_level("sage", 5) > progression.xp_for_level("mage", 5)


def test_level_up():
    c = _char("Climber")
    c.xp = progression.xp_for_level("warrior", 2)
    assert progression.can_level(c)
    old_hp, old_level = c.max_hp, c.level
    gains = progression.level_up(c, random.Random(3))
    assert c.level == old_level + 1
    assert c.max_hp == old_hp + gains["hp"]
    assert gains["hp"] >= 1
    assert all(3 <= v <= 20 for v in c.stats.values())


# ---- temple --------------------------------------------------------------

def test_temple_costs_scale():
    c = _char("Lazarus")
    c.status = "DEAD"
    c.level = 4
    assert temple.cost_for(c) == 1000
    c.status = "POISONED"
    assert temple.cost_for(c) == 50


def test_resurrection_outcomes():
    revived = ashed = 0
    for seed in range(300):
        c = _char("Lazarus", vitality=10)
        c.status = "DEAD"
        success, _ = temple.attempt_service(c, random.Random(seed))
        if success:
            assert c.status == "OK" and c.hp == 1
            revived += 1
        else:
            assert c.status == "ASHES"
            ashed += 1
    assert revived > 0 and ashed > 0  # both outcomes possible


def test_ashes_never_lost_forever():
    c = _char("Phoenix", vitality=3)
    c.status = "ASHES"
    for seed in range(50):
        success, _ = temple.attempt_service(c, random.Random(seed))
        assert c.status in ("ASHES", "OK")  # never worse
        if success:
            break
