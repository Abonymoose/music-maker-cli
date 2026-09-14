"""Data model: settings and the step-sequencer grid."""

import json

NUM_PIANO_ROWS = 12
NUM_DRUM_ROWS = 2
NUM_ROWS = NUM_PIANO_ROWS + NUM_DRUM_ROWS

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
DRUM_LABELS = ["Kick", "Snare"]

LENGTH_CHOICES = [8, 16, 32]
INSTRUMENT_CHOICES = ["sine", "square", "saw"]

DEFAULT_SAVE_FILE = "song.json"


def row_label(row):
    if row < NUM_PIANO_ROWS:
        # Row 0 = top = highest note. Single octave, C4..B4.
        return f"{NOTE_NAMES[NUM_PIANO_ROWS - 1 - row]}4"
    return DRUM_LABELS[row - NUM_PIANO_ROWS]


def row_frequency(row):
    # MIDI note number for C4 = 60.
    semitone = NUM_PIANO_ROWS - 1 - row
    midi = 60 + semitone
    return 440.0 * (2 ** ((midi - 69) / 12.0))


class Settings:
    def __init__(self, bpm=120, volume=0.5, length=16, instrument="sine"):
        self.bpm = bpm
        self.volume = volume
        self.length = length
        self.instrument = instrument

    def step_duration(self):
        return 60.0 / self.bpm / 2  # eighth notes

    def adjust_bpm(self, delta):
        self.bpm = max(40, min(240, self.bpm + delta))

    def adjust_volume(self, delta):
        self.volume = max(0.0, min(1.0, round(self.volume + delta, 2)))

    def cycle_length(self, direction):
        idx = LENGTH_CHOICES.index(self.length)
        idx = (idx + direction) % len(LENGTH_CHOICES)
        self.length = LENGTH_CHOICES[idx]

    def cycle_instrument(self, direction):
        idx = INSTRUMENT_CHOICES.index(self.instrument)
        idx = (idx + direction) % len(INSTRUMENT_CHOICES)
        self.instrument = INSTRUMENT_CHOICES[idx]


class Sequencer:
    def __init__(self, settings):
        self.settings = settings
        self.grid = [[False] * settings.length for _ in range(NUM_ROWS)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.playing_col = None
        self.status = ""

    def toggle(self):
        self.grid[self.cursor_row][self.cursor_col] = not self.grid[self.cursor_row][self.cursor_col]

    def resize(self, new_length):
        for row in self.grid:
            if new_length > len(row):
                row.extend([False] * (new_length - len(row)))
            else:
                del row[new_length:]
        self.cursor_col = min(self.cursor_col, new_length - 1)

    def save(self, path=DEFAULT_SAVE_FILE):
        data = {
            "bpm": self.settings.bpm,
            "volume": self.settings.volume,
            "length": self.settings.length,
            "instrument": self.settings.instrument,
            "grid": self.grid,
        }
        with open(path, "w") as f:
            json.dump(data, f)
        self.status = f"Saved to {path}"

    def load(self, path=DEFAULT_SAVE_FILE):
        with open(path) as f:
            data = json.load(f)
        grid = data.get("grid")
        length = data.get("length", len(grid[0]) if grid else self.settings.length)
        if grid and len(grid) == NUM_ROWS and all(len(r) == length for r in grid):
            self.settings.bpm = data.get("bpm", self.settings.bpm)
            self.settings.volume = data.get("volume", self.settings.volume)
            self.settings.instrument = data.get("instrument", self.settings.instrument)
            self.settings.length = length
            self.grid = [[bool(v) for v in r] for r in grid]
            self.cursor_col = min(self.cursor_col, length - 1)
            self.status = f"Loaded {path}"
        else:
            self.status = "Invalid save file"
