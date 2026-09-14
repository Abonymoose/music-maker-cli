# Music Maker CLI

A simple terminal-based step sequencer built with `curses` and `pygame`.

## Grid

- 54 columns represent 54 time steps (beats).
- The top 24 rows are piano notes, full chromatic, two octaves (C3 to
  B4, high notes at the top).
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

- Arrow keys: move the cursor around the grid (works even while playing)
- Space: toggle a note/drum hit on or off at the cursor. Toggling a piano
  note ON plays a quick preview tone at that note's pitch; toggling OFF
  and drum rows are silent.
- `Enter`: start playback from the cursor's beat; press `Enter` again to
  pause. Pausing again and pressing `Enter` resumes from where you left off.
- `P`: play the sequence from the very beginning (overrides any pause)
- `+`/`-`: adjust tempo by 10 BPM (default 120)
- `R`: toggle repeat (loop the song continuously when playing)
- `S`: save the current pattern to `song.json`
- `L`: load a pattern from `song.json`
- `Q`: quit

Notes are played with a simple sine-wave synth; the kick and snare use
short synthesized percussion sounds (a pitch-swept sine for the kick,
filtered noise for the snare).
