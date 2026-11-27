"""The game loop's front end: frames, keys, the text box, messages, menus.

Scenes are written as plain step-by-step code. Each call here draws frames
until it's done:

    ui.say(draw, "Hello")          # types a message, waits for Enter
    i = ui.menu(draw, head, opts)  # arrow keys + Enter

`draw` is a function returning the Canvas to show for the current frame.
"""
import time
from collections import deque

from . import sound
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


# Options that mean "never mind": Esc picks the last one of these a menu has.
CANCEL = ("Back", "Leave", "Never mind", "Back to the road", "Not now", "Not yet", "Stay a while longer",
          "Stay here", "Keep it", "Go back", "Keep playing", "Keep fighting")


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
        self.confirm_quit = None          # (question, note, stay, leave): ask before Esc leaves
        self.want_quit = False
        self.tester = None                # `play --test`: a function () -> [(label, action)]
        self.want_test = False
        self.battle = None                # the battle on screen, if there is one
        self.cancel = None                # the "never mind" option of the menu on screen, if it has one

    @property
    def S(self):
        return self.display.S

    # ----- frames and keys ----------------------------------------------
    def poll(self):
        for k in self.keys.poll():
            if k == "quit" and self.cancel is not None:        # in a menu, Esc backs out of the menu
                self.pending.append("back")
                continue
            if k == "quit":
                if self.confirm_quit and not self.headless:
                    self.want_quit = True
                    continue
                raise Quit()
            if k in ("bigger", "smaller"):
                self.display.adjust += 1 if k == "bigger" else -1
                continue
            if k == "tester":
                self.want_test = bool(self.tester) and not self.headless
                continue
            if k == "sound":                       # V: normal, quiet, off
                sound.cycle()
                sound.fx("select")
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
        if self.want_quit:
            self.want_quit = False
            self.ask_quit(cv, cols, rows_)
        if self.want_test:
            self.want_test = False
            self.ask_tester(cv, cols, rows_)
        self.next_t += 1 / self.FPS
        delay = self.next_t - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        elif delay < -0.25:
            self.next_t = time.perf_counter()

    def ask_quit(self, cv, cols, rows_):
        """Esc was pressed: check before leaving. Esc again goes back to the game."""
        question, note, stay, leave = self.confirm_quit
        sel = 0
        while True:
            blink = int(time.perf_counter() * 4) % 2 == 0
            rows = [[(WHITE, "  " + question)], [(GREY, "  " + note)], []]
            for i, label in enumerate((stay, leave)):
                rows.append([(GOLD, "  " + ("\u25b6 " if (i == sel and blink) else "  ")),
                             (GOLD if i == sel else WHITE, label)])
            self.display.present(cv, box_lines(rows), cols, rows_)
            for k in self.keys.poll():
                if k in ("up", "down"):
                    sel = 1 - sel
                elif k == "quit" or (k == "enter" and sel == 0):
                    self.pending.clear()
                    self.next_t = time.perf_counter()
                    return
                elif k == "enter":
                    raise Quit()
            time.sleep(0.04)

    def ask_tester(self, cv, cols, rows_):
        """T was pressed in test mode: dials for whoever is trying the game out.
        Up/Down choose a line, Left lowers it, Right raises it. T or Esc goes back.
        self.tester() gives the lines: (label, current value, lower, raise)."""
        opts = self.tester()
        sel = 0
        while True:
            blink = int(time.perf_counter() * 4) % 2 == 0
            rows = [[(GOLD, "  Tester's dials"),
                     (GREY, "     Up/Down choose.  Left lowers, Right raises.  T or Esc goes back.")]]
            top = max(0, min(sel - 1, len(opts) - 4))
            for i in range(top, min(len(opts), top + 4)):
                label, value = opts[i][0], opts[i][1]
                rows.append([(GOLD, "  " + ("\u25b6 " if (i == sel and blink) else "  ")),
                             (GOLD if i == sel else WHITE, label.ljust(20)),
                             (GOLD if i == sel else GREY, "\u25c0 " if i == sel else "  "),
                             (WHITE, value),
                             (GOLD, " \u25b6" if i == sel else "")])
            self.display.present(cv, box_lines(rows), cols, rows_)
            for k in self.keys.poll():
                if k == "up":
                    sel = (sel - 1) % len(opts)
                elif k == "down":
                    sel = (sel + 1) % len(opts)
                elif k in ("quit", "tester"):
                    self.pending.clear()
                    self.next_t = time.perf_counter()
                    return
                elif k in ("left", "right", "enter"):
                    opts[sel][2 if k == "left" else 3]()
                    opts = self.tester()
                    sel = min(sel, len(opts) - 1)
            time.sleep(0.04)

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
                    sound.fx("next")
                    return
        else:
            for _ in range(hold):
                self.frame(draw(), message_rows(text, shown, speaker))
                if self.advanced():
                    return

    def menu(self, draw, head, options, cols=2, desc=None, start=0, blocked=None, col_width=47, tag=None):
        """Arrow keys move, Enter picks, Esc backs out (when there is a way out). Returns the chosen index."""
        outs = [i for i, o in enumerate(options) if "".join(t for _, t in o).strip() in CANCEL]
        was, self.cancel = self.cancel, (outs[-1] if outs else None)
        try:
            return self._menu(draw, head, options, cols, desc, start, blocked, col_width, tag)
        finally:
            self.cancel = was

    def pager(self, draw, rows, n, start=0, blocked=None, cancel=False, tag=None):
        """A full page for each choice. Left / Right flips through them, Enter picks,
        Esc backs out (when `cancel`). Returns the index chosen, or None for "back".

        draw     function (sel) -> the picture for that choice
        rows     function (sel, blink, note) -> the text rows under it
        blocked  function (sel) -> message if that choice can't be picked
        tag      what is being chosen; only test robots look at it
        """
        sel = start
        note = None
        was, self.cancel = self.cancel, (-1 if cancel else None)
        self.take()
        try:
            while True:
                blink = (self.tick // 8) % 2 == 0
                self.frame(draw(sel), rows(sel, blink, note))
                for k in self.take():
                    if k == "back" and cancel:
                        sound.fx("next")
                        return None
                    if k in ("left", "up"):
                        sel, note = (sel - 1) % n, None
                        sound.fx("move")
                    elif k in ("right", "down"):
                        sel, note = (sel + 1) % n, None
                        sound.fx("move")
                    elif k == "enter":
                        note = blocked(sel) if blocked else None
                        if not note:
                            sound.fx("select")
                            return sel
                        sound.fx("deny")
        finally:
            self.cancel = was

    def _menu(self, draw, head, options, cols, desc, start, blocked, col_width, tag):
        """The menu itself.

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
                if k == "back" and self.cancel is not None:
                    sound.fx("next")
                    return self.cancel
                if k in ("left", "right", "up", "down"):
                    sound.fx("move")
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
                        sound.fx("select")
                        return sel
                    sound.fx("deny")
                    note = msg
                    continue
                last_row = (n - 1) // cols
                row = row % (last_row + 1)
                new = row * cols + col
                if new >= n:
                    new = n - 1
                sel = new

    def grid_menu(self, draw, head, rows, desc=None, start=(0, 0), blocked=None, tag=None):
        """Like menu(), but each row can hold a different number of cells.

        rows     list of rows; each row is a list of cells (segment lists)
        Returns (row, column) of the chosen cell. desc and blocked take (row, column).
        """
        r, c = start
        r = max(0, min(r, len(rows) - 1))
        c = max(0, min(c, len(rows[r]) - 1))
        note = None
        self.take()
        while True:
            blink = (self.tick // 6) % 2 == 0
            out = [head]
            for ri, cells in enumerate(rows):
                width = (INNER - 2) // len(cells)
                seg = [(GOLD, "  ")]
                for ci, cell in enumerate(cells):
                    here = (ri, ci) == (r, c)
                    seg.append((GOLD, "▶ " if (here and blink) else "  "))
                    used = 2
                    for j, (col, t) in enumerate(cell):
                        seg.append((GOLD if (here and j == 0) else col, t))
                        used += len(t)
                    seg.append((GREY, " " * max(0, width - used)))
                out.append(seg)
            if note:
                out.append([(RED, "  " + note)])
            elif desc:
                out.append(desc(r, c))
            self.frame(draw(), out)
            for k in self.take():
                note = None
                if k in ("left", "right", "up", "down"):
                    sound.fx("move")
                if k == "left":
                    c = (c - 1) % len(rows[r])
                elif k == "right":
                    c = (c + 1) % len(rows[r])
                elif k in ("up", "down"):
                    nr = (r + (1 if k == "down" else -1)) % len(rows)
                    old, new = len(rows[r]), len(rows[nr])
                    c = int(round(c * (new - 1) / (old - 1))) if old > 1 else 0
                    c = max(0, min(c, new - 1))
                    r = nr
                elif k == "enter":
                    msg = blocked(r, c) if blocked else None
                    if not msg:
                        sound.fx("select")
                        return r, c
                    sound.fx("deny")
                    note = msg

