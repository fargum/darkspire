"""Tests for the character creation rules layer."""

import random

import pytest

from game import creation, data
from game.character import Character, STATS, ALIGNMENTS


def test_data_files_load():
    races = data.races()
    classes = data.classes()
    assert len(races) == 5
    assert len(classes) == 8
    for race in races.values():
        assert set(race["stats"].keys()) == set(STATS)
    for cls in classes.values():
        for stat in cls["reqs"]:
            assert stat in STATS
        assert set(cls["alignments"]) <= set(ALIGNMENTS)
        assert cls["hit_die"] in (4, 6, 8, 10)


def test_bonus_roll_bounds():
    for seed in range(500):
        bonus = creation.roll_bonus(random.Random(seed))
        assert 7 <= bonus <= creation.BONUS_CAP


def test_bonus_windfalls_happen_but_rarely():
    rolls = [creation.roll_bonus(random.Random(seed)) for seed in range(2000)]
    big = sum(1 for b in rolls if b >= 17)
    assert 0 < big < len(rolls) // 4


def _stats(**overrides):
    base = {s: 10 for s in STATS}
    base.update(overrides)
    return base


def test_eligibility_basic():
    assert "warrior" in creation.eligible_classes(_stats(might=11), "gray")
    assert "warrior" not in creation.eligible_classes(_stats(might=10), "gray")
    assert "mage" in creation.eligible_classes(_stats(intellect=11), "light")
    assert "priest" in creation.eligible_classes(_stats(faith=11), "shadow")
    assert "rogue" in creation.eligible_classes(_stats(agility=11), "gray")


def test_eligibility_alignment_gates():
    stats = _stats(might=18, agility=18, intellect=18, faith=18, luck=18)
    light = creation.eligible_classes(stats, "light")
    gray = creation.eligible_classes(stats, "gray")
    shadow = creation.eligible_classes(stats, "shadow")
    assert "templar" in light and "templar" not in gray and "templar" not in shadow
    assert "spellblade" not in light and "spellblade" in gray and "spellblade" in shadow
    assert "shadowdancer" not in light and "shadowdancer" not in gray
    assert "shadowdancer" in shadow
    assert "sage" in light and "sage" in gray and "sage" in shadow


def test_shadowdancer_needs_high_rolls():
    assert "shadowdancer" not in creation.eligible_classes(
        _stats(agility=14, luck=14), "shadow"
    )
    assert "shadowdancer" in creation.eligible_classes(
        _stats(agility=15, luck=14), "shadow"
    )


def test_create_character():
    rng = random.Random(42)
    stats = _stats(might=12)
    char = creation.create_character("Borin", "dwarf", "gray", "warrior", stats, rng)
    assert char.level == 1
    assert 1 <= char.hp <= 12
    assert char.hp == char.max_hp
    assert 100 <= char.gold <= 190
    assert char.status == "OK"


def test_create_character_rejects_ineligible():
    rng = random.Random(1)
    with pytest.raises(AssertionError):
        creation.create_character(
            "Weakling", "halfling", "gray", "warrior", _stats(might=5), rng
        )


def test_character_roundtrip():
    rng = random.Random(7)
    char = creation.create_character(
        "Elara", "elf", "light", "mage", _stats(intellect=14), rng
    )
    clone = Character.from_dict(char.to_dict())
    assert clone == char


def test_hp_vitality_modifier():
    assert creation.vit_hp_mod(3) == -1
    assert creation.vit_hp_mod(10) == 0
    assert creation.vit_hp_mod(15) == 1
    assert creation.vit_hp_mod(18) == 2
    rng = random.Random(9)
    for _ in range(200):
        assert creation.roll_hp("mage", 3, rng) >= 1
