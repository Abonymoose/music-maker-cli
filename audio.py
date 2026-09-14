"""Sound synthesis: piano tones (per waveform) and drum hits."""

import numpy as np
import pygame

from model import NUM_PIANO_ROWS, row_frequency

SAMPLE_RATE = 44100


def _envelope(n_samples, attack_ratio=0.1):
    envelope = np.ones(n_samples)
    fade = max(1, int(n_samples * attack_ratio))
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    return envelope


def _to_sound(wave, volume):
    audio = np.int16(np.clip(wave * volume, -1, 1) * 32767)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def make_tone(freq, duration, waveform="sine", volume=0.5):
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, False)
    if waveform == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    elif waveform == "saw":
        wave = 2 * (t * freq - np.floor(0.5 + t * freq))
    else:
        wave = np.sin(2 * np.pi * freq * t)
    wave = wave * _envelope(n_samples)
    return _to_sound(wave, volume)


def make_kick(duration, volume=0.5):
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, False)
    freq = np.linspace(150, 40, n_samples)
    wave = np.sin(2 * np.pi * freq * t) * np.exp(-8 * t / duration)
    return _to_sound(wave, volume * 1.6)


def make_snare(duration, volume=0.5):
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, False)
    noise = np.random.uniform(-1, 1, n_samples)
    wave = noise * np.exp(-10 * t / duration)
    return _to_sound(wave, volume * 1.2)


def build_sounds(settings):
    duration = settings.step_duration()
    sounds = {}
    for row in range(NUM_PIANO_ROWS):
        sounds[row] = make_tone(row_frequency(row), duration, settings.instrument, settings.volume)
    sounds["kick"] = make_kick(duration, settings.volume)
    sounds["snare"] = make_snare(duration, settings.volume)
    return sounds
