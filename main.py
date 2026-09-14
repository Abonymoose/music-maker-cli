#!/usr/bin/env python3
"""CLI music maker: a curses step-sequencer with synth playback."""

import curses
import json
import sys

import numpy as np
import pygame

SETTINGS = {
    "bars": 5,
    "beats_per_bar": 4,  # fixed
}
MIN_BARS = 1
MAX_BARS = 999  # effectively unbounded horizontal scroll

NUM_PIANO_ROWS = 24
NUM_DRUM_ROWS = 2
NUM_ROWS = NUM_PIANO_ROWS + NUM_DRUM_ROWS

LABEL_WIDTH = 5
CELL_WIDTH = 3
DEFAULT_VIEWPORT_WIDTH = 16  # used before the terminal size is known

SAMPLE_RATE = 44100
DEFAULT_BPM = 120
MIN_BPM = 40
MAX_BPM = 300
BPM_STEP = 10

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
DRUM_LABELS = ["Kick", "Snare"]

PREVIEW_DURATION = 0.15  # seconds, quick preview when toggling a note on

DEFAULT_SAVE_FILE = "song.json"


def num_steps():
    return SETTINGS["bars"] * SETTINGS["beats_per_bar"]


def compute_viewport_width(max_x):
    """Widest number of columns that fit max_x, rounded down to a multiple
    of beats_per_bar (so the viewport always shows whole bars)."""
    multiple = SETTINGS["beats_per_bar"]
    available = max(multiple, (max_x - LABEL_WIDTH) // CELL_WIDTH)
    width = (available // multiple) * multiple
    return min(width, num_steps())


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
        self.grid = [[False] * num_steps() for _ in range(NUM_ROWS)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.view_offset = 0
        self.viewport_width = DEFAULT_VIEWPORT_WIDTH
        self.bpm = DEFAULT_BPM
        self.repeat = False
        self.status = ""
        self.is_playing = False
        self.play_col = None

    def scroll_to(self, col):
        if col < self.view_offset:
            self.view_offset = col
        elif col >= self.view_offset + self.viewport_width:
            self.view_offset = col - self.viewport_width + 1
        max_offset = max(0, num_steps() - self.viewport_width)
        self.view_offset = max(0, min(self.view_offset, max_offset))

    def move_cursor_col(self, delta):
        self.cursor_col = max(0, min(num_steps() - 1, self.cursor_col + delta))
        self.scroll_to(self.cursor_col)

    def resize_to_bars(self, bars):
        SETTINGS["bars"] = bars
        length = num_steps()
        for row in self.grid:
            if length > len(row):
                row.extend([False] * (length - len(row)))
            else:
                del row[length:]
        self.cursor_col = min(self.cursor_col, length - 1)
        self.scroll_to(self.cursor_col)

    def adjust_bpm(self, delta):
        self.bpm = max(MIN_BPM, min(MAX_BPM, self.bpm + delta))
        self.status = f"BPM: {self.bpm}"

    def toggle_repeat(self):
        self.repeat = not self.repeat
        self.status = f"Repeat: {'ON' if self.repeat else 'OFF'}"

    def toggle(self):
        self.grid[self.cursor_row][self.cursor_col] = not self.grid[self.cursor_row][self.cursor_col]

    def save(self, path):
        data = {"bars": SETTINGS["bars"], "grid": self.grid}
        with open(path, "w") as f:
            json.dump(data, f)
        self.status = f"Saved to {path}"

    def load(self, path):
        with open(path) as f:
            data = json.load(f)
        grid = data.get("grid")
        bars = data.get("bars", SETTINGS["bars"])
        length = bars * SETTINGS["beats_per_bar"]
        if grid and len(grid) == NUM_ROWS and all(len(row) == length for row in grid):
            SETTINGS["bars"] = bars
            self.grid = [[bool(v) for v in row] for row in grid]
            self.cursor_col = min(self.cursor_col, length - 1)
            self.scroll_to(self.cursor_col)
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

    seq.viewport_width = compute_viewport_width(max_x)
    seq.scroll_to(seq.cursor_col)

    label_width = LABEL_WIDTH
    cell_width = CELL_WIDTH
    view_start = seq.view_offset
    view_end = min(num_steps(), view_start + seq.viewport_width)

    for row in range(NUM_ROWS):
        y = row
        if y >= max_y:
            break
        label = row_label(row).rjust(label_width - 1) + " "
        stdscr.addstr(y, 0, label[:label_width])
        for i, col in enumerate(range(view_start, view_end)):
            x = label_width + i * cell_width
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
        bar_now = seq.cursor_col // SETTINGS["beats_per_bar"] + 1
        info = (
            f"BPM: {seq.bpm}   Repeat: {repeat_label}   {play_label}   "
            f"Bar {bar_now}/{SETTINGS['bars']}   Beats {view_start + 1}-{view_end}/{num_steps()}"
        )
        stdscr.addstr(info_y, 0, info[: max_x - 1])

    help_y = NUM_ROWS + 2
    if help_y < max_y:
        stdscr.addstr(
            help_y, 0,
            "Arrows: move (view scrolls)  Space: toggle  Enter: play/pause"
            "  P: play from start  +/-: tempo  R: repeat  O: settings"
            "  S: save  L: load  Q: quit"[: max_x - 1],
        )
    status_y = NUM_ROWS + 3
    if status_y < max_y and seq.status:
        try:
            stdscr.addstr(status_y, 0, seq.status[: max_x - 1])
        except curses.error:
            pass

    stdscr.refresh()


def draw_settings(stdscr, seq):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    title = " SETTINGS "
    stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD | curses.A_REVERSE)

    line1 = f"  Bars: {SETTINGS['bars']}   (+/- to adjust)"
    line2 = f"  Beats per bar: {SETTINGS['beats_per_bar']} (fixed)"
    line3 = f"  Total steps: {num_steps()}"
    line4 = f"  Visible at once: {compute_viewport_width(max_x)} (fits your terminal, multiple of 4)"
    if 2 < max_y:
        stdscr.addstr(2, 0, line1[: max_x - 1])
    if 3 < max_y:
        stdscr.addstr(3, 0, line2[: max_x - 1])
    if 4 < max_y:
        stdscr.addstr(4, 0, line3[: max_x - 1])
    if 5 < max_y:
        stdscr.addstr(5, 0, line4[: max_x - 1])
    if 7 < max_y:
        stdscr.addstr(7, 0, "O or Enter or Esc: back to grid"[: max_x - 1])

    stdscr.refresh()


def start_playback(seq, from_col):
    seq.play_col = from_col
    seq.is_playing = True
    seq.status = "Playing"
    seq.scroll_to(from_col)


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
    if next_col >= num_steps():
        if seq.repeat:
            next_col = 0
        else:
            seq.is_playing = False
            seq.play_col = None
            seq.status = "Playback finished"
            return
    seq.play_col = next_col
    seq.scroll_to(next_col)


def main(stdscr):
    curses.curs_set(0)
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
    pygame.mixer.set_num_channels(NUM_ROWS + 4)

    seq = Sequencer()
    sounds = build_sounds(step_duration(seq.bpm))
    mode = "grid"  # or "settings"

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
        elif mode == "settings":
            if key in (ord("+"), ord("=")):
                seq.resize_to_bars(min(MAX_BARS, SETTINGS["bars"] + 1))
            elif key in (ord("-"), ord("_")):
                seq.resize_to_bars(max(MIN_BARS, SETTINGS["bars"] - 1))
            elif key in (ord("o"), ord("O"), curses.KEY_ENTER, 10, 13, 27):
                mode = "grid"
        elif key in (curses.KEY_UP,):
            seq.cursor_row = (seq.cursor_row - 1) % NUM_ROWS
        elif key in (curses.KEY_DOWN,):
            seq.cursor_row = (seq.cursor_row + 1) % NUM_ROWS
        elif key in (curses.KEY_LEFT,):
            seq.move_cursor_col(-1)
        elif key in (curses.KEY_RIGHT,):
            seq.move_cursor_col(1)
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
        elif key in (ord("o"), ord("O")):
            mode = "settings"
        elif key in (ord("s"), ord("S")):
            seq.save(DEFAULT_SAVE_FILE)
        elif key in (ord("l"), ord("L")):
            try:
                seq.load(DEFAULT_SAVE_FILE)
            except (FileNotFoundError, json.JSONDecodeError):
                seq.status = f"Could not load {DEFAULT_SAVE_FILE}"
        elif key in (ord("q"), ord("Q")):
            break

        if mode == "settings":
            draw_settings(stdscr, seq)
        else:
            draw(stdscr, seq)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
