"""Training Grounds — create, inspect, and delete characters."""

import random

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, TextInput, draw_panel
from game import creation, data
from game.character import STATS, STAT_LABELS, ALIGNMENTS, ALIGNMENT_LABELS, STAT_CAP
from scenes.common import draw_character_sheet

ALIGN_DESCS = {
    "light": "Sworn to mercy and the dawn. May not party with Shadow.",
    "gray": "Beholden to no creed. Walks with anyone.",
    "shadow": "Takes what the dark offers. May not party with Light.",
}


class TrainingScene(Scene):
    def on_enter(self):
        self.rng = random.Random()
        self.message = ""
        self._to_menu()

    @property
    def roster(self):
        return self.app.state.roster

    # ---- state helpers ---------------------------------------------------
    def _to_menu(self):
        self.state = "MENU"
        self.menu = Menu([
            MenuItem("Create a Character", "create",
                     enabled=len(self.roster) < creation.ROSTER_CAP),
            MenuItem("Inspect the Roster", "inspect", enabled=bool(self.roster)),
            MenuItem("Dismiss a Character", "delete", enabled=bool(self.roster)),
            MenuItem("Leave the Training Grounds", "leave"),
        ])

    def _start_creation(self):
        self.state = "NAME"
        self.name_input = TextInput(max_len=14)
        self.new_name = ""
        self.race_key = None
        self.alignment = None
        self.error = ""

    def _to_race(self):
        self.state = "RACE"
        self.race_menu = Menu([
            MenuItem(r["name"], key) for key, r in data.races().items()
        ])

    def _to_align(self):
        self.state = "ALIGN"
        self.align_menu = Menu([
            MenuItem(ALIGNMENT_LABELS[a], a) for a in ALIGNMENTS
        ])

    def _to_alloc(self, reroll=True):
        self.state = "ALLOC"
        self.base_stats = dict(data.races()[self.race_key]["stats"])
        self.alloc_stats = dict(self.base_stats)
        if reroll:
            self.bonus_total = creation.roll_bonus(self.rng)
        self.bonus_left = self.bonus_total
        self.alloc_index = 0

    def _to_class(self):
        self.state = "CLASS"
        classes = data.classes()
        self.class_menu = Menu([
            MenuItem(classes[key]["name"], key)
            for key in creation.eligible_classes(self.alloc_stats, self.alignment)
        ])

    def _to_confirm(self, cls_key):
        self.state = "CONFIRM"
        self.candidate = creation.create_character(
            self.new_name, self.race_key, self.alignment, cls_key,
            self.alloc_stats, self.rng,
        )
        self.confirm_menu = Menu([
            MenuItem("Keep this character", "keep"),
            MenuItem("Discard", "discard"),
        ])

    def _roster_menu(self):
        classes = data.classes()
        return Menu([
            MenuItem(
                f"{c.name:<14} Lv{c.level:>2} {classes[c.cls]['name']}", i
            )
            for i, c in enumerate(self.roster)
        ])

    # ---- events ----------------------------------------------------------
    def handle_event(self, event):
        handler = getattr(self, f"_ev_{self.state.lower()}", None)
        if handler:
            handler(event)

    def _ev_menu(self, event):
        choice = self.menu.handle_event(event)
        if choice == "create":
            self.message = ""
            self._start_creation()
        elif choice == "inspect":
            self.state = "INSPECT_LIST"
            self.list_menu = self._roster_menu()
        elif choice == "delete":
            self.state = "DELETE_LIST"
            self.list_menu = self._roster_menu()
        elif choice == "leave":
            self.app.pop()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.pop()

    def _ev_name(self, event):
        result = self.name_input.handle_event(event)
        if not result:
            return
        action, text = result
        if action == "cancel":
            self._to_menu()
        elif action == "done":
            if any(c.name.lower() == text.lower() for c in self.roster):
                self.error = "That name is already on the roster."
            else:
                self.new_name = text
                self.error = ""
                self._to_race()

    def _ev_race(self, event):
        choice = self.race_menu.handle_event(event)
        if choice:
            self.race_key = choice
            self._to_align()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "NAME"

    def _ev_align(self, event):
        choice = self.align_menu.handle_event(event)
        if choice:
            self.alignment = choice
            self._to_alloc(reroll=True)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._to_race()

    def _ev_alloc(self, event):
        if event.type != pygame.KEYDOWN:
            return
        stat = STATS[self.alloc_index]
        if event.key in (pygame.K_UP, pygame.K_w):
            self.alloc_index = (self.alloc_index - 1) % len(STATS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.alloc_index = (self.alloc_index + 1) % len(STATS)
        elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_PLUS, pygame.K_KP_PLUS):
            if self.bonus_left > 0 and self.alloc_stats[stat] < STAT_CAP:
                self.alloc_stats[stat] += 1
                self.bonus_left -= 1
        elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_MINUS, pygame.K_KP_MINUS):
            if self.alloc_stats[stat] > self.base_stats[stat]:
                self.alloc_stats[stat] -= 1
                self.bonus_left += 1
        elif event.key == pygame.K_r:
            self._to_alloc(reroll=True)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.bonus_left == 0 and creation.eligible_classes(
                self.alloc_stats, self.alignment
            ):
                self._to_class()
        elif event.key == pygame.K_ESCAPE:
            self._to_align()

    def _ev_class(self, event):
        choice = self.class_menu.handle_event(event)
        if choice:
            self._to_confirm(choice)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._to_alloc(reroll=False)

    def _ev_confirm(self, event):
        choice = self.confirm_menu.handle_event(event)
        if choice == "keep":
            self.roster.append(self.candidate)
            self.app.state.save()
            self.message = f"{self.candidate.name} joins the roster."
            self._to_menu()
        elif choice == "discard":
            self.message = "The candidate departs, unremembered."
            self._to_menu()

    def _ev_inspect_list(self, event):
        choice = self.list_menu.handle_event(event)
        if choice is not None:
            self.view_index = choice
            self.state = "INSPECT_VIEW"
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._to_menu()

    def _ev_inspect_view(self, event):
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER
        ):
            self.state = "INSPECT_LIST"

    def _ev_delete_list(self, event):
        choice = self.list_menu.handle_event(event)
        if choice is not None:
            self.delete_index = choice
            self.state = "DELETE_CONFIRM"
            self.confirm_menu = Menu([
                MenuItem("No, keep them", "no"),
                MenuItem("Yes, dismiss them forever", "yes"),
            ])
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._to_menu()

    def _ev_delete_confirm(self, event):
        choice = self.confirm_menu.handle_event(event)
        if choice == "yes":
            gone = self.roster[self.delete_index]
            self.app.state.dismiss(gone)
            self.app.state.save()
            self.message = f"{gone.name} walks out of the gates."
            self._to_menu()
        elif choice == "no":
            self._to_menu()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._to_menu()

    # ---- update / draw ---------------------------------------------------
    def update(self, dt):
        if self.state == "NAME":
            self.name_input.update(dt)

    def draw(self, surf):
        tr = self.app.text
        draw_panel(surf, (30, 24, 580, 352), tr, "TRAINING GROUNDS")
        drawer = getattr(self, f"_draw_{self.state.lower()}", None)
        if drawer:
            drawer(surf, tr)

    def _draw_menu(self, surf, tr):
        tr.draw(surf, "The drillmaster looks you over.", (60, 54), palette.DIM)
        self.menu.draw(surf, tr, 80, 100, width=320)
        tr.draw(
            surf,
            f"Roster: {len(self.roster)}/{creation.ROSTER_CAP}",
            (60, 330), palette.TEXT,
        )
        if self.message:
            tr.draw(surf, self.message, (60, 300), palette.ACCENT)

    def _draw_name(self, surf, tr):
        tr.draw(surf, "Name the newcomer:", (60, 80), palette.TEXT)
        self.name_input.draw(surf, tr, 60, 80 + tr.ch * 2)
        if self.error:
            tr.draw(surf, self.error, (60, 200), palette.BAD)
        tr.draw(surf, "enter accepts · esc cancels", (60, 330), palette.DIM)

    def _draw_race(self, surf, tr):
        tr.draw(surf, f"{self.new_name}'s lineage:", (60, 60), palette.TEXT)
        self.race_menu.draw(surf, tr, 80, 100, width=160)
        race = data.races()[self.race_menu.selected.value]
        x = 300
        tr.draw(surf, race["name"], (x, 100), palette.BRIGHT)
        for i, stat in enumerate(STATS):
            tr.draw(surf, f"{STAT_LABELS[stat]:<10}{race['stats'][stat]:>2}",
                    (x, 130 + i * tr.ch), palette.TEXT)
        self._wrap(surf, tr, race["desc"], x, 130 + 7 * tr.ch, 28)

    def _draw_align(self, surf, tr):
        tr.draw(surf, f"{self.new_name}'s creed:", (60, 60), palette.TEXT)
        self.align_menu.draw(surf, tr, 80, 100, width=140)
        self._wrap(surf, tr, ALIGN_DESCS[self.align_menu.selected.value], 280, 100, 34)

    def _draw_alloc(self, surf, tr):
        tr.draw(surf, f"Distribute {self.new_name}'s gifts:", (60, 50), palette.TEXT)
        bonus_color = palette.GOOD if self.bonus_left == 0 else palette.ACCENT
        tr.draw(surf, f"Bonus points left: {self.bonus_left:>2}", (60, 50 + tr.ch), bonus_color)
        y = 120
        for i, stat in enumerate(STATS):
            row_y = y + i * (tr.ch + 4)
            selected = i == self.alloc_index
            if selected:
                pygame.draw.rect(
                    surf, palette.SELECT_BG, (66, row_y - 1, 200, tr.ch + 2)
                )
            val = self.alloc_stats[stat]
            raised = val > self.base_stats[stat]
            color = palette.BRIGHT if selected else palette.TEXT
            tr.draw(surf, f"{'► ' if selected else '  '}{STAT_LABELS[stat]:<10}", (70, row_y), color)
            tr.draw(surf, f"{val:>2}", (70 + 12 * tr.cw, row_y),
                    palette.GOOD if raised else color)
            if val >= STAT_CAP:
                tr.draw(surf, "MAX", (70 + 16 * tr.cw, row_y), palette.DIM)

        x = 320
        tr.draw(surf, "Qualifies for:", (x, 120), palette.DIM)
        eligible = creation.eligible_classes(self.alloc_stats, self.alignment)
        classes = data.classes()
        if eligible:
            for i, key in enumerate(eligible):
                color = palette.ACCENT if classes[key]["elite"] else palette.TEXT
                tr.draw(surf, classes[key]["name"], (x, 145 + i * tr.ch), color)
        else:
            tr.draw(surf, "(no class yet)", (x, 145), palette.BAD)
        hint = "enter continues" if self.bonus_left == 0 and eligible \
            else "spend every point"
        tr.draw(surf, f"◄ ► adjust · R rerolls · {hint} · esc back", (60, 340), palette.DIM)

    def _draw_class(self, surf, tr):
        tr.draw(surf, f"{self.new_name}'s calling:", (60, 60), palette.TEXT)
        self.class_menu.draw(surf, tr, 80, 100, width=180)
        cls = data.classes()[self.class_menu.selected.value]
        x = 320
        title_color = palette.ACCENT if cls["elite"] else palette.BRIGHT
        tr.draw(surf, cls["name"] + ("  (ELITE)" if cls["elite"] else ""), (x, 100), title_color)
        self._wrap(surf, tr, cls["desc"], x, 100 + tr.ch * 2, 28)

    def _draw_confirm(self, surf, tr):
        draw_character_sheet(surf, tr, self.candidate, 70, 60)
        self.confirm_menu.draw(surf, tr, 80, 270, width=300)

    def _draw_inspect_list(self, surf, tr):
        tr.draw(surf, "Inspect whom?", (60, 60), palette.TEXT)
        self.list_menu.draw(surf, tr, 80, 96, width=320, max_rows=10)
        tr.draw(surf, "esc backs out", (60, 340), palette.DIM)

    def _draw_inspect_view(self, surf, tr):
        draw_character_sheet(surf, tr, self.roster[self.view_index], 70, 60)
        tr.draw(surf, "esc backs out", (60, 340), palette.DIM)

    def _draw_delete_list(self, surf, tr):
        tr.draw(surf, "Dismiss whom? This cannot be undone.", (60, 60), palette.BAD)
        self.list_menu.draw(surf, tr, 80, 96, width=320, max_rows=10)
        tr.draw(surf, "esc backs out", (60, 340), palette.DIM)

    def _draw_delete_confirm(self, surf, tr):
        gone = self.roster[self.delete_index]
        tr.draw(surf, f"Dismiss {gone.name} forever?", (60, 80), palette.BAD)
        self.confirm_menu.draw(surf, tr, 80, 130, width=300)

    # ---- misc ------------------------------------------------------------
    def _wrap(self, surf, tr, text, x, y, width_chars):
        line = ""
        row = 0
        for word in text.split():
            if line and len(line) + 1 + len(word) > width_chars:
                tr.draw(surf, line, (x, y + row * tr.ch), palette.DIM)
                row += 1
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            tr.draw(surf, line, (x, y + row * tr.ch), palette.DIM)
