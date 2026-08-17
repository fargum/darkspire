"""Procedural retro sound effects: square waves, noise, sweeps, fanfares."""

import numpy as np
import pygame

RATE = 44100


def _to_sound(wave):
    clipped = np.clip(wave, -1.0, 1.0)
    samples = (clipped * 32767 * 0.5).astype(np.int16)
    init = pygame.mixer.get_init()
    channels = init[2] if init else 1
    if channels > 1:                   # driver may force stereo despite mono pre_init
        samples = np.repeat(samples[:, np.newaxis], channels, axis=1)
    return pygame.sndarray.make_sound(samples)


def _env(n, attack=0.01, decay=1.0):
    """Attack-decay envelope over n samples."""
    t = np.linspace(0, 1, n, endpoint=False)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.exp(-t * 4 * decay)
    return a * d


def square(freq, dur, vol=0.6, decay=1.0):
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * vol
    return wave * _env(n, decay=decay)


def noise(dur, vol=0.5, decay=1.5, lowpass=1):
    n = int(RATE * dur)
    rng = np.random.default_rng(7)
    wave = rng.uniform(-1, 1, n)
    if lowpass > 1:                    # crude smoothing for thuddier noise
        kernel = np.ones(lowpass) / lowpass
        wave = np.convolve(wave, kernel, mode="same")
    return wave * vol * _env(n, decay=decay)


def sweep(f0, f1, dur, vol=0.5, decay=1.0):
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    freq = np.linspace(f0, f1, n)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    wave = np.sign(np.sin(phase)) * vol
    return wave * _env(n, decay=decay)


def tones(notes, dur=0.08, vol=0.5, gap=0.0, decay=2.0):
    parts = []
    for f in notes:
        parts.append(square(f, dur, vol, decay=decay))
        if gap:
            parts.append(np.zeros(int(RATE * gap)))
    return np.concatenate(parts)


def build_all():
    return {name: _to_sound(wave) for name, wave in {
        "move":    square(880, 0.03, 0.25, decay=3),
        "select":  tones([660, 990], 0.05, 0.35),
        "step":    noise(0.05, 0.3, decay=4, lowpass=24),
        "bump":    square(90, 0.09, 0.5, decay=2) + noise(0.09, 0.25, lowpass=16),
        "door":    sweep(210, 120, 0.14, 0.4) + noise(0.14, 0.2, lowpass=8),
        "stairs":  sweep(320, 150, 0.25, 0.35),
        "hit":     noise(0.07, 0.5, decay=3, lowpass=6) + square(190, 0.07, 0.3, decay=3),
        "slain":   sweep(420, 70, 0.28, 0.5),
        "spell":   sweep(280, 1400, 0.18, 0.4),
        "heal":    tones([523, 659, 784], 0.07, 0.4),
        "gold":    tones([1319, 1760], 0.06, 0.35),
        "trap":    noise(0.22, 0.6, decay=2, lowpass=3),
        "levelup": tones([392, 523, 659, 784], 0.09, 0.45) ,
        "victory": tones([523, 659, 784, 1047, 784, 1047], 0.11, 0.5),
        "defeat":  tones([220, 196, 175, 147], 0.22, 0.5, decay=1.2),
    }.items()}
