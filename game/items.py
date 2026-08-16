"""Item rules: usability, equipping, AC recalculation. Pure Python — no pygame.

Inventory entries are dicts: {"key": item_key, "equipped": bool}.
"""

from game import data

INVENTORY_CAP = 8
EQUIP_SLOTS = ("weapon", "armor", "shield", "helm", "gloves")


def item(key):
    return data.load("items")[key]


def can_use(char, key):
    classes = item(key)["classes"]
    return classes == "all" or char.cls in classes


def is_equippable(key):
    return item(key)["slot"] in EQUIP_SLOTS


def display_name(entry):
    it = item(entry["key"])
    if not entry.get("identified", True):
        return it.get("unid_name", "? Something")
    return it["name"]


def is_cursed_stuck(entry):
    return entry.get("equipped") and item(entry["key"]).get("cursed")


def recalc_ac(char):
    bonus = sum(
        item(entry["key"])["ac"]
        for entry in char.inventory
        if entry.get("equipped")
    )
    char.ac = 10 - bonus


def equip(char, index):
    """Toggle equip on inventory[index]. Returns (ok, message)."""
    entry = char.inventory[index]
    it = item(entry["key"])
    if entry.get("equipped"):
        if it.get("cursed"):
            return False, f"The {it['name']} will not let go!"
        entry["equipped"] = False
        recalc_ac(char)
        return True, f"{it['name']} unequipped."
    if not is_equippable(entry["key"]):
        return False, f"{display_name(entry)} cannot be equipped."
    if not can_use(char, entry["key"]):
        return False, f"A {data.classes()[char.cls]['name']} cannot use that."
    for other in char.inventory:
        if other.get("equipped") and item(other["key"])["slot"] == it["slot"]:
            if item(other["key"]).get("cursed"):
                return False, f"The {item(other['key'])['name']} refuses to be replaced!"
            other["equipped"] = False
    entry["equipped"] = True
    recalc_ac(char)
    if it.get("cursed"):
        entry["identified"] = True
        return True, f"A chill runs up the arm — the {it['name']} is CURSED!"
    return True, f"{display_name(entry)} equipped."


def add_item(char, key, identified=True):
    """Returns True if the item fit in the character's pack."""
    if len(char.inventory) >= INVENTORY_CAP:
        return False
    char.inventory.append({"key": key, "equipped": False,
                           "identified": identified})
    return True


def identify_fee(entry):
    return max(50, item(entry["key"])["price"] // 2)


def sage_identify(sage, entry, rng):
    """A Sage studies an item at camp. Returns a message."""
    if entry.get("identified", True):
        return "It holds no secrets."
    if rng.randint(1, 100) <= 8 and item(entry["key"]).get("cursed"):
        entry["identified"] = True
        return f"Mishap! The {item(entry['key'])['name']} is cursed — and it knows your name now."
    if rng.randint(1, 100) <= 50 + 5 * sage.stats["intellect"]:
        entry["identified"] = True
        return f"It is revealed: {item(entry['key'])['name']}."
    return "Its nature eludes the Sage... for now."


def remove_item(char, index):
    entry = char.inventory.pop(index)
    if entry.get("equipped"):
        recalc_ac(char)
    return entry


def transfer_item(giver, index, receiver):
    """Hand inventory[index] from giver to receiver. Returns (ok, message)."""
    if receiver is giver:
        return False, "They already have it."
    entry = giver.inventory[index]
    if len(receiver.inventory) >= INVENTORY_CAP:
        return False, f"{receiver.name}'s pack is full."
    if is_cursed_stuck(entry):
        return False, f"The {display_name(entry)} will not let go!"
    giver.inventory.pop(index)
    receiver.inventory.append(entry)
    return True, f"{display_name(entry)} passed to {receiver.name}."


def sell_price(key):
    return item(key)["price"] // 2


def use_item(char, index, party, rng):
    """Use a consumable from char's pack on char. Returns a message."""
    entry = char.inventory[index]
    it = item(entry["key"])
    effect = it.get("use")
    if effect is None:
        return f"The {it['name']} has no obvious use."
    if effect == "heal_1d8":
        if char.hp >= char.max_hp:
            return f"{char.name} is already hale."
        healed = min(rng.randint(1, 8), char.max_hp - char.hp)
        char.hp += healed
        char.inventory.pop(index)
        return f"{char.name} drinks deep and recovers {healed} HP."
    if effect == "cure_poison":
        if char.status != "POISONED":
            return f"{char.name} has no poison to cure."
        char.status = "OK"
        char.inventory.pop(index)
        return f"The venom leaves {char.name}'s veins."
    return f"Nothing happens."
