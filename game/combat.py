"""Turn-based combat engine. Pure Python — no pygame. RNG is injected.

Log lines are (kind, text) tuples; kinds: info, good, bad, dim.

Actions (declared per living party member, keyed by party index):
    ("fight", group_index) ("parry",) ("hide",) ("use", item_index)
    ("cast", spell_key, target) ("run",)
"""

from collections import Counter

from game import data, dice, items

FRONT_ROWS = 3      # first three party slots can melee and be meleed
MELEE_REACH = 2     # party can strike the first two living monster groups
WARRIORLIKE = {"warrior", "templar", "spellblade"}
STEALTHY = {"rogue", "shadowdancer"}
ACTIVE = ("OK", "POISONED")                       # can act
BODIES = ("OK", "POISONED", "ASLEEP", "PARALYZED")  # not dead: targetable

# What monster casters can throw at the party.
MONSTER_SPELLS = {
    "halito": ("one", "1d8"),
    "badios": ("one", "1d8"),
    "molito": ("party", "3d6"),
    "mahalito": ("party", "4d6"),
    "katino": ("sleep", None),
    "manifo": ("hold", None),
}


def mdef(key):
    return data.load("monsters")[key]


def build_encounter(depth, rng):
    """Roll a random encounter for a maze depth. Returns group list."""
    table = data.load("encounters")[str(depth)]
    total = sum(e["weight"] for e in table)
    pick = rng.randint(1, total)
    for entry in table:
        pick -= entry["weight"]
        if pick <= 0:
            break
    groups = []
    for key, count_dice in entry["groups"]:
        count = dice.roll(rng, count_dice)
        members = [{"hp": dice.roll(rng, mdef(key)["hp"])} for _ in range(count)]
        groups.append({"key": key, "members": members})
    return groups


class Combat:
    def __init__(self, party, groups, rng):
        self.party = party
        self.groups = groups
        self.rng = rng
        self.round_num = 0
        self.parrying = set()          # id(char)
        self.hidden = set()            # id(char)
        self.ac_bonus = {}             # id(char) -> spell AC bonus (this combat)
        self.party_ac_bonus = 0        # party-wide spell AC bonus
        self.identified = False
        self.result = None             # None | victory | defeat | fled
        self.null = False              # anti-magic zone: nobody casts
        self.kills = Counter()
        for group in groups:
            for m in group["members"]:
                m.setdefault("status", "OK")
        roll = rng.random()
        self.surprise = "monsters" if roll < 0.15 else (
            "party" if roll > 0.92 else None
        )

    # ---- queries ---------------------------------------------------------
    def living(self):
        return [c for c in self.party if c.status in ACTIVE]

    def bodies(self):
        return [c for c in self.party if c.status in BODIES]

    def _sink_incapacitated(self):
        """Push anyone who can't act to the back so the living can front-line."""
        self.party.sort(key=lambda c: c.status not in ACTIVE)

    def alive_groups(self):
        return [g for g in self.groups if g["members"]]

    def reachable_groups(self):
        return self.alive_groups()[:MELEE_REACH]

    def group_label(self, group):
        d = mdef(group["key"])
        n = len(group["members"])
        if self.identified:
            return f"{n} {d['name'] if n == 1 else d['plural']}"
        return f"{n} {d['unknown']}"

    def monster_name(self, group):
        return mdef(group["key"])["name"] if self.identified \
            else "creature"

    def mdef_of(self, group):
        return mdef(group["key"])

    def kill_monster(self, group, monster, lines, quiet=False):
        if monster in group["members"]:
            group["members"].remove(monster)
            self.kills[group["key"]] += 1
            if not quiet:
                lines.append(("good", f"The {self.monster_name(group)} is destroyed!"))

    # ---- character math --------------------------------------------------
    def _weapon_dice(self, char):
        for entry in char.inventory:
            if entry.get("equipped") and items.item(entry["key"])["slot"] == "weapon":
                return items.item(entry["key"])["damage"]
        return "1d2"

    def _attack_bonus(self, char):
        base = char.level if char.cls in WARRIORLIKE else char.level // 2
        return base + (char.stats["might"] - 10) // 3

    def _swings(self, char):
        return 1 + (char.level // 4 if char.cls in WARRIORLIKE else 0)

    # ---- round resolution ------------------------------------------------
    def resolve(self, actions):
        lines = []
        self.round_num += 1
        rng = self.rng

        if self.surprise == "party" and self.round_num == 1:
            lines.append(("bad", "You are taken by surprise!"))
            actions = {}

        if any(a[0] == "run" for a in actions.values()):
            agi = [c.stats["agility"] for c in self.living()]
            chance = max(0.25, min(0.95, 0.55 + (sum(agi) / len(agi) - 10) * 0.03))
            if rng.random() < chance:
                self.result = "fled"
                lines.append(("good", "The party flees into the dark!"))
                return lines
            lines.append(("bad", "No escape — they cut off your retreat!"))
            actions = {}

        # Instant actions: parry and hide take effect before blows land.
        for i, action in actions.items():
            char = self.party[i]
            if char.status not in ACTIVE:
                continue
            if action[0] == "parry":
                self.parrying.add(id(char))
                lines.append(("dim", f"{char.name} parries."))
            elif action[0] == "hide":
                if rng.randint(1, 100) <= 35 + 3 * char.stats["agility"]:
                    self.hidden.add(id(char))
                    lines.append(("good", f"{char.name} melts into the shadows."))
                else:
                    lines.append(("dim", f"{char.name} finds no cover."))

        # Initiative queue: fighting/item-using characters and monsters.
        queue = []
        for i, action in actions.items():
            char = self.party[i]
            if char.status in ACTIVE and action[0] in ("fight", "use", "cast"):
                init = rng.randint(1, 8) + char.stats["agility"]
                if action[0] == "cast":
                    init += 4   # words are quicker than blades
                queue.append((init, "char", (char, action)))
        monsters_act = not (self.surprise == "monsters" and self.round_num == 1)
        if not monsters_act:
            lines.append(("good", "You catch them unawares!"))
        else:
            for group in self.reachable_groups():
                d = mdef(group["key"])
                for monster in list(group["members"]):
                    init = rng.randint(1, 8) + 8 + d["level"]
                    queue.append((init, "monster", (group, monster)))
        queue.sort(key=lambda entry: -entry[0])

        for _, kind, payload in queue:
            if self.result:
                break
            if kind == "char":
                char, action = payload
                if char.status not in ACTIVE:
                    continue  # cut down before acting
                if action[0] == "fight":
                    self._char_fight(char, action[1], lines)
                elif action[0] == "use":
                    lines.append(("dim", items.use_item(
                        char, action[1], self.party, self.rng)))
                elif action[0] == "cast":
                    from game import spells
                    lines.extend(spells.cast_combat(
                        char, action[1], action[2], self, self.rng))
            else:
                group, monster = payload
                if (monster in group["members"] and monster["hp"] > 0
                        and monster.get("status", "OK") == "OK"):
                    self._monster_act(group, monster, lines)

        # Sleepers may wake at the end of the round — both sides.
        for group in self.alive_groups():
            for monster in group["members"]:
                if monster.get("status") == "ASLEEP" and rng.random() < 0.5:
                    monster["status"] = "OK"
        for c in self.party:
            if c.status == "ASLEEP" and rng.random() < 0.4:
                c.status = "OK"
                lines.append(("good", f"{c.name} shakes off the sleep."))

        self.parrying.clear()
        self.identified = True
        if not self.alive_groups():
            self.result = "victory"
        elif not self.bodies():
            self.result = "defeat"
            lines.append(("bad", "The last of the party falls..."))
        if self.result:   # nobody sleeps through the end of a battle
            for c in self.party:
                if c.status == "ASLEEP":
                    c.status = "OK"
        self._sink_incapacitated()
        return lines

    def _char_fight(self, char, group_index, lines):
        rng = self.rng
        reach = self.reachable_groups()
        if not reach:
            return
        group = next(
            (g for g in reach if self.groups.index(g) == group_index), reach[0]
        )
        d = mdef(group["key"])
        from_hiding = id(char) in self.hidden
        self.hidden.discard(id(char))
        for _ in range(self._swings(char)):
            if not group["members"]:
                break
            monster = group["members"][0]
            helpless = monster.get("status", "OK") != "OK"
            ac = d["ac"] + group.get("ac_pen", 0)
            if not helpless and \
                    rng.randint(1, 20) + self._attack_bonus(char) < 20 - ac:
                lines.append(("dim", f"{char.name} misses the {d['name']}."))
                continue
            if (from_hiding and char.cls == "shadowdancer"
                    and rng.randint(1, 100) <= min(50, 15 + 3 * char.level)):
                monster["hp"] = 0
                lines.append(("good",
                              f"{char.name} strikes from the dark — a killing blow!"))
            else:
                dmg = dice.roll(rng, self._weapon_dice(char))
                dmg += max(0, (char.stats["might"] - 10) // 3)
                if from_hiding:
                    dmg *= 2
                    lines.append(("good", f"{char.name} backstabs for {dmg}!"))
                elif helpless:
                    dmg *= 2
                    lines.append(("good",
                                  f"{char.name} strikes the helpless {d['name']} for {dmg}!"))
                else:
                    lines.append(("info", f"{char.name} hits the {d['name']} for {dmg}."))
                monster["hp"] -= dmg
            from_hiding = False
            if monster["hp"] <= 0:
                self.kill_monster(group, monster, lines)

    def _monster_act(self, group, monster, lines):
        rng = self.rng
        d = mdef(group["key"])
        caster = d.get("caster")
        if (caster and not group.get("silenced") and not self.null
                and rng.random() < caster["chance"]):
            self._monster_cast(group, rng.choice(caster["spells"]), lines)
            return
        breath = d.get("breath")
        if breath and rng.random() < breath["chance"]:
            lines.append(("bad", f"The {d['name']} breathes fire!"))
            for char in list(self.bodies()):
                self._hurt(char, dice.roll(rng, breath["dice"]), lines)
            return
        self._monster_attack(group, monster, lines)

    def _monster_cast(self, group, spell, lines):
        rng = self.rng
        d = mdef(group["key"])
        kind, dmg_dice = MONSTER_SPELLS[spell]
        lines.append(("bad", f"The {self.monster_name(group)} casts {spell.upper()}!"))
        targets = [c for c in self.bodies() if id(c) not in self.hidden]
        if not targets:
            return
        if kind == "one":
            self._hurt(rng.choice(targets), dice.roll(rng, dmg_dice), lines)
        elif kind == "party":
            for char in list(targets):
                self._hurt(char, dice.roll(rng, dmg_dice), lines)
        elif kind == "sleep":
            for char in targets:
                if char.status == "OK" and rng.random() < 0.35:
                    char.status = "ASLEEP"
                    lines.append(("bad", f"{char.name} slumps asleep!"))
        elif kind == "hold":
            front = [c for c in targets if c in self.party[:FRONT_ROWS]]
            for char in front or targets:
                if char.status in ("OK", "POISONED") and rng.random() < 0.4:
                    char.status = "PARALYZED"
                    lines.append(("bad", f"{char.name} is frozen in place!"))

    def _hurt(self, char, dmg, lines):
        char.hp -= dmg
        lines.append(("bad", f"{char.name} takes {dmg}."))
        if char.hp <= 0:
            char.hp = 0
            char.status = "DEAD"
            lines.append(("bad", f"{char.name} is slain!"))

    def _monster_attack(self, group, monster, lines):
        rng = self.rng
        d = mdef(group["key"])
        for attack in d["attacks"]:
            front = [c for c in self.party[:FRONT_ROWS]
                     if c.status in BODIES and id(c) not in self.hidden]
            targets = front or [c for c in self.bodies()
                                if id(c) not in self.hidden]
            if not targets:
                lines.append(("dim", f"The {d['name']} snuffles about, finding no one."))
                return
            char = rng.choice(targets)
            helpless = char.status in ("ASLEEP", "PARALYZED")
            ac = char.ac - (2 if id(char) in self.parrying else 0) \
                - self.ac_bonus.get(id(char), 0) - self.party_ac_bonus
            if not helpless and rng.randint(1, 20) + d["level"] < 20 - ac:
                lines.append(("dim", f"The {d['name']} misses {char.name}."))
                continue
            dmg = dice.roll(rng, attack)
            if helpless:
                dmg *= 2
            char.hp -= dmg
            lines.append(("bad", f"The {d['name']} hits {char.name} for {dmg}."))
            if char.status == "ASLEEP":
                char.status = "OK"      # rude awakening
            poison = d.get("special", {}).get("poison", 0)
            if char.status == "OK" and poison and rng.random() < poison:
                char.status = "POISONED"
                lines.append(("bad", f"{char.name} is poisoned!"))
            drain = d.get("drain", 0)
            if (char.status in ("OK", "POISONED") and drain
                    and char.level > 1 and rng.random() < drain):
                char.level -= 1
                char.drained += 1
                from game import spells
                spells.ensure(char)
                lines.append(("bad",
                              f"{char.name} feels life itself drawn away!"))
            sp_drain = d.get("sp_drain", 0)
            if (char.status in ("OK", "POISONED") and sp_drain
                    and rng.random() < sp_drain):
                from game import spells
                spells.ensure(char)
                for school in ("mage", "priest"):
                    pools = char.sp[school]
                    hit_pool = next(
                        (i for i in range(6, -1, -1) if pools[i] > 0), None)
                    if hit_pool is not None:
                        pools[hit_pool] -= 1
                        lines.append(("bad",
                                      f"A spell is devoured from {char.name}'s mind!"))
                        break
            if char.hp <= 0:
                char.hp = 0
                char.status = "DEAD"
                lines.append(("bad", f"{char.name} is slain!"))

    # ---- rewards ---------------------------------------------------------
    def distribute_rewards(self):
        """Apply XP/gold to survivors. Returns summary lines."""
        xp_total = sum(mdef(k)["xp"] * n for k, n in self.kills.items())
        gold_total = sum(
            dice.roll(self.rng, mdef(k)["gold"])
            for k, n in self.kills.items() for _ in range(n)
        )
        alive = self.living()
        lines = [("good", "The foes lie still.")]
        if alive:
            xp_share = xp_total // len(alive)
            gold_share = gold_total // len(alive)
            for c in alive:
                c.xp += xp_share
                c.gold += gold_share
            lines.append(("info", f"Each survivor gains {xp_share} XP."))
            lines.append(("info", f"Each survivor pockets {gold_share} gold."))
        return lines
