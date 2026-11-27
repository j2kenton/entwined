"""Backdrops: one per land, plus the Citadel's hall, its rooftop and the title.

Every backdrop is 100 x 60 logical pixels. The lower half is ground, where
battles put their two platforms.
"""
import math

from ..engine.canvas import Canvas, I, ball_shader, darker, lighter, mix, rng, vgrad

W, H = 100, 60
HORIZON = 31
ENEMY_SPOT = (76, 31)     # where the far creature stands
PLAYER_SPOT = (25, 56)    # where the near creature stands


def _clouds(cv, spots, col, shade):
    for cx, cy, s in spots:
        for ox, oy, rx, ry in ((0, 0, 7, 2.4), (-5, 1, 5, 2), (6, 1, 5, 1.8), (1, -1.6, 4, 2)):
            cv.ellipse(cx + ox * s, cy + oy, rx * s, ry, col)
        cv.ellipse(cx, cy + 1.5, 8 * s, 0.9, shade)


def _ground(cv, S, stops, speck, seed, n=70):
    cv.rect(0, HORIZON, W - 1, H - 1, vgrad(HORIZON, H, stops, S))
    r = rng(seed)
    for _ in range(n):
        x, y = r.randrange(W), r.randrange(HORIZON + 1, H)
        cv.set(x, y, r.choice(speck))


def _platforms(cv, dark, light):
    for (cx, cy), rx in ((ENEMY_SPOT, 18), (PLAYER_SPOT, 23)):
        cv.ellipse(cx, cy, rx, 3.6, darker(dark, 0.8))
        cv.ellipse(cx, cy - 0.6, rx - 1, 3.0, light)
        cv.ellipse(cx, cy - 0.3, rx - 4, 2.0, mix(light, dark, 0.45))


def _ridge(cv, base, amp, col, seed, step=1.2, bottom=HORIZON):
    r = rng(seed)
    h = float(base)
    for x in range(W):
        h = max(base - amp, min(base + amp, h + r.uniform(-step, step)))
        cv.rect(x, int(h), x, bottom, col)


# ----- the six lands -----------------------------------------------------
def wave(cv, S):
    cv.rect(0, 0, W - 1, 24, vgrad(0, 24, [(96, 170, 245), (150, 210, 255), (205, 238, 255)], S))
    _clouds(cv, ((16, 7, 1.0), (70, 5, 1.2), (92, 14, 0.7)), (255, 255, 255), (215, 232, 250))
    cv.rect(0, 24, W - 1, HORIZON, vgrad(24, HORIZON + 1, [(46, 140, 210), (30, 104, 180)], S))
    r = rng(11)
    for _ in range(26):
        y, x = r.randrange(25, HORIZON), r.randrange(W)
        cv.line(x, y, x + r.randrange(2, 5), y, (150, 215, 245))
    cv.rect(0, 24, W - 1, 24, (210, 240, 255))
    for (x0, x1, top) in ((4, 26, 17), (34, 50, 20), (84, 99, 18)):       # islands
        mid = (x0 + x1) / 2
        cv.polygon([(x0, 25), (mid - 4, top + 2), (mid, top), (mid + 5, top + 3), (x1, 25)], (70, 150, 100))
        cv.polygon([(x0 + 2, 25), (mid - 3, top + 3), (mid - 1, top + 1), (mid, 25)], (104, 184, 120))
        cv.rect(x0, 25, x1, 25, (236, 220, 170))
    _ground(cv, S, [(238, 218, 166), (220, 194, 138), (196, 166, 114)],
            [(250, 236, 196), (186, 156, 106), (255, 255, 255)], 12)
    cv.rect(0, HORIZON, W - 1, HORIZON, (226, 246, 255))
    return (196, 166, 116), (236, 214, 160)


def flame(cv, S):
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(38, 14, 40), (120, 40, 52), (236, 124, 70)], S))
    r = rng(9)
    for _ in range(14):
        cv.setp(int(r.randrange(W) * S), int(r.randrange(0, 8) * S), (190, 150, 200))
    _ridge(cv, 27, 3, (92, 38, 56), 5)
    cv.polygon([(46, 32), (62, 9), (70, 9), (88, 32)], lambda x, y: (82, 34, 46) if x < 64 else (58, 24, 38))
    cv.rect(62, 9, 70, 9, (255, 150, 60))
    cv.rect(63, 8, 69, 8, (255, 210, 110))
    for x0, x1 in ((64, 58), (67, 70), (66, 64)):
        cv.line(x0, 10, x1, 24, (230, 90, 40))
    for cx, cy, rr in ((66, 5, 3), (62, 3, 2.5), (70, 2, 2.2), (65, 0, 2)):
        cv.ellipse(cx, cy, rr + 1, rr * 0.8, (110, 70, 80))
        cv.ellipse(cx - 0.6, cy - 0.5, rr * 0.7, rr * 0.5, (150, 100, 105))
    _ground(cv, S, [(112, 62, 52), (72, 38, 36), (52, 26, 28)], [(60, 32, 30), (60, 32, 30), (140, 84, 66)], 10)
    for pts in (((4, 40), (12, 43), (18, 42)), ((80, 52), (88, 50), (96, 53)),
                ((52, 36), (58, 38)), ((60, 56), (70, 57))):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            cv.line(x0, y0, x1, y1, (240, 110, 40))
    return (96, 52, 44), (144, 86, 66)


def root(cv, S):
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(50, 110, 104), (120, 184, 146), (204, 234, 172)], S))
    r = rng(21)
    for layer, (col, base, size) in enumerate((((60, 124, 96), 22, 5), ((40, 98, 76), 26, 6), ((28, 74, 58), 30, 7))):
        x = -4 + layer * 2
        while x < W + 6:
            h = size + r.uniform(-1.5, 2.5)
            cv.polygon([(x - h * 0.55, base + 2), (x, base - h * 1.6), (x + h * 0.55, base + 2)], col)
            cv.rect(int(x - h * 0.55), base + 2, int(x + h * 0.55), HORIZON, col)
            x += h * 0.75 + r.uniform(0, 2)
    for tx, top in ((3, 0), (95, 0)):                    # big near trunks
        cv.rect(tx - 2, top, tx + 2, 46, lambda x, y: (96, 64, 40) if (I(x) + I(y) // 4) % 3 else (70, 46, 30))
        for ox, oy, rr in ((-6, 3, 8), (5, 1, 9), (0, 9, 8), (-9, 12, 6), (9, 13, 6)):
            cv.ellipse(tx + ox, top + oy, rr, rr * 0.7, ball_shader(tx + ox, top + oy, rr, rr * 0.7, (44, 110, 62), (80, 150, 80), (26, 76, 50)))
    _ground(cv, S, [(86, 156, 78), (58, 122, 64), (38, 88, 54)],
            [(120, 190, 96), (40, 96, 52), (40, 96, 52), (250, 230, 120), (240, 150, 170)], 22, 90)
    return (52, 110, 58), (104, 168, 88)


def breeze(cv, S):
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(80, 140, 228), (150, 200, 246), (226, 240, 250)], S))
    for (x, top, half, col) in ((12, 3, 4, (132, 146, 176)), (88, 1, 5, (132, 146, 176)),
                                (24, 12, 3, (160, 172, 198)), (60, 8, 3.5, (160, 172, 198)),
                                (76, 15, 2.5, (182, 192, 214)), (42, 17, 2.2, (182, 192, 214))):
        cv.polygon([(x - half, HORIZON + 1), (x - half * 0.5, top + 3), (x, top), (x + half * 0.6, top + 4), (x + half, HORIZON + 1)],
                   lambda px, py, x=x, col=col: col if px < x else darker(col, 0.8))
        cv.line(x - half * 0.2, top + 6, x - half * 0.4, top + 14, lighter(col, 0.3))
    _clouds(cv, ((30, 6, 0.9), (72, 22, 0.8), (50, 13, 0.6)), (255, 255, 255), (214, 228, 246))
    for x in range(-4, W + 6, 9):                         # sea of cloud at the edge
        cv.ellipse(x + (x * 7) % 5, 30, 7, 2.6, (246, 250, 255))
    _ground(cv, S, [(206, 212, 224), (176, 184, 202), (142, 150, 174)],
            [(226, 232, 242), (120, 130, 156), (120, 130, 156)], 31, 60)
    for (x0, y0, x1, y1) in ((6, 40, 16, 43), (16, 43, 20, 48), (70, 50, 84, 52), (84, 52, 92, 57), (44, 36, 52, 38)):
        cv.line(x0, y0, x1, y1, (118, 126, 152))
    return (150, 158, 182), (214, 220, 232)


def soil(cv, S):
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(236, 156, 100), (250, 200, 146), (255, 232, 196)], S))
    cv.ellipse(22, 9, 5, 5, (255, 244, 214))
    for (x0, x1, top, col) in ((0, 26, 15, (150, 80, 56)), (56, 99, 12, (150, 80, 56)),
                               (20, 48, 21, (180, 100, 66)), (70, 96, 22, (180, 100, 66))):
        cv.polygon([(x0 - 2, HORIZON + 1), (x0 + 2, top + 1), (x0 + 4, top), (x1 - 4, top), (x1 - 1, top + 2), (x1 + 2, HORIZON + 1)], col)
        for k in range(top + 3, HORIZON, 4):
            cv.line(x0 + 2, k, x1 - 1, k, darker(col, 0.82))
        cv.rect(x0 + 4, top, x1 - 4, top, lighter(col, 0.35))
    _ground(cv, S, [(196, 124, 82), (164, 98, 64), (122, 72, 50)],
            [(224, 160, 112), (110, 64, 44), (110, 64, 44), (150, 150, 160)], 41, 80)
    return (140, 84, 58), (206, 142, 100)


def lightning(cv, S):
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(26, 22, 56), (64, 54, 108), (136, 112, 156)], S))
    for cx, cy, rx in ((14, 4, 16), (44, 2, 18), (78, 5, 20), (60, 9, 12), (26, 10, 11), (94, 11, 10)):
        cv.ellipse(cx, cy, rx, 4.2, (46, 40, 82))
        cv.ellipse(cx - 2, cy - 1.2, rx * 0.7, 2.4, (66, 58, 108))
    bolt = [(30, 12), (27, 17), (31, 18), (26, 24), (29, 25), (25, 30)]
    for (x0, y0), (x1, y1) in zip(bolt, bolt[1:]):
        cv.line(x0, y0, x1, y1, (255, 250, 210))
        cv.line(x0 + 1, y0, x1 + 1, y1, (255, 230, 120))
    r = rng(51)
    x = -3.0
    while x < W + 4:                                     # jagged crags
        h = r.uniform(4, 11)
        w = r.uniform(4, 8)
        cv.polygon([(x, HORIZON + 1), (x + w * 0.4, HORIZON - h), (x + w * 0.6, HORIZON - h * 0.7), (x + w, HORIZON + 1)],
                   lambda px, py, x=x, w=w: (58, 52, 92) if px < x + w * 0.45 else (40, 36, 68))
        x += w * 0.8
    _ground(cv, S, [(92, 86, 130), (64, 60, 98), (44, 40, 72)],
            [(124, 116, 168), (36, 32, 60), (36, 32, 60), (255, 232, 110)], 52, 80)
    return (62, 58, 98), (118, 110, 162)


# ----- the Citadel --------------------------------------------------------
def _rift(cv, cx, cy, rx, ry):
    cols = [(70, 20, 110), (150, 40, 190), (220, 90, 230), (255, 200, 255)]

    def swirl(x, y):
        dx = (x + 0.5 - cx) / rx
        dy = (y + 0.5 - cy) / ry
        d = math.sqrt(dx * dx + dy * dy)
        band = int(d * 7 + math.atan2(dy, dx) * 1.6 + 7) % 3
        return cols[max(0, min(3, int((1 - d) * 3.2) + (1 if band == 0 else 0)))]
    cv.ellipse(cx, cy, rx, ry, swirl)
    cv.ellipse(cx, cy, rx * 0.25, ry * 0.26, (255, 235, 255))


def hall(cv, S):
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(14, 10, 26), (30, 20, 48), (48, 30, 70)], S))
    for wx in (30, 62):                                   # tall windows on to the Rift
        cv.ellipse(wx, 9, 5, 5, (150, 40, 190))
        cv.rect(wx - 5, 9, wx + 4, 24, vgrad(9, 25, [(150, 40, 190), (220, 90, 230)], S))
        cv.rect(wx - 1, 5, wx - 1, 24, (30, 20, 48))
        cv.rect(wx - 5, 16, wx + 4, 16, (30, 20, 48))
    for px in (10, 46, 90):                               # pillars with torches
        cv.rect(px - 3, 0, px + 3, HORIZON, lambda x, y, px=px: (58, 42, 84) if x < px - 1 else ((40, 30, 62) if x < px + 2 else (26, 18, 42)))
        cv.rect(px - 4, HORIZON - 2, px + 4, HORIZON, (66, 48, 96))
        cv.rect(px - 4, 0, px + 4, 1, (66, 48, 96))
        cv.rect(px - 1, 15, px, 17, (90, 70, 60))
        cv.polygon([(px - 2.5, 15), (px - 0.5, 9), (px + 1.5, 15)], (200, 90, 240))
        cv.polygon([(px - 1.5, 15), (px - 0.5, 11.5), (px + 0.5, 15)], (255, 210, 255))
    cv.rect(0, HORIZON, W - 1, H - 1, vgrad(HORIZON, H, [(52, 38, 76), (34, 24, 52), (22, 16, 36)], S))
    for y in (33, 36, 40, 45, 51, 58):                    # floor tiles in perspective
        cv.line(0, y, W - 1, y, (70, 52, 100))
    for k in range(-8, 9):
        cv.line(50 + k * 6, HORIZON, 50 + k * 16, H - 1, (70, 52, 100))
    return (56, 40, 84), (112, 80, 150)


def rooftop(cv, S):
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(8, 5, 22), (40, 12, 52), (120, 30, 70)], S))
    r = rng(23)
    for _ in range(40):
        cv.setp(int(r.randrange(W) * S), int(r.randrange(0, 26) * S),
                r.choice([(90, 80, 140), (150, 140, 210), (230, 225, 255)]))
    _rift(cv, 50, 9, 34, 8.5)
    for x in range(20, 81):                               # halo
        for y in range(0, 24):
            dx, dy = (x - 50) / 40, (y - 9) / 11.5
            if 1.0 < dx * dx + dy * dy < 1.35 and (x + y) % 2 == 0:
                cv.set(x, y, mix(cv.get(x, y), (150, 40, 190), 0.35))
    bolt = [(44, 14), (47, 19), (45, 20), (49, 26)]
    for (x0, y0), (x1, y1) in zip(bolt, bolt[1:]):
        cv.line(x0, y0, x1, y1, (255, 240, 255))
    cv.rect(0, 27, W - 1, HORIZON, (24, 18, 34))          # battlements
    for x in range(0, W, 6):
        cv.rect(x, 24, x + 2, 27, (24, 18, 34))
        cv.rect(x, 24, x, 27, (92, 56, 128))
    cv.rect(0, HORIZON, W - 1, H - 1, vgrad(HORIZON, H, [(60, 40, 84), (38, 26, 56), (22, 16, 34)], S))
    for y in (33, 36, 40, 45, 51, 58):
        cv.line(0, y, W - 1, y, (84, 58, 116))
    for k in range(-8, 9):
        cv.line(50 + k * 6, HORIZON, 50 + k * 16, H - 1, (84, 58, 116))
    return (60, 40, 88), (128, 88, 170)


def _dais(cv, top, face, face_lo, lip, runner=None):
    """The platform at the centre of the Citadel's roof: two steps up from the stones."""
    cv.polygon([(34, 39), (66, 39), (71, 46), (29, 46)], top)
    cv.rect(29, 46, 71, 49, face)
    cv.rect(29, 46, 71, 46, lip)
    cv.polygon([(27, 49), (73, 49), (76, 53), (24, 53)], top)
    cv.rect(24, 53, 76, 56, face_lo)
    cv.rect(24, 53, 76, 53, lip)
    if runner:                                            # a cloth laid up and over the steps
        hi, lo = runner
        cv.polygon([(46, 39), (54, 39), (55.5, 46), (44.5, 46)], hi)
        cv.rect(44.5, 46, 55.5, 49, lo)
        cv.polygon([(44, 49), (56, 49), (57, 53), (43, 53)], hi)
        cv.rect(43, 53, 57, 56, lo)
        cv.polygon([(43, 56), (57, 56), (59, H - 1), (41, H - 1)], hi)


def roof_dais(cv, S):
    """The rooftop at night, seen from further back: the platform stands in the middle of it."""
    rooftop(cv, S)
    _dais(cv, (76, 54, 106), (44, 30, 66), (30, 20, 48), (120, 86, 160))
    return None, None


def wedding(cv, S):
    """The same rooftop in spring daylight, dressed for a wedding: a raised
    platform in the middle with a canopy over it."""
    cv.rect(0, 0, W - 1, HORIZON, vgrad(0, HORIZON, [(118, 168, 226), (176, 208, 238), (250, 226, 206)], S))
    _clouds(cv, [(12, 7, 1.0), (88, 6, 1.1), (76, 15, 0.5)], (255, 255, 255), (228, 234, 246))
    # the Rift, quiet for once: a pale ring where it howled before
    for x in range(16, 85):
        for y in range(0, 22):
            dx, dy = (x - 50) / 34, (y - 9) / 8.5
            d = dx * dx + dy * dy
            if 0.66 < d < 1.0 and (x + y) % 2 == 0:
                cv.set(x, y, mix(cv.get(x, y), (236, 206, 250), 0.6))
    stone, edge = (168, 156, 186), (212, 204, 226)
    cv.rect(0, 27, W - 1, HORIZON, stone)                 # the same battlements
    for x in range(0, W, 6):
        cv.rect(x, 24, x + 2, 27, stone)
        cv.rect(x, 24, x, 27, edge)
    cv.rect(0, HORIZON, W - 1, H - 1, vgrad(HORIZON, H, [(214, 202, 214), (192, 178, 196), (166, 152, 174)], S))
    for y in (33, 36, 40, 45, 51, 58):
        cv.line(0, y, W - 1, y, (226, 216, 228))
    for k in range(-8, 9):
        cv.line(50 + k * 6, HORIZON, 50 + k * 16, H - 1, (226, 216, 228))
    from ..rules import ELEMENTS
    cols = [tuple(ELEMENTS["colour"][e]) for e in ELEMENTS["order"]]
    # bunting from the walls to the canopy, in all six natures' colours
    for x0, x1 in ((2, 30), (98, 70)):
        pts = [(x0 + (x1 - x0) * t / 10, 22 - 10 * (t / 10) + 3.5 * (1 - (2 * t / 10 - 1) ** 2)) for t in range(11)]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            cv.line(xa, ya, xb, yb, (120, 96, 84))
        for n, (x, y) in enumerate(pts[1:-1]):
            cv.polygon([(x - 1.4, y + 0.4), (x + 1.4, y + 0.4), (x, y + 3.8)], cols[n % 6])
    # the canopy: four poles and a cloth roof, flowers along its edge
    pole, cloth, cloth_lo = (236, 226, 214), (255, 252, 246), (232, 222, 226)
    for x in (39, 61):                                    # back poles
        cv.rect(x, 15, x, 40, darker(pole, 0.85))
    cv.polygon([(30, 11), (70, 11), (62, 16), (38, 16)], cloth_lo)             # the roof's underside
    cv.polygon([(29, 8), (71, 8), (70, 12), (30, 12)], cloth)                  # its front edge
    for i, x in enumerate(range(30, 70, 4)):
        cv.polygon([(x, 12), (x + 4, 12), (x + 2, 15)], cloth if i % 2 else (250, 214, 222))
    for i, x in enumerate(range(30, 71, 3)):
        cv.ellipse(x, 8.6, 1.3, 1.2, [(255, 236, 240), (250, 196, 208), (255, 246, 214)][i % 3])
    # the platform: two steps up from the stones
    _dais(cv, (244, 238, 244), (170, 154, 184), (142, 126, 162), (255, 255, 255), ((228, 148, 156), (196, 108, 122)))
    for x in (31, 69):                                    # front poles, wound with flowers
        cv.rect(x, 10, x, 46, pole)
        cv.rect(x + 1, 10, x + 1, 46, darker(pole, 0.85))
        for i, y in enumerate(range(14, 46, 5)):
            cv.ellipse(x + (0.5 if i % 2 else 1), y, 1.4, 1.3, [(250, 196, 208), (255, 246, 214), (255, 236, 240)][i % 3])
            cv.set(x - 1 + 3 * (i % 2), y + 1, (120, 180, 120))
    r = rng(57)                                           # petals in the air and on the stones
    for _ in range(70):
        x, y = r.randrange(2, W - 2), r.randrange(14, H - 1)
        if 24 < x < 76 and 16 < y < 57:
            continue                                      # not across the couple or the steps
        cv.set(x, y, r.choice([(255, 236, 240), (250, 196, 208), (255, 246, 214)]))
    return None, None


def title(cv, S):
    """The Citadel from outside, under the Rift."""
    r = rng(23)
    cv.rect(0, 0, W - 1, H - 1, vgrad(0, 52, [(8, 5, 22), (34, 10, 46), (96, 22, 58), (190, 58, 48)], S))
    for _ in range(60):
        cv.setp(int(r.randrange(W) * S), int(r.randrange(0, 28) * S),
                r.choice([(90, 80, 140), (150, 140, 210), (230, 225, 255)]))
    _rift(cv, 50, 9, 20, 7)
    for y in range(0, 22):
        for x in range(20, 81):
            dx, dy = (x - 50) / 26, (y - 9) / 10
            if 1.0 < dx * dx + dy * dy < 1.6 and (x + y) % 2 == 0:
                cv.set(x, y, mix(cv.get(x, y), (150, 40, 190), 0.35))
    _ridge(cv, 40, 5, (58, 22, 66), 5, 1.6, H - 1)
    _ridge(cv, 46, 3, (32, 12, 40), 9, 1.6, H - 1)
    obs = (24, 18, 34)

    def stone(x0, x1):
        def f(x, y):
            x, y = I(x), I(y)
            if x <= x0 + 1:
                return (92, 56, 128)
            if x >= x1 - 1:
                return (120, 40, 40)
            base = obs if (x + y // 3) % 7 else (34, 26, 46)
            return mix(base, (110, 30, 20), (y - 46) / 14) if y > 46 else base
        return f

    def tower(x0, x1, top, roof_top, bottom=52):
        cv.rect(x0, top, x1, bottom, stone(x0, x1))
        mid = (x0 + x1) / 2
        cv.polygon([(x0 - 1, top + 0.5), (mid + 0.5, roof_top), (x1 + 2, top + 0.5)],
                   lambda x, y: (60, 30, 80) if x < mid else (28, 16, 36))
        for x in range(x0, x1 + 1, 2):
            cv.set(x, top, (14, 10, 22))

    def wall(x0, x1, top, bottom=52):
        cv.rect(x0, top, x1, bottom, stone(x0, x1))
        for x in range(x0, x1 + 1, 2):
            cv.set(x, top - 1, obs)

    wall(22, 30, 40); wall(70, 78, 40)
    wall(35, 42, 35); wall(58, 65, 35)
    tower(16, 22, 35, 28); tower(78, 84, 35, 28)
    tower(29, 36, 27, 17); tower(64, 71, 27, 17)
    cv.rect(42, 21, 58, 52, stone(42, 58))
    cv.polygon([(41, 21.5), (50, 4), (59.5, 21.5)], lambda x, y: (70, 34, 96) if x < 50 else (30, 16, 40))
    cv.line(50, 4, 50, 21, (130, 70, 170))
    for x in range(42, 59, 2):
        cv.set(x, 21, (14, 10, 22))
    for (x0, y0), (x1, y1) in zip([(47, 10), (49, 6), (48, 5), (50, 4)], [(49, 6), (48, 5), (50, 4), (50, 4)]):
        cv.line(x0, y0, x1, y1, (255, 240, 255))
    win = [(45, 25), (49, 25), (53, 25), (55, 31), (45, 31), (50, 35), (32, 31), (67, 31),
           (32, 38), (67, 38), (19, 40), (81, 40), (26, 44), (74, 44), (38, 40), (61, 40)]
    for i, (x, y) in enumerate(win):
        c = (255, 170, 60) if i % 3 else (220, 110, 255)
        cv.set(x, y, c)
        cv.set(x, y + 1, darker(c, 0.75))
    cv.ellipse(50, 46, 4, 4, (40, 10, 10))
    cv.rect(46, 46, 54, 52, (40, 10, 10))
    glow = lambda x, y: mix((255, 120, 40), (255, 210, 90), (y - 44) / 8)
    cv.ellipse(50, 47, 3, 3, glow)
    cv.rect(47, 47, 53, 52, glow)
    for x in range(47, 54, 2):
        cv.line(x, 44, x, 52, (60, 20, 14))
    for y in (47, 50):
        cv.line(47, y, 53, y, (60, 20, 14))
    cv.rect(0, 52, W - 1, H - 1, (28, 14, 22))
    cv.rect(0, 53, W - 1, 57, vgrad(53, 58, [(255, 210, 90), (240, 100, 30), (150, 30, 20)], S))
    for _ in range(30):
        x, y = r.randrange(W), r.randrange(53, 58)
        cv.line(x, y, x + 1, y, (255, 240, 170))
    cv.polygon([(45.5, 52), (54.5, 52), (59, 60), (41, 60)], (36, 24, 40))
    cv.line(45, 52, 41, 59, (110, 70, 110))
    cv.line(55, 52, 59, 59, (110, 50, 50))
    for _ in range(26):
        if r.random() < 0.6:
            cv.set(r.randrange(W), r.randrange(30, 52), r.choice([(255, 140, 50), (255, 200, 90), (200, 70, 40)]))
    return None, None


def blocked(answer, S):
    """The Citadel hall with something barring the way. `answer` is the nature
    whose power clears it (so a wall of fire is the "wave" picture)."""
    key = ("blocked", answer, S)
    if key in _cache:
        return _cache[key]
    cv = backdrop("hall", S, platforms=False).copy()
    r = rng(77)
    if answer == "wave":                                   # a wall of fire
        for x in range(-2, W + 4, 5):
            h = r.uniform(26, 44)
            for col, k in (((226, 64, 32), 1.0), ((255, 140, 40), 0.72), ((255, 226, 100), 0.42)):
                cv.polygon([(x - 4 * k, 58), (x - 2 * k, 58 - h * k * 0.6), (x + r.uniform(-1, 1), 58 - h * k),
                            (x + 2 * k, 58 - h * k * 0.6), (x + 4 * k, 58)], col)
        cv.rect(0, 57, W - 1, H - 1, (40, 20, 20))
    elif answer == "flame":                                # dry thorned vines over a door
        cv.rect(34, 8, 66, 52, (30, 22, 40))
        cv.rect(36, 10, 64, 52, (52, 40, 62))
        for _ in range(16):
            x0, x1 = r.uniform(26, 50), r.uniform(50, 74)
            y0, y1 = r.uniform(6, 54), r.uniform(6, 54)
            cv.thick_line(x0, y0, x1, y1, 1.1, (120, 104, 56))
            for t in (0.25, 0.5, 0.75):
                px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                cv.line(px, py, px + 2, py - 2, (176, 156, 90))
    elif answer == "root":                                 # a gap with old roots
        cv.polygon([(22, 36), (78, 36), (96, 60), (4, 60)], (6, 4, 12))
        cv.polygon([(26, 38), (74, 38), (88, 60), (12, 60)], (14, 8, 24))
        for x, sx in ((24, 1), (30, 1), (36, 1), (76, -1), (70, -1), (64, -1)):
            cv.thick_line(x, 36, x + sx * r.uniform(3, 8), 36 + r.uniform(8, 16), 0.8, (130, 124, 116))
    elif answer == "breeze":                               # choking smoke
        for _ in range(46):
            x, y, rr = r.uniform(0, W), r.uniform(4, 56), r.uniform(5, 11)
            cv.ellipse(x, y, rr, rr * 0.6, r.choice([(84, 80, 92), (110, 106, 118), (64, 60, 72)]))
    elif answer == "soil":                                 # a pit and loose rubble
        cv.ellipse(50, 47, 30, 9, (6, 4, 12))
        cv.ellipse(50, 48, 26, 7, (14, 8, 24))
        for _ in range(22):
            x, y, rr = r.uniform(6, 30), r.uniform(46, 58), r.uniform(1.5, 3.5)
            cv.ellipse(x, y, rr, rr * 0.8, ball_shader(x, y, rr, rr * 0.8, (120, 108, 112), (166, 154, 156), (76, 68, 76)))
    else:                                                  # an iron door and a dead machine
        cv.rect(32, 6, 68, 52, lambda x, y: (96, 100, 112) if x < 50 else (78, 82, 94))
        cv.rect(32, 6, 68, 7, (140, 144, 156))
        cv.rect(49, 6, 50, 52, (40, 42, 52))
        for y in (12, 24, 36, 48):
            for x in (35, 46, 53, 65):
                cv.set(x, y, (170, 174, 186))
        for k in range(7):                                 # copper coils
            cv.ellipse(80, 20 + k * 4, 5, 1.6, (190, 110, 60))
            cv.ellipse(80, 19.6 + k * 4, 3.4, 0.8, (240, 170, 100))
        cv.rect(77, 46, 83, 54, (70, 72, 84))
        cv.line(74, 32, 68, 30, (190, 110, 60))
    _cache[key] = cv
    return cv


PAINTERS = {"wave": wave, "flame": flame, "root": root, "breeze": breeze, "soil": soil,
            "lightning": lightning, "hall": hall, "rooftop": rooftop, "title": title, "wedding": wedding, "roof_dais": roof_dais}
_cache = {}


def backdrop(kind, S, platforms=True):
    """A finished backdrop canvas. Treat it as read-only: copy before drawing on it."""
    key = (kind, S, platforms)
    if key not in _cache:
        cv = Canvas(W, H, scale=S)
        dark, light = PAINTERS[kind](cv, S)
        if platforms and dark:
            _platforms(cv, dark, light)
        _cache[key] = cv
    return _cache[key]
