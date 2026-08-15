"""The Gilded Griffin Tavern — form and manage the party."""

import random

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, draw_panel
from game import data
from game.state import PARTY_CAP
from scenes.common import draw_character_sheet, draw_party_bar


class TavernScene(Scene):
    def on_enter(self):
        self.state_ = None
        self.message = ""
        self.rumor = ""
        self.rng = random.Random()
        self._to_menu()

    @property
    def gs(self):
        return self.app.state

    def _to_menu(self):
        self.state_ = "MENU"
        party = self.gs.party
        bench = [c for c in self.gs.roster if c not in party]
        self.menu = Menu([
            MenuItem("Add a member", "add",
                     enabled=bool(bench) and len(party) < PARTY_CAP),
            MenuItem("Remove a member", "remove", enabled=bool(party)),
            MenuItem("Swap marching order", "reorder", enabled=len(party) > 1),
            MenuItem("Inspect a member", "inspect", enabled=bool(party)),
            MenuItem("Divvy gold", "divvy", enabled=bool(party)),
            MenuItem("Buy a round, hear rumors", "rumor",
                     enabled=self.gs.party_gold() >= 10),
            MenuItem("Leave the tavern", "leave"),
        ])

    def _member_menu(self, chars):
        classes = data.classes()
        return Menu([
            MenuItem(f"{c.name:<14} Lv{c.level:>2} {classes[c.cls]['name']}", i)
            for i, c in enumerate(chars)
        ])

    def handle_event(self, event):
        esc = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if self.state_ == "MENU":
            choice = self.menu.handle_event(event)
            if choice == "add":
                self.bench = [c for c in self.gs.roster if c not in self.gs.party]
                self.list_menu = self._member_menu(self.bench)
                self.state_ = "ADD"
            elif choice == "remove":
                self.list_menu = self._member_menu(self.gs.party)
                self.state_ = "REMOVE"
            elif choice == "reorder":
                self.list_menu = self._member_menu(self.gs.party)
                self.swap_first = None
                self.state_ = "REORDER"
            elif choice == "inspect":
                self.list_menu = self._member_menu(self.gs.party)
                self.state_ = "INSPECT_LIST"
            elif choice == "divvy":
                self.gs.divvy_gold()
                self.gs.save()
                self.message = "The gold is divided evenly."
            elif choice == "rumor":
                self.gs.party_pay(10)
                self.gs.save()
                self.message = ""
                rumors = data.load("rumors")
                pool = list(rumors["main"])
                if self.gs.quest.get("quest_complete"):
                    pool += rumors["postgame"] * 3   # the town can't stop talking
                self.rumor = self.rng.choice(pool)
            elif choice == "leave" or esc:
                self.gs.save()
                self.app.pop()
        elif self.state_ == "ADD":
            choice = self.list_menu.handle_event(event)
            if choice is not None:
                ok, reason = self.gs.add_to_party(self.bench[choice])
                self.message = (
                    f"{self.bench[choice].name} joins the party." if ok else reason
                )
                if ok:
                    self.gs.save()
                self._to_menu()
            elif esc:
                self._to_menu()
        elif self.state_ == "REMOVE":
            choice = self.list_menu.handle_event(event)
            if choice is not None:
                gone = self.gs.party[choice]
                self.gs.remove_from_party(gone)
                self.gs.save()
                self.message = f"{gone.name} returns to the bench."
                self._to_menu()
            elif esc:
                self._to_menu()
        elif self.state_ == "REORDER":
            choice = self.list_menu.handle_event(event)
            if choice is not None:
                if self.swap_first is None:
                    self.swap_first = choice
                else:
                    p = self.gs.party
                    p[self.swap_first], p[choice] = p[choice], p[self.swap_first]
                    self.gs.save()
                    self.message = "Marching order changed."
                    self._to_menu()
            elif esc:
                self._to_menu()
        elif self.state_ == "INSPECT_LIST":
            choice = self.list_menu.handle_event(event)
            if choice is not None:
                self.view_index = choice
                self.state_ = "INSPECT_VIEW"
            elif esc:
                self._to_menu()
        elif self.state_ == "INSPECT_VIEW":
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER
            ):
                self.state_ = "INSPECT_LIST"

    def draw(self, surf):
        tr = self.app.text
        draw_panel(surf, (30, 20, 580, 210), tr, "THE GILDED GRIFFIN")
        if self.state_ == "MENU":
            tr.draw(surf, "Smoke, ale, and half-true stories of the deep.",
                    (60, 44), palette.DIM)
            self.menu.draw(surf, tr, 80, 70, width=280)
            if self.message:
                tr.draw(surf, self.message, (330, 90), palette.ACCENT)
            if self.rumor:
                y = 90
                for line in self._wrap_text(self.rumor, 26):
                    tr.draw(surf, line, (380, y), palette.ACCENT)
                    y += tr.ch
        elif self.state_ in ("ADD", "REMOVE", "INSPECT_LIST"):
            titles = {
                "ADD": "Who joins the party?",
                "REMOVE": "Who steps out?",
                "INSPECT_LIST": "Look over whom?",
            }
            tr.draw(surf, titles[self.state_], (60, 44), palette.TEXT)
            self.list_menu.draw(surf, tr, 80, 70, width=320)
            tr.draw(surf, "esc backs out", (430, 200), palette.DIM)
        elif self.state_ == "REORDER":
            prompt = "Swap whom?" if self.swap_first is None else \
                f"Swap {self.gs.party[self.swap_first].name} with whom?"
            tr.draw(surf, prompt, (60, 44), palette.TEXT)
            self.list_menu.draw(surf, tr, 80, 70, width=320)
        elif self.state_ == "INSPECT_VIEW":
            draw_character_sheet(surf, tr, self.gs.party[self.view_index], 60, 44)
        draw_party_bar(surf, tr, self.gs.party)
        if not self.gs.party and self.state_ == "MENU":
            tr.draw(surf, "No party yet. Add members from the roster.",
                    (16, 300), palette.DIM)

    @staticmethod
    def _wrap_text(text, width):
        lines, line = [], ""
        for word in text.split():
            if line and len(line) + 1 + len(word) > width:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            lines.append(line)
        return lines
