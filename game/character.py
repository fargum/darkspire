"""Character model. Pure Python — no pygame."""

from dataclasses import dataclass, field

STATS = ["might", "agility", "vitality", "intellect", "faith", "luck"]
STAT_LABELS = {
    "might": "Might",
    "agility": "Agility",
    "vitality": "Vitality",
    "intellect": "Intellect",
    "faith": "Faith",
    "luck": "Luck",
}
ALIGNMENTS = ["light", "gray", "shadow"]
ALIGNMENT_LABELS = {"light": "Light", "gray": "Gray", "shadow": "Shadow"}
STAT_CAP = 18  # at creation; 20 lifetime cap via level-ups


@dataclass
class Character:
    name: str
    race: str            # key into races.json
    cls: str             # key into classes.json
    alignment: str       # "light" | "gray" | "shadow"
    stats: dict          # {stat_key: int}
    level: int = 1
    xp: int = 0
    gold: int = 0
    hp: int = 1
    max_hp: int = 1
    ac: int = 10         # lower is better
    status: str = "OK"   # OK | ASLEEP | POISONED | PARALYZED | STONED | DEAD | ASHES
    inventory: list = field(default_factory=list)
    sp: dict = None      # spell points {"mage": [7 ints], "priest": [7 ints]}
    drained: int = 0     # levels lost to drain, restorable at the temple

    def to_dict(self):
        return {
            "name": self.name,
            "race": self.race,
            "cls": self.cls,
            "alignment": self.alignment,
            "stats": dict(self.stats),
            "level": self.level,
            "xp": self.xp,
            "gold": self.gold,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "status": self.status,
            "inventory": list(self.inventory),
            "sp": self.sp,
            "drained": self.drained,
        }

    @classmethod
    def from_dict(cls, d):
        d.setdefault("sp", None)      # pre-M5 saves have no spell points
        d.setdefault("drained", 0)    # pre-M6 saves have no drain tracking
        if d.get("race") == "hobbit":  # renamed in the public release
            d["race"] = "halfling"
        return cls(**d)
