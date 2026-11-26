"""Tiny pixel-art engine for Entwined.

Draws into an RGB canvas, then either prints it to a truecolor terminal using
half-block characters (2 pixels per character cell) or saves it as a PNG.
Standard library only.
"""
import math
import random
import struct
import sys
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
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


def darker(c, f=0.7):
    return tuple(max(0, int(v * f)) for v in c)


def lighter(c, f=0.35):
    return tuple(min(255, int(v + (255 - v) * f)) for v in c)


SCALE = 1  # resolution multiplier of the scene being drawn (used by dithering)


def I(v):
    """Round a logical coordinate to the logical pixel it falls in."""
    return int(math.floor(v + 0.5))


class Canvas:
    """All drawing calls use LOGICAL coordinates (the original low-res grid).
    With scale=2 every logical pixel becomes 2x2 real pixels, and shapes are
    rasterised at the real resolution, so curves and outlines get finer.
    `setp` / `getp` address real (physical) pixels for extra-fine detail."""

    def __init__(self, w, h, fill=None, scale=1):
        self.S = scale
        self.lw, self.lh = w, h
        self.w, self.h = w * scale, h * scale
        self.px = [[fill for _ in range(self.w)] for _ in range(self.h)]

    # ----- physical access ----------------------------------------------
    def inside(self, px, py):
        return 0 <= px < self.w and 0 <= py < self.h

    def setp(self, px, py, c):
        px, py = int(px), int(py)
        if c is not None and self.inside(px, py):
            self.px[py][px] = c

    def getp(self, px, py):
        if self.inside(px, py):
            return self.px[py][px]
        return None

    # ----- logical access -----------------------------------------------
    def set(self, x, y, c):
        """Fill one logical pixel (an S x S block)."""
        if c is None:
            return
        S = self.S
        bx, by = int(math.floor(x)) * S, int(math.floor(y)) * S
        for py in range(by, by + S):
            for px in range(bx, bx + S):
                self.setp(px, py, c)

    def get(self, x, y):
        return self.getp(int(math.floor(x)) * self.S, int(math.floor(y)) * self.S)

    # ----- shapes (colour may be a function (x, y) -> colour) -----------
    def _col(self, c, px, py):
        if not callable(c):
            return c
        S = self.S
        return c((px + 0.5) / S - 0.5, (py + 0.5) / S - 0.5)

    def rect(self, x0, y0, x1, y1, c):
        S = self.S
        for py in range(int(y0) * S, (int(y1) + 1) * S):
            for px in range(int(x0) * S, (int(x1) + 1) * S):
                self.setp(px, py, self._col(c, px, py))

    def ellipse(self, cx, cy, rx, ry, c):
        S = self.S
        for py in range(int(math.floor((cy - ry) * S)) - 1, int(math.ceil((cy + ry) * S)) + 1):
            for px in range(int(math.floor((cx - rx) * S)) - 1, int(math.ceil((cx + rx) * S)) + 1):
                dx = ((px + 0.5) / S - cx) / rx
                dy = ((py + 0.5) / S - cy) / ry
                if dx * dx + dy * dy <= 1.0:
                    self.setp(px, py, self._col(c, px, py))

    def polygon(self, pts, c):
        S = self.S
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        for py in range(int(math.floor(min(ys) * S)) - 1, int(math.ceil(max(ys) * S)) + 1):
            for px in range(int(math.floor(min(xs) * S)) - 1, int(math.ceil(max(xs) * S)) + 1):
                if point_in_poly((px + 0.5) / S, (py + 0.5) / S, pts):
                    self.setp(px, py, self._col(c, px, py))

    def line(self, x0, y0, x1, y1, c):
        """A 1-real-pixel line (finer than a logical pixel when S > 1)."""
        S = self.S
        off = (S - 1) / 2
        x0, y0 = int(round(x0 * S + off)), int(round(y0 * S + off))
        x1, y1 = int(round(x1 * S + off)), int(round(y1 * S + off))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.setp(x0, y0, self._col(c, x0, y0))
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
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2 * self.S) + 1
        for i in range(steps + 1):
            t = i / steps
            self.ellipse(lerp(x0, x1, t), lerp(y0, y1, t), r, r, c)

    # ----- compositing --------------------------------------------------
    def paste(self, other, ox, oy):
        S = self.S
        for py in range(other.h):
            for px in range(other.w):
                c = other.px[py][px]
                if c is not None:
                    self.setp(int(ox * S) + px, int(oy * S) + py, c)

    def outline(self, c, diagonal=False):
        """Add an outline around every non-empty region (sprite canvases)."""
        add = []
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diagonal:
            nb += [(1, 1), (-1, -1), (1, -1), (-1, 1)]
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is None:
                    for dx, dy in nb:
                        if self.getp(x + dx, y + dy) is not None:
                            add.append((x, y))
                            break
        for x, y in add:
            self.px[y][x] = c

    # ----- output -------------------------------------------------------
    def to_ansi(self, bg=(12, 12, 18)):
        out = []
        for y in range(0, self.h, 2):
            row = []
            last = None
            for x in range(self.w):
                top = self.px[y][x] or bg
                bot = (self.px[y + 1][x] if y + 1 < self.h else None) or bg
                key = (top, bot)
                if key != last:
                    row.append("\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm" % (top + bot))
                    last = key
                row.append("▀")
            row.append("\x1b[0m")
            out.append("".join(row))
        return "\n".join(out)

    def print(self):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(self.to_ansi())

    def save_png(self, path, scale=None, bg=(12, 12, 18), pad=None):
        """Save as PNG, each real pixel drawn as a scale x scale square,
        with a small terminal-coloured border. Same output size at any S."""
        scale = scale or max(1, 8 // self.S)
        pad = pad if pad is not None else 2 * self.S
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
        png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        png += chunk(b"IEND", b"")
        with open(path, "wb") as f:
            f.write(png)


def point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y):
            xcross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xcross:
                inside = not inside
        j = i
    return inside


# ----- shading helpers ---------------------------------------------------
LIGHT = (-0.55, -0.75)  # light comes from top-left


def ball_shader(cx, cy, rx, ry, base, hi=None, lo=None, bands=(0.45, -0.3)):
    """Banded 3-tone shading for a round shape, lit from the top-left."""
    hi = hi or lighter(base, 0.35)
    lo = lo or darker(base, 0.72)

    def f(x, y):
        nx = (x + 0.5 - cx) / rx
        ny = (y + 0.5 - cy) / ry
        t = nx * LIGHT[0] + ny * LIGHT[1]
        if t > bands[0]:
            return hi
        if t < bands[1]:
            return lo
        return base
    return f


def vgrad(y0, y1, stops, dither=True):
    """Vertical gradient through colour stops, with ordered dithering."""
    def f(x, y):
        t = (y - y0) / max(1, (y1 - y0))
        t = max(0.0, min(0.9999, t))
        seg = t * (len(stops) - 1)
        i = int(seg)
        frac = seg - i
        a, b = stops[i], stops[min(i + 1, len(stops) - 1)]
        if dither:
            # quantise into 4 steps per segment, dither between steps
            steps = 4
            q = frac * steps
            lo_step = int(q)
            bx = int(math.floor((x + 0.5) * SCALE)) % 4
            by = int(math.floor((y + 0.5) * SCALE)) % 4
            th = (BAYER4[by][bx] + 0.5) / 16
            step = lo_step + (1 if (q - lo_step) > th else 0)
            return mix(a, b, step / steps)
        return mix(a, b, frac)
    return f


def rng(seed):
    return random.Random(seed)


# ----- 5x7 bitmap font -------------------------------------------------
_FONT = {
    "A": ".###.#...##...#######...##...##...#",
    "B": "####.#...##...#####.#...##...#####.",
    "C": ".###.#...##....#....#....#...#.###.",
    "D": "####.#...##...##...##...##...#####.",
    "E": "######....#....####.#....#....#####",
    "F": "######....#....####.#....#....#....",
    "G": ".###.#...##....#.####...##...#.####",
    "H": "#...##...##...#######...##...##...#",
    "I": ".###...#....#....#....#....#...###.",
    "J": "..###...#....#....#....#.#..#..##..",
    "K": "#...##..#.#.#..##...#.#..#..#.#...#",
    "L": "#....#....#....#....#....#....#####",
    "M": "#...###.###.#.##.#.##...##...##...#",
    "N": "#...##...###..##.#.##..###...##...#",
    "O": ".###.#...##...##...##...##...#.###.",
    "P": "####.#...##...#####.#....#....#....",
    "Q": ".###.#...##...##...##.#.##..#..##.#",
    "R": "####.#...##...#####.#.#..#..#.#...#",
    "S": ".#####....#.....###.....#....#####.",
    "T": "#####..#....#....#....#....#....#..",
    "U": "#...##...##...##...##...##...#.###.",
    "V": "#...##...##...##...##...#.#.#...#..",
    "W": "#...##...##...##.#.##.#.##.#.#.#.#.",
    "X": "#...##...#.#.#...#...#.#.#...##...#",
    "Y": "#...##...#.#.#...#....#....#....#..",
    "Z": "#####....#...#...#...#...#....#####",
    "0": ".###.#...##..###.#.###..##...#.###.",
    "1": "..#...##....#....#....#....#...###.",
    "2": ".###.#...#....#...#...#...#...#####",
    "3": "####.....#....#.###.....#....#####.",
    "4": "...#...##..#.#.#..#.#####...#....#.",
    "5": "######....####.....#....##...#.###.",
    "6": ".###.#....#....####.#...##...#.###.",
    "7": "#####....#...#...#...#....#....#...",
    "8": ".###.#...##...#.###.#...##...#.###.",
    "9": ".###.#...##...#.####....#....#.###.",
    "-": "..... ..... ..... .###. ..... ..... .....".replace(" ", ""),
    ".": "..... ..... ..... ..... ..... ..... ..#..".replace(" ", ""),
    "/": "....#....#...#...#...#...#....#....",
    ":": "..... ..#.. ..... ..... ..... ..#.. .....".replace(" ", ""),
    "!": "..#....#....#....#....#.........#..",
    "'": "..#.. ..#.. ..... ..... ..... ..... .....".replace(" ", ""),
    "?": ".###. #...# ....# ...#. ..#.. ..... ..#..".replace(" ", ""),
    ",": "..... ..... ..... ..... ..... ..#.. .#...".replace(" ", ""),
    ">": "#.... .#... ..#.. ...#. ..#.. .#... #....".replace(" ", ""),
    " ": "",
}


# ----- 3x5 mini font (battle UI) ----------------------------------------
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
"""
_MINI = {}
for _line in _MINI_SRC.strip().splitlines():
    _k, *_rows = _line.split()
    _MINI[_k] = "".join(_rows)


def mini_width(s):
    return len(s) * 4 - 1


def draw_mini(cv, x, y, s, color, shadow=None):
    for ch in s.upper():
        g = _MINI.get(ch, "")
        for i, bit in enumerate(g):
            if bit == "#":
                gx, gy = x + i % 3, y + i // 3
                if shadow:
                    cv.set(gx + 1, gy + 1, shadow)
                cv.set(gx, gy, color)
        x += 4


def text_width(s, spacing=1):
    return len(s) * (5 + spacing) - spacing


def draw_text(cv, x, y, s, color, shadow=None, spacing=1):
    for ch in s.upper():
        g = _FONT.get(ch, "")
        g = (g + "." * 35)[:35]
        for i, bit in enumerate(g):
            if bit == "#":
                gx, gy = x + i % 5, y + i // 5
                if shadow:
                    cv.set(gx + 1, gy + 1, shadow)
                cv.set(gx, gy, color)
        x += 5 + spacing
