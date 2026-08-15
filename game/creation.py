"""Character creation rules. Pure Python — no pygame. RNG is injected."""

from game import data
from game.character import Character, STATS

ROSTER_CAP = 20
BONUS_CAP = 29


def roll_bonus(rng):
    """Classic bonus-point roll: usually 7-10, rare windfalls of +10."""
    bonus = 7 + rng.randrange(0, 4)
    while bonus + 10 <= BONUS_CAP and rng.random() < 0.09:
        bonus += 10
    return bonus


def class_allowed(cls_def, stats, alignment):
    if alignment not in cls_def["alignments"]:
        return False
    return all(stats.get(stat, 0) >= need for stat, need in cls_def["reqs"].items())


def eligible_classes(stats, alignment):
    """Class keys this stat line / alignment qualifies for, in data order."""
    return [
        key for key, cls_def in data.classes().items()
        if class_allowed(cls_def, stats, alignment)
    ]


def vit_hp_mod(vitality):
    if vitality <= 5:
        return -1
    if vitality >= 18:
        return 2
    if vitality >= 15:
        return 1
    return 0


def roll_hp(cls_key, vitality, rng):
    hit_die = data.classes()[cls_key]["hit_die"]
    return max(1, rng.randint(1, hit_die) + vit_hp_mod(vitality))


def roll_gold(rng):
    return 90 + rng.randint(10, 100)


def create_character(name, race_key, alignment, cls_key, stats, rng):
    """Build a level-1 character from a finished creation flow."""
    assert cls_key in eligible_classes(stats, alignment), "class requirements not met"
    hp = roll_hp(cls_key, stats["vitality"], rng)
    return Character(
        name=name,
        race=race_key,
        cls=cls_key,
        alignment=alignment,
        stats={s: stats[s] for s in STATS},
        hp=hp,
        max_hp=hp,
        gold=roll_gold(rng),
    )
