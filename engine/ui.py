"""Reusable keyboard-driven UI widgets: panels, menus, text input."""

import pygame

from engine import palette


def draw_panel(surf, rect, tr=None, title=None):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, palette.PANEL_BG, rect)
    pygame.draw.rect(surf, palette.BORDER, rect, 1)
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surf, palette.BORDER_DIM, inner, 1)
    if title and tr:
        label = f" {title} "
        x = rect.x + 12
        w = tr.font.size(label)[0]
        pygame.draw.rect(surf, palette.PANEL_BG, (x, rect.y - 2, w, 5))
        tr.draw(surf, label, (x, rect.y - tr.ch // 2), palette.ACCENT)


class MenuItem:
    def __init__(self, label, value=None, enabled=True, note=None):
        self.label = label
        self.value = value if value is not None else label
        self.enabled = enabled
        self.note = note


class Menu:
    """Vertical menu. handle_event returns the chosen item's value, else None."""

    def __init__(self, items):
        self.items = [i if isinstance(i, MenuItem) else MenuItem(*i) for i in items]
        self.index = 0
        self._snap_to_enabled(1)

    def _snap_to_enabled(self, direction):
        n = len(self.items)
        for _ in range(n):
            if self.items[self.index].enabled:
                return
            self.index = (self.index + direction) % n

    def move(self, direction):
        n = len(self.items)
        self.index = (self.index + direction) % n
        self._snap_to_enabled(direction)

    @property
    def selected(self):
        return self.items[self.index]

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        import audio
        if event.key in (pygame.K_UP, pygame.K_w):
            self.move(-1)
            audio.play("move", 0.5)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.move(1)
            audio.play("move", 0.5)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.selected.enabled:
                audio.play("select", 0.6)
                return self.selected.value
        return None

    def draw(self, surf, tr, x, y, width=None, max_rows=None):
        start = 0
        count = len(self.items)
        if max_rows and count > max_rows:
            start = max(0, min(self.index - max_rows // 2, count - max_rows))
        end = min(count, start + (max_rows or count))
        row = 0
        if start > 0:
            tr.draw(surf, "  ▲ more", (x, y), palette.DIM)
            row += 1
        for i in range(start, end):
            item = self.items[i]
            row_y = y + row * (tr.ch + 2)
            selected = i == self.index
            if selected:
                w = width or (tr.font.size(item.label)[0] + 3 * tr.cw)
                pygame.draw.rect(surf, palette.SELECT_BG, (x - 4, row_y - 1, w + 8, tr.ch + 2))
            color = palette.DIM if not item.enabled else (
                palette.BRIGHT if selected else palette.TEXT
            )
            prefix = "► " if selected else "  "
            tr.draw(surf, prefix + item.label, (x, row_y), color)
            if item.note:
                note_x = x + (width or 200) - tr.font.size(item.note)[0]
                tr.draw(surf, item.note, (note_x, row_y), palette.DIM)
            row += 1
        if end < count:
            tr.draw(surf, "  ▼ more", (x, y + row * (tr.ch + 2)), palette.DIM)


class TextInput:
    """Single-line text input. handle_event returns ('done', text) | ('cancel', None) | None."""

    ALLOWED = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'"

    def __init__(self, max_len=14, text=""):
        self.max_len = max_len
        self.text = text
        self._blink = 0.0

    def update(self, dt):
        self._blink = (self._blink + dt) % 1.0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.text.strip():
                return ("done", self.text.strip())
        elif event.key == pygame.K_ESCAPE:
            return ("cancel", None)
        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.unicode and event.unicode in self.ALLOWED:
            if len(self.text) < self.max_len:
                self.text += event.unicode
        return None

    def draw(self, surf, tr, x, y):
        cursor = "_" if self._blink < 0.6 else " "
        tr.draw(surf, self.text + cursor, (x, y), palette.BRIGHT)
