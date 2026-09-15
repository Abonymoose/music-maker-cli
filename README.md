# Music Maker CLI

A simple terminal-based step sequencer built with `curses` and `pygame`.

## Grid

- The song length is adjustable: `bars` (default 5) × `beats_per_bar`
  (fixed at 4) = total steps. The visible viewport automatically sizes
  itself to fit your terminal width, always in multiples of 4 (whole
  bars) — e.g. an 80-column terminal shows 24 columns at once. The view
  scrolls horizontally to follow the cursor and the playhead as the song
  grows past the viewport, so the grid effectively scrolls indefinitely
  as you add bars.
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

- Arrow keys: move the cursor around the grid; the view scrolls to keep
  the cursor visible (works even while playing)
- Space: toggle a note/drum hit on or off at the cursor. Toggling a hit
  ON plays a quick preview (a sine tone at that note's pitch for piano
  rows, the actual kick/snare sound for drum rows); toggling OFF is
  silent.
- `Enter`: start playback from the cursor's beat; press `Enter` again to
  pause. Pausing again and pressing `Enter` resumes from where you left off.
- `P`: play the sequence from the very beginning (overrides any pause)
- `+`/`-`: adjust tempo by 10 BPM (default 120)
- `R`: toggle repeat (loop the song continuously when playing)
- `O`: open the settings panel — `+`/`-` there adjusts the number of
  bars live, resizing the grid (existing notes are kept); `F` there
  fills the song out to however many whole bars fit your current
  terminal width; `O`, `Enter`, or `Esc` returns to the grid
- `S`: save the current pattern (and bar count) to `song.json`
- `L`: load a pattern from `song.json`
- `Q`: quit

Notes are played with a simple sine-wave synth; the kick and snare use
short synthesized percussion sounds (a pitch-swept sine for the kick,
filtered noise for the snare).
