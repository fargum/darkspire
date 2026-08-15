"""Drawing helpers shared across scenes."""

import pygame

from engine import palette
from game import data
from game.character import STATS, STAT_LABELS, ALIGNMENT_LABELS


def draw_party_bar(surf, tr, party, y=None, highlight=None):
    """Six-row party status table anchored at the bottom of the screen."""
    if y is None:
        y = surf.get_height() - (len(party) + 2) * tr.ch - 6
    header = f"  {'NAME':<14} {'CLASS':<13} {'AC':>3} {'HP':>9}  {'STATUS':<9} {'GOLD':>6}"
    tr.draw(surf, header, (16, y), palette.DIM)
    classes = data.classes()
    for i, c in enumerate(party):
        row_y = y + (i + 1) * tr.ch
        if highlight == i:
            pygame.draw.rect(
                surf, palette.SELECT_BG,
                (12, row_y - 1, surf.get_width() - 24, tr.ch + 1),
            )
        status_color = palette.GOOD if c.status == "OK" else palette.BAD
        line = (
            f"{i + 1} {c.name:<14} {classes[c.cls]['name']:<13} {c.ac:>3} "
            f"{c.hp:>4}/{c.max_hp:<4}"
        )
        tr.draw(surf, line, (16, row_y), palette.TEXT)
        tr.draw(surf, f"{c.status:<9}", (16 + 51 * tr.cw, row_y), status_color)
        tr.draw(surf, f"{c.gold:>6}", (16 + 61 * tr.cw, row_y), palette.ACCENT)


def draw_character_sheet(surf, tr, char, x, y):
    """Full character sheet, top-left anchored at (x, y)."""
    race = data.races()[char.race]["name"]
    cls = data.classes()[char.cls]["name"]
    align = ALIGNMENT_LABELS[char.alignment]

    tr.draw(surf, char.name, (x, y), palette.BRIGHT)
    tr.draw(surf, f"Level {char.level} {align} {race} {cls}", (x, y + tr.ch), palette.TEXT)

    sy = y + tr.ch * 3
    for i, stat in enumerate(STATS):
        tr.draw(surf, f"{STAT_LABELS[stat]:<10}", (x, sy + i * tr.ch), palette.DIM)
        tr.draw(surf, f"{char.stats[stat]:>2}", (x + 10 * tr.cw, sy + i * tr.ch), palette.TEXT)

    cx = x + 16 * tr.cw
    hp_color = palette.GOOD if char.hp >= char.max_hp else (
        palette.TEXT if char.hp > char.max_hp // 3 else palette.BAD
    )
    tr.draw(surf, f"HP     {char.hp}/{char.max_hp}", (cx, sy), hp_color)
    tr.draw(surf, f"AC     {char.ac}", (cx, sy + tr.ch), palette.TEXT)
    tr.draw(surf, f"XP     {char.xp}", (cx, sy + tr.ch * 2), palette.TEXT)
    tr.draw(surf, f"Gold   {char.gold}", (cx, sy + tr.ch * 3), palette.ACCENT)
    status_color = palette.GOOD if char.status == "OK" else palette.BAD
    tr.draw(surf, f"Status {char.status}", (cx, sy + tr.ch * 4), status_color)

    from game import spells
    if spells.is_caster(char):
        mx = spells.ensure(char)
        row = 5
        for school in ("mage", "priest"):
            if any(mx[school]):
                pts = "/".join(str(v) for v in char.sp[school])
                tr.draw(surf, f"{school.capitalize():<7}{pts}",
                        (cx, sy + tr.ch * row), palette.ACCENT)
                row += 1
    return sy + 7 * tr.ch  # bottom y, for callers that draw more below
