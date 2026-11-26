"""Pixel canvas, sprites, shading helpers and bitmap fonts.

Drawing calls use LOGICAL coordinates (the low-res design grid). A canvas has
a scale, which may be fractional: every logical unit becomes `scale` real
pixels, and shapes are rasterised at the real resolution. So the same drawing
code gives retro art at scale 1, HD art at scale 2, and bigger or smaller
versions of a sprite at anything in between.
"""
import math
import random
import struct
import zlib

BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (int(round(c1[0] + (c2[0] - c1[0]) * t)),
            int(round(c1[1] + (c2[1] - c1[1]) * t)),
            int(round(c1[2] + (c2[2] - c1[2]) * t)))


def darker(c, f=0.7):
    return (max(0, int(c[0] * f)), max(0, int(c[1] * f)), max(0, int(c[2] * f)))


def lighter(c, f=0.35):
    return (min(255, int(c[0] + (255 - c[0]) * f)),
            min(255, int(c[1] + (255 - c[1]) * f)),
            min(255, int(c[2] + (255 - c[2]) * f)))


def I(v):
    """Round a logical coordinate to the logical pixel it falls in."""
    return int(math.floor(v + 0.5))


def rng(seed):
    return random.Random(seed)


class Canvas:
    def __init__(self, w, h, scale=1, fill=None):
        self.S = scale
        self.lw, self.lh = w, h
        self.w = int(round(w * scale))
        self.h = int(round(h * scale))
        self.px = [[fill] * self.w for _ in range(self.h)]

    def copy(self):
        c = Canvas.__new__(Canvas)
        c.S, c.lw, c.lh, c.w, c.h = self.S, self.lw, self.lh, self.w, self.h
        c.px = [row[:] for row in self.px]
        return c

    # ----- real-pixel access --------------------------------------------
    def setp(self, px, py, c):
        if c is not None and 0 <= px < self.w and 0 <= py < self.h:
            self.px[py][px] = c

    def getp(self, px, py):
        if 0 <= px < self.w and 0 <= py < self.h:
            return self.px[py][px]
        return None

    # ----- logical access -----------------------------------------------
    def set(self, x, y, c):
        """Fill one logical pixel."""
        if c is None:
            return
        S = self.S
        fx, fy = math.floor(x), math.floor(y)
        x0, x1 = max(0, int(round(fx * S))), min(self.w, int(round((fx + 1) * S)))
        y0, y1 = max(0, int(round(fy * S))), min(self.h, int(round((fy + 1) * S)))
        if x1 <= x0:
            return
        fill = [c] * (x1 - x0)
        for py in range(y0, y1):
            self.px[py][x0:x1] = fill

    def get(self, x, y):
        S = self.S
        return self.getp(int(round(math.floor(x) * S)), int(round(math.floor(y) * S)))

    # ----- shapes (colour may be a function (x, y) -> colour) -----------
    def _col(self, c, px, py):
        S = self.S
        return c((px + 0.5) / S - 0.5, (py + 0.5) / S - 0.5)

    def rect(self, x0, y0, x1, y1, c):
        S = self.S
        px0 = max(0, int(round(int(x0) * S)))
        px1 = min(self.w, int(round((int(x1) + 1) * S)))
        py0 = max(0, int(round(int(y0) * S)))
        py1 = min(self.h, int(round((int(y1) + 1) * S)))
        if px1 <= px0:
            return
        if callable(c):
            for py in range(py0, py1):
                row = self.px[py]
                for px in range(px0, px1):
                    v = self._col(c, px, py)
                    if v is not None:
                        row[px] = v
        elif c is not None:
            fill = [c] * (px1 - px0)
            for py in range(py0, py1):
                self.px[py][px0:px1] = fill

    def ellipse(self, cx, cy, rx, ry, c):
        S = self.S
        call = callable(c)
        y_lo = max(0, int(math.floor((cy - ry) * S)) - 1)
        y_hi = min(self.h, int(math.ceil((cy + ry) * S)) + 1)
        x_lo = max(0, int(math.floor((cx - rx) * S)) - 1)
        x_hi = min(self.w, int(math.ceil((cx + rx) * S)) + 1)
        for py in range(y_lo, y_hi):
            dy = ((py + 0.5) / S - cy) / ry
            dy2 = dy * dy
            if dy2 > 1.0:
                continue
            row = self.px[py]
            for px in range(x_lo, x_hi):
                dx = ((px + 0.5) / S - cx) / rx
                if dx * dx + dy2 <= 1.0:
                    v = self._col(c, px, py) if call else c
                    if v is not None:
                        row[px] = v

    def polygon(self, pts, c):
        S = self.S
        call = callable(c)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        y_lo = max(0, int(math.floor(min(ys) * S)) - 1)
        y_hi = min(self.h, int(math.ceil(max(ys) * S)) + 1)
        x_lo = max(0, int(math.floor(min(xs) * S)) - 1)
        x_hi = min(self.w, int(math.ceil(max(xs) * S)) + 1)
        for py in range(y_lo, y_hi):
            row = self.px[py]
            ly = (py + 0.5) / S
            for px in range(x_lo, x_hi):
                if point_in_poly((px + 0.5) / S, ly, pts):
                    v = self._col(c, px, py) if call else c
                    if v is not None:
                        row[px] = v

    def line(self, x0, y0, x1, y1, c):
        """A 1-real-pixel line."""
        S = self.S
        off = (S - 1) / 2
        x0, y0 = int(round(x0 * S + off)), int(round(y0 * S + off))
        x1, y1 = int(round(x1 * S + off)), int(round(y1 * S + off))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        call = callable(c)
        while True:
            self.setp(x0, y0, self._col(c, x0, y0) if call else c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def thick_line(self, x0, y0, x1, y1, r, c):
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2 * max(1, self.S)) + 1
        for i in range(steps + 1):
            t = i / steps
            self.ellipse(lerp(x0, x1, t), lerp(y0, y1, t), r, r, c)

    # ----- compositing --------------------------------------------------
    def paste(self, other, ox, oy):
        """Paste another canvas with its top-left at logical (ox, oy)."""
        bx, by = int(round(ox * self.S)), int(round(oy * self.S))
        for y in range(other.h):
            ty = by + y
            if not 0 <= ty < self.h:
                continue
            row, src = self.px[ty], other.px[y]
            for x in range(other.w):
                c = src[x]
                if c is not None and 0 <= bx + x < self.w:
                    row[bx + x] = c

    def outline(self, c, diagonal=False):
        """Outline every non-empty region (for sprite canvases)."""
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diagonal:
            nb += [(1, 1), (-1, -1), (1, -1), (-1, 1)]
        add = []
        for y in range(self.h):
            row = self.px[y]
            for x in range(self.w):
                if row[x] is None:
                    for dx, dy in nb:
                        if self.getp(x + dx, y + dy) is not None:
                            add.append((x, y))
                            break
        for x, y in add:
            self.px[y][x] = c

    def rim_light(self, side, col, amt=0.45):
        """Tint the edge pixels on one side (call before outlining)."""
        dx = 1 if side == "right" else -1
        marks = []
        for y in range(self.h):
            row = self.px[y]
            for x in range(self.w):
                if row[x] is not None and self.getp(x + dx, y) is None:
                    marks.append((x, y))
        for x, y in marks:
            self.px[y][x] = mix(self.px[y][x], col, amt)

    # ----- output -------------------------------------------------------
    def to_ansi(self, bg=(12, 12, 18)):
        """Half-block text: each character cell shows two pixels."""
        out = []
        for y in range(0, self.h, 2):
            top_row = self.px[y]
            bot_row = self.px[y + 1] if y + 1 < self.h else None
            row = []
            last = None
            for x in range(self.w):
                top = top_row[x] or bg
                bot = (bot_row[x] if bot_row else None) or bg
                key = (top, bot)
                if key != last:
                    row.append("\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm" % (top + bot))
                    last = key
                row.append("▀")
            row.append("\x1b[0m")
            out.append("".join(row))
        return out

    def save_png(self, path, scale=None, bg=(12, 12, 18), pad=0):
        scale = scale or max(1, int(8 // max(1, self.S)))
        W = (self.w + pad * 2) * scale
        H = (self.h + pad * 2) * scale
        raw = bytearray()
        for py in range(H):
            raw.append(0)
            y = py // scale - pad
            for px in range(W):
                x = px // scale - pad
                c = self.px[y][x] if (0 <= x < self.w and 0 <= y < self.h) else None
                raw.extend(c or bg)

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        png += chunk(b"IEND", b"")
        with open(path, "wb") as f:
            f.write(png)


def point_in_poly(x, y, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y):
            if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


# =========================================================================
# Sprites: canvases turned into runs of pixels, for fast drawing
# =========================================================================
class Sprite:
    def __init__(self, rows, w, h, anchor=(0, 0)):
        self.rows, self.w, self.h, self.anchor = rows, w, h, anchor

    @classmethod
    def from_canvas(cls, cv, anchor=(0, 0)):
        """anchor: the real-pixel point of the sprite that gets positioned."""
        rows = []
        for src in cv.px:
            runs = []
            x = 0
            n = len(src)
            while x < n:
                if src[x] is None:
                    x += 1
                    continue
                start = x
                while x < n and src[x] is not None:
                    x += 1
                runs.append((start, src[start:x]))
            rows.append(runs)
        return cls(rows, cv.w, cv.h, anchor)

    def blit(self, cv, x, y, clip_y=None):
        """Draw with the anchor at real pixel (x, y); cut off below clip_y."""
        x -= self.anchor[0]
        y -= self.anchor[1]
        W, H = cv.w, cv.h
        for dy, runs in enumerate(self.rows):
            ty = y + dy
            if ty < 0:
                continue
            if ty >= H or (clip_y is not None and ty > clip_y):
                break
            row = cv.px[ty]
            for rx, cols in runs:
                tx = x + rx
                n = len(cols)
                if tx >= W or tx + n <= 0:
                    continue
                a = -tx if tx < 0 else 0
                b = W - tx if tx + n > W else n
                row[tx + a:tx + b] = cols[a:b]

    def mapped(self, fn):
        return Sprite([[(x, [fn(c) for c in cols]) for x, cols in runs] for runs in self.rows],
                      self.w, self.h, self.anchor)

    def silhouette(self, col):
        return self.mapped(lambda c: col)

    def flipped(self):
        rows = [[(self.w - x - len(cols), cols[::-1]) for x, cols in reversed(runs)]
                for runs in self.rows]
        return Sprite(rows, self.w, self.h, (self.w - 1 - self.anchor[0], self.anchor[1]))


# =========================================================================
# Shading helpers
# =========================================================================
LIGHT = (-0.55, -0.75)  # light comes from the top-left


def ball_shader(cx, cy, rx, ry, base, hi=None, lo=None, bands=(0.45, -0.3)):
    """Banded 3-tone shading for a round shape."""
    hi = hi or lighter(base, 0.35)
    lo = lo or darker(base, 0.72)
    lx, ly = LIGHT
    b_hi, b_lo = bands

    def f(x, y):
        t = (x + 0.5 - cx) / rx * lx + (y + 0.5 - cy) / ry * ly
        if t > b_hi:
            return hi
        if t < b_lo:
            return lo
        return base
    return f


def vgrad(y0, y1, stops, s=1, dither=True):
    """Vertical gradient through colour stops, with ordered dithering.
    `s` is the canvas scale, so the dither pattern stays one real pixel."""
    span = max(1, y1 - y0)
    last = len(stops) - 1

    def f(x, y):
        t = max(0.0, min(0.9999, (y - y0) / span))
        seg = t * last
        i = int(seg)
        frac = seg - i
        a, b = stops[i], stops[min(i + 1, last)]
        if not dither:
            return mix(a, b, frac)
        q = frac * 4
        lo_step = int(q)
        bx = int(math.floor((x + 0.5) * s)) % 4
        by = int(math.floor((y + 0.5) * s)) % 4
        step = lo_step + (1 if (q - lo_step) > (BAYER4[by][bx] + 0.5) / 16 else 0)
        return mix(a, b, step / 4)
    return f


# =========================================================================
# Bitmap fonts
# =========================================================================
_FONT_SRC = """
A .###. #...# #...# ##### #...# #...# #...#
B ####. #...# #...# ####. #...# #...# ####.
C .###. #...# #.... #.... #.... #...# .###.
D ####. #...# #...# #...# #...# #...# ####.
E ##### #.... #.... ####. #.... #.... #####
F ##### #.... #.... ####. #.... #.... #....
G .###. #...# #.... #.### #...# #...# .####
H #...# #...# #...# ##### #...# #...# #...#
I .###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.
J ..### ...#. ...#. ...#. ...#. #..#. .##..
K #...# #..#. #.#.. ##... #.#.. #..#. #...#
L #.... #.... #.... #.... #.... #.... #####
M #...# ##.## #.#.# #.#.# #...# #...# #...#
N #...# #...# ##..# #.#.# #..## #...# #...#
O .###. #...# #...# #...# #...# #...# .###.
P ####. #...# #...# ####. #.... #.... #....
Q .###. #...# #...# #...# #.#.# #..#. .##.#
R ####. #...# #...# ####. #.#.. #..#. #...#
S .#### #.... #.... .###. ....# ....# ####.
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
U #...# #...# #...# #...# #...# #...# .###.
V #...# #...# #...# #...# #...# .#.#. ..#..
W #...# #...# #...# #.#.# #.#.# #.#.# .#.#.
X #...# #...# .#.#. ..#.. .#.#. #...# #...#
Y #...# #...# .#.#. ..#.. ..#.. ..#.. ..#..
Z ##### ....# ...#. ..#.. .#... #.... #####
0 .###. #...# #..## #.#.# ##..# #...# .###.
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.
2 .###. #...# ....# ...#. ..#.. .#... #####
3 ####. ....# ....# .###. ....# ....# ####.
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#.
5 ##### #.... ####. ....# ....# #...# .###.
6 .###. #.... #.... ####. #...# #...# .###.
7 ##### ....# ...#. ..#.. .#... .#... .#...
8 .###. #...# #...# .###. #...# #...# .###.
9 .###. #...# #...# .#### ....# ....# .###.
- ..... ..... ..... .###. ..... ..... .....
. ..... ..... ..... ..... ..... ..... ..#..
! ..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..
? .###. #...# ....# ...#. ..#.. ..... ..#..
' ..#.. ..#.. ..... ..... ..... ..... .....
: ..... ..#.. ..... ..... ..... ..#.. .....
/ ....# ....# ...#. ..#.. .#... #.... #....
"""

_MINI_SRC = """
A .#. #.# ### #.# #.#
B ##. #.# ##. #.# ##.
C .## #.. #.. #.. .##
D ##. #.# #.# #.# ##.
E ### #.. ##. #.. ###
F ### #.. ##. #.. #..
G .## #.. #.# #.# .##
H #.# #.# ### #.# #.#
I ### .#. .#. .#. ###
J ..# ..# ..# #.# .#.
K #.# #.# ##. #.# #.#
L #.. #.. #.. #.. ###
M #.# ### ### #.# #.#
N ##. #.# #.# #.# #.#
O .#. #.# #.# #.# .#.
P ##. #.# ##. #.. #..
Q .#. #.# #.# ##. .##
R ##. #.# ##. #.# #.#
S .## #.. .#. ..# ##.
T ### .#. .#. .#. .#.
U #.# #.# #.# #.# ###
V #.# #.# #.# #.# .#.
W #.# #.# ### ### #.#
X #.# #.# .#. #.# #.#
Y #.# #.# .#. .#. .#.
Z ### ..# .#. #.. ###
0 ### #.# #.# #.# ###
1 .#. ##. .#. .#. ###
2 ##. ..# .#. #.. ###
3 ##. ..# .#. ..# ##.
4 #.# #.# ### ..# ..#
5 ### #.. ##. ..# ##.
6 .## #.. ### #.# ###
7 ### ..# .#. .#. .#.
8 ### #.# ### #.# ###
9 ### #.# ### ..# ##.
/ ..# ..# .#. #.. #..
! .#. .#. .#. ... .#.
. ... ... ... ... .#.
- ... ... ### ... ...
' .#. .#. ... ... ...
? ##. ..# .#. ... .#.
"""


def _parse(src):
    out = {}
    for line in src.strip().splitlines():
        k, *rows = line.split()
        out[k] = "".join(rows)
    return out


_FONT = _parse(_FONT_SRC)
_MINI = _parse(_MINI_SRC)


def text_width(s, spacing=1):
    return len(s) * (5 + spacing) - spacing


def draw_text(cv, x, y, s, color, shadow=None, spacing=1, size=1):
    """5x7 font. `size` multiplies the letter size (in logical pixels)."""
    for ch in s.upper():
        g = _FONT.get(ch, "")
        for i, bit in enumerate(g):
            if bit == "#":
                gx, gy = x + (i % 5) * size, y + (i // 5) * size
                if size == 1:
                    if shadow:
                        cv.set(gx + 1, gy + 1, shadow)
                    cv.set(gx, gy, color)
                else:
                    if shadow:
                        cv.rect(gx + 1, gy + 1, gx + size, gy + size, shadow)
                    cv.rect(gx, gy, gx + size - 1, gy + size - 1, color)
        x += (5 + spacing) * size


def mini_width(s):
    return len(s) * 4 - 1


def draw_mini(cv, x, y, s, color, shadow=None):
    """3x5 font."""
    for ch in s.upper():
        g = _MINI.get(ch, "")
        for i, bit in enumerate(g):
            if bit == "#":
                gx, gy = x + i % 3, y + i // 3
                if shadow:
                    cv.set(gx + 1, gy + 1, shadow)
                cv.set(gx, gy, color)
        x += 4
