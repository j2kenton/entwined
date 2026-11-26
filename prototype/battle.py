"""Entwined battle clip: Ripplefin (Water) vs Emberkit (Fire).

    python battle.py           # play the clip (needs 100 x 36 terminal)
    python battle.py --frames  # save a few PNG stills into images/ instead
    python battle.py --gif     # record the clip as images/battle.gif

Press Esc to stop early. If the window is too small it says how to fix it.
"""
import math
import os
import random
import sys
import time

import pixel
from pixel import Canvas, ball_shader, darker, draw_mini, mini_width, mix, vgrad
from scenes import ripplefin_sprite

W, H = 100, 60          # battle picture in pixels (100 columns x 30 rows)
BOX_ROWS = 6            # text box under the picture, in real terminal text
FPS = 25
RNG = random.Random(4)

# where things stand on the field
ENEMY_HOME = (58, 0)     # top-left of Emberkit's sprite
PLAYER_HOME = (-3, 15)   # top-left of Ripplefin's sprite


# =========================================================================
# Sprites
# =========================================================================
def emberkit_sprite(phase):
    """Emberkit, a Fire creature: a fox-kit with a flame tail.
    `phase` (0..1) animates the flames."""
    s = Canvas(40, 34)
    body = (238, 118, 44)
    body_sh = ball_shader(19, 24, 9, 7, body, (255, 172, 92), (176, 66, 28))
    head_sh = ball_shader(17, 13, 10, 8.5, body, (255, 176, 96), (176, 66, 28))
    cream = (255, 228, 184)
    a = phase * math.tau

    # flame tail
    s.thick_line(25, 27, 32, 20, 2.6, body_sh)
    s.thick_line(32, 20, 34, 15, 2.0, body_sh)
    fx, fy = 34.5 + math.sin(a) * 0.8, 11
    for col, sc in (((230, 60, 30), 1.0), ((255, 140, 40), 0.7), ((255, 224, 96), 0.42)):
        s.polygon([(fx - 5 * sc, fy + 6 * sc),
                   (fx - 3 * sc + math.sin(a + 1) * 1.5, fy - 2 * sc),
                   (fx + math.sin(a * 2) * 1.2, fy - 9 * sc),
                   (fx + 3 * sc + math.cos(a) * 1.5, fy - 2 * sc),
                   (fx + 5 * sc, fy + 6 * sc)], col)
    # body, belly, legs
    s.ellipse(19, 24, 9, 7, body_sh)
    s.ellipse(18, 26, 5, 4.5, cream)
    for lx in (13, 24):
        s.ellipse(lx, 30.5, 3, 2, darker(body, 0.82))
        s.set(lx - 1, 31, cream); s.set(lx + 1, 31, cream)
    # ears with dark insides and tiny flame tips
    s.polygon([(9, 9), (7, 0), (14.5, 6)], body_sh)
    s.polygon([(20, 6), (27, 0), (25, 9)], body_sh)
    s.polygon([(9.5, 7), (8.4, 2.5), (12.5, 6)], (120, 36, 30))
    s.polygon([(22, 6), (25.6, 2.5), (24.4, 7)], (120, 36, 30))
    flick = 1 if math.sin(a * 3) > 0 else 0
    s.set(7, 0 - flick, (255, 210, 80)); s.set(27, 0 - (1 - flick), (255, 210, 80))
    # head + cheek tufts + muzzle
    s.polygon([(8, 13), (3.5, 15), (8, 17.5)], body_sh)
    s.polygon([(26, 13), (30.5, 15), (26, 17.5)], body_sh)
    s.ellipse(17, 13, 10, 8.5, head_sh)
    s.ellipse(17, 16.8, 5, 3, cream)
    # flame mark on the forehead
    s.polygon([(17, 5), (18.6, 7.5), (17, 9), (15.4, 7.5)], (255, 220, 90))
    # eyes
    for ex in (12.5, 21.5):
        s.ellipse(ex, 12.5, 2.3, 2.8, (44, 20, 22))
        s.set(ex - 1, 11, (255, 255, 255))
        s.set(ex + 0.6, 14, (255, 170, 70))
    # nose, grin, fang
    s.set(17, 15, (60, 24, 24))
    s.set(15, 17, (90, 30, 30)); s.set(16, 18, (90, 30, 30))
    s.set(17, 18, (90, 30, 30)); s.set(18, 17, (90, 30, 30))
    s.set(16, 19, (255, 255, 255))
    s.outline((54, 20, 16))
    return s


def flipped(c):
    out = Canvas(c.lw, c.lh, scale=c.S)
    out.px = [list(reversed(row)) for row in c.px]
    return out


def silhouette(c, col):
    out = Canvas(c.lw, c.lh, scale=c.S)
    out.px = [[col if p is not None else None for p in row] for row in c.px]
    return out


# =========================================================================
# Background: the pass into Ember Peaks
# =========================================================================
def background():
    pixel.SCALE = 1
    cv = Canvas(W, H)
    cv.rect(0, 0, W - 1, 31, vgrad(0, 31, [(38, 14, 40), (120, 40, 52), (236, 124, 70)]))
    r = random.Random(9)
    for _ in range(14):
        cv.set(r.randrange(W), r.randrange(0, 8), (190, 150, 200))
    # far ridge
    h = 27.0
    for x in range(W):
        h = max(24, min(30, h + r.uniform(-1.2, 1.2)))
        cv.rect(x, int(h), x, 31, (92, 38, 56))
    # volcano with glowing crater and lava streaks
    cv.polygon([(46, 32), (62, 9), (70, 9), (88, 32)],
               lambda x, y: (82, 34, 46) if x < 64 else (58, 24, 38))
    cv.rect(62, 9, 70, 9, (255, 150, 60))
    cv.rect(63, 8, 69, 8, (255, 210, 110))
    for x0, x1 in ((64, 58), (67, 70), (66, 64)):
        cv.line(x0, 10, x1, 24, (230, 90, 40))
    for cx, cy, rr in ((66, 5, 3), (62, 3, 2.5), (70, 2, 2.2), (65, 0, 2)):
        cv.ellipse(cx, cy, rr + 1, rr * 0.8, (110, 70, 80))
        cv.ellipse(cx - 0.6, cy - 0.5, rr * 0.7, rr * 0.5, (150, 100, 105))
    # ash ground with glowing cracks
    cv.rect(0, 31, W - 1, H - 1, vgrad(31, H, [(112, 62, 52), (72, 38, 36), (52, 26, 28)]))
    for _ in range(70):
        x, y = r.randrange(W), r.randrange(32, H)
        cv.set(x, y, (60, 32, 30) if r.random() < .7 else (140, 84, 66))
    for pts in (((4, 40), (12, 43), (18, 42)), ((80, 52), (88, 50), (96, 53)),
                ((52, 36), (58, 38)), ((60, 56), (70, 57))):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            cv.line(x0, y0, x1, y1, (240, 110, 40))
    # battle platforms
    for cx, cy, rx in ((76, 31, 18), (25, 56, 23)):
        cv.ellipse(cx, cy, rx, 3.6, (90, 48, 40))
        cv.ellipse(cx, cy - 0.6, rx - 1, 3.0, (140, 84, 64))
        cv.ellipse(cx, cy - 0.3, rx - 4, 2.0, (122, 72, 56))
    return cv


# =========================================================================
# Particles
# =========================================================================
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "r", "col", "g")

    def __init__(self, x, y, vx, vy, life, r, col, g=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.r, self.col, self.g = life, r, col, g


WATER = [(120, 200, 255), (200, 240, 255), (60, 140, 230), (255, 255, 255)]
FIRE = [(255, 220, 90), (255, 140, 40), (230, 60, 30), (255, 250, 200)]


# =========================================================================
# State + rendering
# =========================================================================
class State:
    def __init__(self):
        self.tick = 0
        self.enemy_on = False
        self.player_on = False
        self.ex, self.ey = ENEMY_HOME
        self.px_, self.py_ = PLAYER_HOME
        self.e_flash = 0
        self.p_flash = 0
        self.e_sink = 0
        self.p_sink = 0
        self.rows = None
        self.shake = 0
        self.reveal = 1.0
        self.panels = False
        self.e_hp, self.e_hp_shown = 1.0, 1.0
        self.p_hp_max = 52
        self.p_hp, self.p_hp_shown = 52.0, 52.0
        self.parts = []
        self.speaker = None
        self.text = ""
        self.shown = 0
        self.menu = False
        self.menu_pick = False
        self.banner = None


BG = None
EMBER = []
EMBER_WHITE = None
RIPPLE = None
RIPPLE_WHITE = None


def load_assets():
    global BG, EMBER, EMBER_WHITE, RIPPLE, RIPPLE_WHITE
    BG = background()
    EMBER = [emberkit_sprite(i / 6) for i in range(6)]
    EMBER_WHITE = silhouette(EMBER[0], (255, 255, 255))
    RIPPLE = flipped(ripplefin_sprite())
    RIPPLE_WHITE = silhouette(RIPPLE, (255, 255, 255))


def paste_clip(cv, spr, ox, oy, clip_y=None):
    for y in range(spr.h):
        ty = oy + y
        if clip_y is not None and ty > clip_y:
            break
        row = spr.px[y]
        for x in range(spr.w):
            c = row[x]
            if c is not None:
                cv.setp(ox + x, ty, c)


def hp_colour(t):
    if t > 0.5:
        return (96, 222, 112)
    if t > 0.2:
        return (250, 206, 70)
    return (240, 72, 60)


def panel(cv, x0, y0, x1, y1, accent):
    cv.rect(x0, y0, x1, y1, (22, 16, 30))
    cv.rect(x0, y0, x1, y0, accent)
    cv.rect(x0, y1, x1, y1, darker(accent, 0.6))
    cv.rect(x0, y0, x0, y1, darker(accent, 0.8))
    cv.rect(x1, y0, x1, y1, darker(accent, 0.6))


def hp_bar(cv, x0, y, width, t):
    cv.rect(x0 - 1, y - 1, x0 + width, y + 2, (10, 8, 14))
    cv.rect(x0, y, x0 + width - 1, y + 1, (60, 50, 62))
    n = int(round(width * max(0.0, min(1.0, t))))
    if n > 0:
        col = hp_colour(t)
        cv.rect(x0, y, x0 + n - 1, y + 1, col)
        cv.rect(x0, y, x0 + n - 1, y, mix(col, (255, 255, 255), 0.35))


def render(st):
    cv = Canvas(W, H)
    cv.px = [row[:] for row in BG.px]
    bob = 1 if (st.tick // 12) % 2 else 0

    if st.enemy_on:
        spr = EMBER_WHITE if (st.e_flash and st.e_flash % 4 < 2) else EMBER[(st.tick // 3) % len(EMBER)]
        paste_clip(cv, spr, int(st.ex), int(st.ey) + bob + st.e_sink,
                   clip_y=31 if st.e_sink else None)
    if st.player_on:
        spr = RIPPLE_WHITE if (st.p_flash and st.p_flash % 4 < 2) else RIPPLE
        paste_clip(cv, spr, int(st.px_), int(st.py_) + (1 - bob) + st.p_sink)

    for p in st.parts:
        if p.r <= 0.7:
            cv.set(p.x, p.y, p.col)
        else:
            cv.ellipse(p.x, p.y, p.r, p.r, p.col)

    if st.panels:
        # enemy panel (top-left)
        panel(cv, 2, 2, 44, 13, (255, 140, 40))
        draw_mini(cv, 5, 4, "EMBERKIT", (255, 236, 200), shadow=(60, 30, 20))
        cv.rect(38, 4, 41, 7, (255, 140, 40))            # fire element pip
        cv.set(39, 5, (255, 220, 90))
        draw_mini(cv, 5, 9, "HP", (255, 200, 80))
        hp_bar(cv, 13, 10, 28, st.e_hp_shown)
        # player panel (bottom-right)
        panel(cv, 54, 43, 98, 58, (90, 190, 255))
        draw_mini(cv, 57, 45, "RIPPLEFIN", (220, 244, 255), shadow=(20, 40, 70))
        cv.rect(93, 45, 96, 48, (90, 190, 255))          # water element pip
        cv.set(94, 46, (220, 250, 255))
        draw_mini(cv, 57, 50, "HP", (255, 200, 80))
        hp_bar(cv, 65, 51, 30, st.p_hp_shown / st.p_hp_max)
        hp_txt = "%d/%d" % (round(st.p_hp_shown), st.p_hp_max)
        draw_mini(cv, 96 - mini_width(hp_txt), 54, hp_txt, (220, 230, 240))

    if st.banner:
        txt, col = st.banner
        tw = mini_width(txt)
        x0 = (W - tw) // 2
        cv.rect(x0 - 4, 22, x0 + tw + 3, 30, (20, 14, 26))
        cv.rect(x0 - 4, 22, x0 + tw + 3, 22, col)
        cv.rect(x0 - 4, 30, x0 + tw + 3, 30, col)
        draw_mini(cv, x0, 24, txt, col, shadow=darker(col, 0.3))

    # screen shake
    if st.shake:
        dx = (2 if st.shake % 2 else -2)
        cv.px = [([(8, 6, 10)] * dx + row[:-dx]) if dx > 0 else (row[-dx:] + [(8, 6, 10)] * -dx)
                 for row in cv.px]
    # venetian-blind reveal / fade
    if st.reveal < 1.0:
        for y in range(H):
            if (y % 6) / 6 >= st.reveal:
                cv.px[y] = [(8, 6, 10)] * W
    return cv


# ----- text box (real terminal text, crisp) ------------------------------
RESET = "\x1b[0m"


def fg(c):
    return "\x1b[38;2;%d;%d;%dm" % c


def bgc(c):
    return "\x1b[48;2;%d;%d;%dm" % c


BOX_BG = (16, 14, 24)
BORDER = (242, 200, 82)


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        lines.append(cur)
    return lines


def text_box(st):
    inner = W - 2
    rows = []
    if st.rows is not None:
        rows = st.rows
    elif st.menu:
        blink = (st.tick // 6) % 2 == 0 or st.menu_pick
        cur = ("▶" if blink else " ")
        pick_col = (255, 255, 255) if not st.menu_pick or (st.tick // 2) % 2 else (120, 200, 255)
        rows = [
            [((200, 200, 210), "  What will "), ((120, 200, 255), "RIPPLEFIN"), ((200, 200, 210), " do?")],
            [((255, 220, 120), "   " + cur + " "), (pick_col, "TIDAL BURST   "), ((90, 170, 255), "Water"),
             ((160, 160, 170), "            BUBBLE GUARD  "), ((90, 170, 255), "Water")],
            [((160, 160, 170), "     SPLASH FIN    "), ((90, 170, 255), "Water"),
             ((160, 160, 170), "            REST")],
            [],
        ]
    else:
        body = st.text[:st.shown]
        lines = wrap(body, inner - 4)
        first = []
        if st.speaker:
            name, col = st.speaker
            first = [(col, "  " + name + ": ")]
        rows = []
        for i in range(4):
            seg = []
            if i == 0 and first:
                seg += first
                seg.append(((240, 240, 245), lines[0] if lines else ""))
            elif i == 0:
                seg.append(((240, 240, 245), "  " + (lines[0] if lines else "")))
            elif i < len(lines):
                pad = "  " + (" " * (len(first[0][1]) - 2) if first else "")
                seg.append(((240, 240, 245), pad + lines[i]))
            rows.append(seg)
        if st.shown >= len(st.text) and st.text and (st.tick // 8) % 2 == 0 and not rows[3]:
            rows[3] = [((242, 200, 82), " " * (inner - 3) + "▼")]
    out = [bgc(BOX_BG) + fg(BORDER) + "╭" + "─" * inner + "╮" + RESET]
    for seg in rows:
        vis = sum(len(t) for _, t in seg)
        s = bgc(BOX_BG) + fg(BORDER) + "│"
        for col, t in seg:
            s += fg(col) + t
        s += " " * max(0, inner - vis) + fg(BORDER) + "│" + RESET
        out.append(s)
    out.append(bgc(BOX_BG) + fg(BORDER) + "╰" + "─" * inner + "╯" + RESET)
    return out


# =========================================================================
# Playback engine
# =========================================================================
class Stop(Exception):
    pass


NEED_COLS, NEED_ROWS = W, H // 2 + BOX_ROWS


def term_size():
    try:
        return tuple(os.get_terminal_size())
    except OSError:
        return NEED_COLS, NEED_ROWS          # unknown (not a terminal): assume it fits


def size_message(cols, rows):
    """A short, centred 'make the window bigger' screen that fits any size."""
    lines = [
        ("\x1b[1;38;2;255;200;90m", "The window is too small"),
        ("", ""),
        ("\x1b[38;2;230;230;235m", "Needs at least %d x %d characters." % (NEED_COLS, NEED_ROWS)),
        ("\x1b[38;2;230;230;235m", "Yours is %d x %d." % (cols, rows)),
        ("", ""),
        ("\x1b[38;2;170;200;255m", "Make the window bigger,"),
        ("\x1b[38;2;170;200;255m", "press F11 for full screen,"),
        ("\x1b[38;2;170;200;255m", "or zoom out with Ctrl and minus (-)."),
        ("", ""),
        ("\x1b[38;2;150;150;160m", "It starts as soon as it fits.  Esc quits."),
    ]
    top = max(0, (rows - len(lines)) // 2)
    out = ["\n" * top]
    for style, text in lines:
        text = text[:max(0, cols - 1)]
        pad = max(0, (cols - len(text)) // 2)
        out.append(" " * pad + style + text + "\x1b[0m\n")
    return "".join(out).rstrip("\n")


class Player:
    def __init__(self, st, out=sys.stdout, stills=None, recorder=None):
        self.st = st
        self.out = out
        self.stills = stills      # dict of tick -> filename when saving PNGs
        self.recorder = recorder  # called with (state, canvas) instead of drawing
        self.next_t = time.perf_counter()

    def check_keys(self):
        if os.name == "nt":
            import msvcrt
            while msvcrt.kbhit():
                if msvcrt.getwch() == "\x1b":     # Esc
                    raise Stop()

    def wait_for_size(self):
        """While the window is too small, show how to fix it instead of the game.
        Resumes by itself as soon as it fits. Esc quits."""
        shown = None
        while True:
            cols, rows = term_size()
            if cols >= NEED_COLS and rows >= NEED_ROWS:
                if shown is not None:
                    self.out.write("\x1b[0m\x1b[2J")
                    self.next_t = time.perf_counter()
                return
            if (cols, rows) != shown:
                self.out.write("\x1b[0m\x1b[2J\x1b[H" + size_message(cols, rows))
                self.out.flush()
                shown = (cols, rows)
            self.check_keys()
            time.sleep(0.2)

    def step(self):
        st = self.st
        st.tick += 1
        # physics
        alive = []
        for p in st.parts:
            p.x += p.vx
            p.y += p.vy
            p.vy += p.g
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        st.parts = alive
        st.e_hp_shown += (st.e_hp - st.e_hp_shown) * 0.12
        if abs(st.e_hp - st.e_hp_shown) < 0.004:
            st.e_hp_shown = st.e_hp
        st.p_hp_shown += (st.p_hp - st.p_hp_shown) * 0.12
        if abs(st.p_hp - st.p_hp_shown) < 0.2:
            st.p_hp_shown = st.p_hp
        st.e_flash = max(0, st.e_flash - 1)
        st.p_flash = max(0, st.p_flash - 1)
        st.shake = max(0, st.shake - 1)

        cv = render(st)
        if self.recorder is not None:
            self.recorder(st, cv)
            return
        if self.stills is not None:
            name = self.stills.get(st.tick)
            if name:
                cv.save_png(name)
            return
        if self.out.isatty():
            self.wait_for_size()     # returns at once when the window fits
        frame = "\x1b[H" + cv.to_ansi() + "\n" + "\n".join(text_box(st))
        self.out.write(frame)
        self.out.flush()
        self.check_keys()
        self.next_t += 1 / FPS
        delay = self.next_t - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        else:
            self.next_t = time.perf_counter()

    def wait(self, n, fn=None):
        for i in range(n):
            if fn:
                fn(i)
            self.step()

    def say(self, text, speaker=None, hold=28, speed=2):
        st = self.st
        st.menu = False
        st.speaker, st.text, st.shown = speaker, text, 0
        while st.shown < len(text):
            st.shown = min(len(text), st.shown + speed)
            self.step()
        self.wait(hold)


def ease(t):
    return 1 - (1 - t) ** 3


# ----- effects -----------------------------------------------------------
def tidal_burst(pl, big=False, hit=True):
    st = pl.st
    sx, sy = 40, 30          # Ripplefin's mouth
    tx, ty = 76, 16          # Emberkit
    # lunge
    pl.wait(5, lambda i: setattr(st, "px_", PLAYER_HOME[0] + [1, 2, 3, 2, 1][i]))
    st.px_ = PLAYER_HOME[0]
    frames = 22 if big else 16

    def spray(i):
        for _ in range(7 if big else 5):
            t = RNG.uniform(0.85, 1.15)
            life = int(RNG.uniform(12, 16))
            vx = (tx - sx) / life * t
            vy = (ty - sy) / life * t - 0.9 + RNG.uniform(-0.4, 0.4)
            st.parts.append(Particle(sx + RNG.uniform(-1, 1), sy + RNG.uniform(-2, 2),
                                     vx, vy, life, RNG.choice([0.5, 1.0, 1.4]),
                                     RNG.choice(WATER), g=0.12))
    pl.wait(frames, spray)
    pl.wait(6)
    if not hit:
        for _ in range(10):
            st.parts.append(Particle(tx + RNG.uniform(-14, -6), ty + 14, RNG.uniform(-0.6, 0.6),
                                     RNG.uniform(-1.2, -0.4), 10, 0.5, RNG.choice(WATER), g=0.15))
        return
    # impact
    st.e_flash = 14
    st.shake = 8
    for _ in range(40 if big else 28):
        a = RNG.uniform(0, math.tau)
        v = RNG.uniform(0.6, 2.2)
        st.parts.append(Particle(tx, ty, math.cos(a) * v, math.sin(a) * v - 0.8,
                                 int(RNG.uniform(8, 18)), RNG.choice([0.5, 1.0, 1.3]),
                                 RNG.choice(WATER), g=0.15))
    # steam where water meets fire
    for _ in range(14):
        st.parts.append(Particle(tx + RNG.uniform(-8, 8), ty + RNG.uniform(-4, 6),
                                 RNG.uniform(-0.2, 0.2), RNG.uniform(-0.7, -0.3),
                                 int(RNG.uniform(14, 24)), RNG.choice([1.0, 1.5]),
                                 RNG.choice([(220, 220, 230), (180, 180, 195)])))


def flame_dash(pl, hit=True):
    st = pl.st
    path_to = (36, 22)

    def go(i, n, a, b):
        t = ease(i / (n - 1))
        st.ex = a[0] + (b[0] - a[0]) * t
        st.ey = a[1] + (b[1] - a[1]) * t
        for _ in range(4):
            st.parts.append(Particle(st.ex + 18 + RNG.uniform(-6, 6), st.ey + 20 + RNG.uniform(-6, 4),
                                     RNG.uniform(-0.3, 0.3), RNG.uniform(-0.9, -0.2),
                                     int(RNG.uniform(8, 14)), RNG.choice([0.5, 1.0, 1.4]),
                                     RNG.choice(FIRE)))
    pl.wait(4, lambda i: setattr(st, "ex", ENEMY_HOME[0] + [1, 2, 1, 0][i]))   # wind-up
    pl.wait(9, lambda i: go(i, 9, ENEMY_HOME, path_to))
    if hit:
        st.p_flash = 12
        st.shake = 6
    for _ in range(26 if hit else 0):
        a = RNG.uniform(0, math.tau)
        v = RNG.uniform(0.5, 1.8)
        st.parts.append(Particle(32, 32, math.cos(a) * v, math.sin(a) * v - 0.5,
                                 int(RNG.uniform(8, 16)), RNG.choice([0.5, 1.0, 1.3]),
                                 RNG.choice(FIRE), g=0.05))
    pl.wait(3)
    pl.wait(10, lambda i: go(i, 10, path_to, ENEMY_HOME))
    st.ex, st.ey = ENEMY_HOME


def sparkle(st, x, y, cols, n=24):
    for _ in range(n):
        a = RNG.uniform(0, math.tau)
        v = RNG.uniform(0.4, 1.6)
        st.parts.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                                 int(RNG.uniform(10, 20)), 0.5, RNG.choice(cols)))


# =========================================================================
# The clip
# =========================================================================
KAEL = ("KAEL", (255, 150, 60))


def script(pl):
    st = pl.st
    # open
    st.reveal = 0.0
    pl.wait(18, lambda i: setattr(st, "reveal", (i + 1) / 18))
    pl.say("Kael, Lord of Ember Peaks, blocks the path!", hold=22)
    pl.say("Nobody crosses into my land without a battle. Nobody.", speaker=KAEL, hold=26)
    # enemy appears
    pl.say("Kael sends out EMBERKIT!", hold=0)
    st.enemy_on = True
    st.e_flash = 10
    sparkle(st, 76, 16, FIRE, 30)
    pl.wait(22)
    # player slides in
    pl.say("Go, RIPPLEFIN!", hold=0)
    st.player_on = True
    pl.wait(14, lambda i: setattr(st, "px_", -56 + (PLAYER_HOME[0] + 56) * ease((i + 1) / 14)))
    sparkle(st, 26, 40, WATER, 24)
    st.panels = True
    pl.wait(20)
    # choose a move
    st.menu = True
    pl.wait(34)
    st.menu_pick = True
    pl.wait(10)
    st.menu_pick = False
    # turn 1
    pl.say("RIPPLEFIN used TIDAL BURST!", hold=4)
    tidal_burst(pl)
    st.e_hp = 0.36
    pl.wait(14)
    pl.say("It's strong against Fire!", hold=22)
    # enemy turn
    pl.say("EMBERKIT used FLAME DASH!", hold=4)
    flame_dash(pl)
    st.p_hp = 44
    pl.wait(10)
    pl.say("Fire is weak against Water. Ripplefin barely felt it.", hold=22)
    # turn 2: finish
    st.menu = True
    pl.wait(14)
    st.menu_pick = True
    pl.wait(8)
    st.menu_pick = False
    pl.say("RIPPLEFIN used TIDAL BURST!", hold=4)
    tidal_burst(pl, big=True)
    st.e_hp = 0.0
    pl.wait(20)
    # faint: sinks into the platform
    st.e_flash = 8
    pl.wait(8)
    pl.wait(26, lambda i: setattr(st, "e_sink", int(ease((i + 1) / 26) * 34)))
    st.enemy_on = False
    st.e_sink = 0
    pl.say("EMBERKIT can't battle any more!", hold=22)
    # Kael's two-part comment
    pl.say("Your water went straight through my flames. I never stood a chance.",
           speaker=KAEL, hold=30)
    pl.say("You Tidewell folk are calmer than I gave you credit for.", speaker=KAEL, hold=28)
    pl.say("...The Citadel? You're going after the Citadel? Then I'm coming with you.",
           speaker=KAEL, hold=26)
    # join
    st.banner = ("KAEL JOINED YOUR PARTY!", (255, 200, 90))
    for k in range(3):
        sparkle(st, RNG.uniform(20, 80), RNG.uniform(10, 30), FIRE + WATER, 30)
        pl.wait(10)
    st.speaker, st.text, st.shown = None, "", 0
    pl.wait(40)
    pl.wait(18, lambda i: setattr(st, "reveal", 1 - (i + 1) / 18))


def play():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if os.name == "nt":
        os.system("")
    load_assets()
    st = State()
    out = sys.stdout
    out.write("\x1b[?1049h\x1b[?25l\x1b[2J")   # alternate screen, hide cursor
    try:
        pl = Player(st, out)
        pl.wait_for_size()
        script(pl)
    except (Stop, KeyboardInterrupt):
        pass
    finally:
        out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        out.flush()
    print("Entwined battle clip: run it again with  python battle.py")


def save_stills():
    """Render selected frames to PNG (for checking without a terminal)."""
    load_assets()
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, "images")
    os.makedirs(out_dir, exist_ok=True)
    picks = {}
    for t in (int(a) for a in os.environ.get("STILLS", "60,175,215,300,420,520").split(",")):
        picks[t] = os.path.join(out_dir, "battle_%04d.png" % t)
    st = State()
    try:
        script(Player(st, stills=picks))
    except Stop:
        pass
    print("total frames:", st.tick, "(%.1f seconds)" % (st.tick / FPS))
    for t, p in sorted(picks.items()):
        if os.path.exists(p):
            print("saved", p)


# =========================================================================
# GIF export (the text box is drawn in pixel lettering)
# =========================================================================
GIF_SCALE = 4             # picture pixels -> GIF pixels
BOX_W, BOX_H = 200, 36    # text box in its own pixels, shown at 2x
BOX_CHARS = 32


def box_canvas(st):
    from pixel import draw_text
    cv = Canvas(BOX_W, BOX_H, fill=BOX_BG)
    cv.rect(0, 0, BOX_W - 1, 0, BORDER)
    cv.rect(0, BOX_H - 1, BOX_W - 1, BOX_H - 1, BORDER)
    cv.rect(0, 0, 0, BOX_H - 1, BORDER)
    cv.rect(BOX_W - 1, 0, BOX_W - 1, BOX_H - 1, BORDER)
    white, grey, blue = (240, 240, 245), (150, 150, 160), (120, 200, 255)

    def line(i, segs):
        x = 5
        for col, t in segs:
            draw_text(cv, x, 4 + i * 8, t, col)
            x += 6 * len(t)

    if st.menu:
        blink = (st.tick // 6) % 2 == 0 or st.menu_pick
        pick = blue if (st.menu_pick and (st.tick // 2) % 2) else white
        line(0, [(grey, "WHAT WILL "), (blue, "RIPPLEFIN"), (grey, " DO?")])
        line(1, [((255, 220, 120), "> " if blink else "  "), (pick, "TIDAL BURST"),
                 (grey, "  SPLASH FIN")])
        line(2, [(grey, "  BUBBLE GUARD REST")])
        return cv

    prefix = (st.speaker[0] + ": ") if st.speaker else ""
    full = prefix + st.text
    shown_len = len(prefix) + st.shown
    rows = wrap(full, BOX_CHARS)
    pos = 0
    for i, row in enumerate(rows[:4]):
        segs = []
        for j, ch in enumerate(row):
            g = pos + j
            if g >= shown_len:
                break
            col = st.speaker[1] if g < len(prefix) else white
            segs.append((col, ch))
        # merge characters into runs for drawing
        x = 5
        for col, ch in segs:
            draw_text(cv, x, 4 + i * 8, ch, col)
            x += 6
        pos += len(row) + 1
    if st.text and st.shown >= len(st.text) and (st.tick // 8) % 2 == 0:
        cv.polygon([(BOX_W - 10, BOX_H - 8), (BOX_W - 4, BOX_H - 8), (BOX_W - 7, BOX_H - 4)], BORDER)
    return cv


def make_gif(path, every=2):
    from collections import Counter
    import gif

    load_assets()
    st = State()
    frames = []

    def rec(state, cv):
        if state.tick % every:
            return
        frames.append(([row[:] for row in cv.px], box_canvas(state).px))

    try:
        script(Player(st, recorder=rec))
    except Stop:
        pass
    print("recorded %d frames" % len(frames))

    counts = Counter()
    for art, box in frames:
        for row in art:
            counts.update(row)
        for row in box:
            counts.update(row)
    if len(counts) <= 256:
        palette = list(counts)
        lookup = {c: i for i, c in enumerate(palette)}
    else:
        palette = gif.median_cut(counts, 256)
        lookup = {}
        for c in counts:
            lookup[c] = min(range(len(palette)), key=lambda i: sum(
                (a - b) ** 2 for a, b in zip(c, palette[i])))
    print("colours used: %d -> palette %d" % (len(counts), len(palette)))

    S = GIF_SCALE
    GW = W * S
    art_h, box_h = H * S, BOX_H * 2
    GH = art_h + box_h
    delay = int(round(100 * every / FPS))

    def expand(rows, k):
        return [bytes(b for b in r for _ in range(k)) for r in rows]

    out = []
    prev_art = prev_box = None
    for art, box in frames:
        a_idx = [bytes(lookup[c] for c in row) for row in art]
        b_idx = [bytes(lookup[c] for c in row) for row in box]
        # changed area, in GIF pixels
        x0, y0, x1, y1 = GW, GH, -1, -1
        if prev_art is None:
            x0, y0, x1, y1 = 0, 0, GW - 1, GH - 1
        else:
            for y in range(H):
                if a_idx[y] != prev_art[y]:
                    r1, r2 = a_idx[y], prev_art[y]
                    xs = [x for x in range(W) if r1[x] != r2[x]]
                    x0, x1 = min(x0, xs[0] * S), max(x1, xs[-1] * S + S - 1)
                    y0, y1 = min(y0, y * S), max(y1, y * S + S - 1)
            for y in range(BOX_H):
                if b_idx[y] != prev_box[y]:
                    r1, r2 = b_idx[y], prev_box[y]
                    xs = [x for x in range(BOX_W) if r1[x] != r2[x]]
                    x0, x1 = min(x0, xs[0] * 2), max(x1, xs[-1] * 2 + 1)
                    y0, y1 = min(y0, art_h + y * 2), max(y1, art_h + y * 2 + 1)
        prev_art, prev_box = a_idx, b_idx
        if x1 < 0:
            out[-1][5] += delay        # nothing changed: hold the last frame longer
            continue
        rows = expand(a_idx, S)
        full = [r for r in rows for _ in range(S)]
        brows = expand(b_idx, 2)
        full += [r for r in brows for _ in range(2)]
        sub = b"".join(full[y][x0:x1 + 1] for y in range(y0, y1 + 1))
        out.append([x0, y0, x1 - x0 + 1, y1 - y0 + 1, sub, delay])
    out[-1][5] += 150                 # pause on the last frame before looping
    gif.write_gif(path, GW, GH, palette, [tuple(f) for f in out])
    print("saved %s  (%d x %d, %d frames, %.1f MB)"
          % (path, GW, GH, len(out), os.path.getsize(path) / 1e6))


if __name__ == "__main__":
    if "--gif" in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(os.path.join(here, "images"), exist_ok=True)
        make_gif(os.path.join(here, "images", "battle.gif"))
    elif "--frames" in sys.argv:
        save_stills()
    else:
        play()
