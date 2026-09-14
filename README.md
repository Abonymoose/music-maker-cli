# Music Maker CLI

A full-screen terminal step sequencer built with `curses` and `pygame`.

## Code structure

- `model.py` — data model: `Settings` (tempo, volume, length, instrument)
  and `Sequencer` (the grid, cursor, save/load).
- `audio.py` — sound synthesis: piano tones (sine/square/saw) and
  synthesized kick/snare hits, built from the current `Settings`.
- `ui.py` — curses rendering: the sidebar + grid layout, the status bar,
  and the settings panel.
- `main.py` — `App` class wiring input handling and playback to the model
  and UI; entry point.

## Grid

- The number of columns (time steps) is adjustable in Settings: 8, 16, or
  32.
- The top 12 rows are piano notes, a single octave (C4 to B4, high notes
  at the top).
- The bottom 2 rows are drums: kick and snare.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### Controls

**Grid view**
- Arrow keys: move the cursor around the grid
- Space: toggle a note/drum hit on or off at the cursor
- `Enter`: play the sequence starting from the cursor's beat
- `P`: play the whole sequence from the start
- `O`: open the settings panel
- `S`: save the current pattern to `song.json`
- `L`: load a pattern from `song.json`
- `Q`: quit
- `Esc`: stop playback early

**Settings panel**
- Up/Down: select a field (Tempo, Volume, Instrument, Length)
- Left/Right: adjust the selected field's value
- `Enter`/`Esc`: return to the grid (changing the length resizes the grid,
  keeping existing notes)

The status bar at the bottom always shows the current BPM, beat counter
during playback, volume, instrument, and grid length. During playback the
current column is highlighted in the grid in real time.

Notes are played with a selectable synth waveform (sine, square, or saw);
the kick and snare use short synthesized percussion sounds (a pitch-swept
sine for the kick, filtered noise for the snare).
