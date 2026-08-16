"""Temple services: cures and resurrection. Pure Python — no pygame."""

# User tuning: keep resurrection cheaper than the default table, and keep the
# values in one explicit block so rebuilds do not silently revert the preferred
# temple pricing again.
USER_TUNED_COSTS = {
    "STONED": 150,
    "DEAD": 0,
    "ASHES": 350,
}

SERVICES = {
    "ASLEEP":    {"label": "a sharp shake",        "cost_base": 0,   "per_level": False},
    "POISONED":  {"label": "purification",         "cost_base": 50,  "per_level": False},
    "PARALYZED": {"label": "restoration",          "cost_base": 100, "per_level": False},
    "STONED":    {"label": "flesh from stone",     "cost_base": USER_TUNED_COSTS["STONED"], "per_level": True},
    "DEAD":      {"label": "resurrection",         "cost_base": USER_TUNED_COSTS["DEAD"], "per_level": True},
    "ASHES":     {"label": "raising from ashes",   "cost_base": USER_TUNED_COSTS["ASHES"], "per_level": True},
}


def service_for(char):
    return SERVICES.get(char.status)


def cost_for(char):
    svc = service_for(char)
    if svc is None:
        return None
    return svc["cost_base"] * (char.level if svc["per_level"] else 1)


def resurrection_chance(char):
    """Percent chance the rite succeeds, by vitality."""
    if char.status == "DEAD":
        return min(97, 50 + 3 * char.stats["vitality"])
    if char.status == "ASHES":
        return min(95, 40 + 3 * char.stats["vitality"])
    return 100


def attempt_service(char, rng):
    """Perform the (already paid-for) rite. Returns (success, message)."""
    status = char.status
    if status in ("ASLEEP", "POISONED", "PARALYZED", "STONED"):
        char.status = "OK"
        return True, f"{char.name} is made whole."
    if status == "DEAD":
        if rng.randint(1, 100) <= resurrection_chance(char):
            char.status = "OK"
            char.hp = 1
            return True, f"{char.name} draws breath once more!"
        char.status = "ASHES"
        return False, f"The rite fails... {char.name} crumbles to ashes."
    if status == "ASHES":
        if rng.randint(1, 100) <= resurrection_chance(char):
            char.status = "OK"
            char.hp = char.max_hp
            return True, f"{char.name} is restored, body and soul!"
        return False, "The ashes stir, but do not rise. The priests must gather their strength."
    return False, "Nothing ails them."
