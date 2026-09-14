"""Curses rendering: full-screen grid, sidebar, status bar, settings panel."""

import curses

from model import NUM_ROWS, NUM_PIANO_ROWS, row_label, LENGTH_CHOICES, INSTRUMENT_CHOICES

SIDEBAR_WIDTH = 8
MIN_CELL_WIDTH = 3

SETTINGS_FIELDS = ["Tempo (BPM)", "Volume", "Instrument", "Length (steps)"]


def _cell_width(max_x, length):
    available = max(max_x - SIDEBAR_WIDTH, length * MIN_CELL_WIDTH)
    return max(MIN_CELL_WIDTH, available // length)


def draw_grid(stdscr, seq, settings):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    length = settings.length
    cell_width = _cell_width(max_x, length)

    title = " MUSIC MAKER CLI "
    stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD | curses.A_REVERSE)

    grid_top = 2
    for row in range(NUM_ROWS):
        y = grid_top + row
        if y >= max_y - 3:
            break
        is_drum = row >= NUM_PIANO_ROWS
        label = row_label(row).rjust(SIDEBAR_WIDTH - 1) + " "
        label_attr = curses.A_DIM if is_drum else curses.A_NORMAL
        stdscr.addstr(y, 0, label[:SIDEBAR_WIDTH], label_attr)

        for col in range(length):
            x = SIDEBAR_WIDTH + col * cell_width
            if x + cell_width > max_x:
                break
            active = seq.grid[row][col]
            is_cursor = (row == seq.cursor_row and col == seq.cursor_col)
            is_playing = (col == seq.playing_col)
            symbol = "#" if active else "."
            attr = curses.A_NORMAL
            if is_playing:
                attr |= curses.A_BOLD | curses.A_UNDERLINE
            if is_cursor:
                attr |= curses.A_REVERSE
            cell = f"[{symbol}]".ljust(cell_width)
            try:
                stdscr.addstr(y, x, cell[:cell_width], attr)
            except curses.error:
                pass

    help_y = max_y - 3
    if 0 <= help_y < max_y:
        try:
            stdscr.addstr(
                help_y, 0,
                "Arrows: move  Space: toggle  Enter: play from here  P: play all"
                "  O: settings  S: save  L: load  Q: quit"[: max_x - 1],
            )
        except curses.error:
            pass

    draw_status_bar(stdscr, seq, settings)
    stdscr.refresh()


def draw_status_bar(stdscr, seq, settings):
    max_y, max_x = stdscr.getmaxyx()
    status_y = max_y - 2
    beat = (seq.playing_col + 1) if seq.playing_col is not None else "-"
    volume_pct = int(round(settings.volume * 100))
    bar = (
        f" BPM: {settings.bpm}   Beat: {beat}/{settings.length}   "
        f"Volume: {volume_pct}%   Instrument: {settings.instrument}   Length: {settings.length}"
    )
    if 0 <= status_y < max_y:
        try:
            stdscr.addstr(status_y, 0, bar.ljust(max_x - 1)[: max_x - 1], curses.A_REVERSE)
        except curses.error:
            pass

    message_y = max_y - 1
    if 0 <= message_y < max_y and seq.status:
        try:
            stdscr.addstr(message_y, 0, seq.status[: max_x - 1])
        except curses.error:
            pass


def draw_settings(stdscr, settings, selected_index):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    title = " SETTINGS "
    stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD | curses.A_REVERSE)

    values = [
        str(settings.bpm),
        f"{int(round(settings.volume * 100))}%",
        settings.instrument,
        str(settings.length),
    ]

    for i, (field, value) in enumerate(zip(SETTINGS_FIELDS, values)):
        y = 2 + i * 2
        if y >= max_y:
            break
        attr = curses.A_REVERSE if i == selected_index else curses.A_NORMAL
        line = f"  {field:<18} < {value:^8} >"
        try:
            stdscr.addstr(y, 2, line, attr)
        except curses.error:
            pass

    help_y = 2 + len(SETTINGS_FIELDS) * 2 + 1
    if help_y < max_y:
        try:
            stdscr.addstr(
                help_y, 2,
                "Up/Down: select field   Left/Right: change value   Enter/Esc: back to grid",
            )
        except curses.error:
            pass

    stdscr.refresh()
