"""Tests for maze data integrity and movement."""

from collections import deque

import pytest

from game import maze
from game.maze import DOOR, OPEN, WALL

DEPTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def _level():
    return maze.load_level(1)


@pytest.mark.parametrize("depth", DEPTHS)
def test_grid_shape(depth):
    lvl = maze.load_level(depth)
    assert lvl.width == 20 and lvl.height == 20
    assert len(lvl.grid) == 41
    assert all(len(row) == 41 for row in lvl.grid)


@pytest.mark.parametrize("depth", DEPTHS)
def test_border_sealed(depth):
    lvl = maze.load_level(depth)
    for x in range(lvl.width):
        assert lvl.edge(x, 0, 0) == WALL
        assert lvl.edge(x, lvl.height - 1, 2) == WALL
    for y in range(lvl.height):
        assert lvl.edge(0, y, 3) == WALL
        assert lvl.edge(lvl.width - 1, y, 1) == WALL


@pytest.mark.parametrize("depth", DEPTHS)
def test_edges_symmetric(depth):
    lvl = maze.load_level(depth)
    for y in range(lvl.height):
        for x in range(lvl.width):
            for facing in (0, 1, 2, 3):
                nx, ny = maze.step(x, y, facing)
                if 0 <= nx < lvl.width and 0 <= ny < lvl.height:
                    opposite = maze.turn(facing, 2)
                    assert lvl.edge(x, y, facing) == lvl.edge(nx, ny, opposite)


@pytest.mark.parametrize("depth", DEPTHS)
def test_every_cell_reachable_from_start(depth):
    lvl = maze.load_level(depth)
    start = (lvl.start["x"], lvl.start["y"])
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for facing in (0, 1, 2, 3):
            if lvl.passable(x, y, facing):
                nxt = maze.step(x, y, facing)
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    unreached = {(x, y) for x in range(20) for y in range(20)} - seen
    assert not unreached, f"depth {depth} unreachable: {sorted(unreached)}"


@pytest.mark.parametrize("depth", DEPTHS)
def test_specials_placed(depth):
    lvl = maze.load_level(depth)
    kinds = [s["type"] for s in lvl.specials.values()]
    assert kinds.count("stairs_up") == 1
    if depth < 10:
        assert kinds.count("stairs_down") == 1
    else:   # the only way home from the Sanctum is the portal
        assert kinds.count("stairs_down") == 0
        assert kinds.count("portal") == 1
    up = next(pos for pos, s in lvl.specials.items() if s["type"] == "stairs_up")
    assert up == (lvl.start["x"], lvl.start["y"])


def test_stairs_align_between_levels():
    for depth in DEPTHS[:-1]:
        lvl = maze.load_level(depth)
        below = maze.load_level(depth + 1)
        down = next(pos for pos, s in lvl.specials.items()
                    if s["type"] == "stairs_down")
        up = next(pos for pos, s in below.specials.items()
                  if s["type"] == "stairs_up")
        assert down == up, f"L{depth} down {down} != L{depth + 1} up {up}"


@pytest.mark.parametrize("depth", DEPTHS)
def test_special_targets_in_bounds(depth):
    lvl = maze.load_level(depth)
    for pos, s in lvl.specials.items():
        if s["type"] == "teleporter":
            x, y = s["to"]
            assert 0 <= x < 20 and 0 <= y < 20
        elif s["type"] == "chute":
            assert maze.level_exists(s["to_depth"])
        elif s["type"] == "elevator":
            for floor in s["floors"]:
                assert maze.level_exists(floor)


def test_movement_and_doors():
    lvl = _level()
    x, y = lvl.start["x"], lvl.start["y"]
    # entrance faces north through a door into the entry hall
    assert lvl.edge(x, y, 0) == DOOR
    assert lvl.passable(x, y, 0)
    nx, ny = maze.step(x, y, 0)
    assert (nx, ny) == (x, y - 1)
    # turning wraps
    assert maze.turn(0, -1) == 3 and maze.turn(3, 1) == 0


def test_out_of_bounds_is_wall():
    lvl = _level()
    assert lvl.edge(-1, 5, 0) == WALL
    assert lvl.edge(5, 99, 1) == WALL
