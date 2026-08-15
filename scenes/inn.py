"""The Adventurer's Rest — heal by the night, and level up when ready."""

import random

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, draw_panel
from game import data, progression, spells
from game.character import STAT_LABELS
from scenes.common import draw_party_bar

ROOMS = [
    ("The Stables", 0, 0),
    ("A Cot in the Common Room", 10, 2),
    ("An Economy Room", 50, 5),
    ("A Merchant Suite", 200, 12),
    ("The Royal Suite", 500, 25),
]


class InnScene(Scene):
    def on_enter(self):
        self.rng = random.Random()
        self.message = ""
        self._to_who()

    @property
    def gs(self):
        return self.app.state

    def _to_who(self):
        self.state_ = "WHO"
        classes = data.classes()
        self.who_menu = Menu(
            [
                MenuItem(
                    f"{c.name:<14} Lv{c.level:>2} {classes[c.cls]['name']}", i,
                    enabled=c.status == "OK",
                )
                for i, c in enumerate(self.gs.party)
            ]
            + [MenuItem("Leave the inn", "leave")]
        )

    def _to_room(self):
        self.state_ = "ROOM"
        c = self.guest
        self.room_menu = Menu([
            MenuItem(f"{name:<26} {cost:>4} gold/night", i,
                     enabled=cost == 0 or c.gold >= cost)
            for i, (name, cost, heal) in enumerate(ROOMS)
        ])

    def _stay(self, room_index):
        name, cost, heal = ROOMS[room_index]
        c = self.guest
        nights = 0
        spent = 0
        healed = 0
        if heal > 0:
            while c.hp < c.max_hp and c.gold >= cost:
                c.gold -= cost
                spent += cost
                gained = min(heal, c.max_hp - c.hp)
                c.hp += gained
                healed += gained
                nights += 1
        else:
            nights = 1
        self.result_lines = [
            f"{c.name} spends {nights} night{'s' if nights != 1 else ''} in {name.lower()}.",
        ]
        if healed:
            self.result_lines.append(f"Recovered {healed} HP for {spent} gold.")
        elif heal == 0:
            self.result_lines.append("Cold straw, but the price is right.")
        if heal > 0 and spells.is_caster(c):
            spells.restore(c)
            self.result_lines.append("Rest returns every spell to mind.")
        if progression.can_level(c):
            import audio
            audio.play("levelup")
            gains = progression.level_up(c, self.rng)
            c.hp = c.max_hp
            spells.restore(c)
            self.result_lines.append("")
            self.result_lines.append(f"{c.name} has reached level {c.level}!")
            self.result_lines.append(f"Hit points +{gains['hp']}.")
            for stat, delta in gains["stats"].items():
                word = "rises" if delta > 0 else "fades"
                self.result_lines.append(f"{STAT_LABELS[stat]} {word}.")
        self.gs.save()
        self.state_ = "RESULT"

    def handle_event(self, event):
        esc = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if self.state_ == "WHO":
            choice = self.who_menu.handle_event(event)
            if choice == "leave" or esc:
                self.app.pop()
            elif choice is not None:
                self.guest = self.gs.party[choice]
                self._to_room()
        elif self.state_ == "ROOM":
            choice = self.room_menu.handle_event(event)
            if choice is not None:
                self._stay(choice)
            elif esc:
                self._to_who()
        elif self.state_ == "RESULT":
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE
            ):
                self._to_who()

    def draw(self, surf):
        tr = self.app.text
        draw_panel(surf, (30, 20, 580, 210), tr, "THE ADVENTURER'S REST")
        if not self.gs.party:
            tr.draw(surf, "The innkeeper eyes your empty table.", (60, 60), palette.DIM)
            tr.draw(surf, "Form a party at the tavern first. (esc)", (60, 90), palette.TEXT)
        elif self.state_ == "WHO":
            tr.draw(surf, "Who takes a room?", (60, 44), palette.TEXT)
            self.who_menu.draw(surf, tr, 80, 70, width=330)
        elif self.state_ == "ROOM":
            c = self.guest
            ready = progression.can_level(c)
            headline = f"{c.name} — {c.hp}/{c.max_hp} HP, {c.gold} gold"
            tr.draw(surf, headline, (60, 44), palette.TEXT)
            if ready:
                tr.draw(surf, "They look ready to advance!", (400, 44), palette.GOOD)
            self.room_menu.draw(surf, tr, 80, 70, width=380)
        elif self.state_ == "RESULT":
            y = 50
            for line in self.result_lines:
                color = palette.GOOD if "level" in line else palette.TEXT
                tr.draw(surf, line, (60, y), color)
                y += tr.ch
            tr.draw(surf, "enter continues", (430, 200), palette.DIM)
        draw_party_bar(surf, tr, self.gs.party)
