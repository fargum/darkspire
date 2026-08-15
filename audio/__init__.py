"""Sound system. All effects are synthesized at startup — no audio files.

If the mixer can't initialize (headless, no device), audio silently disables.
"""

_enabled = False
_sounds = {}


def init():
    global _enabled, _sounds
    try:
        import pygame
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.mixer.init()
        from audio import synth
        _sounds = synth.build_all()
        _enabled = True
    except Exception:
        _enabled = False


def play(name, volume=1.0):
    if _enabled and name in _sounds:
        sound = _sounds[name]
        sound.set_volume(volume)
        sound.play()
