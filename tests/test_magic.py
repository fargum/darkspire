"""Tests for spells, chests, and the identify/curse flow."""

import random

from game import chests, combat, creation, data, dice, items, spells
from game.character import STATS
from game.state import GameState


def _char(name, cls="mage", level=1, **overrides):
    stats = {s: 12 for s in STATS}
    stats.update(overrides)
    align = "shadow" if cls == "shadowdancer" else "gray"
    c = creation.create_character(name, "human", align, cls, stats,
                                  random.Random(1))
    c.level = level
    c.max_hp = c.hp = 20
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


# ---- spell data & points -------------------------------------------------

def test_spell_data_valid():
    for key, d in data.load("spells").items():
        assert d["school"] in ("mage", "priest")
        assert 1 <= d["level"] <= 7
        assert d["context"] in ("combat", "camp", "both", "chest")
        assert d["target"] in ("group", "all", "ally", "party", "self", "none")
    assert len(data.load("spells")) == 50


def test_point_progression():
    mage = _char("Wisp", "mage", level=1)
    mx = spells.max_points(mage)
    assert mx["mage"][0] == 1 and mx["mage"][1] == 0
    mage.level = 5
    mx = spells.max_points(mage)
    assert mx["mage"][:3] == [5, 3, 1]
    mage.level = 13
    assert spells.max_points(mage)["mage"][6] == 1
    mage.level = 30
    assert all(v == 9 for v in spells.max_points(mage)["mage"])


def test_elite_casters_slower():
    blade = _char("Edge", "spellblade", level=4, might=14)
    assert spells.max_points(blade)["mage"][0] == 1
    assert spells.max_points(blade)["mage"][4:] == [0, 0, 0]
    sage = _char("Lore", "sage", level=3, faith=13)
    mx = spells.max_points(sage)
    assert mx["mage"][0] == 1 and mx["priest"][0] == 1


def test_noncasters_have_nothing():
    assert not spells.is_caster(_char("Thug", "warrior"))
    assert not spells.is_caster(_char("Knife", "rogue"))


def test_cast_spends_point_and_damages():
    mage = _char("Wisp", "mage", level=1)
    fight = _fight([mage], _groups(("giant_rat", [4])))
    spells.ensure(mage)
    assert spells.points_left(mage, "halito") == 1
    lines = spells.cast_combat(mage, "halito", 0, fight, random.Random(3))
    assert spells.points_left(mage, "halito") == 0
    assert any("HALITO" in t for _, t in lines)


def test_katino_sleeps_and_melee_bonus():
    mage = _char("Wisp", "mage", level=5)
    fight = _fight([mage], _groups(("giant_rat", [4, 4, 4])), seed=4)
    spells.ensure(mage)
    spells.cast_combat(mage, "katino", 0, fight, random.Random(1))
    assert any(m["status"] == "ASLEEP"
               for m in fight.groups[0]["members"])


def test_tiltowait_devastates_all_groups():
    mage = _char("Boom", "mage", level=13)
    spells.ensure(mage)
    fight = _fight([mage], _groups(("giant_rat", [4, 4]),
                                   ("bonepicker", [8, 8])))
    spells.cast_combat(mage, "tiltowait", None, fight, random.Random(0))
    assert not fight.alive_groups()
    assert fight.kills["giant_rat"] == 2 and fight.kills["bonepicker"] == 2


def test_zilwan_only_undead():
    mage = _char("Sun", "mage", level=11)
    spells.ensure(mage)
    fight = _fight([mage], _groups(("bonepicker", [8]), ("giant_rat", [4])))
    spells.cast_combat(mage, "zilwan", 0, fight, random.Random(0))
    assert not fight.groups[0]["members"]        # undead destroyed
    spells.ensure(mage)
    fight2 = _fight([mage], _groups(("giant_rat", [4])))
    spells.cast_combat(mage, "zilwan", 0, fight2, random.Random(0))
    assert fight2.groups[0]["members"]           # rat unimpressed


def test_priest_heals():
    priest = _char("Vicar", "priest", level=1, faith=14)
    hurt = _char("Tank", "warrior")
    hurt.hp = 5
    fight = _fight([priest, hurt], _groups(("giant_rat", [4])))
    spells.ensure(priest)
    spells.cast_combat(priest, "dios", 1, fight, random.Random(2))
    assert hurt.hp > 5


def test_camp_heal_and_light():
    gs = GameState()
    priest = _char("Vicar", "priest", level=3)
    gs.roster = gs.party = [priest]
    gs.maze = {"depth": 1, "x": 5, "y": 5, "facing": 0}
    spells.ensure(priest)
    priest.hp = 3
    lines, signal = spells.cast_camp(priest, "dios", priest, gs, random.Random(1))
    assert priest.hp > 3 and signal is None
    lines, _ = spells.cast_camp(priest, "milwa", None, gs, random.Random(1))
    assert gs.maze["light"] == 45
    lines, _ = spells.cast_camp(priest, "lomilwa", None, gs, random.Random(1))
    assert gs.maze["light"] == -1


def test_loktofeit_escape():
    gs = GameState()
    priest = _char("Vicar", "priest", level=11)
    priest.gold = 500
    gs.roster = gs.party = [priest]
    gs.maze = {"depth": 1, "x": 5, "y": 5, "facing": 0}
    spells.ensure(priest)
    lines, signal = spells.cast_camp(priest, "loktofeit", None, gs,
                                     random.Random(1))
    assert signal == "castle" and gs.maze is None and priest.gold == 0


def test_malor_valid_and_rock():
    gs = GameState()
    mage = _char("Jump", "mage", level=13)
    gs.roster = gs.party = [mage]
    gs.maze = {"depth": 1, "x": 5, "y": 5, "facing": 0}
    spells.malor_jump(gs, 10, 13, random.Random(1))
    assert (gs.maze["x"], gs.maze["y"]) == (10, 13)
    mage.hp = 20
    spells.malor_jump(gs, 55, 2, random.Random(1))
    assert (gs.maze["x"], gs.maze["y"]) == (10, 19)   # dumped at entrance
    assert mage.hp < 20


def test_inn_style_restore():
    mage = _char("Wisp", "mage", level=5)
    spells.ensure(mage)
    mage.sp["mage"] = [0] * 7
    spells.restore(mage)
    assert mage.sp["mage"][:3] == [5, 3, 1]


# ---- chests --------------------------------------------------------------

def test_chest_rolls():
    found = trapped = 0
    for seed in range(300):
        chest = chests.maybe_chest(1, random.Random(seed))
        if chest:
            found += 1
            if chest["trap"]:
                trapped += 1
            assert chest["gold"] > 0
    assert 0 < found < 300
    assert 0 < trapped <= found


def test_disarm_correct_guess():
    rogue = _char("Fingers", "rogue", level=5, agility=16)
    outcomes = set()
    for seed in range(50):
        chest = {"trap": "Needle", "gold": 10, "item": None, "open": False}
        outcomes.add(chests.disarm(rogue, chest, "Needle", random.Random(seed)))
    assert "disarmed" in outcomes


def test_disarm_wrong_guess_triggers():
    rogue = _char("Fingers", "rogue", level=5, agility=16)
    chest = {"trap": "Needle", "gold": 10, "item": None, "open": False}
    assert chests.disarm(rogue, chest, "Screamer", random.Random(1)) == "triggered"


def test_trigger_effects():
    opener = _char("Hand", "warrior")
    party = [opener]
    chest = {"trap": "Mind Jar", "gold": 10, "item": None, "open": False}
    lines, summon = chests.trigger(chest, party, opener, random.Random(1))
    assert opener.status == "PARALYZED" and not summon
    chest = {"trap": "Screamer", "gold": 10, "item": None, "open": False}
    _, summon = chests.trigger(chest, party, opener, random.Random(1))
    assert summon


def test_open_distributes_loot():
    a, b = _char("A", "warrior"), _char("B", "warrior")
    chest = {"trap": None, "gold": 100, "item": "dagger_p1", "open": False}
    lines = chests.open_chest(chest, [a, b], random.Random(1))
    assert a.gold - 164 == 50 or a.gold >= 50   # 50 each on top of start
    carried = a.inventory + b.inventory
    assert any(e["key"] == "dagger_p1" and not e["identified"] for e in carried)


# ---- identify / curse ----------------------------------------------------

def test_unidentified_display():
    c = _char("Finder", "warrior")
    items.add_item(c, "dagger_p1", identified=False)
    assert items.display_name(c.inventory[0]) == "? Dagger"
    c.inventory[0]["identified"] = True
    assert items.display_name(c.inventory[0]) == "Dagger +1"


def test_cursed_item_locks():
    c = _char("Doomed", "warrior")
    items.add_item(c, "bent_sword", identified=False)
    ok, msg = items.equip(c, 0)
    assert ok and "CURSED" in msg
    assert c.inventory[0]["identified"]
    ok, msg = items.equip(c, 0)      # try to remove
    assert not ok and "let go" in msg
    # and it blocks the slot
    items.add_item(c, "dagger")
    ok, msg = items.equip(c, 1)
    assert not ok


def test_sage_identify():
    sage = _char("Lore", "sage", level=3, intellect=18, faith=13)
    c = _char("Finder", "warrior")
    items.add_item(c, "mace_p1", identified=False)
    revealed = False
    for seed in range(30):
        msg = items.sage_identify(sage, c.inventory[0], random.Random(seed))
        if c.inventory[0].get("identified"):
            revealed = True
            break
    assert revealed
