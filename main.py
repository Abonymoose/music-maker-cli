#!/usr/bin/env python3
"""CLI music maker: a full-screen curses step-sequencer with synth playback."""

import curses
import json
import sys

import pygame

import audio
import ui
from model import NUM_ROWS, NUM_PIANO_ROWS, DEFAULT_SAVE_FILE, Sequencer, Settings

ESC = 27
ENTER_KEYS = (curses.KEY_ENTER, 10, 13)


class App:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.settings = Settings()
        self.seq = Sequencer(self.settings)
        self.sounds = audio.build_sounds(self.settings)
        self.mode = "grid"  # or "settings"
        self.settings_index = 0

    def rebuild_sounds(self):
        self.sounds = audio.build_sounds(self.settings)

    def play_from(self, start_col):
        length = self.settings.length
        self.stdscr.nodelay(True)
        try:
            for col in range(start_col, length):
                self.seq.playing_col = col
                ui.draw_grid(self.stdscr, self.seq, self.settings)
                for row in range(NUM_ROWS):
                    if not self.seq.grid[row][col]:
                        continue
                    if row < NUM_PIANO_ROWS:
                        self.sounds[row].play()
                    elif row == NUM_PIANO_ROWS:
                        self.sounds["kick"].play()
                    else:
                        self.sounds["snare"].play()
                curses.napms(int(self.settings.step_duration() * 1000))
                key = self.stdscr.getch()
                if key == ESC:
                    break
        finally:
            self.stdscr.nodelay(False)
            self.seq.playing_col = None
            self.seq.status = "Playback finished"

    def handle_grid_key(self, key):
        length = self.settings.length
        if key == curses.KEY_UP:
            self.seq.cursor_row = (self.seq.cursor_row - 1) % NUM_ROWS
        elif key == curses.KEY_DOWN:
            self.seq.cursor_row = (self.seq.cursor_row + 1) % NUM_ROWS
        elif key == curses.KEY_LEFT:
            self.seq.cursor_col = (self.seq.cursor_col - 1) % length
        elif key == curses.KEY_RIGHT:
            self.seq.cursor_col = (self.seq.cursor_col + 1) % length
        elif key == ord(" "):
            self.seq.toggle()
        elif key in ENTER_KEYS:
            self.play_from(self.seq.cursor_col)
        elif key in (ord("p"), ord("P")):
            self.play_from(0)
        elif key in (ord("o"), ord("O")):
            self.mode = "settings"
        elif key in (ord("s"), ord("S")):
            self.seq.save(DEFAULT_SAVE_FILE)
        elif key in (ord("l"), ord("L")):
            try:
                self.seq.load(DEFAULT_SAVE_FILE)
                self.rebuild_sounds()
            except (FileNotFoundError, json.JSONDecodeError):
                self.seq.status = f"Could not load {DEFAULT_SAVE_FILE}"
        elif key in (ord("q"), ord("Q")):
            return False
        return True

    def handle_settings_key(self, key):
        num_fields = len(ui.SETTINGS_FIELDS)
        if key == curses.KEY_UP:
            self.settings_index = (self.settings_index - 1) % num_fields
        elif key == curses.KEY_DOWN:
            self.settings_index = (self.settings_index + 1) % num_fields
        elif key == curses.KEY_LEFT:
            self._adjust_setting(-1)
        elif key == curses.KEY_RIGHT:
            self._adjust_setting(1)
        elif key in ENTER_KEYS or key == ESC:
            self.rebuild_sounds()
            self.mode = "grid"
        return True

    def _adjust_setting(self, direction):
        field = self.settings_index
        if field == 0:
            self.settings.adjust_bpm(direction * 5)
        elif field == 1:
            self.settings.adjust_volume(direction * 0.05)
        elif field == 2:
            self.settings.cycle_instrument(direction)
        elif field == 3:
            old_length = self.settings.length
            self.settings.cycle_length(direction)
            if self.settings.length != old_length:
                self.seq.resize(self.settings.length)

    def run(self):
        ui.draw_grid(self.stdscr, self.seq, self.settings)
        while True:
            key = self.stdscr.getch()
            if self.mode == "grid":
                if not self.handle_grid_key(key):
                    break
                ui.draw_grid(self.stdscr, self.seq, self.settings)
            else:
                self.handle_settings_key(key)
                if self.mode == "grid":
                    ui.draw_grid(self.stdscr, self.seq, self.settings)
                else:
                    ui.draw_settings(self.stdscr, self.settings, self.settings_index)


def main(stdscr):
    curses.curs_set(0)
    pygame.mixer.init(frequency=audio.SAMPLE_RATE, size=-16, channels=2)
    pygame.mixer.set_num_channels(NUM_ROWS + 4)
    App(stdscr).run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
