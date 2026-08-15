"""Edge of Town — the gate between Aldenmoor and the Darkspire."""

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, draw_panel
from scenes.common import draw_party_bar


class EdgeScene(Scene):
    def on_enter(self):
        self._build_menu()

    def on_resume(self):
        self._build_menu()

    def _build_menu(self):
        gs = self.app.state
        label = "Descend into the Darkspire" if not gs.maze else \
            f"Return to the maze (Level {gs.maze['depth']})"
        able = any(c.status in ("OK", "POISONED") for c in gs.party)
        self.menu = Menu([
            MenuItem(label, "enter", enabled=able),
            MenuItem("Back to the castle", "back"),
        ])

    def handle_event(self, event):
        choice = self.menu.handle_event(event)
        if choice == "enter":
            from scenes.maze_explore import MazeScene
            self.app.push(MazeScene(self.app))
        elif choice == "back" or (
            event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        ):
            self.app.pop()

    def draw(self, surf):
        tr = self.app.text
        draw_panel(surf, (40, 20, 560, 220), tr, "EDGE OF TOWN")
        tr.draw(surf, "A cold draft rises from the maze entrance.", (70, 50),
                palette.DIM)
        if not self.app.state.party:
            tr.draw(surf, "None dare enter alone — form a party at the tavern.",
                    (70, 76), palette.BAD)
        self.menu.draw(surf, tr, 90, 110, width=340)
        draw_party_bar(surf, tr, self.app.state.party)
