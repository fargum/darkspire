"""DARKSPIRE: Depths of the Mad Archon — entry point."""

import sys

from engine.app import App
from game.state import GameState
from scenes.title import TitleScene


def main():
    app = App(scale=2)
    app.state = GameState.load()
    app.push(TitleScene(app))
    if "--smoke" in sys.argv:   # build verification: boot, draw one frame, exit
        app.render_one_frame()
        print("SMOKE OK")
        return
    app.run()


if __name__ == "__main__":
    main()
