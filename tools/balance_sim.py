"""Headless balance simulator.

For each maze depth, builds a benchmark party of the expected level with
tiered gear, fights N random encounters from that depth's table with a
simple policy, and reports win rate, casualties, and average rounds.

Run:  python tools/balance_sim.py [fights-per-depth]
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import combat, creation, items, progression, spells
from game.character import STATS

# Party level and gear tier expected at each depth (lean, Wizardry-ish pacing).
DEPTH_LEVEL = {1: 1, 2: 3, 3: 5, 4: 6, 5: 8, 6: 9, 7: 11, 8: 12, 9: 13, 10: 14}
GEAR = {
    1: ["short_sword", "leather_armor"],
    4: ["long_sword", "chain_mail", "buckler"],
    7: ["long_sword_p1", "chain_p1", "buckler_p1", "helm"],
    13: ["flame_blade", "seraph_mail", "buckler_p1", "helm", "gauntlets"],
}

ATTACK_SPELLS = [  # strongest first
    "tiltowait", "madalto", "lahalito", "dalto", "mahalito", "molito", "halito",
]
HEAL_SPELLS = ["dialma", "dial", "dios"]


def make_party(level, rng):
    party = []
    for name, cls in [("Bash", "warrior"), ("Smash", "warrior"),
                      ("Sneak", "rogue"), ("Vicar", "priest"),
                      ("Wisp", "mage"), ("Lore", "sage")]:
        stats = {s: 12 for s in STATS}
        stats["might" if cls == "warrior" else
              "agility" if cls == "rogue" else
              "faith" if cls == "priest" else "intellect"] = 15
        c = creation.create_character(name, "human", "gray", cls, stats, rng)
        c.level = level
        c.max_hp = c.hp = sum(
            max(1, rng.randint(1, 10 if cls == "warrior" else 6)
                + creation.vit_hp_mod(12))
            for _ in range(level)
        )
        tier = max((t for t in GEAR if t <= level), default=1)
        for key in GEAR[tier]:
            if items.can_use(c, key):
                items.add_item(c, key)
                items.equip(c, len(c.inventory) - 1)
        spells.restore(c)
        party.append(c)
    return party


def pick_spell(char, spell_list):
    for key in spell_list:
        if (key, spells.sdef(key)) in spells.known(char, ("combat", "both")) \
                or key in dict(spells.known(char, ("combat", "both"))):
            if spells.points_left(char, key) > 0:
                return key
    return None


def policy(party, fight):
    actions = {}
    for i, c in enumerate(party):
        if c.status not in combat.ACTIVE:
            continue
        reach = fight.reachable_groups()
        target = fight.groups.index(reach[0]) if reach else 0
        if c.cls in ("mage", "sage"):
            spell = pick_spell(c, ATTACK_SPELLS)
            if spell and not fight.null:
                actions[i] = ("cast", spell, target)
                continue
        if c.cls == "priest":
            hurt = min((c2 for c2 in party if c2.status in combat.ACTIVE),
                       key=lambda c2: c2.hp / c2.max_hp)
            if hurt.hp < hurt.max_hp * 0.5 and not fight.null:
                spell = pick_spell(c, HEAL_SPELLS)
                if spell:
                    actions[i] = ("cast", spell, party.index(hurt))
                    continue
        if i < combat.FRONT_ROWS:
            actions[i] = ("fight", target)
        else:
            actions[i] = ("parry",)
    return actions


DELVE_FIGHTS = 8   # encounters per expedition, no inn in between


def _between_fights(party):
    """Priest patches the party up between fights, while points last."""
    priest = next((c for c in party
                   if c.cls == "priest" and c.status in combat.ACTIVE), None)
    if not priest:
        return
    for _ in range(20):
        hurt = min((c for c in party if c.status in combat.ACTIVE),
                   key=lambda c: c.hp / c.max_hp, default=None)
        if hurt is None or hurt.hp >= hurt.max_hp * 0.75:
            return
        spell = pick_spell(priest, HEAL_SPELLS)
        if spell is None:
            return
        spells.spend(priest, spell)
        import game.dice as dice_mod
        hurt.hp = min(hurt.max_hp,
                      hurt.hp + dice_mod.roll(random.Random(hurt.hp), "2d8"))


def simulate(depth, delves, seed_base=0):
    survived = deaths_total = fights_cleared = 0
    for trial in range(delves):
        rng = random.Random(seed_base * 100003 + trial)
        party = make_party(DEPTH_LEVEL[depth], rng)
        for encounter in range(DELVE_FIGHTS):
            groups = combat.build_encounter(depth, rng)
            fight = combat.Combat(party, groups, rng)
            rounds = 0
            while fight.result is None and rounds < 50:
                rounds += 1
                fight.resolve(policy(party, fight))
            if fight.result != "victory":
                break
            fights_cleared += 1
            _between_fights(party)
        else:
            survived += 1
        deaths_total += sum(1 for c in party if c.status in ("DEAD", "ASHES"))
    return (survived / delves, deaths_total / delves,
            fights_cleared / delves)


def main():
    delves = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    print(f"{'depth':>5} {'lvl':>4} {'delve-ok%':>9} {'deaths':>7} "
          f"{'fights won':>11}  (delve = {DELVE_FIGHTS} fights, no rest)")
    for depth in range(1, 11):
        ok, deaths, cleared = simulate(depth, delves, seed_base=depth)
        flag = ""
        if ok < 0.5:
            flag = "  << HARD"
        elif ok > 0.95 and deaths < 0.2:
            flag = "  << EASY"
        print(f"{depth:>5} {DEPTH_LEVEL[depth]:>4} {ok * 100:>8.0f}% "
              f"{deaths:>7.2f} {cleared:>11.1f}{flag}")


if __name__ == "__main__":
    main()
