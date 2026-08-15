"""Filesystem roots, aware of PyInstaller-frozen builds."""

import sys
from pathlib import Path


def resource_root():
    """Where read-only bundled data lives (data/, ...)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def save_root():
    """Where saves are written — next to the exe when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
