"""Spell system: points, learning, and casting. Pure Python — no pygame.

Spell points are per-school, per-spell-level pools (index 0 = level 1).
A character knows every spell of a level they have points for.
"""

from game import data, dice, maze, progression

SCHOOLS = ("mage", "priest")

# First character level at which each spell level unlocks, per class.
ACCESS = {
    "mage": {"mage": [1, 3, 5, 7, 9, 11, 13]},
    "priest": {"priest": [1, 3, 5, 7, 9, 11, 13]},
    "spellblade": {"mage": [4, 8, 12, 16]},
    "templar": {"priest": [4, 8, 12, 16]},
    "sage": {
        "mage": [3, 5, 7, 9, 11, 13, 15],
        "priest": [3, 5, 7, 9, 11, 13, 15],
    },
}


def sdef(key):
    return data.load("spells")[key]


def max_points(char):
    out = {"mage": [0] * 7, "priest": [0] * 7}
    for school, reqs in ACCESS.get(char.cls, {}).items():
        for i, req in enumerate(reqs):
            if char.level >= req:
                out[school][i] = min(9, char.level - req + 1)
    return out


def ensure(char):
    """Initialize/clamp char.sp against the maximum. Returns the maximum."""
    mx = max_points(char)
    if not char.sp:
        char.sp = {s: mx[s][:] for s in SCHOOLS}
    else:
        for school in SCHOOLS:
            cur = list(char.sp.get(school, []))[:7]
            cur += [0] * (7 - len(cur))
            char.sp[school] = [min(c, m) for c, m in zip(cur, mx[school])]
    return mx


def restore(char):
    mx = max_points(char)
    char.sp = {s: mx[s][:] for s in SCHOOLS}


def is_caster(char):
    mx = max_points(char)
    return any(any(v) for v in mx.values())


def known(char, contexts):
    """[(key, def)] of spells castable by class/level in the given contexts."""
    ensure(char)
    mx = max_points(char)
    out = []
    for key, d in data.load("spells").items():
        if d["context"] in contexts and mx[d["school"]][d["level"] - 1] > 0:
            out.append((key, d))
    return out


def points_left(char, key):
    ensure(char)
    d = sdef(key)
    return char.sp[d["school"]][d["level"] - 1]


def spend(char, key):
    d = sdef(key)
    char.sp[d["school"]][d["level"] - 1] -= 1


# ---- combat casting ------------------------------------------------------

def cast_combat(char, key, target, fight, rng):
    """Resolve a combat spell. `target` is a group index or ally index."""
    spend(char, key)
    d = sdef(key)
    eff = d["effect"]
    kind = eff["type"]
    lines = [("info", f"{char.name} casts {d['name']}!")]

    def group():
        reach = [g for g in fight.groups if g["members"]]
        for g in reach:
            if fight.groups.index(g) == target:
                return g
        return reach[0] if reach else None

    if kind == "damage_one":
        g = group()
        if g:
            m = g["members"][0]
            dmg = dice.roll(rng, eff["dice"])
            m["hp"] -= dmg
            name = fight.monster_name(g)
            lines.append(("info", f"The {name} takes {dmg}."))
            if m["hp"] <= 0:
                fight.kill_monster(g, m, lines)
    elif kind in ("damage_group", "damage_all"):
        targets = [group()] if kind == "damage_group" else list(fight.alive_groups())
        for g in [t for t in targets if t]:
            name = fight.monster_name(g)
            total = 0
            for m in list(g["members"]):
                dmg = dice.roll(rng, eff["dice"])
                m["hp"] -= dmg
                total += dmg
                if m["hp"] <= 0:
                    fight.kill_monster(g, m, lines, quiet=True)
            slain = sum(1 for _ in ())
            lines.append(("info", f"The {name} group is scoured for {total}."))
            if not g["members"]:
                lines.append(("good", f"The {name}s are wiped out!"))
    elif kind == "sleep_group":
        g = group()
        if g:
            put = 0
            for m in g["members"]:
                if rng.random() < eff["chance"]:
                    m["status"] = "ASLEEP"
                    put += 1
            lines.append(("good", f"{put} of them slump asleep.") if put
                         else ("dim", "None succumb."))
    elif kind == "hold_group":
        g = group()
        if g:
            held = 0
            for m in g["members"]:
                if rng.random() < eff["chance"]:
                    m["status"] = "PARALYZED"
                    held += 1
            lines.append(("good", f"{held} of them freeze in place.") if held
                         else ("dim", "None are held."))
    elif kind == "silence_group":
        g = group()
        if g:
            g["silenced"] = True
            lines.append(("good", "Their voices die away."))
    elif kind in ("fear", "fear_all"):
        targets = list(fight.alive_groups()) if kind == "fear_all" else [group()]
        for g in [t for t in targets if t]:
            g["ac_pen"] = max(g.get("ac_pen", 0), eff["ac_pen"])
        lines.append(("good", "Dread takes hold of your foes."))
    elif kind == "kill_threshold":
        slain = 0
        for g in fight.alive_groups():
            for m in list(g["members"]):
                if m["hp"] <= eff["hp"]:
                    fight.kill_monster(g, m, lines, quiet=True)
                    slain += 1
        lines.append(("good", f"The air is torn away — {slain} foes fall dead."))
    elif kind == "kill_group":
        g = group()
        if g:
            slain = 0
            for m in list(g["members"]):
                if rng.random() < eff["chance"]:
                    fight.kill_monster(g, m, lines, quiet=True)
                    slain += 1
            lines.append(("good", f"{slain} of them suffocate."))
    elif kind == "kill_one":
        g = group()
        if g:
            m = g["members"][0]
            if rng.random() < eff["chance"]:
                fight.kill_monster(g, m, lines)
            else:
                lines.append(("dim", "Its heart holds fast."))
    elif kind == "zilwan":
        g = group()
        if g:
            if fight.mdef_of(g).get("undead"):
                fight.kill_monster(g, g["members"][0], lines)
                lines.append(("good", "Sunfire unmakes the dead thing!"))
            else:
                lines.append(("dim", "The lance of light passes through harmlessly."))
    elif kind == "mabadi":
        g = group()
        if g:
            m = g["members"][0]
            left = rng.randint(1, 8)
            if m["hp"] > left:
                m["hp"] = left
                lines.append(("good", "Nearly all its life is ripped away!"))
            else:
                lines.append(("dim", "It clings to what little life it has."))
    elif kind == "ac_self":
        fight.ac_bonus[id(char)] = fight.ac_bonus.get(id(char), 0) + eff["amount"]
        lines.append(("good", f"{char.name} is warded."))
    elif kind == "ac_party":
        fight.party_ac_bonus += eff["amount"]
        lines.append(("good", "The whole party is warded."))
    elif kind == "heal":
        ally = fight.party[target]
        healed = min(dice.roll(rng, eff["dice"]), ally.max_hp - ally.hp)
        ally.hp += healed
        lines.append(("good", f"{ally.name} recovers {healed} HP."))
    elif kind == "heal_full":
        ally = fight.party[target]
        ally.hp = ally.max_hp
        if ally.status in ("POISONED", "PARALYZED"):
            ally.status = "OK"
        lines.append(("good", f"{ally.name} is wholly restored!"))
    elif kind == "cure_poison":
        ally = fight.party[target]
        if ally.status == "POISONED":
            ally.status = "OK"
            lines.append(("good", f"The venom leaves {ally.name}."))
        else:
            lines.append(("dim", "There is no poison to cure."))
    elif kind == "cure_paralysis":
        ally = fight.party[target]
        if ally.status == "PARALYZED":
            ally.status = "OK"
            lines.append(("good", f"{ally.name} can move again."))
        else:
            lines.append(("dim", "Nothing binds them."))
    elif kind == "identify_monsters":
        fight.identified = True
        lines.append(("good", "The foes' true names are revealed."))
    elif kind in ("haman", "mahaman"):
        lines += _wish(char, fight, rng, greater=kind == "mahaman")
    else:
        lines.append(("dim", "Nothing happens."))
    return lines


def _wish(char, fight, rng, greater):
    lines = []
    roll = rng.random()
    if roll < 0.35:
        for c in fight.party:
            if c.status in ("OK", "POISONED"):
                c.hp = c.max_hp if greater else min(c.max_hp, c.hp + c.max_hp // 2)
        lines.append(("good", "Vitality floods the party!"))
    elif roll < 0.7:
        for g in fight.alive_groups():
            for m in g["members"]:
                if rng.random() < (0.9 if greater else 0.6):
                    m["status"] = "ASLEEP"
        lines.append(("good", "Your foes drop where they stand!"))
    else:
        dmg_dice = "10d10" if greater else "6d8"
        for g in list(fight.alive_groups()):
            for m in list(g["members"]):
                m["hp"] -= dice.roll(rng, dmg_dice)
                if m["hp"] <= 0:
                    fight.kill_monster(g, m, lines, quiet=True)
        lines.append(("good", "Fate lashes out at every foe!"))
    if greater or rng.random() < 0.25:
        char.level = max(1, char.level - 1)
        char.xp = progression.xp_for_level(char.cls, char.level)
        ensure(char)
        lines.append(("bad", f"The bargain takes its price — {char.name} is diminished."))
    return lines


# ---- camp casting --------------------------------------------------------

def cast_camp(char, key, target_char, gs, rng):
    """Resolve a camp spell. Returns (lines, signal); signal None|'castle'."""
    spend(char, key)
    d = sdef(key)
    eff = d["effect"]
    kind = eff["type"]
    lines = [("info", f"{char.name} casts {d['name']}.")]
    signal = None

    if kind == "heal":
        healed = min(dice.roll(rng, eff["dice"]),
                     target_char.max_hp - target_char.hp)
        target_char.hp += healed
        lines.append(("good", f"{target_char.name} recovers {healed} HP."))
    elif kind == "heal_full":
        target_char.hp = target_char.max_hp
        if target_char.status in ("POISONED", "PARALYZED"):
            target_char.status = "OK"
        lines.append(("good", f"{target_char.name} is wholly restored!"))
    elif kind == "cure_poison":
        if target_char.status == "POISONED":
            target_char.status = "OK"
            lines.append(("good", f"The venom leaves {target_char.name}."))
        else:
            lines.append(("dim", "There is no poison to cure."))
    elif kind == "cure_paralysis":
        if target_char.status == "PARALYZED":
            target_char.status = "OK"
            lines.append(("good", f"{target_char.name} can move again."))
        else:
            lines.append(("dim", "Nothing binds them."))
    elif kind == "res_dead":
        if target_char.status == "DEAD":
            chance = min(90, 40 + 3 * target_char.stats["vitality"])
            if rng.randint(1, 100) <= chance:
                target_char.status = "OK"
                target_char.hp = 1
                lines.append(("good", f"{target_char.name} draws breath once more!"))
            else:
                target_char.status = "ASHES"
                lines.append(("bad", f"The rite fails — {target_char.name} crumbles to ashes!"))
        else:
            lines.append(("dim", "They are not dead."))
    elif kind == "res_ashes":
        if target_char.status == "ASHES":
            chance = min(85, 30 + 3 * target_char.stats["vitality"])
            if rng.randint(1, 100) <= chance:
                target_char.status = "OK"
                target_char.hp = target_char.max_hp
                lines.append(("good", f"{target_char.name} rises, whole again!"))
            else:
                lines.append(("bad", "The ashes stir, but do not rise."))
        else:
            lines.append(("dim", "There are no ashes to raise."))
    elif kind == "light":
        if gs.maze:
            gs.maze["light"] = eff["steps"]
            lines.append(("good", "Radiance blooms around the party."))
    elif kind == "dumapic":
        if gs.maze:
            level = maze.load_level(gs.maze["depth"])
            east = gs.maze["x"]
            north = level.height - 1 - gs.maze["y"]
            facing = maze.DIR_NAMES[gs.maze["facing"]]
            lines.append(("good",
                          f"Depth {gs.maze['depth']}: {east} east, {north} north, facing {facing}."))
    elif kind == "ac_party_expedition":
        if gs.maze:
            gs.maze["maporfic"] = eff["amount"]
            lines.append(("good", "An enduring ward settles over the party."))
    elif kind == "loktofeit":
        for c in gs.party:
            c.gold = 0
        gs.maze = None
        lines.append(("bad", "The Dawnmother takes her tithe — every coin."))
        lines.append(("good", "The party awakens at the castle gates."))
        signal = "castle"
    elif kind == "kandi":
        lines.append(("dim", "You sense no lost souls nearby."))
    else:
        lines.append(("dim", "Nothing happens."))
    return lines, signal


def malor_jump(gs, x, y, rng):
    """Camp MALOR to (x, y) on the current level. Returns lines."""
    level = maze.load_level(gs.maze["depth"])
    if 0 <= x < level.width and 0 <= y < level.height:
        gs.maze["x"], gs.maze["y"] = x, y
        return [("good", "The world folds, and you are elsewhere.")]
    # Softened rock-teleport: dumped at the entrance, badly hurt.
    gs.maze["x"], gs.maze["y"] = level.start["x"], level.start["y"]
    lines = [("bad", "STONE! The spell recoils and hurls you back to the entrance!")]
    for c in gs.party:
        if c.status in ("OK", "POISONED"):
            c.hp = max(1, c.hp - max(1, c.hp // 2))
    lines.append(("bad", "The party is battered and shaken."))
    return lines
