"""Scene base class. Scenes live on the App's stack."""


class Scene:
    def __init__(self, app):
        self.app = app

    def on_enter(self):
        """Called when the scene is pushed onto the stack."""

    def on_resume(self):
        """Called when the scene above this one is popped."""

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass
