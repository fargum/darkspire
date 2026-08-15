"""Procedural monster portraits: seeded, mirrored pixel sprites.

Deterministic per monster key (crc32 seed), so every Giant Rat always
looks like the same Giant Rat. Two-tone body, dark outline, bright eyes.
Swappable for hand-drawn art later.
"""

import random
import zlib

import pygame

GRID = 9          # sprite is GRID x GRID cells, mirrored left-to-right
FILL_CHANCE = 0.52

HUES = [
    (196, 92, 70), (222, 170, 80), (140, 196, 110), (110, 160, 210),
    (180, 130, 200), (200, 200, 180), (214, 140, 96), (120, 200, 185),
]
ACCENTS = [
    (240, 210, 140), (150, 220, 220), (230, 150, 150), (180, 210, 130),
]
EYE = (250, 250, 240)
OUTLINE = (10, 10, 18)

_cache = {}


def portrait(key, size=42):
    if (key, size) in _cache:
        return _cache[(key, size)]
    seed = zlib.crc32(key.encode())
    rng = random.Random(seed)
    base = HUES[seed % len(HUES)]
    accent = ACCENTS[(seed >> 4) % len(ACCENTS)]
    dark = tuple(v // 3 for v in base)

    half = GRID // 2 + 1
    filled = [[False] * GRID for _ in range(GRID)]
    color = [[None] * GRID for _ in range(GRID)]
    for y in range(GRID):
        for x in range(half):
            if rng.random() < FILL_CHANCE:
                roll = rng.random()
                c = base if roll < 0.65 else (accent if roll < 0.85 else dark)
                for px in (x, GRID - 1 - x):
                    filled[y][px] = True
                    color[y][px] = c

    # Eyes: a symmetric bright pair in the upper half, on filled cells if we can.
    eye_row = rng.randrange(1, GRID // 2 + 1)
    eye_col = rng.randrange(1, half - 1)
    for px in (eye_col, GRID - 1 - eye_col):
        filled[eye_row][px] = True
        color[eye_row][px] = EYE

    cells = pygame.Surface((GRID + 2, GRID + 2))
    cells.fill((0, 0, 0))
    cells.set_colorkey((0, 0, 0))
    # Outline pass: any empty cell touching a filled one gets the outline color.
    for y in range(GRID):
        for x in range(GRID):
            if filled[y][x]:
                cells.set_at((x + 1, y + 1), color[y][x])
            else:
                touching = any(
                    0 <= y + dy < GRID and 0 <= x + dx < GRID
                    and filled[y + dy][x + dx]
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                )
                if touching:
                    cells.set_at((x + 1, y + 1), OUTLINE)
    sprite = pygame.transform.scale(cells, (size, size))
    _cache[(key, size)] = sprite
    return sprite
