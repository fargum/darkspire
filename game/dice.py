"""Dice-notation rolls ("2d4", "1d8+2"). Pure Python — RNG is injected."""

import re

_PATTERN = re.compile(r"(\d+)d(\d+)([+-]\d+)?$")


def roll(rng, spec):
    m = _PATTERN.fullmatch(spec)
    if not m:
        raise ValueError(f"bad dice spec: {spec!r}")
    n, sides, mod = int(m[1]), int(m[2]), int(m[3] or 0)
    return sum(rng.randint(1, sides) for _ in range(n)) + mod
