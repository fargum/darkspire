"""Level authoring library. See gen_levels.py for the actual maps.

Authoring model: 20x20 cells with walls on cell edges (Wizardry style).
The JSON stores a human-readable 41x41 ASCII grid plus specials/zones.
"""

import json
from pathlib import Path

W = H = 20
LEVEL_DIR = Path(__file__).resolve().parent.parent / "data" / "levels"


class Builder:
    def __init__(self, name, depth):
        self.name = name
        self.depth = depth
        self.start = None
        self.specials = {}
        self.zones = {}
        # h[y][x]: edge north of cell (x, y); h[H] is the south border
        self.h = [[" "] * W for _ in range(H + 1)]
        # v[y][x]: edge west of cell (x, y); v[y][W] is the east border
        self.v = [[" "] * (W + 1) for _ in range(H)]
        for x in range(W):
            self.h[0][x] = self.h[H][x] = "-"
        for y in range(H):
            self.v[y][0] = self.v[y][W] = "|"

    def room(self, x0, y0, x1, y1, doors=()):
        for x in range(x0, x1 + 1):
            self.h[y0][x] = "-"
            self.h[y1 + 1][x] = "-"
        for y in range(y0, y1 + 1):
            self.v[y][x0] = "|"
            self.v[y][x1 + 1] = "|"
        for side, coord in doors:
            if side == "N":
                self.h[y0][coord] = "D"
            elif side == "S":
                self.h[y1 + 1][coord] = "D"
            elif side == "W":
                self.v[coord][x0] = "D"
            elif side == "E":
                self.v[coord][x1 + 1] = "D"

    def hrun(self, y_edge, x0, x1, gaps=()):
        for x in range(x0, x1 + 1):
            if x not in gaps:
                self.h[y_edge][x] = "-"

    def vrun(self, x_edge, y0, y1, gaps=()):
        for y in range(y0, y1 + 1):
            if y not in gaps:
                self.v[y][x_edge] = "|"

    def hillusion(self, y_edge, *xs):
        for x in xs:
            self.h[y_edge][x] = "I"

    def villusion(self, x_edge, *ys):
        for y in ys:
            self.v[y][x_edge] = "I"

    def special(self, x, y, **payload):
        self.specials[f"{x},{y}"] = payload

    def message(self, x, y, text):
        self.special(x, y, type="message", text=text)

    def dark(self, x0, y0, x1, y1):
        self.zones.setdefault("dark", []).append([x0, y0, x1, y1])

    def serialize(self):
        rows = []
        for y in range(H):
            rows.append("+" + "+".join(self.h[y][x] for x in range(W)) + "+")
            rows.append("".join(self.v[y][x] + " " for x in range(W)) + self.v[y][W])
        rows.append("+" + "+".join(self.h[H][x] for x in range(W)) + "+")
        return rows

    def write(self):
        assert self.start, f"level {self.depth} has no start"
        payload = {
            "name": self.name,
            "depth": self.depth,
            "start": self.start,
            "grid": self.serialize(),
            "specials": self.specials,
            "zones": self.zones,
        }
        LEVEL_DIR.mkdir(parents=True, exist_ok=True)
        out = LEVEL_DIR / f"level{self.depth:02d}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1)
        return out
