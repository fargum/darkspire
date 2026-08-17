"""Experience tables and leveling. Pure Python — no pygame. RNG is injected."""

from game import data
from game.character import STATS
from game.creation import vit_hp_mod

STAT_FLOOR = 3
STAT_LIFETIME_CAP = 20


def xp_for_level(cls_key, level):
    """Cumulative XP required to BE the given level."""
    if level <= 0:
        return 0
    base = 1000 * data.classes()[cls_key]["xp_mult"]
    return int(base * (1.72 ** (level - 2)))


def can_level(char):
    return char.xp >= xp_for_level(char.cls, char.level + 1)


def level_up(char, rng):
    """Advance one level. Returns {'hp': gain, 'stats': {stat: +/-1}}."""
    hit_die = data.classes()[char.cls]["hit_die"]
    changes = {}
    for stat in STATS:
        roll = rng.random()
        if roll < 0.22 and char.stats[stat] < STAT_LIFETIME_CAP:
            char.stats[stat] += 1
            changes[stat] = 1
        elif roll > 0.95 and char.stats[stat] > STAT_FLOOR:
            char.stats[stat] -= 1
            changes[stat] = -1
    gain = max(1, rng.randint(1, hit_die) + vit_hp_mod(char.stats["vitality"]))
    char.level += 1
    char.max_hp += gain
    return {"hp": gain, "stats": changes}
