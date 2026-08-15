"""Castle Aldenmoor — the hub."""

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, draw_panel
from scenes.common import draw_party_bar


class CastleScene(Scene):
    def on_enter(self):
        self.menu = Menu([
            MenuItem("Gilded Griffin Tavern", "tavern"),
            MenuItem("Adventurer's Rest (Inn)", "inn"),
            MenuItem("The Iron Ledger (Shop)", "shop"),
            MenuItem("Temple of the Dawnmother", "temple"),
            MenuItem("Training Grounds", "training"),
            MenuItem("Edge of Town (Maze)", "maze"),
            MenuItem("Return to Title", "back"),
        ])

    def handle_event(self, event):
        choice = self.menu.handle_event(event)
        if choice == "training":
            from scenes.training import TrainingScene
            self.app.push(TrainingScene(self.app))
        elif choice == "tavern":
            from scenes.tavern import TavernScene
            self.app.push(TavernScene(self.app))
        elif choice == "inn":
            from scenes.inn import InnScene
            self.app.push(InnScene(self.app))
        elif choice == "shop":
            from scenes.shop import ShopScene
            self.app.push(ShopScene(self.app))
        elif choice == "temple":
            from scenes.temple import TempleScene
            self.app.push(TempleScene(self.app))
        elif choice == "maze":
            from scenes.edge import EdgeScene
            self.app.push(EdgeScene(self.app))
        elif choice == "back":
            self.app.state.save()
            self.app.pop()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.state.save()
            self.app.pop()

    def draw(self, surf):
        tr = self.app.text
        state = self.app.state
        draw_panel(surf, (40, 20, 560, 220), tr, "CASTLE ALDENMOOR")
        tr.draw(surf, "Torchlight gutters along the walls. Somewhere below,", (70, 44), palette.DIM)
        tr.draw(surf, "the Darkspire waits.", (70, 44 + tr.ch), palette.DIM)
        self.menu.draw(surf, tr, 90, 90, width=340)
        if state.party:
            draw_party_bar(surf, tr, state.party)
        else:
            tr.draw(
                surf,
                f"Roster: {len(state.roster)} adventurers. No party formed — visit the tavern.",
                (40, 320),
                palette.DIM,
            )
