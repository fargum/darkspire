"""Whole-game state: roster + active party, with persistence.

Party members ARE roster members (same objects); the save stores party
membership by name. Pure Python — no pygame.
"""

import json
import os

from game.character import Character
from game.paths import save_root

SAVE_DIR = save_root() / "saves"
GAME_FILE = SAVE_DIR / "game.json"
LEGACY_ROSTER = SAVE_DIR / "roster.json"

PARTY_CAP = 6


class GameState:
    def __init__(self, roster=None, party=None):
        self.roster = roster or []
        self.party = party or []
        self.maze = None  # None in the castle, else {"depth", "x", "y", "facing"}
        self.quest = {}   # quest flags: bronze_sigil, iron_key, enc_* ...

    # -- party management --------------------------------------------------
    def find(self, name):
        for c in self.roster:
            if c.name == name:
                return c
        return None

    def can_join(self, char):
        """Returns (ok, reason)."""
        if char in self.party:
            return False, "Already in the party."
        if len(self.party) >= PARTY_CAP:
            return False, "The party is full."
        aligns = {c.alignment for c in self.party} | {char.alignment}
        if "light" in aligns and "shadow" in aligns:
            return False, "Light and Shadow will not walk together."
        return True, ""

    def add_to_party(self, char):
        ok, reason = self.can_join(char)
        if ok:
            self.party.append(char)
        return ok, reason

    def remove_from_party(self, char):
        if char in self.party:
            self.party.remove(char)

    def dismiss(self, char):
        """Remove from roster (and party) entirely."""
        self.remove_from_party(char)
        if char in self.roster:
            self.roster.remove(char)

    # -- gold --------------------------------------------------------------
    def party_gold(self):
        return sum(c.gold for c in self.party)

    def party_pay(self, amount):
        """Pay from the party collectively. Returns False if they can't afford it."""
        if self.party_gold() < amount:
            return False
        for c in self.party:
            take = min(c.gold, amount)
            c.gold -= take
            amount -= take
            if amount == 0:
                break
        return True

    def pool_gold(self, target):
        """Everyone hands their gold to `target`."""
        total = self.party_gold()
        for c in self.party:
            c.gold = 0
        target.gold = total

    def divvy_gold(self):
        """Split party gold evenly; remainder to the front of the line."""
        if not self.party:
            return
        total = self.party_gold()
        share, extra = divmod(total, len(self.party))
        for i, c in enumerate(self.party):
            c.gold = share + (1 if i < extra else 0)

    # -- persistence -------------------------------------------------------
    def save(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "roster": [c.to_dict() for c in self.roster],
            "party": [c.name for c in self.party],
            "maze": self.maze,
            "quest": self.quest,
        }
        tmp = GAME_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, GAME_FILE)

    @classmethod
    def load(cls):
        if GAME_FILE.exists():
            with open(GAME_FILE, encoding="utf-8") as f:
                payload = json.load(f)
            state = cls(roster=[Character.from_dict(d) for d in payload["roster"]])
            state.party = [c for n in payload["party"] if (c := state.find(n))]
            state.maze = payload.get("maze")
            state.quest = payload.get("quest", {})
            return state
        if LEGACY_ROSTER.exists():  # migrate M1-era save
            with open(LEGACY_ROSTER, encoding="utf-8") as f:
                roster = [Character.from_dict(d) for d in json.load(f)]
            return cls(roster=roster)
        return cls()
