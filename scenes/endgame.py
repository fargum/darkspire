"""The Everflame returns — victory sequence."""

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import draw_panel
from scenes.common import draw_party_bar

XP_AWARD = 50000
GOLD_AWARD = 25000

STORY = [
    "White fire folds around the party --",
    "-- and opens onto the castle courtyard at dawn.",
    "",
    "Bells. Every bell in Aldenmoor, all at once.",
    "",
    "The Wardlantern is carried through weeping crowds",
    "to the ward-brazier at the city's heart. The",
    "Everflame leaps home, and the great wards flare",
    "so bright the stars flinch.",
    "",
    "The deep things stop climbing. The town is safe.",
    "",
    "By decree of Aldenmoor, you are named",
]


class EndgameScene(Scene):
    def on_enter(self):
        import audio
        audio.play("victory")
        gs = self.app.state
        self.first_time = not gs.quest.get("quest_complete")
        if self.first_time:
            gs.quest["quest_complete"] = True
            self.survivors = [c for c in gs.party
                              if c.status in ("OK", "POISONED")]
            for c in self.survivors:
                c.xp += XP_AWARD
                c.gold += GOLD_AWARD
        gs.maze = None
        gs.save()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE
        ):
            self.app.pop_to("CastleScene")

    def draw(self, surf):
        tr = self.app.text
        cx = surf.get_width() // 2
        draw_panel(surf, (60, 16, 520, 300), tr, "THE EVERFLAME RETURNS")
        y = 36
        for line in STORY:
            tr.draw_center(surf, line, cx, y,
                           palette.TEXT if line else palette.TEXT)
            y += tr.ch
        tr.draw_center(surf, "WARD-BEARERS OF ALDENMOOR", cx, y + 2,
                       palette.ACCENT, tr.big)
        y += 40
        tr.draw_center(surf,
                       f"Each hero is granted {XP_AWARD} XP and "
                       f"{GOLD_AWARD} gold.", cx, y, palette.GOOD)
        tr.draw_center(surf, "enter returns to the castle", cx, y + tr.ch + 4,
                       palette.DIM)
        draw_party_bar(surf, tr, self.app.state.party)
