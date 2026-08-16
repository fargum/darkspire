"""Filesystem roots, aware of PyInstaller-frozen builds."""

import os
import shutil
import sys
from pathlib import Path


def resource_root():
    """Where read-only bundled data lives (data/, ...)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _legacy_save_dir():
    return Path(__file__).resolve().parent.parent / "saves"


def _migrate_legacy_saves(appdata_root):
    """Copy repo save files into the AppData folder when the packaged build is newer."""
    appdata_save_dir = appdata_root / "saves"
    appdata_save_dir.mkdir(parents=True, exist_ok=True)
    legacy_dir = _legacy_save_dir()
    for name in ("game.json", "roster.json"):
        src = legacy_dir / name
        dest = appdata_save_dir / name
        if src.exists() and not dest.exists():
            shutil.copy2(src, dest)


def save_root():
    """Where saves are written.

    Local source runs should stay in the project directory so dev play and tests do
    not silently overwrite a user's real packaged save data. Frozen builds use the
    per-user AppData directory instead, but will first migrate any existing repo save
    data into that location so no progress is lost.
    """
    override = os.environ.get("DARKSPIRE_SAVE_ROOT")
    if override:
        return Path(override).expanduser()

    repo_root = Path(__file__).resolve().parent.parent
    appdata_root = None
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA")
        if appdata:
            appdata_root = Path(appdata) / "Darkspire"
        else:
            appdata_root = Path.home() / "AppData" / "Roaming" / "Darkspire"

        if appdata_root:
            appdata_save_dir = appdata_root / "saves"
            if not any(appdata_save_dir.glob("*")):
                if any((repo_root / "saves").glob("*.json")):
                    _migrate_legacy_saves(appdata_root)
            return appdata_root

    return repo_root
