"""Loads and caches JSON game data. Pure Python — no pygame."""

import json

from game.paths import resource_root

DATA_DIR = resource_root() / "data"

_cache = {}


def load(name):
    if name not in _cache:
        with open(DATA_DIR / f"{name}.json", encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def races():
    return load("races")


def classes():
    return load("classes")
