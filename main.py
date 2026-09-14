#!/usr/bin/env python3
"""CLI music maker: a curses step-sequencer with synth playback."""

import curses
import json
import sys
import time

import numpy as np
import pygame

NUM_STEPS = 16
NUM_PIANO_ROWS = 12
NUM_DRUM_ROWS = 2
NUM_ROWS = NUM_PIANO_ROWS + NUM_DRUM_ROWS

SAMPLE_RATE = 44100
BPM = 120
STEP_DURATION = 60.0 / BPM / 2  # eighth notes

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
DRUM_LABELS = ["Kick", "Snare"]

DEFAULT_SAVE_FILE = "song.json"


def row_label(row):
    if row < NUM_PIANO_ROWS:
        # Row 0 = top = highest note. Single octave, C4..B4.
        name = NOTE_NAMES[NUM_PIANO_ROWS - 1 - row]
        return f"{name}4"
    return DRUM_LABELS[row - NUM_PIANO_ROWS]


def row_frequency(row):
    # MIDI note number for C4 = 60.
    semitone = NUM_PIANO_ROWS - 1 - row
    midi = 60 + semitone
    return 440.0 * (2 ** ((midi - 69) / 12.0))


def make_tone(freq, duration):
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, False)
    wave = np.sin(freq * t * 2 * np.pi)
    # Simple envelope to avoid clicks.
    envelope = np.ones(n_samples)
    fade = max(1, int(n_samples * 0.1))
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    wave = wave * envelope
    audio = np.int16(wave * 32767 * 0.5)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def make_kick(duration):
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, False)
    freq = np.linspace(150, 40, n_samples)
    wave = np.sin(2 * np.pi * freq * t)
    envelope = np.exp(-8 * t / duration)
    wave = wave * envelope
    audio = np.int16(wave * 32767 * 0.8)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def make_snare(duration):
    n_samples = int(SAMPLE_RATE * duration)
    noise = np.random.uniform(-1, 1, n_samples)
    t = np.linspace(0, duration, n_samples, False)
    envelope = np.exp(-10 * t / duration)
    wave = noise * envelope
    audio = np.int16(wave * 32767 * 0.6)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


class Sequencer:
    def __init__(self):
        self.grid = [[False] * NUM_STEPS for _ in range(NUM_ROWS)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.status = ""

    def toggle(self):
        self.grid[self.cursor_row][self.cursor_col] = not self.grid[self.cursor_row][self.cursor_col]

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.grid, f)
        self.status = f"Saved to {path}"

    def load(self, path):
        with open(path) as f:
            data = json.load(f)
        if len(data) == NUM_ROWS and all(len(row) == NUM_STEPS for row in data):
            self.grid = [[bool(v) for v in row] for row in data]
            self.status = f"Loaded {path}"
        else:
            self.status = "Invalid save file"


def build_sounds():
    sounds = {}
    for row in range(NUM_PIANO_ROWS):
        sounds[row] = make_tone(row_frequency(row), STEP_DURATION)
    sounds["kick"] = make_kick(STEP_DURATION)
    sounds["snare"] = make_snare(STEP_DURATION)
    return sounds


def draw(stdscr, seq, playing_col=None):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    label_width = 5
    cell_width = 3

    for row in range(NUM_ROWS):
        y = row
        if y >= max_y:
            break
        label = row_label(row).rjust(label_width - 1) + " "
        stdscr.addstr(y, 0, label[:label_width])
        for col in range(NUM_STEPS):
            x = label_width + col * cell_width
            if x + cell_width > max_x:
                break
            active = seq.grid[row][col]
            is_cursor = (row == seq.cursor_row and col == seq.cursor_col)
            is_playing = (col == playing_col)
            symbol = "#" if active else "."
            attr = curses.A_NORMAL
            if is_playing:
                attr |= curses.A_BOLD
            if is_cursor:
                attr |= curses.A_REVERSE
            cell = f"[{symbol}]"
            try:
                stdscr.addstr(y, x, cell, attr)
            except curses.error:
                pass

    help_y = NUM_ROWS + 1
    if help_y < max_y:
        stdscr.addstr(help_y, 0, "Arrows: move  Space: toggle  P: play  S: save  L: load  Q: quit")
    status_y = NUM_ROWS + 2
    if status_y < max_y and seq.status:
        try:
            stdscr.addstr(status_y, 0, seq.status[: max_x - 1])
        except curses.error:
            pass

    stdscr.refresh()


def play(stdscr, seq, sounds):
    for col in range(NUM_STEPS):
        draw(stdscr, seq, playing_col=col)
        for row in range(NUM_ROWS):
            if not seq.grid[row][col]:
                continue
            if row < NUM_PIANO_ROWS:
                sounds[row].play()
            elif row == NUM_PIANO_ROWS:
                sounds["kick"].play()
            else:
                sounds["snare"].play()
        stdscr.timeout(int(STEP_DURATION * 1000))
        stdscr.getch()
    stdscr.timeout(-1)
    seq.status = "Playback finished"


def main(stdscr):
    curses.curs_set(0)
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
    pygame.mixer.set_num_channels(NUM_ROWS + 4)

    sounds = build_sounds()
    seq = Sequencer()

    draw(stdscr, seq)

    while True:
        key = stdscr.getch()

        if key in (curses.KEY_UP,):
            seq.cursor_row = (seq.cursor_row - 1) % NUM_ROWS
        elif key in (curses.KEY_DOWN,):
            seq.cursor_row = (seq.cursor_row + 1) % NUM_ROWS
        elif key in (curses.KEY_LEFT,):
            seq.cursor_col = (seq.cursor_col - 1) % NUM_STEPS
        elif key in (curses.KEY_RIGHT,):
            seq.cursor_col = (seq.cursor_col + 1) % NUM_STEPS
        elif key == ord(" "):
            seq.toggle()
        elif key in (ord("p"), ord("P")):
            play(stdscr, seq, sounds)
        elif key in (ord("s"), ord("S")):
            seq.save(DEFAULT_SAVE_FILE)
        elif key in (ord("l"), ord("L")):
            try:
                seq.load(DEFAULT_SAVE_FILE)
            except (FileNotFoundError, json.JSONDecodeError):
                seq.status = f"Could not load {DEFAULT_SAVE_FILE}"
        elif key in (ord("q"), ord("Q")):
            break

        draw(stdscr, seq)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
