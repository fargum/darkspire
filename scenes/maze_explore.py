"""Exploring the Darkspire — movement, special squares, encounters."""

import random

import pygame

import audio
from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, TextInput, draw_panel
from game import dice, maze
from render import wireframe
from scenes.common import draw_party_bar

VIEW = pygame.Rect(12, 12, 396, 240)
ENCOUNTER_CHANCE = 0.08
LOG_LINES = 11
ACTIVE = ("OK", "POISONED")


class MazeScene(Scene):
    def on_enter(self):
        self.rng = random.Random()
        gs = self.app.state
        if not gs.maze:
            level = maze.load_level(1)
            gs.maze = {
                "depth": 1,
                "x": level.start["x"],
                "y": level.start["y"],
                "facing": level.start["facing"],
            }
            gs.save()
        self.level = maze.load_level(gs.maze["depth"])
        self.log = []
        self.overlay = None      # (kind, widget, data)
        self.say(f"You stand in {self.level.name}.")

    def on_resume(self):
        self.app.state.save()

    @property
    def pos(self):
        return self.app.state.maze

    @property
    def quest(self):
        return self.app.state.quest

    def say(self, text, color=palette.TEXT):
        self.log.append((text, color))
        del self.log[:-40]

    def _load_depth(self, depth):
        self.pos["depth"] = depth
        self.level = maze.load_level(depth)
        self.say(f"— {self.level.name} —", palette.ACCENT)
        if depth >= 9 and not self.quest.get("reached_l9"):
            self.quest["reached_l9"] = True

    # ---- movement --------------------------------------------------------
    def _forward(self):
        p = self.pos
        edge = self.level.edge(p["x"], p["y"], p["facing"])
        if edge == maze.WALL:
            self.say("*oof* You walk into stone.", palette.BAD)
            audio.play("bump")
            return
        if edge == maze.DOOR:
            self.say("You push through the door.", palette.DIM)
            audio.play("door")
        else:
            audio.play("step", 0.4)
        p["x"], p["y"] = maze.step(p["x"], p["y"], p["facing"])
        self._poison_tick()
        if p.get("light", 0) > 0:
            p["light"] -= 1
            if p["light"] == 0:
                self.say("Your light gutters out.", palette.DIM)
        self.app.state.save()
        if self._party_down():
            return
        self._arrive()

    def _poison_tick(self):
        for c in self.app.state.party:
            if c.status == "POISONED":
                c.hp -= 1
                if c.hp <= 0:
                    c.hp = 0
                    c.status = "DEAD"
                    self.say(f"{c.name} succumbs to the poison!", palette.BAD)

    def _party_down(self):
        gs = self.app.state
        if any(c.status in ACTIVE for c in gs.party):
            return False
        self.say("The last of the party falls...", palette.BAD)
        for c in gs.party:
            c.gold //= 2
        gs.maze = None
        gs.save()
        self.app.pop_to("CastleScene")
        return True

    # ---- arrival & special squares ---------------------------------------
    def _arrive(self, hops=0):
        p = self.pos
        special = self.level.special_at(p["x"], p["y"])
        if special:
            handler = getattr(self, f"_sp_{special['type']}", None)
            if handler:
                handler(special, hops)
        elif self.rng.random() < ENCOUNTER_CHANCE:
            self._random_encounter()

    def _random_encounter(self):
        self.say("Something stirs in the shadows!", palette.BAD)
        from scenes.combat import CombatScene
        self.app.push(CombatScene(self.app, depth=self.level.depth))

    def _sp_message(self, special, hops):
        self.say(special["text"], palette.ACCENT)

    def _sp_stairs_up(self, special, hops):
        if self.level.depth == 1:
            self.say("Stairs climb toward daylight.", palette.ACCENT)
            self.overlay = ("menu", Menu([
                MenuItem("Climb to the castle", "leave"),
                MenuItem("Stay in the dark", "stay"),
            ]), {"title": "THE ENTRANCE", "action": "exit"})
        else:
            self.overlay = ("menu", Menu([
                MenuItem(f"Climb to level {self.level.depth - 1}", "up"),
                MenuItem("Stay here", "stay"),
            ]), {"title": "STAIRS UP", "action": "up"})

    def _sp_stairs_down(self, special, hops):
        req = special.get("requires")
        if req and not self.quest.get(req):
            self.say(special["locked_text"], palette.BAD)
            return
        if not maze.level_exists(self.level.depth + 1):
            self.say("Stairs descend — but that dark is not yet delved.",
                     palette.DIM)
            return
        if req:
            self.say("The seal yields to what you carry.", palette.GOOD)
        self.overlay = ("menu", Menu([
            MenuItem(f"Descend to level {self.level.depth + 1}", "down"),
            MenuItem("Stay here", "stay"),
        ]), {"title": "STAIRS DOWN", "action": "down"})

    def _sp_spinner(self, special, hops):
        self.pos["facing"] = self.rng.randrange(4)   # silently. Good luck.
        self.app.state.save()

    def _sp_teleporter(self, special, hops):
        self.pos["x"], self.pos["y"] = special["to"]  # silent, as tradition demands
        self.app.state.save()
        if hops < 3:
            self._arrive(hops + 1)

    def _sp_chute(self, special, hops):
        audio.play("trap")
        self.say(special.get("text", "The floor gives way!"), palette.BAD)
        for c in self.app.state.party:
            if c.status in ACTIVE:
                c.hp = max(1, c.hp - dice.roll(self.rng, "1d6"))
        self._load_depth(special["to_depth"])
        self.app.state.save()
        if hops < 3:
            self._arrive(hops + 1)

    def _sp_pit(self, special, hops):
        audio.play("trap")
        self.say(special["text"], palette.BAD)
        for c in self.app.state.party:
            if c.status in ACTIVE:
                c.hp -= dice.roll(self.rng, special["dice"])
                if c.hp <= 0:
                    c.hp = 0
                    c.status = "DEAD"
                    self.say(f"{c.name} is slain!", palette.BAD)
        self.app.state.save()
        self._party_down()

    def _sp_elevator(self, special, hops):
        req = special.get("requires")
        if req and not self.quest.get(req):
            self.say(special.get("locked_text", "The cage is chained shut."),
                     palette.BAD)
            return
        floors = special["floors"]
        self.say("The elevator cage rattles open.", palette.ACCENT)
        self.overlay = ("menu", Menu([
            MenuItem(f"Level {f}", f, enabled=f != self.level.depth)
            for f in floors
        ] + [MenuItem("Step back out", "stay")]),
            {"title": "THE ELEVATOR", "action": "elevator"})

    def _sp_gate(self, special, hops):
        if self.quest.get(special["requires"]):
            flag = f"gate_open_{self.level.depth}_{self.pos['x']}_{self.pos['y']}"
            if not self.quest.get(flag):
                self.quest[flag] = True
                self.say("The way opens before you.", palette.GOOD)
            return
        self.say(special["text"], palette.BAD)
        back = maze.turn(self.pos["facing"], 2)
        self.pos["x"], self.pos["y"] = maze.step(self.pos["x"], self.pos["y"], back)
        self.app.state.save()

    def _sp_quest_item(self, special, hops):
        if not self.quest.get(special["grant"]):
            self.quest[special["grant"]] = True
            self.say(special["text"], palette.GOOD)
            audio.play("levelup")
            self.app.state.save()

    def _sp_riddle(self, special, hops):
        if self.quest.get(special["grant"]):
            return
        self.say(special["text"], palette.ACCENT)
        self.overlay = ("input", TextInput(max_len=20),
                        {"title": "ANSWER THE GHOST", "special": special})

    def _sp_font(self, special, hops):
        audio.play("heal")
        self.say(special["text"], palette.ACCENT)
        healed = 0
        for c in self.app.state.party:
            if c.status in ACTIVE and c.hp < c.max_hp:
                gain = min(dice.roll(self.rng, special["dice"]),
                           c.max_hp - c.hp)
                c.hp += gain
                healed += gain
        if healed:
            self.say(f"The waters mend {healed} HP of wounds.", palette.GOOD)
        self.app.state.save()

    def _sp_portal(self, special, hops):
        if not self.quest.get(special["requires"]):
            self.say(special["text"], palette.DIM)
            return
        self.say("The portal blazes white — it knows the Everflame!",
                 palette.GOOD)
        self.overlay = ("menu", Menu([
            MenuItem("Carry the flame home", "home"),
            MenuItem("Not yet", "stay"),
        ]), {"title": "THE WAY HOME", "action": "portal"})

    def _sp_encounter(self, special, hops):
        if special.get("once") and self.quest.get(f"enc_{special['id']}"):
            return
        self.say(special["text"], palette.BAD)
        from game import combat as combat_mod
        groups = []
        for key, count_dice in special["groups"]:
            count = dice.roll(self.rng, count_dice)
            groups.append({
                "key": key,
                "members": [
                    {"hp": dice.roll(self.rng, combat_mod.mdef(key)["hp"]),
                     "status": "OK"}
                    for _ in range(count)
                ],
            })
        from scenes.combat import CombatScene
        self.app.push(CombatScene(
            self.app, groups=groups, depth=self.level.depth,
            encounter_id=special.get("id"),
            grant=special.get("grant"),
            victory_text=special.get("victory_text"),
        ))

    # ---- events ----------------------------------------------------------
    def handle_event(self, event):
        if self.overlay is not None:
            self._overlay_event(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        p = self.pos
        if event.key in (pygame.K_UP, pygame.K_w):
            self._forward()
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            p["facing"] = maze.turn(p["facing"], -1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            p["facing"] = maze.turn(p["facing"], 1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            p["facing"] = maze.turn(p["facing"], 2)
        elif event.key in (pygame.K_c, pygame.K_ESCAPE):
            from scenes.camp import CampScene
            self.app.push(CampScene(self.app))

    def _overlay_event(self, event):
        kind, widget, data = self.overlay
        esc = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if kind == "menu":
            choice = widget.handle_event(event)
            if choice in ("stay", None) and not esc:
                if choice == "stay":
                    self.overlay = None
                return
            if esc:
                self.overlay = None
                return
            self.overlay = None
            gs = self.app.state
            if data["action"] == "exit" and choice == "leave":
                gs.maze = None
                gs.save()
                self.app.pop()
            elif data["action"] == "up" and choice == "up":
                audio.play("stairs")
                self._load_depth(self.level.depth - 1)
                gs.save()
            elif data["action"] == "down" and choice == "down":
                audio.play("stairs")
                self._load_depth(self.level.depth + 1)
                gs.save()
            elif data["action"] == "elevator" and isinstance(choice, int):
                self._load_depth(choice)
                self.say("Chains scream. The cage lurches.", palette.DIM)
                gs.save()
            elif data["action"] == "portal" and choice == "home":
                from scenes.endgame import EndgameScene
                self.app.push(EndgameScene(self.app))
        elif kind == "input":
            result = widget.handle_event(event)
            if not result:
                return
            action, text = result
            self.overlay = None
            if action == "done":
                special = data["special"]
                if text.strip().lower() == special["answer"]:
                    self.quest[special["grant"]] = True
                    self.say(special["success"], palette.GOOD)
                    self.app.state.save()
                else:
                    self.say("The ghost sighs and fades a little more.",
                             palette.DIM)

    # ---- draw ------------------------------------------------------------
    def update(self, dt):
        if self.overlay and self.overlay[0] == "input":
            self.overlay[1].update(dt)

    def draw(self, surf):
        tr = self.app.text
        p = self.pos
        if self.level.dark_at(p["x"], p["y"]):
            light = 1
        elif p.get("light", 0) != 0:
            light = 4
        else:
            light = 2
        wireframe.draw(surf, VIEW, self.level, p["x"], p["y"], p["facing"],
                       light=light,
                       reveal_illusions=bool(self.quest.get("void_lens")))

        panel = pygame.Rect(416, 12, 212, 240)
        draw_panel(surf, panel, tr, self.level.name.upper())
        y = panel.y + 18
        for text, color in self.log[-LOG_LINES:]:
            for line in self._wrap(text, 25):
                tr.draw(surf, line, (panel.x + 10, y), color)
                y += tr.ch
                if y > panel.bottom - tr.ch:
                    break
            if y > panel.bottom - tr.ch:
                break

        if self.overlay is not None:
            kind, widget, data = self.overlay
            box = pygame.Rect(120, 110, 300, 110)
            draw_panel(surf, box, tr, data["title"])
            if kind == "menu":
                widget.draw(surf, tr, box.x + 20, box.y + 20, width=250)
            else:
                widget.draw(surf, tr, box.x + 20, box.y + 40)
        else:
            tr.draw(surf, "↑ forward · ◄ ► turn · ↓ about-face · C camp",
                    (12, 262), palette.DIM)
        draw_party_bar(surf, tr, self.app.state.party)

    @staticmethod
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
