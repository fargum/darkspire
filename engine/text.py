"""Text rendering at the logical resolution. Crisp (non-antialiased) monospace."""

import pygame

from engine import palette


class TextRenderer:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.SysFont("consolas,couriernew,monospace", 15)
        self.big = pygame.font.SysFont("consolas,couriernew,monospace", 30, bold=True)
        self.ch = self.font.get_height()          # line height
        self.cw = self.font.size("M")[0]          # monospace cell width

    def draw(self, surf, text, pos, color=palette.TEXT, font=None):
        f = font or self.font
        surf.blit(f.render(text, False, color), pos)

    def draw_center(self, surf, text, center_x, y, color=palette.TEXT, font=None):
        f = font or self.font
        img = f.render(text, False, color)
        surf.blit(img, (center_x - img.get_width() // 2, y))

    def draw_right(self, surf, text, right_x, y, color=palette.TEXT, font=None):
        f = font or self.font
        img = f.render(text, False, color)
        surf.blit(img, (right_x - img.get_width(), y))
