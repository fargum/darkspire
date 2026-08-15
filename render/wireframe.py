"""First-person wireframe maze renderer.

Classic corridor projection: nested frames, one per wall plane. Frame i is the
cross-section of the corridor at distance (i - 0.5) cells ahead of the party.
Painter's algorithm far-to-near, with each depth clipped to its own frame so
nearer geometry always occludes deeper geometry.
"""

import pygame

from game import maze

MAX_DEPTH = 4  # cells visible ahead

# Fills darken and lines dim with distance.
WALL_FILL = [(30, 30, 52), (24, 24, 44), (19, 19, 36), (15, 15, 30)]
WALL_LINE = [(150, 190, 230), (110, 145, 185), (78, 105, 140), (52, 72, 100)]
DOOR_FILL = [(52, 40, 24), (42, 32, 20), (33, 25, 16), (26, 20, 13)]
DOOR_LINE = [(226, 178, 74), (176, 138, 58), (128, 100, 44), (90, 70, 32)]
VOID = (2, 2, 6)
FLOOR_LINE = (40, 52, 70)


def _scale(i):
    """Projection scale of frame i (wall plane at distance i - 0.5)."""
    return 1.5 / (i + 0.5)


def _frame(view, i):
    cx, cy = view.centerx, view.centery
    half_w = view.width / 2 * _scale(i)
    half_h = view.height / 2 * _scale(i)
    return pygame.Rect(cx - half_w, cy - half_h, half_w * 2, half_h * 2)


def _poly(surf, points, fill, line):
    pygame.draw.polygon(surf, fill, points)
    pygame.draw.polygon(surf, line, points, 1)


def draw(surf, view, level, x, y, facing, light=MAX_DEPTH,
         reveal_illusions=False):
    """Render the view from (x, y) looking toward `facing` into rect `view`."""

    def edge_of(cx, cy, direction):
        e = level.edge(cx, cy, direction)
        if e == maze.ILLUSION:
            return maze.OPEN if reveal_illusions else maze.WALL
        return e

    view = pygame.Rect(view)
    old_clip = surf.get_clip()
    surf.set_clip(view)
    surf.fill(VOID, view)

    frames = [_frame(view, i) for i in range(MAX_DEPTH + 1)]
    left_dir = maze.turn(facing, -1)
    right_dir = maze.turn(facing, 1)
    depth = min(MAX_DEPTH, light)

    for d in range(depth - 1, -1, -1):
        cx = x + maze.DIRS[facing][0] * d
        cy = y + maze.DIRS[facing][1] * d
        near = frames[d]           # geometry (may exceed the viewport)
        far = frames[d + 1]
        surf.set_clip(near.clip(view))
        shade = min(d, len(WALL_FILL) - 1)

        # Flats: front walls of the side-neighbor cells, seen through openings.
        for side_dir, sign in ((left_dir, -1), (right_dir, 1)):
            if edge_of(cx, cy, side_dir) != maze.WALL:
                nx, ny = maze.step(cx, cy, side_dir)
                edge = edge_of(nx, ny, facing)
                if edge != maze.OPEN:
                    w = far.width
                    rect = pygame.Rect(
                        far.left - w if sign < 0 else far.right,
                        far.top, w, far.height,
                    )
                    fill = DOOR_FILL if edge == maze.DOOR else WALL_FILL
                    line = DOOR_LINE if edge == maze.DOOR else WALL_LINE
                    _poly(surf, [rect.topleft, rect.topright,
                                 rect.bottomright, rect.bottomleft],
                          fill[shade], line[shade])

        # Side walls: trapezoids between this frame and the next.
        for side_dir, near_x, far_x in (
            (left_dir, near.left, far.left),
            (right_dir, near.right, far.right),
        ):
            edge = edge_of(cx, cy, side_dir)
            if edge != maze.OPEN:
                pts = [
                    (near_x, near.top), (far_x, far.top),
                    (far_x, far.bottom), (near_x, near.bottom),
                ]
                fill = DOOR_FILL if edge == maze.DOOR else WALL_FILL
                line = DOOR_LINE if edge == maze.DOOR else WALL_LINE
                _poly(surf, pts, fill[shade], line[shade])
            else:
                # open corridor: floor and ceiling edge lines
                pygame.draw.line(surf, FLOOR_LINE,
                                 (near_x, near.bottom), (far_x, far.bottom))
                pygame.draw.line(surf, FLOOR_LINE,
                                 (near_x, near.top), (far_x, far.top))

        # Front wall of this cell.
        edge = edge_of(cx, cy, facing)
        if edge != maze.OPEN:
            fill = DOOR_FILL if edge == maze.DOOR else WALL_FILL
            line = DOOR_LINE if edge == maze.DOOR else WALL_LINE
            _poly(surf, [far.topleft, far.topright,
                         far.bottomright, far.bottomleft],
                  fill[shade], line[shade])
            if edge == maze.DOOR:
                # inset door slab
                inset = far.inflate(-far.width // 3, -far.height // 4)
                inset.bottom = far.bottom
                pygame.draw.rect(surf, WALL_FILL[shade], inset)
                pygame.draw.rect(surf, line[shade], inset, 1)

    surf.set_clip(view)
    pygame.draw.rect(surf, WALL_LINE[1], view, 1)
    surf.set_clip(old_clip)
