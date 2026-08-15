"""Title screen."""

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem


class TitleScene(Scene):
    def on_enter(self):
        self.menu = Menu([
            MenuItem("Enter Aldenmoor", "enter"),
            MenuItem("Quit", "quit"),
        ])

    def handle_event(self, event):
        choice = self.menu.handle_event(event)
        if choice == "enter":
            from scenes.castle import CastleScene
            self.app.push(CastleScene(self.app))
        elif choice == "quit":
            self.app.quit()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.quit()

    def draw(self, surf):
        tr = self.app.text
        cx = surf.get_width() // 2
        tr.draw_center(surf, "D A R K S P I R E", cx, 90, palette.TITLE_RED, tr.big)
        tr.draw_center(surf, "Depths of the Mad Archon", cx, 132, palette.ACCENT)
        tr.draw_center(
            surf,
            "The Everflame is stolen. The wards grow dim.",
            cx, 170, palette.DIM,
        )
        self.menu.draw(surf, tr, cx - 70, 230, width=160)
        tr.draw_center(surf, "arrows move · enter selects · esc backs out", cx, 360, palette.DIM)
