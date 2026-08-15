"""Temple of the Dawnmother — cures and resurrection, paid by the party."""

import random

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, draw_panel
from game import items, temple
from scenes.common import draw_party_bar


class TempleScene(Scene):
    def on_enter(self):
        self.rng = random.Random()
        self.message = ""
        quest = self.gs.quest
        if quest.get("reached_l9") and not quest.get("wardlantern"):
            quest["wardlantern"] = True
            self.gs.save()
            self.message = ("The High Matriarch presses the WARDLANTERN into "
                            "your hands: 'Bring our flame home.'")
        self._to_list()

    @property
    def gs(self):
        return self.app.state

    def _to_list(self):
        self.state_ = "LIST"
        self.cases = []      # ("status", char) or ("uncurse", char, inv_index)
        rows = []
        for c in self.gs.party:
            if temple.service_for(c):
                cost = temple.cost_for(c)
                self.cases.append(("status", c, cost))
                rows.append(MenuItem(
                    f"{c.name:<14} {c.status:<10} {cost:>6}g",
                    len(self.cases) - 1,
                    enabled=self.gs.party_gold() >= cost,
                ))
            for idx, entry in enumerate(c.inventory):
                if items.is_cursed_stuck(entry):
                    cost = max(100, items.item(entry["key"])["price"])
                    self.cases.append(("uncurse", c, cost, idx))
                    rows.append(MenuItem(
                        f"{c.name:<14} CURSED     {cost:>6}g",
                        len(self.cases) - 1,
                        enabled=self.gs.party_gold() >= cost,
                    ))
            if c.drained > 0:
                cost = 350 * (c.level + 1)
                self.cases.append(("drained", c, cost))
                rows.append(MenuItem(
                    f"{c.name:<14} DRAINED    {cost:>6}g",
                    len(self.cases) - 1,
                    enabled=self.gs.party_gold() >= cost,
                ))
        self.patients = self.cases
        rows.append(MenuItem("Leave the temple", "leave"))
        self.list_menu = Menu(rows)

    def handle_event(self, event):
        esc = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if self.state_ == "LIST":
            choice = self.list_menu.handle_event(event)
            if choice == "leave" or esc:
                self.app.pop()
            elif choice is not None:
                case = self.cases[choice]
                if case[0] == "status":
                    _, patient, cost = case
                    if self.gs.party_pay(cost):
                        success, msg = temple.attempt_service(patient, self.rng)
                        self.message = msg
                        self.gs.save()
                elif case[0] == "drained":
                    _, patient, cost = case
                    if self.gs.party_pay(cost):
                        from game import progression, spells
                        patient.level += 1
                        patient.drained -= 1
                        patient.xp = max(patient.xp,
                                         progression.xp_for_level(patient.cls,
                                                                  patient.level))
                        spells.ensure(patient)
                        self.message = f"Life floods back into {patient.name}."
                        self.gs.save()
                else:
                    _, patient, cost, idx = case
                    if self.gs.party_pay(cost):
                        entry = patient.inventory.pop(idx)
                        items.recalc_ac(patient)
                        name = items.item(entry["key"])["name"]
                        self.message = f"The {name} shrieks as it burns to nothing."
                        self.gs.save()
                self._to_list()
        elif self.state_ == "RESULT":
            pass

    def draw(self, surf):
        tr = self.app.text
        draw_panel(surf, (30, 20, 580, 210), tr, "TEMPLE OF THE DAWNMOTHER")
        if not self.gs.party:
            tr.draw(surf, "Candles burn for the absent.", (60, 60), palette.DIM)
            tr.draw(surf, "Form a party at the tavern first. (esc)", (60, 90), palette.TEXT)
        elif not self.patients:
            tr.draw(surf, "The priests find no affliction among you.", (60, 60), palette.DIM)
            tr.draw(surf, "Go with the dawn's blessing. (esc)", (60, 90), palette.TEXT)
            if self.message:
                tr.draw(surf, self.message, (60, 130), palette.ACCENT)
        else:
            tr.draw(surf, f"Party gold: {self.gs.party_gold()}", (60, 44), palette.ACCENT)
            tr.draw(surf, "Who needs the Dawnmother's mercy?", (60, 44 + tr.ch), palette.TEXT)
            self.list_menu.draw(surf, tr, 80, 90, width=380)
            if self.message:
                tr.draw(surf, self.message, (60, 200), palette.ACCENT)
        draw_party_bar(surf, tr, self.gs.party)
