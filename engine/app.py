"""Application shell: pygame init, logical canvas, scene stack, main loop."""

import pygame

from engine import palette
from engine.text import TextRenderer

LOGICAL_SIZE = (640, 400)


class App:
    def __init__(self, scale=2, caption="DARKSPIRE: Depths of the Mad Archon"):
        pygame.init()
        import audio
        audio.init()
        self.scale = scale
        self.screen = pygame.display.set_mode(
            (LOGICAL_SIZE[0] * scale, LOGICAL_SIZE[1] * scale)
        )
        pygame.display.set_caption(caption)
        self.canvas = pygame.Surface(LOGICAL_SIZE)
        self.text = TextRenderer()
        self.clock = pygame.time.Clock()
        self.scenes = []
        self.running = True

    # -- scene stack -------------------------------------------------------
    @property
    def scene(self):
        return self.scenes[-1] if self.scenes else None

    def push(self, scene):
        self.scenes.append(scene)
        scene.on_enter()

    def pop(self):
        if self.scenes:
            self.scenes.pop()
        if self.scenes:
            self.scene.on_resume()
        else:
            self.running = False

    def replace(self, scene):
        if self.scenes:
            self.scenes.pop()
        self.push(scene)

    def pop_to(self, scene_name):
        """Pop scenes until the named scene type is on top."""
        while len(self.scenes) > 1 and type(self.scene).__name__ != scene_name:
            self.scenes.pop()
        if self.scenes:
            self.scene.on_resume()

    def quit(self):
        self.running = False

    # -- main loop ---------------------------------------------------------
    def run(self):
        while self.running and self.scenes:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.scene:
                    self.scene.handle_event(event)
            if not self.running:
                break
            if self.scene:
                self.scene.update(dt)
                self.canvas.fill(palette.BG)
                self.scene.draw(self.canvas)
            pygame.transform.scale(self.canvas, self.screen.get_size(), self.screen)
            pygame.display.flip()
        pygame.quit()

    # -- headless single frame (for tests) ---------------------------------
    def render_one_frame(self):
        if self.scene:
            self.scene.update(0.016)
            self.canvas.fill(palette.BG)
            self.scene.draw(self.canvas)
