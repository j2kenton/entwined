"""The three Entwined concept images: hero, creature, Citadel."""
import math

import pixel
from pixel import (Canvas, I, ball_shader, darker, draw_text, lighter, mix, rng,
                   text_width, vgrad)

W = 100          # pixels wide  (= terminal columns)
SCENE_H = 56     # pixels tall for the picture
CAP_H = 10       # caption strip
H = SCENE_H + CAP_H

OUTLINE = (16, 18, 38)


def caption(cv, left, right, right_col, accent):
    y0 = SCENE_H
    cv.rect(0, y0, W - 1, H - 1, (16, 18, 30))
    cv.rect(0, y0, W - 1, y0, accent)
    draw_text(cv, 3, y0 + 2, left, (245, 225, 170), shadow=(60, 45, 30))
    rw = text_width(right)
    draw_text(cv, W - 3 - rw, y0 + 2, right, right_col, shadow=darker(right_col, 0.35))


def rim_light(sprite, side, col, amt=0.45):
    """Tint the edge pixels of a sprite on one side (before outlining)."""
    dx = 1 if side == "right" else -1
    marks = []
    for y in range(sprite.h):
        for x in range(sprite.w):
            if sprite.px[y][x] is not None and sprite.getp(x + dx, y) is None:
                marks.append((x, y))
    for x, y in marks:
        sprite.px[y][x] = mix(sprite.px[y][x], col, amt)


# =========================================================================
# 1. HERO: Marisol, the Water sky-sailor, on deck at sunset
# =========================================================================
def lowres_face(s):
    """The original retro face: each feature is one or two big pixels."""
    lash, iris, iris_d = (24, 28, 60), (46, 120, 210), (30, 70, 150)
    for ex in (16, 23):
        s.set(ex, 16, lash); s.set(ex + 1, 16, lash)
        s.set(ex, 17, (255, 255, 255)); s.set(ex + 1, 17, iris)
        s.set(ex, 18, iris_d); s.set(ex + 1, 18, iris)
    s.set(15, 14, (22, 108, 145)); s.set(16, 14, (22, 108, 145))
    s.set(24, 14, (22, 108, 145)); s.set(25, 14, (22, 108, 145))
    s.set(20, 19, (238, 186, 156))
    s.set(19, 21, (206, 104, 112)); s.set(20, 21, (206, 104, 112))
    s.set(15, 20, (245, 150, 150)); s.set(25, 20, (245, 150, 150))


def hd_face(s):
    """A finer face drawn in real pixels (designed for scale 2).
    The head is centred on real pixel x=40."""
    P = s.setp
    L = (24, 28, 60)          # lash / outline
    W_ = (244, 244, 252)      # eye white
    H_ = (255, 255, 255)      # highlight
    Ir = (46, 120, 210)       # iris
    Il = (120, 196, 252)      # lower iris glow
    Pu = (20, 40, 104)        # pupil
    sh = (236, 182, 152)      # skin shadow
    eye = ["LLLLL",
           "WHHIW",
           "WHPIW",
           "WIPIW",
           "WIllW",
           ".sss."]
    cmap = {"L": L, "W": W_, "H": H_, "I": Ir, "P": Pu, "l": Il, "s": sh}
    for x0, flick in ((31, -1), (45, +1)):
        for dy, row in enumerate(eye):
            for dx, ch in enumerate(row):
                if ch != ".":
                    P(x0 + dx, 32 + dy, cmap[ch])
        # lash flick on the outer corner
        fx = x0 - 1 if flick < 0 else x0 + 5
        P(fx, 32, L)
        P(fx + flick, 31, L)
    # nose and smile
    P(40, 39, sh)
    for x, y in ((37, 42), (38, 43), (39, 43), (40, 43), (41, 43), (42, 42)):
        P(x, y, (190, 92, 106))
    P(39, 44, (232, 150, 150)); P(40, 44, (232, 150, 150))
    # blush
    for x, y in ((29, 39), (31, 39), (30, 40), (32, 40),
                 (48, 39), (50, 39), (49, 40), (51, 40)):
        P(x, y, (246, 156, 164))
    # fine hair strands over the bangs and side locks
    strand = (160, 240, 242)
    for (x0, y0, x1, y1) in ((14.5, 10.5, 15.5, 13.5), (17.2, 10, 18.2, 13.8),
                             (21.6, 10, 22.4, 13.6), (25.6, 10.5, 25.2, 12.5),
                             (13, 12, 13.2, 20), (27, 12, 27.4, 19)):
        s.line(x0, y0, x1, y1, strand)

def hero(scale=1):
    pixel.SCALE = scale
    cv = Canvas(W, H, scale=scale)
    r = rng(7)

    # sky
    cv.rect(0, 0, W - 1, 41, vgrad(0, 41, [(24, 24, 70), (80, 45, 120),
                                          (215, 100, 105), (250, 185, 110)]))
    # stars in the high sky
    for _ in range(18):
        x, y = r.randrange(W), r.randrange(0, 12)
        cv.setp(x * scale, y * scale, (200, 200, 255) if r.random() < .5 else (140, 140, 210))
    # sun with retro stripe cuts
    sun = (255, 222, 150)
    cv.ellipse(76, 38, 9, 9, lambda x, y: mix(sun, (255, 160, 100), (y - 29) / 18))
    for yy, gap in ((34, 1), (37, 1), (40, 2)):
        for x in range(66, 87):
            for g in range(gap):
                if cv.get(x, yy + g) and (yy + g) <= 41:
                    cv.set(x, yy + g, vgrad(0, 41, [(24, 24, 70), (80, 45, 120),
                                                    (215, 100, 105), (250, 185, 110)])(x, yy + g))
    # clouds
    for cx, cy, s in ((20, 14, 1.0), (58, 9, 0.8), (88, 20, 0.7), (40, 24, 0.6)):
        for ox, oy, rx, ry in ((0, 0, 7, 2.2), (-5, 1, 5, 1.8), (6, 1, 5, 1.6), (2, -1.5, 4, 1.8)):
            cv.ellipse(cx + ox * s, cy + oy, rx * s, ry, (210, 120, 140))
        cv.ellipse(cx - 1, cy - 1.2, 5 * s, 1.0, (245, 170, 160))
    # distant island
    cv.polygon([(2, 42), (8, 38), (14, 37), (20, 39), (26, 42)], (70, 40, 90))
    # sea
    cv.rect(0, 42, W - 1, 50, vgrad(42, 50, [(70, 70, 140), (30, 40, 95)]))
    for _ in range(40):  # sun glitter
        y = r.randrange(42, 50)
        x = int(76 + r.gauss(0, 5 + (y - 42)))
        cv.line(x, y, x + r.randrange(1, 4), y, (255, 205, 130))
    for _ in range(25):  # wave crests
        y = r.randrange(43, 50)
        x = r.randrange(W)
        cv.line(x, y, x + 2, y, (120, 120, 190))
    # mast and rigging (left)
    cv.rect(5, 0, 8, 49, lambda x, y: (120, 72, 40) if x < 7 else (85, 50, 30))
    for (x0, y0, x1, y1) in ((8, 4, 30, 44), (8, 12, 22, 44), (5, 8, 0, 30)):
        cv.line(x0, y0, x1, y1, (60, 40, 35))
    cv.rect(0, 2, 18, 3, (95, 58, 34))  # yard arm
    # ship rail
    cv.rect(0, 44, W - 1, 45, (110, 66, 38))
    cv.rect(0, 44, W - 1, 44, (150, 95, 55))
    for x in range(2, W, 9):
        cv.rect(x, 45, x + 1, 50, (85, 50, 30))
    # deck planks
    cv.rect(0, 50, W - 1, SCENE_H - 1, lambda x, y: (128, 80, 48) if (I(y) % 3) else (96, 58, 34))
    for y in range(50, SCENE_H):
        for x in range((y * 13) % 17, W, 17):
            cv.set(x, y, (80, 48, 28))
    cv.rect(0, 50, W - 1, 50, (165, 110, 65))

    # ---- the hero sprite -------------------------------------------------
    s = Canvas(42, 60, scale=scale)
    hair = (40, 178, 198)
    hair_sh = ball_shader(20, 16, 10, 14, hair, (130, 232, 236), (22, 108, 145))
    coat = (40, 60, 138)
    coat_sh = ball_shader(20, 36, 12, 16, coat, (78, 104, 186), (24, 34, 92))
    skin = (250, 206, 172)
    skin_sh = ball_shader(20, 16, 7.5, 8, skin, (255, 230, 204), (232, 178, 150), bands=(0.6, -0.8))
    gold = (242, 200, 82)
    red = (212, 58, 64)
    red_sh = ball_shader(22, 26, 8, 4, red, (245, 105, 105), (150, 34, 48))
    boot = (92, 56, 36)

    # back hair blowing left in the wind
    s.polygon([(13, 9), (27, 9), (28, 20), (26, 30), (20, 33), (13, 36),
               (4, 39), (7, 33), (9, 25), (11, 15)], hair_sh)
    s.polygon([(10, 30), (3, 34), (1, 37), (6, 36)], hair_sh)
    # scarf tail streaming right
    s.polygon([(24, 25), (35, 22), (40, 25), (34, 27), (38, 31), (28, 29)], red_sh)
    # legs + boots
    s.rect(15, 44, 18, 50, (226, 228, 238))
    s.rect(22, 44, 25, 50, (196, 200, 218))
    s.rect(14, 50, 18, 56, boot)
    s.rect(22, 50, 26, 56, darker(boot, 0.8))
    s.rect(14, 50, 18, 51, (130, 84, 52))
    s.rect(22, 50, 26, 51, (112, 72, 46))
    s.rect(13, 55, 18, 56, darker(boot, 0.6))
    s.rect(22, 55, 27, 56, darker(boot, 0.55))
    # coat
    s.polygon([(12, 26), (28, 26), (31.5, 48), (8.5, 48)], coat_sh)
    s.polygon([(18, 28), (22, 28), (23, 48), (17, 48)], (232, 234, 244))  # shirt
    s.rect(17, 38, 23, 39, (80, 50, 32))      # belt
    s.rect(19, 38, 21, 39, gold)              # buckle
    s.line(18, 28, 17, 48, gold)
    s.line(22, 28, 23, 48, gold)
    s.line(9, 48, 31, 48, gold)
    for y in (31, 34, 42):
        s.set(15, y, gold)
        s.set(25, y, gold)
    s.polygon([(18, 27), (14, 29), (17, 33)], (28, 40, 100))   # lapels
    s.polygon([(22, 27), (26, 29), (23, 33)], (22, 32, 84))
    # arms: left holds a brass spyglass, right on hip
    s.thick_line(12.5, 28, 9, 39, 2.2, coat_sh)
    s.rect(7, 38, 11, 39, gold)
    s.thick_line(8, 41, 2.5, 50, 1.3, lambda x, y: (205, 160, 70) if (I(x) + I(y)) % 4 else (150, 110, 45))
    s.ellipse(2.5, 50.5, 1.6, 1.6, (120, 85, 35))
    s.ellipse(9, 41.5, 2, 2, skin)
    s.thick_line(28, 28, 32, 34, 2.2, coat_sh)
    s.thick_line(32, 34, 27, 38, 1.7, coat_sh)
    s.rect(30, 34, 32, 35, gold)
    s.ellipse(26.5, 38.5, 1.7, 1.7, skin)
    # scarf wrap + knot
    s.ellipse(20, 25.5, 6.2, 2.3, red_sh)
    s.ellipse(23.5, 27.5, 1.7, 1.7, (170, 40, 52))
    # neck + head
    s.rect(18, 22, 22, 24, (222, 160, 132))
    s.ellipse(20, 16, 7.6, 8, skin_sh)
    # bangs and side locks
    s.polygon([(12.4, 9), (27.6, 9), (27.6, 14), (25, 12), (23, 15), (21, 12),
               (18.5, 15), (16, 12), (13, 16)], hair_sh)
    s.polygon([(12.4, 10), (14.5, 10), (14.2, 22), (12, 25)], hair_sh)
    s.polygon([(25.6, 10), (27.6, 10), (28.4, 22), (26, 21)], hair_sh)
    # face
    if scale >= 2:
        hd_face(s)
    else:
        lowres_face(s)
    # tricorn hat with gold trim and a white feather
    hat = (36, 46, 104)
    hat_sh = ball_shader(20, 6, 9, 6, hat, (72, 88, 162), (20, 26, 62))
    s.polygon([(13, 9), (15, 2), (20, 0.5), (25, 2), (27, 9)], hat_sh)
    s.ellipse(20, 8.6, 11.2, 2.6, hat_sh)
    s.line(9, 7, 13, 9, gold); s.line(13, 9, 27, 9, gold); s.line(27, 9, 31, 7, gold)
    s.ellipse(20, 5, 1.6, 1.6, gold)
    s.set(20, 5, (60, 160, 230))
    s.thick_line(25, 4, 33, 2.5, 1.2, (245, 245, 250))
    s.thick_line(33, 2.5, 38, 5.5, 0.9, (220, 225, 240))
    s.line(26, 4, 37, 4.5, (190, 195, 220))

    rim_light(s, "right", (255, 170, 110), 0.5)
    s.outline(OUTLINE)
    # soft shadow on the deck
    cv.ellipse(50, 55, 12, 1.6, (90, 54, 32))
    cv.paste(s, 29, -1)

    caption(cv, "MARISOL", "WATER", (110, 210, 255), (242, 200, 82))
    return cv


def ripplefin_sprite(scale=1):
    """Ripplefin, front view, outlined. 52 x 44 logical pixels."""
    s = Canvas(52, 44, scale=scale)
    body = (66, 150, 232)
    body_sh = ball_shader(24, 30, 11, 9, body, (130, 200, 250), (34, 92, 176))
    head_sh = ball_shader(19, 17, 12, 10, body, (138, 206, 252), (34, 92, 176))
    frill = (110, 226, 214)
    frill_sh = lambda x, y: frill if (I(x) + I(y)) % 5 else (70, 180, 190)
    tip = (246, 140, 186)

    # tail curling up behind
    pts = [(32, 33), (39, 31), (44, 25), (45, 18), (42, 13)]
    radii = [4.2, 3.4, 2.6, 1.9, 1.3]
    for (x0, y0), (x1, y1), r0 in zip(pts, pts[1:], radii):
        s.thick_line(x0, y0, x1, y1, r0, body_sh)
    s.polygon([(42, 14), (48, 6), (49, 14), (45, 19)], frill_sh)
    s.polygon([(44, 24), (50, 20), (47, 28)], frill_sh)
    # back fins
    s.polygon([(28, 23), (32, 16), (34, 25)], frill_sh)
    s.polygon([(33, 26), (38, 21), (37, 30)], frill_sh)
    # body + belly
    s.ellipse(24, 31, 11, 9, body_sh)
    s.ellipse(23, 34, 7, 6, ball_shader(23, 34, 7, 6, (196, 238, 250), (240, 252, 255), (150, 205, 232)))
    # feet
    for fx, fy in ((16, 39.5), (29, 40)):
        s.ellipse(fx, fy, 3.4, 2.2, ball_shader(fx, fy, 3.4, 2.2, body, (130, 200, 250), (34, 92, 176)))
        for tx in (-2, 0, 2):
            s.set(fx + tx, fy + 1.5, (196, 238, 250))
    # gill frills fanning out, three per side, pink tips
    for (x0, y0, x1, y1) in ((9, 13, 2, 6), (8, 17, 0, 16), (9, 21, 2, 27),
                             (29, 13, 36, 6), (30, 17, 38, 16), (29, 21, 36, 27)):
        s.thick_line(x0, y0, x1, y1, 2.1, frill_sh)
        s.ellipse(x1, y1, 1.8, 1.8, tip)
    # head
    s.ellipse(19, 17, 12, 10, head_sh)
    s.ellipse(19, 21.5, 7, 4, (170, 225, 250))  # muzzle
    # droplet mark on forehead
    s.polygon([(19, 6.5), (21, 10), (19, 12), (17, 10)], (210, 248, 255))
    s.set(18, 9, (255, 255, 255))
    # big eyes
    for ex in (13.5, 24.5):
        s.ellipse(ex, 16.5, 3.1, 3.6, (18, 30, 66))
        s.set(ex - 1.5, 14.5, (255, 255, 255)); s.set(ex - 0.5, 14.5, (255, 255, 255))
        s.set(ex - 1.5, 15.5, (255, 255, 255))
        s.set(ex + 0.8, 18.6, (150, 200, 255))
    # cheeks + smile
    s.ellipse(10.5, 21, 1.6, 1.2, (246, 150, 190))
    s.ellipse(27.5, 21, 1.6, 1.2, (246, 150, 190))
    s.set(17, 22, (30, 50, 100)); s.set(18, 23, (30, 50, 100))
    s.set(19, 23, (30, 50, 100)); s.set(20, 23, (30, 50, 100)); s.set(21, 22, (30, 50, 100))

    s.outline((14, 34, 78))
    return s


# =========================================================================
# 2. CREATURE: Ripplefin, a Water creature, on a tide-pool rock
# =========================================================================
def creature(scale=1):
    pixel.SCALE = scale
    cv = Canvas(W, H, scale=scale)
    r = rng(11)
    cv.rect(0, 0, W - 1, 24, vgrad(0, 24, [(96, 170, 245), (150, 210, 255), (205, 238, 255)]))
    for cx, cy, s in ((16, 7, 1.0), (70, 5, 1.2), (92, 14, 0.7)):
        for ox, oy, rx, ry in ((0, 0, 7, 2.4), (-5, 1, 5, 2), (6, 1, 5, 1.8), (1, -1.6, 4, 2)):
            cv.ellipse(cx + ox * s, cy + oy, rx * s, ry, (255, 255, 255))
        cv.ellipse(cx, cy + 1.5, 8 * s, 0.9, (215, 232, 250))
    # sea
    cv.rect(0, 24, W - 1, 40, vgrad(24, 40, [(46, 140, 210), (26, 96, 170)]))
    for _ in range(45):
        y = r.randrange(25, 40)
        x = r.randrange(W)
        cv.line(x, y, x + r.randrange(2, 5), y, (150, 215, 245) if y < 32 else (90, 170, 225))
    cv.rect(0, 24, W - 1, 24, (210, 240, 255))
    # rocks
    rock = (112, 118, 140)
    cv.polygon([(14, 56), (20, 44), (34, 40), (64, 39), (80, 43), (88, 56)],
               ball_shader(52, 44, 38, 12, rock, (158, 164, 182), (70, 74, 96)))
    cv.polygon([(0, 56), (0, 46), (8, 43), (16, 47), (20, 56)],
               ball_shader(8, 48, 10, 8, rock, (158, 164, 182), (70, 74, 96)))
    cv.polygon([(84, 56), (88, 46), (96, 44), (100, 48), (100, 56)],
               ball_shader(92, 48, 10, 8, rock, (158, 164, 182), (70, 74, 96)))
    for _ in range(30):  # barnacles / texture
        x, y = r.randrange(18, 84), r.randrange(42, 52)
        if cv.get(x, y) in ((112, 118, 140), (158, 164, 182)):
            cv.set(x, y, (90, 96, 118))
    # tide-pool water in front
    cv.rect(0, 51, W - 1, SCENE_H - 1, vgrad(51, SCENE_H, [(70, 180, 220), (40, 130, 190)]))
    for _ in range(25):
        x, y = r.randrange(W), r.randrange(51, SCENE_H)
        cv.line(x, y, x + 2, y, (170, 230, 250))
    cv.rect(0, 51, W - 1, 51, (220, 248, 255))

    s = ripplefin_sprite(scale)
    cv.ellipse(50, 51, 13, 1.6, (82, 88, 110))  # shadow on the rock
    cv.paste(s, 26, 9)
    # splash droplets
    for x, y in ((22, 20), (24, 14), (80, 18), (77, 26), (20, 32)):
        cv.ellipse(x, y, 1.2, 1.6, (200, 245, 255))
        cv.set(x, y - 1, (255, 255, 255))

    caption(cv, "RIPPLEFIN", "WATER", (110, 210, 255), (110, 210, 255))
    return cv


# =========================================================================
# 3. THE OBSIDIAN CITADEL under the Rift
# =========================================================================
def citadel(scale=1):
    pixel.SCALE = scale
    cv = Canvas(W, H, scale=scale)
    r = rng(23)
    sky = vgrad(0, 50, [(8, 5, 22), (34, 10, 46), (96, 22, 58), (190, 58, 48)])
    cv.rect(0, 0, W - 1, SCENE_H - 1, sky)
    for _ in range(60):
        x, y = r.randrange(W), r.randrange(0, 28)
        b = r.choice([(90, 80, 140), (150, 140, 210), (230, 225, 255)])
        cv.setp(x * scale, y * scale, b)

    # the Rift: a swirling portal above the spire
    cx, cy = 50, 9
    cols = [(70, 20, 110), (150, 40, 190), (220, 90, 230), (255, 200, 255)]

    def rift(x, y):
        dx = (x + 0.5 - cx) / 20
        dy = (y + 0.5 - cy) / 7
        d = math.sqrt(dx * dx + dy * dy)
        a = math.atan2(dy, dx)
        band = int(d * 7 + a * 1.6 + 7) % 3
        inner = 1 - d
        idx = min(3, int(inner * 3.2) + (1 if band == 0 else 0))
        return cols[max(0, idx)]
    cv.ellipse(cx, cy, 20, 7, rift)
    cv.ellipse(cx, cy, 5, 1.8, (255, 235, 255))
    # glow halo
    for y in range(0, 22):
        for x in range(20, 81):
            dx, dy = (x - cx) / 26, (y - cy) / 10
            d = dx * dx + dy * dy
            if 1.0 < d < 1.6 and (x + y) % 2 == 0:
                cv.set(x, y, mix(cv.get(x, y), (150, 40, 190), 0.35))

    # distant mountain layers
    def ridge(base, amp, col, seed):
        rr = rng(seed)
        h = base
        for x in range(W):
            h += rr.uniform(-1.6, 1.6)
            h = max(base - amp, min(base + amp, h))
            cv.rect(x, int(h), x, SCENE_H - 1, col)
    ridge(38, 5, (58, 22, 66), 5)
    ridge(44, 3, (32, 12, 40), 9)

    # ---- the fortress ------------------------------------------------------
    obs = (24, 18, 34)

    def stone(x0, x1):
        def f(x, y):
            x, y = I(x), I(y)
            if x <= x0 + 1:
                return (92, 56, 128)           # rift-lit left edge
            if x >= x1 - 1:
                return (120, 40, 40)           # lava-lit right edge
            base = obs if (x + y // 3) % 7 else (34, 26, 46)
            if y > 44:
                base = mix(base, (110, 30, 20), (y - 44) / 14)
            return base
        return f

    def tower(x0, x1, top, roof_top, bottom=50):
        cv.rect(x0, top, x1, bottom, stone(x0, x1))
        mid = (x0 + x1) / 2
        cv.polygon([(x0 - 1, top + 0.5), (mid + 0.5, roof_top), (x1 + 2, top + 0.5)],
                   lambda x, y: (60, 30, 80) if x < mid else (28, 16, 36))
        for x in range(x0, x1 + 1, 2):        # battlement ring
            cv.set(x, top, (14, 10, 22))

    def wall(x0, x1, top, bottom=50):
        cv.rect(x0, top, x1, bottom, stone(x0, x1))
        for x in range(x0, x1 + 1, 2):
            cv.set(x, top - 1, obs)

    wall(22, 30, 38); wall(70, 78, 38)
    wall(35, 42, 33); wall(58, 65, 33)
    tower(16, 22, 33, 26); tower(78, 84, 33, 26)
    tower(29, 36, 25, 15); tower(64, 71, 25, 15)
    # central keep and spire
    cv.rect(42, 19, 58, 50, stone(42, 58))
    cv.polygon([(41, 19.5), (50, 2), (59.5, 19.5)],
               lambda x, y: (70, 34, 96) if x < 50 else (30, 16, 40))
    cv.line(50, 2, 50, 19, (130, 70, 170))
    for x in range(42, 59, 2):
        cv.set(x, 19, (14, 10, 22))
    # lightning from the Rift to the spire tip
    bolt = [(47, 9), (49, 4), (48, 3), (51, 1), (50, 2)]
    for (x0, y0), (x1, y1) in zip(bolt, bolt[1:]):
        cv.line(x0, y0, x1, y1, (255, 240, 255))
    # glowing windows
    win = [(45, 23), (49, 23), (53, 23), (55, 29), (45, 29), (50, 33), (32, 29),
           (67, 29), (32, 36), (67, 36), (19, 38), (81, 38), (26, 42), (74, 42),
           (38, 38), (61, 38)]
    for i, (x, y) in enumerate(win):
        c = (255, 170, 60) if i % 3 else (220, 110, 255)
        cv.set(x, y, c)
        cv.set(x, y + 1, darker(c, 0.75))
    # the great gate
    cv.ellipse(50, 44, 4, 4, (40, 10, 10))
    cv.rect(46, 44, 54, 50, (40, 10, 10))
    cv.ellipse(50, 45, 3, 3, lambda x, y: mix((255, 120, 40), (255, 210, 90), (y - 42) / 8))
    cv.rect(47, 45, 53, 50, lambda x, y: mix((255, 120, 40), (255, 210, 90), (y - 42) / 8))
    for x in range(47, 54, 2):
        cv.line(x, 42, x, 50, (60, 20, 14))
    for y in (45, 48):
        cv.line(47, y, 53, y, (60, 20, 14))

    # ground, lava moat and bridge
    cv.rect(0, 50, W - 1, SCENE_H - 1, (28, 14, 22))
    lava = vgrad(51, 55, [(255, 210, 90), (240, 100, 30), (150, 30, 20)])
    cv.rect(0, 51, W - 1, 54, lava)
    for _ in range(30):
        x, y = r.randrange(W), r.randrange(51, 55)
        cv.line(x, y, x + 1, y, (255, 240, 170))
    cv.polygon([(45.5, 50), (54.5, 50), (58, 56), (42, 56)],
               lambda x, y: (60, 40, 60) if I(x) in (int(42 + (I(y) - 50) * -0.6), 45) else (36, 24, 40))
    cv.line(45, 50, 42, 55, (110, 70, 110))
    cv.line(55, 50, 58, 55, (110, 50, 50))
    # embers rising
    for _ in range(26):
        x = r.randrange(W)
        y = r.randrange(30, 50)
        if r.random() < 0.6:
            cv.set(x, y, r.choice([(255, 140, 50), (255, 200, 90), (200, 70, 40)]))

    caption(cv, "OBSIDIAN CITADEL", "", (0, 0, 0), (200, 80, 230))
    return cv


SCENES = {"hero": hero, "creature": creature, "citadel": citadel}
