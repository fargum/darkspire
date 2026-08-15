"""Treasure chests and their traps. Pure Python — no pygame. RNG injected."""

from game import data, dice, items, spells

TRAPS = [
    "Needle", "Gas Bloom", "Screamer", "Mind Jar",
    "Rust Mist", "Null Spark", "Trapdoor", "Glyph of Ash",
]
STEALTHY = {"rogue", "shadowdancer"}
ACTIVE = ("OK", "POISONED")


def loot_table(depth):
    return data.load("loot")[str(depth)]


def maybe_chest(depth, rng):
    """Roll for a chest after a victory. Returns a chest dict or None."""
    table = loot_table(depth)
    if rng.random() >= table["chest_chance"]:
        return None
    trap = rng.choice(TRAPS) if rng.random() < table["trap_chance"] else None
    gold = dice.roll(rng, table["gold"])
    total = sum(w for _, w in table["items"])
    pick = rng.randint(1, total)
    item_key = None
    for key, weight in table["items"]:
        pick -= weight
        if pick <= 0:
            item_key = key
            break
    return {"trap": trap, "gold": gold, "item": item_key, "open": False}


def inspect(char, chest, rng):
    """Study the chest for traps. Returns a message (possibly wrong!)."""
    skill = 40 + 2 * char.stats["agility"] + 3 * char.level
    if char.cls in STEALTHY:
        skill += 30
    truthful = rng.randint(1, 100) <= min(95, skill)
    if truthful:
        return f"It looks to be... {chest['trap']}." if chest["trap"] \
            else "It looks clean."
    wrong = [t for t in TRAPS if t != chest["trap"]]
    return f"It looks to be... {rng.choice(wrong)}."


def calfo(char, chest, rng):
    spells.spend(char, "calfo")
    if rng.randint(1, 100) <= 95:
        return f"The Dawnmother whispers: {chest['trap']}." if chest["trap"] \
            else "The Dawnmother whispers: it is clean."
    return "The vision is clouded."


def disarm(char, chest, guess, rng):
    """Try to disarm by naming the trap. Returns 'safe'|'disarmed'|'triggered'."""
    if chest["trap"] is None:
        return "safe"
    if guess != chest["trap"]:
        return "triggered"
    skill = 40 + 2 * char.stats["agility"] + 4 * char.level
    if char.cls in STEALTHY:
        skill += 25
    if rng.randint(1, 100) <= min(95, skill):
        chest["trap"] = None
        return "disarmed"
    return "triggered"


def trigger(chest, party, opener, rng):
    """Spring the trap. Returns (lines, summon: bool). Mutates characters."""
    trap = chest["trap"]
    chest["trap"] = None    # a sprung trap is spent
    lines = [("bad", f"{trap}!")]
    live = [c for c in party if c.status in ACTIVE]
    summon = False
    if trap == "Needle":
        opener.hp -= dice.roll(rng, "1d5")
        lines.append(("bad", f"A needle pierces {opener.name}'s hand."))
        if opener.status == "OK" and rng.random() < 0.25:
            opener.status = "POISONED"
            lines.append(("bad", f"{opener.name} is poisoned!"))
    elif trap == "Gas Bloom":
        for c in live:
            if c.status == "OK" and rng.random() < 0.3:
                c.status = "POISONED"
                lines.append(("bad", f"{c.name} breathes the spores — poisoned!"))
    elif trap == "Screamer":
        lines.append(("bad", "A shriek echoes down every corridor!"))
        summon = True
    elif trap == "Mind Jar":
        opener.status = "PARALYZED"
        lines.append(("bad", f"{opener.name}'s mind is caught — paralyzed!"))
    elif trap == "Rust Mist":
        armor = [e for e in opener.inventory
                 if e.get("equipped")
                 and items.item(e["key"])["slot"] == "armor"
                 and not items.item(e["key"]).get("cursed")]
        if armor:
            entry = armor[0]
            name = items.item(entry["key"])["name"]
            opener.inventory.remove(entry)
            items.recalc_ac(opener)
            lines.append(("bad", f"{opener.name}'s {name} crumbles to red dust!"))
        else:
            opener.hp -= dice.roll(rng, "1d6")
            lines.append(("bad", f"The mist sears {opener.name}'s skin."))
    elif trap == "Null Spark":
        spells.ensure(opener)
        opener.sp = {"mage": [0] * 7, "priest": [0] * 7}
        lines.append(("bad", f"Every spell is torn from {opener.name}'s mind!"))
    elif trap == "Trapdoor":
        for c in live:
            c.hp -= dice.roll(rng, "2d6")
            c.hp = max(c.hp, 0)
        lines.append(("bad", "The floor gives way! The party crashes down hard."))
    elif trap == "Glyph of Ash":
        for c in live:
            c.hp -= dice.roll(rng, "2d6")
        lines.append(("bad", "Fire washes over the party!"))
    for c in party:
        if c.status in ACTIVE and c.hp <= 0:
            c.hp = 0
            c.status = "DEAD"
            lines.append(("bad", f"{c.name} is slain!"))
    return lines, summon


def open_chest(chest, party, rng):
    """Distribute the contents. Returns lines. Chest must be trap-free."""
    chest["open"] = True
    lines = []
    live = [c for c in party if c.status in ACTIVE]
    if live:
        share = chest["gold"] // len(live)
        for c in live:
            c.gold += share
        lines.append(("good", f"{chest['gold']} gold — {share} each."))
    if chest["item"]:
        it = data.load("items")[chest["item"]]
        magical = "unid_name" in it
        holder = next(
            (c for c in live if len(c.inventory) < items.INVENTORY_CAP), None
        )
        if holder:
            items.add_item(holder, chest["item"], identified=not magical)
            entry = holder.inventory[-1]
            lines.append(("good",
                          f"{holder.name} takes {items.display_name(entry)}."))
        else:
            lines.append(("dim", "Something else glints inside, but every pack is full."))
    return lines
