"""Sixel output: real image pixels inside the terminal.

Windows Terminal 1.22+ (and others such as WezTerm, foot, mlterm, xterm -ti 340)
can display Sixel images. Each art pixel is drawn as a k x k block of real
pixels, so the picture can fill the window at any size.

The encoder caches each 6-pixel-tall band, so frames where only a small part
changes are cheap to encode.
"""
import os
import re
import sys
import time


# =========================================================================
# Asking the terminal about itself
# =========================================================================
def _read_reply(seconds):
    """Read whatever the terminal sends back within `seconds`."""
    buf = ""
    end = time.perf_counter() + seconds
    if os.name == "nt":
        import msvcrt
        while time.perf_counter() < end:
            while msvcrt.kbhit():
                buf += msvcrt.getwch()
            time.sleep(0.01)
    else:
        import select
        fd = sys.stdin.fileno()
        while time.perf_counter() < end:
            if select.select([fd], [], [], 0.02)[0]:
                buf += os.read(fd, 256).decode(errors="ignore")
    return buf


def query_terminal(cols, rows):
    """Returns (cell_w, cell_h, sixel_supported). sixel_supported is
    True / False, or None if the terminal didn't answer."""
    restore = None
    if os.name == "nt":
        # let the terminal's answers reach us as text (VT input mode), briefly
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.GetStdHandle(-10)
            mode = ctypes.c_uint32()
            if k32.GetConsoleMode(h, ctypes.byref(mode)):
                k32.SetConsoleMode(h, mode.value | 0x0200)
                restore = (k32, h, mode.value)
        except Exception:
            pass
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        restore = ("posix", fd, old)
    try:
        sys.stdout.write("\x1b[16t\x1b[14t\x1b[c")   # cell size, window size, device attributes
        sys.stdout.flush()
        reply = _read_reply(0.6)
    finally:
        if restore and restore[0] == "posix":
            import termios
            termios.tcsetattr(restore[1], termios.TCSADRAIN, restore[2])
        elif restore:
            restore[0].SetConsoleMode(restore[1], restore[2])

    cell_w = cell_h = None
    m = re.search(r"\x1b\[6;(\d+);(\d+)t", reply)
    if m:
        cell_h, cell_w = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"\x1b\[4;(\d+);(\d+)t", reply)
        if m and cols and rows:
            cell_h, cell_w = int(m.group(1)) // rows, int(m.group(2)) // cols
    sixel = None
    m = re.search(r"\x1b\[\?([\d;]+)c", reply)
    if m:
        sixel = "4" in m.group(1).split(";")
    return cell_w or 10, cell_h or 20, sixel, bool(cell_w)


# =========================================================================
# Encoder
# =========================================================================
class SixelEncoder:
    def __init__(self):
        self.palette = []          # list of (r, g, b)
        self.index = {}            # (r, g, b) -> register
        self.cache = {}

    def reg(self, c):
        i = self.index.get(c)
        if i is None:
            if len(self.palette) < 256:
                i = len(self.palette)
                self.palette.append(c)
            else:                  # out of registers: nearest existing colour
                i = min(range(256), key=lambda j: sum((a - b) ** 2 for a, b in zip(c, self.palette[j])))
            self.index[c] = i
        return i

    def encode(self, px, k):
        """px: rows of (r, g, b). Each pixel becomes k x k real pixels."""
        h, w = len(px), len(px[0])
        out_h, out_w = h * k, w * k
        for row in px:                         # register any new colours
            for c in set(row):
                if c not in self.index:
                    self.reg(c)
        parts = ["\x1bPq", '"1;1;%d;%d' % (out_w, out_h)]
        parts += ["#%d;2;%d;%d;%d" % (i, r * 100 // 255, g * 100 // 255, b * 100 // 255)
                  for i, (r, g, b) in enumerate(self.palette)]
        if len(self.cache) > 6000:
            self.cache.clear()
        idx = self.index
        for y0 in range(0, out_h, 6):
            src = {}
            for bit in range(6):
                y = y0 + bit
                if y < out_h:
                    r = y // k
                    src[r] = src.get(r, 0) | (1 << bit)
            key = (k, tuple(src.items())) + tuple(tuple(px[r]) for r in src)
            band = self.cache.get(key)
            if band is None:
                masks = {}
                for r, bits in src.items():
                    row = px[r]
                    for x in range(w):
                        ci = idx[row[x]]
                        arr = masks.get(ci)
                        if arr is None:
                            arr = masks[ci] = [0] * w
                        arr[x] |= bits
                chunks = []
                for ci, arr in masks.items():
                    s = ["#%d" % ci]
                    x = 0
                    last = w
                    while last > 0 and arr[last - 1] == 0:   # drop empty tail
                        last -= 1
                    while x < last:
                        v = arr[x]
                        n = 1
                        while x + n < last and arr[x + n] == v:
                            n += 1
                        ch = chr(63 + v)
                        total = n * k
                        s.append(("!%d%s" % (total, ch)) if total > 3 else ch * total)
                        x += n
                    chunks.append("".join(s))
                band = "$".join(chunks) + "-"
                self.cache[key] = band
            parts.append(band)
        parts.append("\x1b\\")
        return "".join(parts)


# =========================================================================
# Screen layout: picture on top, text box pinned to the bottom
# =========================================================================
class SixelView:
    BOX_ROWS = 6
    BOX_COLS = 100

    def __init__(self, cell_w, cell_h):
        self.cell_w, self.cell_h = cell_w, cell_h
        self.enc = SixelEncoder()
        self.adjust = 0            # player's +/- tweak to the automatic size
        self.last_layout = None

    def layout(self, img_w, img_h, cols, rows):
        room_w = cols * self.cell_w
        room_h = (rows - self.BOX_ROWS) * self.cell_h
        k = max(1, min(room_w // img_w, room_h // img_h) + self.adjust)
        pic_cols = -(-img_w * k // self.cell_w)
        left = max(0, (cols - pic_cols) // 2)
        return k, left

    def frame(self, cv, box_lines, cols, rows):
        k, left = self.layout(cv.w, cv.h, cols, rows)
        lay = (k, left, cols, rows)
        out = []
        if lay != self.last_layout:            # size changed: wipe old picture
            out.append("\x1b[0m\x1b[2J")
            self.last_layout = lay
        out.append("\x1b[1;%dH" % (left + 1))
        out.append(self.enc.encode(cv.px, k))
        box_left = max(0, (cols - self.BOX_COLS) // 2)
        top = rows - self.BOX_ROWS + 1
        for i, line in enumerate(box_lines):
            out.append("\x1b[%d;%dH%s" % (top + i, box_left + 1, line))
        return "".join(out)
