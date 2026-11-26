"""The game loop's front end: frames, keys, the text box, messages, menus.

Scenes are written as plain step-by-step code. Each call here draws frames
until it's done:

    ui.say(draw, "Hello")          # types a message, waits for Enter
    i = ui.menu(draw, head, opts)  # arrow keys + Enter

`draw` is a function returning the Canvas to show for the current frame.
"""
import time
from collections import deque

from .display import BOX_COLS
from .term import size_message, term_size

RESET = "\x1b[0m"
BOX_BG = (16, 14, 24)
BORDER = (242, 200, 82)
WHITE = (240, 240, 245)
GREY = (170, 170, 182)
DIM = (95, 95, 105)
GOLD = (255, 220, 120)
RED = (255, 110, 100)
INNER = BOX_COLS - 2
TEXT_ROWS = 5


class Quit(Exception):
    pass


def fg(c):
    return "\x1b[38;2;%d;%d;%dm" % c


def bgc(c):
    return "\x1b[48;2;%d;%d;%dm" % c


def wrap(text, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            if len(cur) + len(w) + (1 if cur else 0) > width:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w) if cur else w
        lines.append(cur)
    return lines


def box_lines(rows):
    """rows: up to 5 lines, each a list of (colour, text) segments."""
    rows = list(rows)[:TEXT_ROWS] + [[]] * (TEXT_ROWS - len(rows))
    out = [bgc(BOX_BG) + fg(BORDER) + "╭" + "─" * INNER + "╮" + RESET]
    for seg in rows:
        used = 0
        s = [bgc(BOX_BG), fg(BORDER), "│"]
        for col, t in seg:
            t = t[:max(0, INNER - used)]
            used += len(t)
            s.append(fg(col) + t)
        s.append(" " * (INNER - used) + fg(BORDER) + "│" + RESET)
        out.append("".join(s))
    out.append(bgc(BOX_BG) + fg(BORDER) + "╰" + "─" * INNER + "╯" + RESET)
    return out


def message_rows(text, shown, speaker=None, more=False):
    """A typed message, optionally with a coloured speaker name."""
    prefix = (speaker[0] + ": ") if speaker else ""
    indent = "  " + " " * len(prefix)
    lines = wrap(text[:shown], INNER - 4 - len(prefix))
    rows = []
    for i in range(TEXT_ROWS):
        seg = []
        if i < len(lines):
            if i == 0 and speaker:
                seg.append((speaker[1], "  " + prefix))
                seg.append((WHITE, lines[0]))
            else:
                seg.append((WHITE, (indent if speaker else "  ") + lines[i]))
        rows.append(seg)
    if more:
        last = rows[TEXT_ROWS - 1]
        used = sum(len(t) for _, t in last)
        last.append((BORDER, " " * (INNER - 3 - used) + "▼"))
    return rows


class UI:
    FPS = 25

    def __init__(self, display, keys, headless=False):
        self.display = display
        self.keys = keys
        self.headless = headless          # tests: no drawing, no waiting
        self.tick = 0
        self.pending = deque()
        self.next_t = time.perf_counter()
        self.skipped = 0
        self.fast = False                 # hold-to-skip is not used; kept for tests

    @property
    def S(self):
        return self.display.S

    # ----- frames and keys ----------------------------------------------
    def poll(self):
        for k in self.keys.poll():
            if k == "quit":
                raise Quit()
            if k in ("bigger", "smaller"):
                self.display.adjust += 1 if k == "bigger" else -1
                continue
            self.pending.append(k)

    def take(self):
        ks = list(self.pending)
        self.pending.clear()
        return ks

    def advanced(self):
        """Enter or Down (the flashing arrow) moves the text along."""
        return any(k in ("enter", "down") for k in self.take())

    def wait_for_size(self):
        shown = None
        while True:
            cols, rows = term_size()
            if cols >= self.display.need[0] and rows >= self.display.need[1]:
                if shown is not None:
                    self.display.reset()
                    self.next_t = time.perf_counter()
                return cols, rows
            if (cols, rows) != shown:
                out = self.display.out
                out.write("\x1b[0m\x1b[2J\x1b[H" + size_message(cols, rows, self.display.need))
                out.flush()
                shown = (cols, rows)
            self.poll()
            time.sleep(0.2)

    def frame(self, cv, rows):
        """Show one frame, read keys, and keep time."""
        self.tick += 1
        if self.headless:
            self.poll()
            return
        cols, rows_ = self.wait_for_size()
        # heavy frames: if we're running late, skip drawing (never the game)
        late = time.perf_counter() - self.next_t > 0.5 / self.FPS
        if late and self.skipped < 3:
            self.skipped += 1
        else:
            self.skipped = 0
            self.display.present(cv, box_lines(rows), cols, rows_)
        self.poll()
        self.next_t += 1 / self.FPS
        delay = self.next_t - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        elif delay < -0.25:
            self.next_t = time.perf_counter()

    # ----- building blocks ----------------------------------------------
    def pause(self, draw, n, rows=()):
        for _ in range(n):
            self.frame(draw(), rows)

    def say(self, draw, text, speaker=None, wait=True, hold=14, speed=2):
        """Type out a message. wait=True waits for Enter/Down; otherwise it
        holds for `hold` frames (Enter skips)."""
        shown = 0
        self.take()
        while shown < len(text):
            shown = min(len(text), shown + speed)
            self.frame(draw(), message_rows(text, shown, speaker))
            if self.advanced():
                shown = len(text)
        if wait:
            self.take()
            while True:
                more = (self.tick // 8) % 2 == 0
                self.frame(draw(), message_rows(text, shown, speaker, more=more))
                if self.advanced():
                    return
        else:
            for _ in range(hold):
                self.frame(draw(), message_rows(text, shown, speaker))
                if self.advanced():
                    return

    def menu(self, draw, head, options, cols=2, desc=None, start=0, blocked=None, col_width=47, tag=None):
        """Arrow keys move, Enter picks. Returns the chosen index.

        head     segments for the top line, or a function (sel) -> segments
        options  list of segment lists, one per option
        desc     function (sel) -> segments, shown on the line under the options
        blocked  function (sel) -> message if that option can't be picked
        tag      what is being chosen; only test robots look at it
        """
        sel = start
        n = len(options)
        note = None
        self.take()
        while True:
            blink = (self.tick // 6) % 2 == 0
            rows = [head(sel) if callable(head) else head]
            for r in range(0, n, cols):
                seg = [(GOLD, "  ")]
                for i in range(r, min(n, r + cols)):
                    cells = list(options[i])
                    cur = "▶ " if (i == sel and blink) else "  "
                    seg.append((GOLD, cur))
                    width = 0
                    for j, (c, t) in enumerate(cells):
                        if i == sel and j == 0:
                            c = GOLD
                        seg.append((c, t))
                        width += len(t)
                    seg.append((GREY, " " * max(1, col_width - 2 - width)))
                rows.append(seg)
            if note:
                rows.append([(RED, "  " + note)])
            elif desc:
                rows.append(desc(sel))
            self.frame(draw(), rows)
            for k in self.take():
                note = None
                col, row = sel % cols, sel // cols
                if k == "left":
                    col = (col - 1) % cols
                elif k == "right":
                    col = (col + 1) % cols
                elif k == "up":
                    row -= 1
                elif k == "down":
                    row += 1
                elif k == "enter":
                    msg = blocked(sel) if blocked else None
                    if not msg:
                        return sel
                    note = msg
                    continue
                last_row = (n - 1) // cols
                row = row % (last_row + 1)
                new = row * cols + col
                if new >= n:
                    new = n - 1
                sel = new
