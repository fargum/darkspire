"""Combat scene — declaration, resolution, and aftermath."""

import random

import pygame

import audio
from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, draw_panel
from game import chests, combat, items, spells
from render.portraits import portrait
from scenes.common import draw_party_bar

KIND_COLORS = {
    "info": palette.TEXT,
    "good": palette.GOOD,
    "bad": palette.BAD,
    "dim": palette.DIM,
}
LOG_LINES = 11


class CombatScene(Scene):
    def __init__(self, app, groups=None, depth=1, encounter_id=None,
                 grant=None, victory_text=None):
        super().__init__(app)
        self.rng = random.Random()
        self.groups = groups
        self.depth = depth
        self.encounter_id = encounter_id
        self.grant = grant
        self.victory_text = victory_text

    def on_enter(self):
        gs = self.app.state
        if self.groups is None:
            self.groups = combat.build_encounter(self.depth, self.rng)
        self.fight = combat.Combat(gs.party, self.groups, self.rng)
        if gs.maze and gs.maze.get("maporfic"):
            self.fight.party_ac_bonus += gs.maze["maporfic"]
        if gs.quest.get("seraph_blessing"):
            self.fight.party_ac_bonus += 1
        if gs.maze:
            from game import maze as maze_mod
            level = maze_mod.load_level(gs.maze["depth"])
            if level.null_at(gs.maze["x"], gs.maze["y"]):
                self.fight.null = True
        self.chest = None
        self.log = []
        self.say("dim", "You are beset!")
        if self.fight.surprise == "party":
            self._resolve({})       # ambush round happens before you can act
        else:
            self._start_declaration()

    def say(self, kind, text):
        self.log.append((text, KIND_COLORS[kind]))
        del self.log[:-60]

    # ---- declaration flow ------------------------------------------------
    def _actors(self):
        return [
            i for i, c in enumerate(self.app.state.party)
            if c.status in combat.ACTIVE
        ]

    def _start_declaration(self):
        self.actions = {}
        self.declare_queue = self._actors()
        if not self.declare_queue:
            self._resolve({})
            return
        self.state_ = "DECLARE"
        self._build_action_menu()

    def _current_index(self):
        return self.declare_queue[0]

    def _build_action_menu(self):
        i = self._current_index()
        char = self.app.state.party[i]
        leader = i == self._actors()[0]
        usable = any("use" in items.item(e["key"]) for e in char.inventory)
        castable = [
            (key, d) for key, d in spells.known(char, ("combat", "both"))
            if spells.points_left(char, key) > 0
        ]
        rows = [
            MenuItem("Fight", "fight", enabled=i < combat.FRONT_ROWS),
            MenuItem("Parry", "parry"),
        ]
        if spells.is_caster(char):
            if self.fight.null:
                rows.append(MenuItem("Cast a spell", "cast", enabled=False,
                                     note="null"))
            else:
                rows.append(MenuItem("Cast a spell", "cast",
                                     enabled=bool(castable)))
        if char.cls in combat.STEALTHY:
            rows.append(MenuItem("Hide", "hide",
                                 enabled=id(char) not in self.fight.hidden))
        rows.append(MenuItem("Use an item", "use", enabled=usable))
        if leader:
            rows.append(MenuItem("Run!", "run"))
        self.menu = Menu(rows)

    def _advance_declaration(self):
        self.declare_queue.pop(0)
        if self.declare_queue:
            self._build_action_menu()
        else:
            self._resolve(self.actions)

    def _resolve(self, actions):
        lines = self.fight.resolve(actions)
        for kind, text in lines:
            self.say(kind, text)
        texts = " ".join(t for _, t in lines)
        if "casts" in texts:
            audio.play("spell", 0.6)
        if "slain" in texts or "destroyed" in texts:
            audio.play("slain", 0.7)
        elif "hits" in texts or "takes" in texts:
            audio.play("hit", 0.6)
        if self.fight.result == "victory":
            for kind, text in self.fight.distribute_rewards():
                self.say(kind, text)
            if self.encounter_id:
                self.app.state.quest[f"enc_{self.encounter_id}"] = True
            if self.grant:
                self.app.state.quest[self.grant] = True
            if self.victory_text:
                self.say("good", self.victory_text)
            self.encounter_id = self.grant = self.victory_text = None
            self.app.state.save()
            audio.play("victory", 0.7)
            if self.chest is None:      # a Screamer refight keeps the old chest
                self.chest = chests.maybe_chest(self.depth, self.rng)
            if self.chest and not self.chest["open"]:
                self.say("good", "Among the remains: a heavy chest!")
                self._chest_who()
            else:
                self.state_ = "VICTORY"
        elif self.fight.result == "defeat":
            audio.play("defeat")
            self.state_ = "DEFEAT"
        elif self.fight.result == "fled":
            self.app.state.save()
            self.state_ = "FLED"
        else:
            self.state_ = "ROUND_DONE"

    # ---- chest flow ------------------------------------------------------
    def _chest_who(self):
        self.state_ = "CHEST_WHO"
        self.chest_menu = Menu([
            MenuItem(c.name, i)
            for i, c in enumerate(self.app.state.party)
            if c.status in combat.ACTIVE
        ])

    def _chest_main(self):
        self.state_ = "CHEST_MENU"
        worker = self.worker
        can_calfo = any(
            key == "calfo" and spells.points_left(worker, key) > 0
            for key, _ in spells.known(worker, ("chest",))
        )
        self.chest_menu = Menu([
            MenuItem("Open it", "open"),
            MenuItem("Inspect for traps", "inspect"),
            MenuItem("Cast CALFO", "calfo", enabled=can_calfo),
            MenuItem("Disarm...", "disarm"),
            MenuItem("Leave it be", "leave"),
        ])

    def _chest_finish_open(self):
        audio.play("gold")
        for kind, text in chests.open_chest(self.chest, self.app.state.party,
                                            self.rng):
            self.say(kind, text)
        self.app.state.save()
        self.state_ = "VICTORY"

    def _chest_trigger(self):
        audio.play("trap")
        lines, summon = chests.trigger(self.chest, self.app.state.party,
                                       self.worker, self.rng)
        for kind, text in lines:
            self.say(kind, text)
        self.app.state.save()
        if not any(c.status in combat.ACTIVE for c in self.app.state.party):
            self.state_ = "DEFEAT"
        elif summon:
            self.groups = combat.build_encounter(self.depth, self.rng)
            self.fight = combat.Combat(self.app.state.party, self.groups,
                                       self.rng)
            self.fight.surprise = None
            self.say("bad", "Drawn by the shriek, more foes arrive!")
            self._start_declaration()
        else:
            self._chest_finish_open()

    # ---- events ----------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN and self.state_ != "DECLARE":
            return
        if self.state_ == "DECLARE":
            choice = self.menu.handle_event(event)
            if choice is None:
                return
            i = self._current_index()
            if choice == "fight":
                reach = self.fight.reachable_groups()
                if len(reach) > 1:
                    self.state_ = "TARGET"
                    self.target_menu = Menu([
                        MenuItem(self.fight.group_label(g),
                                 self.fight.groups.index(g))
                        for g in reach
                    ])
                    return
                self.actions[i] = ("fight", self.fight.groups.index(reach[0]))
                self._advance_declaration()
            elif choice == "use":
                char = self.app.state.party[i]
                self.state_ = "PICK_ITEM"
                self.item_menu = Menu([
                    MenuItem(items.display_name(e), j)
                    for j, e in enumerate(char.inventory)
                    if "use" in items.item(e["key"])
                ] + [MenuItem("Never mind", "back")])
            elif choice == "cast":
                char = self.app.state.party[i]
                self.state_ = "PICK_SPELL"
                self.spell_menu = Menu([
                    MenuItem(
                        f"{d['name']:<10} L{d['level']} "
                        f"({spells.points_left(char, key)})",
                        key,
                        enabled=spells.points_left(char, key) > 0,
                    )
                    for key, d in spells.known(char, ("combat", "both"))
                ] + [MenuItem("Never mind", "back")])
            elif choice in ("parry", "hide", "run"):
                self.actions[i] = (choice,)
                self._advance_declaration()
        elif self.state_ == "TARGET":
            choice = self.target_menu.handle_event(event)
            if choice is not None:
                self.actions[self._current_index()] = ("fight", choice)
                self.state_ = "DECLARE"
                self._advance_declaration()
            elif event.key == pygame.K_ESCAPE:
                self.state_ = "DECLARE"
        elif self.state_ == "PICK_ITEM":
            choice = self.item_menu.handle_event(event)
            if choice == "back" or event.key == pygame.K_ESCAPE:
                self.state_ = "DECLARE"
            elif choice is not None:
                self.actions[self._current_index()] = ("use", choice)
                self.state_ = "DECLARE"
                self._advance_declaration()
        elif self.state_ == "PICK_SPELL":
            choice = self.spell_menu.handle_event(event)
            if choice == "back" or event.key == pygame.K_ESCAPE:
                self.state_ = "DECLARE"
            elif choice is not None:
                self.pending_spell = choice
                d = spells.sdef(choice)
                if d["target"] == "group":
                    reach = self.fight.alive_groups()
                    if len(reach) > 1:
                        self.state_ = "SPELL_TARGET"
                        self.target_menu = Menu([
                            MenuItem(self.fight.group_label(g),
                                     self.fight.groups.index(g))
                            for g in reach
                        ])
                        return
                    target = self.fight.groups.index(reach[0])
                elif d["target"] == "ally":
                    self.state_ = "SPELL_ALLY"
                    self.target_menu = Menu([
                        MenuItem(f"{c.name} ({c.hp}/{c.max_hp})", j)
                        for j, c in enumerate(self.app.state.party)
                        if c.status in combat.ACTIVE
                    ])
                    return
                else:
                    target = None
                self.actions[self._current_index()] = (
                    "cast", self.pending_spell, target)
                self.state_ = "DECLARE"
                self._advance_declaration()
        elif self.state_ in ("SPELL_TARGET", "SPELL_ALLY"):
            choice = self.target_menu.handle_event(event)
            if choice is not None:
                self.actions[self._current_index()] = (
                    "cast", self.pending_spell, choice)
                self.state_ = "DECLARE"
                self._advance_declaration()
            elif event.key == pygame.K_ESCAPE:
                self.state_ = "PICK_SPELL"
        elif self.state_ == "CHEST_WHO":
            choice = self.chest_menu.handle_event(event)
            if choice is not None:
                self.worker = self.app.state.party[choice]
                self._chest_main()
        elif self.state_ == "CHEST_MENU":
            choice = self.chest_menu.handle_event(event)
            if choice == "open":
                if self.chest["trap"]:
                    self._chest_trigger()
                else:
                    self._chest_finish_open()
            elif choice == "inspect":
                self.say("dim", chests.inspect(self.worker, self.chest, self.rng))
            elif choice == "calfo":
                self.say("info", chests.calfo(self.worker, self.chest, self.rng))
                self._chest_main()   # refresh remaining CALFO points
            elif choice == "disarm":
                self.state_ = "CHEST_DISARM"
                self.chest_menu = Menu(
                    [MenuItem(t, t) for t in chests.TRAPS]
                    + [MenuItem("Never mind", "back")]
                )
            elif choice == "leave":
                self.say("dim", "You leave the chest to the dark.")
                self.state_ = "VICTORY"
        elif self.state_ == "CHEST_DISARM":
            choice = self.chest_menu.handle_event(event)
            if choice == "back" or event.key == pygame.K_ESCAPE:
                self._chest_main()
            elif choice is not None:
                outcome = chests.disarm(self.worker, self.chest, choice, self.rng)
                if outcome == "triggered":
                    self._chest_trigger()
                else:
                    if outcome == "disarmed":
                        self.say("good", "Click. The trap is dead.")
                    else:
                        self.say("dim", "There was no trap at all.")
                    self._chest_finish_open()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.state_ == "ROUND_DONE":
                self._start_declaration()
            elif self.state_ in ("VICTORY", "FLED"):
                self.app.pop()
            elif self.state_ == "DEFEAT":
                gs = self.app.state
                for c in gs.party:
                    c.gold //= 2
                gs.maze = None
                gs.save()
                self.app.pop_to("CastleScene")

    # ---- draw ------------------------------------------------------------
    def draw(self, surf):
        tr = self.app.text
        panel = pygame.Rect(12, 12, 396, 150)
        draw_panel(surf, panel, tr, "AMBUSH" if self.fight.surprise == "party"
                   else "COMBAT")
        y = panel.y + 14
        letters = "ABCD"
        for slot, group in enumerate(self.fight.alive_groups()):
            sprite = portrait(group["key"], 30)
            surf.blit(sprite, (panel.x + 14, y))
            reach = "" if slot < combat.MELEE_REACH else "  (out of reach)"
            tr.draw(surf, f"{letters[slot]}) {self.fight.group_label(group)}{reach}",
                    (panel.x + 56, y + 7), palette.TEXT)
            y += 36

        logp = pygame.Rect(416, 12, 212, 240)
        draw_panel(surf, logp, tr, "BATTLE")
        ly = logp.y + 16
        for text, color in self.log[-LOG_LINES:]:
            for line in _wrap(text, 25):
                tr.draw(surf, line, (logp.x + 10, ly), color)
                ly += tr.ch
                if ly > logp.bottom - tr.ch:
                    break
            if ly > logp.bottom - tr.ch:
                break

        strip = pygame.Rect(12, 172, 396, 96)
        current = None
        if self.state_ == "DECLARE":
            current = self._current_index()
            char = self.app.state.party[current]
            draw_panel(surf, strip, tr, char.name.upper())
            self.menu.draw(surf, tr, strip.x + 24, strip.y + 10, width=160,
                           max_rows=4)
        elif self.state_ == "TARGET":
            current = self._current_index()
            draw_panel(surf, strip, tr, "STRIKE AT")
            self.target_menu.draw(surf, tr, strip.x + 24, strip.y + 14, width=280)
        elif self.state_ == "PICK_ITEM":
            current = self._current_index()
            draw_panel(surf, strip, tr, "FROM THE PACK")
            self.item_menu.draw(surf, tr, strip.x + 24, strip.y + 14, width=280,
                                max_rows=4)
        elif self.state_ == "PICK_SPELL":
            current = self._current_index()
            draw_panel(surf, strip, tr, "INCANTATIONS")
            self.spell_menu.draw(surf, tr, strip.x + 24, strip.y + 10, width=280,
                                 max_rows=4)
        elif self.state_ in ("SPELL_TARGET", "SPELL_ALLY"):
            current = self._current_index()
            title = "UPON WHOM" if self.state_ == "SPELL_ALLY" else "AT WHICH FOES"
            draw_panel(surf, strip, tr, title)
            self.target_menu.draw(surf, tr, strip.x + 24, strip.y + 10, width=280,
                                  max_rows=4)
        elif self.state_ == "CHEST_WHO":
            draw_panel(surf, strip, tr, "WHO WORKS THE CHEST?")
            self.chest_menu.draw(surf, tr, strip.x + 24, strip.y + 10, width=220,
                                 max_rows=4)
        elif self.state_ in ("CHEST_MENU", "CHEST_DISARM"):
            title = "THE CHEST" if self.state_ == "CHEST_MENU" else "NAME THE TRAP"
            draw_panel(surf, strip, tr, title)
            self.chest_menu.draw(surf, tr, strip.x + 24, strip.y + 10, width=240,
                                 max_rows=4)
        else:
            draw_panel(surf, strip, tr)
            prompts = {
                "ROUND_DONE": "enter — next round",
                "VICTORY": "VICTORY!  enter continues",
                "FLED": "You got away.  enter continues",
                "DEFEAT": "The party has fallen. Days later, scavengers drag "
                          "your bodies to the temple... enter",
            }
            color = palette.GOOD if self.state_ == "VICTORY" else (
                palette.BAD if self.state_ == "DEFEAT" else palette.TEXT)
            for j, line in enumerate(_wrap(prompts[self.state_], 48)):
                tr.draw(surf, line, (strip.x + 24, strip.y + 20 + j * tr.ch), color)

        draw_party_bar(surf, tr, self.app.state.party, highlight=current)


def _wrap(text, width):
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
