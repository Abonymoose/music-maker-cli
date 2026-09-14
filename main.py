#!/usr/bin/env python3
"""CLI music maker: a curses step-sequencer with synth playback."""

import curses
import json
import sys

import numpy as np
import pygame

NUM_STEPS = 18
NUM_PIANO_ROWS = 24
NUM_DRUM_ROWS = 2
NUM_ROWS = NUM_PIANO_ROWS + NUM_DRUM_ROWS

SAMPLE_RATE = 44100
DEFAULT_BPM = 120
MIN_BPM = 40
MAX_BPM = 300
BPM_STEP = 10

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
DRUM_LABELS = ["Kick", "Snare"]

PREVIEW_DURATION = 0.15  # seconds, quick preview when toggling a note on

DEFAULT_SAVE_FILE = "song.json"


def row_label(row):
    if row < NUM_PIANO_ROWS:
        # Row 0 = top = highest note. Two octaves, C3..B4.
        semitone = NUM_PIANO_ROWS - 1 - row
        octave = 3 + semitone // 12
        name = NOTE_NAMES[semitone % 12]
        return f"{name}{octave}"
    return DRUM_LABELS[row - NUM_PIANO_ROWS]


def row_frequency(row):
    # MIDI note number for C3 = 48.
    semitone = NUM_PIANO_ROWS - 1 - row
    midi = 48 + semitone
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


def step_duration(bpm):
    return 60.0 / bpm / 2  # eighth notes


def preview_note(freq):
    make_tone(freq, PREVIEW_DURATION).play()


class Sequencer:
    def __init__(self):
        self.grid = [[False] * NUM_STEPS for _ in range(NUM_ROWS)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.bpm = DEFAULT_BPM
        self.repeat = False
        self.status = ""
        self.is_playing = False
        self.play_col = None

    def adjust_bpm(self, delta):
        self.bpm = max(MIN_BPM, min(MAX_BPM, self.bpm + delta))
        self.status = f"BPM: {self.bpm}"

    def toggle_repeat(self):
        self.repeat = not self.repeat
        self.status = f"Repeat: {'ON' if self.repeat else 'OFF'}"

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


def build_sounds(duration):
    sounds = {}
    for row in range(NUM_PIANO_ROWS):
        sounds[row] = make_tone(row_frequency(row), duration)
    sounds["kick"] = make_kick(duration)
    sounds["snare"] = make_snare(duration)
    return sounds


def draw(stdscr, seq):
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
            is_playing = (col == seq.play_col)
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

    info_y = NUM_ROWS + 1
    if info_y < max_y:
        repeat_label = "ON" if seq.repeat else "OFF"
        play_label = "Playing" if seq.is_playing else "Paused" if seq.play_col is not None else "Stopped"
        info = f"BPM: {seq.bpm}   Repeat: {repeat_label}   {play_label}"
        stdscr.addstr(info_y, 0, info[: max_x - 1])

    help_y = NUM_ROWS + 2
    if help_y < max_y:
        stdscr.addstr(
            help_y, 0,
            "Arrows: move  Space: toggle  Enter: play/pause  P: play from start"
            "  +/-: tempo  R: repeat  S: save  L: load  Q: quit"[: max_x - 1],
        )
    status_y = NUM_ROWS + 3
    if status_y < max_y and seq.status:
        try:
            stdscr.addstr(status_y, 0, seq.status[: max_x - 1])
        except curses.error:
            pass

    stdscr.refresh()


def start_playback(seq, from_col):
    seq.play_col = from_col
    seq.is_playing = True
    seq.status = "Playing"


def pause_playback(seq):
    seq.is_playing = False
    seq.status = "Paused"


def toggle_play_pause(seq):
    if seq.is_playing:
        pause_playback(seq)
    else:
        start_playback(seq, seq.play_col if seq.play_col is not None else seq.cursor_col)


def play_current_step(seq, sounds):
    col = seq.play_col
    for row in range(NUM_ROWS):
        if not seq.grid[row][col]:
            continue
        if row < NUM_PIANO_ROWS:
            sounds[row].play()
        elif row == NUM_PIANO_ROWS:
            sounds["kick"].play()
        else:
            sounds["snare"].play()


def advance_playback(seq, sounds):
    play_current_step(seq, sounds)
    next_col = seq.play_col + 1
    if next_col >= NUM_STEPS:
        if seq.repeat:
            next_col = 0
        else:
            seq.is_playing = False
            seq.play_col = None
            seq.status = "Playback finished"
            return
    seq.play_col = next_col


def main(stdscr):
    curses.curs_set(0)
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
    pygame.mixer.set_num_channels(NUM_ROWS + 4)

    seq = Sequencer()
    sounds = build_sounds(step_duration(seq.bpm))

    draw(stdscr, seq)

    while True:
        if seq.is_playing:
            stdscr.timeout(int(step_duration(seq.bpm) * 1000))
        else:
            stdscr.timeout(-1)

        key = stdscr.getch()

        if key == -1:
            if seq.is_playing:
                advance_playback(seq, sounds)
        elif key in (curses.KEY_UP,):
            seq.cursor_row = (seq.cursor_row - 1) % NUM_ROWS
        elif key in (curses.KEY_DOWN,):
            seq.cursor_row = (seq.cursor_row + 1) % NUM_ROWS
        elif key in (curses.KEY_LEFT,):
            seq.cursor_col = (seq.cursor_col - 1) % NUM_STEPS
        elif key in (curses.KEY_RIGHT,):
            seq.cursor_col = (seq.cursor_col + 1) % NUM_STEPS
        elif key == ord(" "):
            seq.toggle()
            note_on = seq.grid[seq.cursor_row][seq.cursor_col]
            if note_on and seq.cursor_row < NUM_PIANO_ROWS:
                preview_note(row_frequency(seq.cursor_row))
        elif key in (curses.KEY_ENTER, 10, 13):
            toggle_play_pause(seq)
        elif key in (ord("p"), ord("P")):
            start_playback(seq, 0)
        elif key in (ord("+"), ord("=")):
            seq.adjust_bpm(BPM_STEP)
            sounds = build_sounds(step_duration(seq.bpm))
        elif key in (ord("-"), ord("_")):
            seq.adjust_bpm(-BPM_STEP)
            sounds = build_sounds(step_duration(seq.bpm))
        elif key in (ord("r"), ord("R")):
            seq.toggle_repeat()
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
