"""Maze levels: parsing, wall queries, movement. Pure Python — no pygame."""

import json

from game.paths import resource_root

LEVEL_DIR = resource_root() / "data" / "levels"

# Facing: 0=N 1=E 2=S 3=W. y increases southward.
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
DIR_NAMES = ["North", "East", "South", "West"]

OPEN, WALL, DOOR = "open", "wall", "door"
ILLUSION = "illusion"   # looks like a wall, walks like a corridor

_cache = {}


class Level:
    def __init__(self, payload):
        self.name = payload["name"]
        self.depth = payload["depth"]
        self.start = payload["start"]
        self.grid = payload["grid"]
        self.width = (len(self.grid[0]) - 1) // 2
        self.height = (len(self.grid) - 1) // 2
        self.specials = {
            tuple(map(int, key.split(","))): value
            for key, value in payload["specials"].items()
        }
        self.zones = payload.get("zones", {})

    def dark_at(self, x, y):
        return any(
            x0 <= x <= x1 and y0 <= y <= y1
            for x0, y0, x1, y1 in self.zones.get("dark", [])
        )

    def null_at(self, x, y):
        """Anti-magic: no casting here, by either side."""
        return any(
            x0 <= x <= x1 and y0 <= y <= y1
            for x0, y0, x1, y1 in self.zones.get("null", [])
        )

    def _edge_char(self, x, y, facing):
        """Raw grid char for the edge of cell (x,y) in the given direction."""
        row, col = 2 * y + 1, 2 * x + 1
        if facing == 0:
            row -= 1
        elif facing == 2:
            row += 1
        elif facing == 1:
            col += 1
        else:
            col -= 1
        return self.grid[row][col]

    def edge(self, x, y, facing):
        """OPEN, WALL, or DOOR for the edge of cell (x,y) toward facing."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return WALL
        ch = self._edge_char(x, y, facing)
        if ch == "D":
            return DOOR
        if ch == "I":
            return ILLUSION
        if ch == " ":
            return OPEN
        return WALL

    def passable(self, x, y, facing):
        return self.edge(x, y, facing) in (OPEN, DOOR, ILLUSION)

    def special_at(self, x, y):
        return self.specials.get((x, y))


def load_level(depth):
    if depth not in _cache:
        path = LEVEL_DIR / f"level{depth:02d}.json"
        with open(path, encoding="utf-8") as f:
            _cache[depth] = Level(json.load(f))
    return _cache[depth]


def level_exists(depth):
    return (LEVEL_DIR / f"level{depth:02d}.json").exists()


def turn(facing, delta):
    return (facing + delta) % 4


def step(x, y, facing):
    dx, dy = DIRS[facing]
    return x + dx, y + dy
