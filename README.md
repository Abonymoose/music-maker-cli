# Music Maker CLI

A simple terminal-based step sequencer built with `curses` and `pygame`.

## Grid

- 16 columns represent 16 time steps (beats).
- The top 16 rows are piano notes, two octaves (C5 down to C4/B4 area, high
  notes at the top).
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

- Arrow keys: move the cursor around the grid
- Space: toggle a note/drum hit on or off at the cursor
- `P`: play the sequence from left to right with synthesized sounds
- `S`: save the current pattern to `song.json`
- `L`: load a pattern from `song.json`
- `Q`: quit

Notes are played with a simple sine-wave synth; the kick and snare use
short synthesized percussion sounds (a pitch-swept sine for the kick,
filtered noise for the snare).
