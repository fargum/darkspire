"""Camp — the in-maze menu: inspect, equip, use items, reorder."""

import random

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, TextInput, draw_panel
from game import data, items, spells
from scenes.common import draw_character_sheet, draw_party_bar


class CampScene(Scene):
    def on_enter(self):
        self.rng = random.Random()
        self.message = ""
        self.cast_lines = []
        self._to_menu()

    @property
    def gs(self):
        return self.app.state

    def _to_menu(self):
        self.state_ = "MENU"
        casters = [c for c in self.gs.party
                   if c.status in ("OK", "POISONED") and spells.is_caster(c)]
        sages = [c for c in self.gs.party
                 if c.cls == "sage" and c.status in ("OK", "POISONED")]
        self.null_zone = False
        if self.gs.maze:
            from game import maze as maze_mod
            level = maze_mod.load_level(self.gs.maze["depth"])
            self.null_zone = level.null_at(self.gs.maze["x"], self.gs.maze["y"])
        self.menu = Menu([
            MenuItem("Cast a spell", "cast",
                     enabled=bool(casters) and not self.null_zone,
                     note="null" if self.null_zone else None),
            MenuItem("Inspect a member", "inspect"),
            MenuItem("Equip gear", "equip"),
            MenuItem("Use an item", "use"),
            MenuItem("Identify (Sage)", "identify", enabled=bool(sages)),
            MenuItem("Swap marching order", "reorder", enabled=len(self.gs.party) > 1),
            MenuItem("Break camp", "back"),
        ])

    def _member_menu(self):
        classes = data.classes()
        return Menu([
            MenuItem(f"{c.name:<14} Lv{c.level:>2} {classes[c.cls]['name']}", i)
            for i, c in enumerate(self.gs.party)
        ])

    def _item_menu(self, char, usable_only=False):
        rows = []
        for i, entry in enumerate(char.inventory):
            it = items.item(entry["key"])
            if usable_only and "use" not in it:
                continue
            label = items.display_name(entry) + (
                "  [equipped]" if entry.get("equipped") else "")
            rows.append(MenuItem(label, i))
        rows.append(MenuItem("Never mind", "back"))
        return Menu(rows)

    def _spell_menu(self, char):
        return Menu([
            MenuItem(
                f"{d['name']:<10} L{d['level']} ({spells.points_left(char, key)})",
                key, enabled=spells.points_left(char, key) > 0,
            )
            for key, d in spells.known(char, ("camp", "both"))
        ] + [MenuItem("Never mind", "back")])

    def _do_cast(self, key, target_char):
        self.cast_lines = []
        if key == "malor":
            self.state_ = "MALOR_INPUT"
            self.malor_input = TextInput(max_len=6)
            return
        lines, signal = spells.cast_camp(self.caster, key, target_char,
                                         self.gs, self.rng)
        self.cast_lines = lines
        self.gs.save()
        if signal == "castle":
            self.app.pop_to("CastleScene")
        else:
            self._to_menu()

    def handle_event(self, event):
        esc = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if self.state_ == "MENU":
            choice = self.menu.handle_event(event)
            if choice in ("inspect", "equip", "use", "cast", "identify"):
                self.action = choice
                if choice == "cast":
                    chars = [c for c in self.gs.party
                             if c.status in ("OK", "POISONED")
                             and spells.is_caster(c)]
                    classes = data.classes()
                    self.cast_choices = chars
                    self.list_menu = Menu([
                        MenuItem(f"{c.name:<14} {classes[c.cls]['name']}", i)
                        for i, c in enumerate(chars)
                    ])
                else:
                    self.list_menu = self._member_menu()
                self.state_ = "WHO"
            elif choice == "reorder":
                self.list_menu = self._member_menu()
                self.swap_first = None
                self.state_ = "REORDER"
            elif choice == "back" or esc:
                self.gs.save()
                self.app.pop()
        elif self.state_ == "WHO":
            choice = self.list_menu.handle_event(event)
            if choice is not None:
                if self.action == "cast":
                    self.caster = self.cast_choices[choice]
                    self.spell_menu = self._spell_menu(self.caster)
                    self.state_ = "SPELL"
                    return
                self.member = self.gs.party[choice]
                if self.action == "inspect":
                    self.state_ = "SHEET"
                elif self.action == "identify":
                    self.item_menu = Menu([
                        MenuItem(items.display_name(e), i)
                        for i, e in enumerate(self.member.inventory)
                        if not e.get("identified", True)
                    ] + [MenuItem("Never mind", "back")])
                    self.state_ = "ID_ITEMS"
                else:
                    self.item_menu = self._item_menu(
                        self.member, usable_only=self.action == "use"
                    )
                    self.state_ = "ITEMS"
            elif esc:
                self._to_menu()
        elif self.state_ == "SPELL":
            choice = self.spell_menu.handle_event(event)
            if choice == "back" or esc:
                self._to_menu()
            elif choice is not None:
                self.pending_spell = choice
                if spells.sdef(choice)["target"] == "ally":
                    self.state_ = "SPELL_TARGET"
                    self.target_menu = Menu([
                        MenuItem(f"{c.name:<14} {c.hp}/{c.max_hp} {c.status}", i)
                        for i, c in enumerate(self.gs.party)
                    ])
                else:
                    self._do_cast(choice, None)
        elif self.state_ == "SPELL_TARGET":
            choice = self.target_menu.handle_event(event)
            if choice is not None:
                self._do_cast(self.pending_spell, self.gs.party[choice])
            elif esc:
                self.state_ = "SPELL"
        elif self.state_ == "MALOR_INPUT":
            result = self.malor_input.handle_event(event)
            if result:
                action, text = result
                if action == "cancel":
                    self._to_menu()
                else:
                    try:
                        x, y = (int(v) for v in text.split())
                    except ValueError:
                        self.message = "Give two numbers: east north (e.g. 10 4)."
                        return
                    from game import maze as maze_mod
                    level = maze_mod.load_level(self.gs.maze["depth"])
                    spells.spend(self.caster, "malor")
                    self.cast_lines = spells.malor_jump(
                        self.gs, x, level.height - 1 - y, self.rng)
                    self.gs.save()
                    self._to_menu()
        elif self.state_ == "ID_ITEMS":
            choice = self.item_menu.handle_event(event)
            if choice == "back" or esc:
                self._to_menu()
            elif choice is not None:
                sage = next(c for c in self.gs.party
                            if c.cls == "sage" and c.status in ("OK", "POISONED"))
                self.message = items.sage_identify(
                    sage, self.member.inventory[choice], self.rng)
                self.gs.save()
                self._to_menu()
        elif self.state_ == "SHEET":
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER
            ):
                self.state_ = "WHO"
        elif self.state_ == "ITEMS":
            choice = self.item_menu.handle_event(event)
            if choice == "back" or esc:
                self.state_ = "WHO"
            elif choice is not None:
                if self.action == "equip":
                    ok, msg = items.equip(self.member, choice)
                    self.message = msg
                    self.item_menu = self._item_menu(self.member)
                else:
                    self.message = items.use_item(
                        self.member, choice, self.gs.party, self.rng
                    )
                    self.gs.save()
                    self.state_ = "WHO"
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

    def update(self, dt):
        if self.state_ == "MALOR_INPUT":
            self.malor_input.update(dt)

    def draw(self, surf):
        tr = self.app.text
        draw_panel(surf, (30, 20, 580, 210), tr, "CAMP")
        if self.state_ == "MENU":
            tr.draw(surf, "The party huddles around a shuttered lantern.",
                    (60, 44), palette.DIM)
            self.menu.draw(surf, tr, 80, 66, width=280)
            y = 70
            colors = {"info": palette.TEXT, "good": palette.GOOD,
                      "bad": palette.BAD, "dim": palette.DIM}
            for kind, text in self.cast_lines[-6:]:
                tr.draw(surf, text, (350, y), colors[kind])
                y += tr.ch
        elif self.state_ == "SPELL":
            tr.draw(surf, f"{self.caster.name}'s incantations:", (60, 44),
                    palette.TEXT)
            self.spell_menu.draw(surf, tr, 80, 70, width=300, max_rows=7)
        elif self.state_ == "SPELL_TARGET":
            tr.draw(surf, "Upon whom?", (60, 44), palette.TEXT)
            self.target_menu.draw(surf, tr, 80, 70, width=340)
        elif self.state_ == "MALOR_INPUT":
            tr.draw(surf, "MALOR — speak the destination: east north",
                    (60, 60), palette.TEXT)
            tr.draw(surf, "(as DUMAPIC counts them; 0-19 each)", (60, 60 + tr.ch),
                    palette.DIM)
            self.malor_input.draw(surf, tr, 60, 120)
        elif self.state_ == "ID_ITEMS":
            tr.draw(surf, f"{self.member.name}'s unidentified finds:", (60, 44),
                    palette.TEXT)
            self.item_menu.draw(surf, tr, 80, 70, width=300, max_rows=7)
        elif self.state_ == "WHO":
            prompts = {"inspect": "Look over whom?", "equip": "Outfit whom?",
                       "use": "Whose pack?", "cast": "Who casts?",
                       "identify": "Whose finds?"}
            tr.draw(surf, prompts[self.action], (60, 44), palette.TEXT)
            self.list_menu.draw(surf, tr, 80, 70, width=330)
        elif self.state_ == "SHEET":
            draw_character_sheet(surf, tr, self.member, 60, 44)
        elif self.state_ == "ITEMS":
            tr.draw(surf, f"{self.member.name} — AC {self.member.ac}", (60, 44),
                    palette.TEXT)
            self.item_menu.draw(surf, tr, 80, 70, width=330, max_rows=7)
        elif self.state_ == "REORDER":
            prompt = "Swap whom?" if self.swap_first is None else \
                f"Swap {self.gs.party[self.swap_first].name} with whom?"
            tr.draw(surf, prompt, (60, 44), palette.TEXT)
            self.list_menu.draw(surf, tr, 80, 70, width=330)
        if self.message:
            tr.draw(surf, self.message, (330, 44), palette.ACCENT)
        draw_party_bar(surf, tr, self.gs.party)
