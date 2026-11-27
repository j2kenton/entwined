"""Twelve more creatures: a quick one and a sturdy one for each nature."""
import math

from ..engine.canvas import I, ball_shader, darker, lighter, mix

PALETTES = {
    "glidefin": dict(body=(62, 124, 214), hi=(124, 184, 246), lo=(36, 78, 162), belly=(222, 240, 255),
                     accent=(120, 222, 232), accent_lo=(70, 170, 200), tip=(246, 150, 190),
                     eye=(16, 28, 64), mark=(200, 240, 255), outline=(14, 30, 76), cheek=(246, 150, 190)),
    "shellby": dict(body=(110, 180, 236), hi=(170, 216, 250), lo=(64, 124, 196), belly=(214, 240, 252),
                    accent=(244, 156, 166), accent_lo=(204, 104, 130), tip=(255, 214, 200),
                    eye=(18, 30, 66), mark=(255, 230, 220), outline=(20, 40, 84), cheek=(246, 140, 170)),
    "flaremoth": dict(body=(236, 206, 164), hi=(255, 236, 204), lo=(190, 150, 110), belly=(255, 240, 214),
                      accent=(255, 140, 40), accent_lo=(226, 64, 32), tip=(255, 226, 100),
                      eye=(46, 22, 22), mark=(255, 210, 90), outline=(60, 24, 18), cheek=(250, 150, 120)),
    "coalback": dict(body=(196, 96, 52), hi=(236, 140, 84), lo=(140, 60, 34), belly=(240, 190, 140),
                     accent=(255, 150, 50), accent_lo=(66, 54, 60), tip=(255, 226, 110),
                     eye=(40, 20, 20), mark=(96, 80, 86), outline=(44, 22, 20), cheek=(250, 150, 110)),
    "twigtail": dict(body=(178, 124, 72), hi=(214, 164, 108), lo=(126, 82, 46), belly=(244, 222, 180),
                     accent=(104, 186, 78), accent_lo=(56, 130, 60), tip=(150, 100, 56),
                     eye=(30, 22, 18), mark=(196, 236, 130), outline=(44, 30, 20), cheek=(244, 150, 130)),
    "stumpkin": dict(body=(140, 100, 66), hi=(182, 140, 96), lo=(96, 66, 42), belly=(222, 190, 140),
                     accent=(104, 186, 78), accent_lo=(56, 130, 60), tip=(236, 90, 80),
                     eye=(26, 18, 14), mark=(190, 156, 110), outline=(40, 26, 18), cheek=(230, 140, 110)),
    "whirlet": dict(body=(150, 226, 204), hi=(210, 250, 236), lo=(90, 176, 160), belly=(244, 255, 246),
                    accent=(214, 244, 250), accent_lo=(120, 190, 214), tip=(255, 196, 80),
                    eye=(22, 40, 56), mark=(255, 255, 255), outline=(28, 64, 76), cheek=(250, 170, 170)),
    "driftpuff": dict(body=(246, 246, 236), hi=(255, 255, 255), lo=(204, 214, 214), belly=(255, 252, 240),
                      accent=(120, 196, 110), accent_lo=(70, 146, 80), tip=(255, 255, 255),
                      eye=(30, 44, 60), mark=(224, 240, 244), outline=(50, 80, 90), cheek=(250, 176, 176)),
    "dusthop": dict(body=(224, 184, 124), hi=(246, 218, 168), lo=(172, 130, 80), belly=(252, 238, 206),
                    accent=(250, 244, 226), accent_lo=(150, 106, 64), tip=(244, 150, 150),
                    eye=(28, 20, 16), mark=(196, 150, 96), outline=(60, 38, 22), cheek=(244, 150, 140)),
    "pebblit": dict(body=(154, 144, 136), hi=(200, 192, 184), lo=(104, 96, 92), belly=(176, 166, 156),
                    accent=(120, 214, 192), accent_lo=(64, 150, 140), tip=(255, 200, 90),
                    eye=(30, 24, 22), mark=(84, 78, 76), outline=(38, 34, 34), cheek=(200, 150, 130)),
    "flashfly": dict(body=(66, 60, 90), hi=(110, 104, 140), lo=(40, 36, 60), belly=(255, 232, 110),
                     accent=(255, 226, 90), accent_lo=(228, 170, 50), tip=(255, 252, 200),
                     eye=(22, 18, 34), mark=(206, 226, 250), outline=(24, 20, 40), cheek=(230, 130, 160),
                     face=(134, 124, 168)),
    "rumblehorn": dict(body=(96, 86, 138), hi=(140, 130, 182), lo=(62, 54, 98), belly=(176, 170, 206),
                       accent=(255, 226, 90), accent_lo=(224, 164, 44), tip=(255, 250, 190),
                       eye=(22, 18, 34), mark=(214, 210, 236), outline=(30, 26, 52), cheek=(230, 130, 160),
                       face=(142, 132, 184)),
}


def scowl(s, p, pts, rx, ry, lid=None):
    """Dark versions only: a heavy slanted lid over each eye, so the same black
    eyes glare instead of gaze. `lid` is the colour of the face around them."""
    if not p.get("dark"):
        return
    lid = lid or p["lo"]
    mid = sum(x for x, _ in pts) / len(pts)
    for ex, ey in pts:
        d = 1 if ex < mid else -1                       # which way is inward
        top = ey - ry - 0.8
        out_x, in_x = ex - d * (rx + 0.9), ex + d * (rx + 0.9)
        s.polygon([(out_x, top), (in_x, top), (in_x, ey - ry * 0.05)], lid)
        s.line(out_x, top + 0.3, in_x, ey - ry * 0.05, p["outline"])
        s.set(ex - d * 0.8 - 0.5, ey + 0.2, p["glint_small"])


def _eyes(s, p, pts, rx=2.0, ry=2.4, lid=None):
    for ex, ey in pts:
        s.ellipse(ex, ey, rx, ry, p["eye"])
        if not p.get("dark"):
            s.set(ex - 1, ey - 1.2, p["glint_small"])
    scowl(s, p, pts, rx, ry, lid)


def _smile(s, cx, y, col, p=None):
    """A little smile; on a dark version, a hard downturned mouth."""
    grim = bool(p and p.get("dark"))
    for x, dy in ((-2, 0), (-1, 1), (0, 1), (1, 0)):
        s.set(cx + x, y + (1 - dy if grim else dy), col)


def spike(s, x, y, dx, dy, half, col):
    """A thorn at (x, y) pointing along (dx, dy), `half` wide at its base."""
    n = math.hypot(dx, dy)
    px, py = -dy / n * half, dx / n * half
    s.polygon([(x + px, y + py), (x + dx, y + dy), (x - px, y - py)], col)


def glidefin(s, p, phase=0):
    cx = 24
    flap = math.sin(phase * math.tau) * 1.5
    sh = ball_shader(cx, 14, 22, 10, p["body"], p["hi"], p["lo"])
    s.thick_line(cx, 22, cx + 2, 27, 1.0, p["lo"])                      # tail
    s.thick_line(cx + 2, 27, cx + 5, 29, 0.7, p["lo"])
    dk = p.get("dark")
    if dk:
        s.polygon([(cx + 3.4, 27.6), (cx + 8.5, 30.6), (cx + 3.8, 30.6)], p["accent_lo"])    # tail barb
        for sx in (-1, 1):
            spike(s, cx + sx * 10.5, 19.5, sx * 0.6, 5.5, 1.5, p["lo"])
            spike(s, cx + sx * 14.5, 18, sx * 1.2, 5, 1.5, p["lo"])
            spike(s, cx + sx * 18.5, 15.5, sx * 2, 4.5, 1.4, p["lo"])
    s.polygon([(cx, 6), (cx + 12, 9), (cx + 22, 13 + flap), (cx + 16, 19), (cx + 7, 21), (cx, 23),
               (cx - 7, 21), (cx - 16, 19), (cx - 22, 13 + flap), (cx - 12, 9)], sh)
    for sx in (-1, 1):                                                  # wing tips + head fins
        s.polygon([(cx + sx * 22, 13 + flap), (cx + sx * 16, 19), (cx + sx * 15, 14)], p["accent"])
        s.polygon([(cx + sx * 4, 7), (cx + sx * 6, 1), (cx + sx * 8, 8)], p["accent_lo"])
        if dk:                                                          # longer, hooked horns
            s.polygon([(cx + sx * 6, 6), (cx + sx * 11.5, 0), (cx + sx * 9, 8)], p["accent_lo"])
        s.line(cx + sx * 9, 12, cx + sx * 14, 16, p["mark"])
    s.ellipse(cx, 17, 8, 4.5, p["belly"])
    _eyes(s, p, ((cx - 5, 12), (cx + 5, 12)))
    for sx in (-1, 1):
        s.ellipse(cx + sx * 8.5, 15.5, 1.5, 1.0, p["cheek"])
    _smile(s, cx, 16, darker(p["lo"], 0.6), p)


def shellby(s, p, phase=0):
    shell = p["accent"]
    s.ellipse(26, 15, 13.5, 12.5, ball_shader(26, 15, 13.5, 12.5, shell, lighter(shell, 0.4), p["accent_lo"]))
    s.ellipse(27, 15.5, 8.5, 8, p["accent_lo"])                          # spiral
    s.ellipse(27.5, 15.5, 5.8, 5.4, shell)
    s.ellipse(28, 16, 3, 2.8, p["accent_lo"])
    s.ellipse(28.5, 16, 1.2, 1.1, p["mark"])
    dk = p.get("dark")
    if dk:
        for deg in (-158, -128, -98, -68, -38, -10):
            a = math.radians(deg)
            spike(s, 26 + math.cos(a) * 12.6, 15 + math.sin(a) * 11.6, math.cos(a) * 4.6, math.sin(a) * 4.6, 2.1, p["accent_lo"])
        for deg in (-143, -113, -83, -53):
            a = math.radians(deg)
            spike(s, 26 + math.cos(a) * 8, 15 + math.sin(a) * 7.4, math.cos(a) * 3.2, math.sin(a) * 3.2, 1.5, darker(p["accent_lo"], 0.78))
    s.ellipse(21, 27.5, 15, 5.6, ball_shader(21, 27.5, 15, 5.6, p["body"], p["hi"], p["lo"]))   # foot
    s.ellipse(10, 21.5, 7, 7.2, ball_shader(10, 21.5, 7, 7.2, p["body"], p["hi"], p["lo"]))     # head
    for ax in (7, 13):                                                   # feelers
        s.line(ax, 15, ax - 1, 9.5, p["lo"])
        s.ellipse(ax - 1, 8.6, 1.3, 1.3, p["hi"])
    _eyes(s, p, ((7.5, 20.5), (12.5, 20.5)), 1.7, 2.1)
    s.ellipse(5, 24, 1.3, 0.9, p["cheek"])
    s.ellipse(15, 24, 1.3, 0.9, p["cheek"])
    _smile(s, 10, 24, darker(p["lo"], 0.6), p)
    for x in (12, 20, 28):
        s.set(x, 31, p["belly"])


def flaremoth(s, p, phase=0):
    cx = 23
    a = phase * math.tau
    flick = math.sin(a) * 1.2
    for sx in (-1, 1):
        s.polygon([(cx + sx * 3, 21), (cx + sx * 15, 31), (cx + sx * 5, 28)], p["accent_lo"])      # lower wings
        s.polygon([(cx + sx * 2, 15), (cx + sx * 19, 3 + flick), (cx + sx * 21, 15), (cx + sx * 13, 23)], p["accent_lo"])
        s.polygon([(cx + sx * 3, 15), (cx + sx * 17, 6 + flick), (cx + sx * 18, 15), (cx + sx * 12, 20)], p["accent"])
        if p.get("dark"):                                               # eyespots that stare back
            s.ellipse(cx + sx * 12.5, 13 + flick * 0.5, 3.6, 3.6, p["outline"])
            s.ellipse(cx + sx * 12.5, 13 + flick * 0.5, 2.5, 2.5, lighter(p["accent"], 0.18))
            s.ellipse(cx + sx * 12.5, 13 + flick * 0.5, 1.2, 1.2, p["outline"])
            s.polygon([(cx + sx * 10, 27), (cx + sx * 19, 32.6), (cx + sx * 14.5, 26)], p["accent_lo"])
            s.polygon([(cx + sx * 17, 17), (cx + sx * 22.6, 21), (cx + sx * 15, 21.5)], p["accent_lo"])
        else:
            s.polygon([(cx + sx * 6, 15), (cx + sx * 14, 9 + flick), (cx + sx * 14, 15), (cx + sx * 10, 18)], p["tip"])
        s.line(cx + sx * 2, 7, cx + sx * 7, 1, p["lo"])                    # feathery antennae
        s.ellipse(cx + sx * 7.5, 1.5, 1.4, 1.2, p["accent"])
    s.ellipse(cx, 20, 5, 8, ball_shader(cx, 20, 5, 8, p["body"], p["hi"], p["lo"]))
    for y in (19, 22, 25):
        s.line(cx - 4, y, cx + 4, y, p["lo"])
    s.ellipse(cx, 10.5, 5.6, 5, ball_shader(cx, 10.5, 5.6, 5, p["body"], p["hi"], p["lo"]))
    _eyes(s, p, ((cx - 2.6, 10), (cx + 2.6, 10)), 1.7, 2.1)
    for sx in (-1, 1):
        s.set(cx + sx * 5, 12.5, p["cheek"])
    s.set(cx - 0.5, 13.4, darker(p["lo"], 0.6))
    s.set(cx + 0.5, 13.4, darker(p["lo"], 0.6))


def coalback(s, p, phase=0):
    coal = p["accent_lo"]
    glow = p["accent"] if int(phase * 4) % 2 == 0 else p["tip"]
    for lx in (11, 20, 28, 36):                                          # legs
        s.ellipse(lx, 28.5, 3.2, 2.6, p["lo"])
    s.thick_line(39, 24, 43, 26, 1.1, p["lo"])                           # tail
    s.ellipse(25, 15.5, 16.5, 11.5, ball_shader(25, 15.5, 16.5, 11.5, coal, p["mark"], darker(coal, 0.7)))
    for pts in (((14, 12), (20, 15), (18, 21)), ((22, 6), (26, 12), (32, 10)), ((26, 12), (25, 19), (31, 22)),
                ((33, 14), (38, 17)), ((20, 15), (26, 12))):              # glowing cracks
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            s.line(x0, y0, x1, y1, glow)
    dk = p.get("dark")
    if dk:                                                               # a ridge of spikes
        for (x, y, dx, dy) in ((13, 9, -2.5, -6), (19, 5.5, -1, -5.5), (25, 4.2, 0.4, -4.2), (31, 5.5, 1.6, -5.2), (36.5, 9, 3, -5.5)):
            spike(s, x, y, dx, dy, 2.3, p["mark"])
            s.set(x + dx * 0.8, y + dy * 0.8, glow)
        s.ellipse(44.5, 26.5, 2.2, 2.2, p["lo"])                         # a clubbed tail
        spike(s, 45.5, 25, 1.8, -2.6, 1.0, p["mark"])
        spike(s, 46, 27.5, 2, 1.6, 1.0, p["mark"])
    else:
        s.polygon([(23, 6), (25, 0.5), (27, 6)], p["accent"])            # vent flame
        s.polygon([(24, 6), (25, 3), (26, 6)], p["tip"])
    s.rect(9, 24, 40, 25, p["lo"])                                       # shell rim
    s.ellipse(8.5, 21, 6.5, 5.8, ball_shader(8.5, 21, 6.5, 5.8, p["body"], p["hi"], p["lo"]))
    _eyes(s, p, ((6, 20), (11, 20)), 1.5, 1.9)
    s.ellipse(3.6, 22.8, 1.2, 0.9, p["cheek"])
    s.ellipse(13.4, 22.8, 1.2, 0.9, p["cheek"])
    _smile(s, 8.5, 23, darker(p["lo"], 0.55), p)


def twigtail(s, p, phase=0):
    leaf = lambda x, y: p["accent"] if (I(x) + I(y)) % 4 else p["mark"]
    s.polygon([(27, 31), (38, 25), (42, 12), (36, 2), (29, 9), (26, 22)], leaf)       # leaf tail
    s.line(28, 29, 37, 5, p["accent_lo"])
    for k in (10, 16, 22):
        s.line(31 + (22 - k) * 0.25, k + 2, 38 + (22 - k) * 0.1, k - 2, p["accent_lo"])
    dk = p.get("dark")
    if dk:                                                               # blight eating through the leaf
        for (x, y, rx, ry) in ((35.5, 11, 1.8, 2.3), (32.5, 19.5, 1.5, 2.0), (38.5, 17.5, 1.3, 1.7), (31, 26, 1.2, 1.4)):
            s.ellipse(x, y, rx + 0.7, ry + 0.7, mix(p["accent"], p["body"], 0.6))     # browned at the edges
            s.ellipse(x, y, rx, ry, p["outline"])
    s.ellipse(19, 27.5, 8.5, 8, ball_shader(19, 27.5, 8.5, 8, p["body"], p["hi"], p["lo"]))
    s.ellipse(18.5, 29, 5, 5.4, p["belly"])
    for sx in (-1, 1):                                                   # ears with tufts
        s.polygon([(19 + sx * 7.5, 11), (19 + sx * 7, 2), (19 + sx * 2.5, 9)], p["body"])
        s.polygon([(19 + sx * 6.5, 9.5), (19 + sx * 6.4, 5), (19 + sx * 4, 9)], p["cheek"])
        if dk:                                                           # longer, ragged ears
            s.polygon([(19 + sx * 7.4, 6), (19 + sx * 10.5, 0), (19 + sx * 5.5, 4)], p["body"])
        s.ellipse(19 + sx * 5, 34.8, 3.6, 1.7, p["lo"])                   # feet
    s.ellipse(19, 15, 9, 7.8, ball_shader(19, 15, 9, 7.8, p["body"], p["hi"], p["lo"]))
    s.ellipse(19, 18, 5, 3.6, p["belly"])
    _eyes(s, p, ((15, 14), (23, 14)), 2.0, 2.5)
    s.ellipse(12, 18, 1.5, 1.0, p["cheek"])
    s.ellipse(26, 18, 1.5, 1.0, p["cheek"])
    s.set(18.5, 16.6, darker(p["lo"], 0.5))
    s.set(19.5, 16.6, darker(p["lo"], 0.5))
    _smile(s, 19, 18, darker(p["lo"], 0.6), p)
    s.ellipse(19, 26, 2.8, 3, p["tip"])                                   # acorn
    s.ellipse(19, 23.8, 3, 1.5, darker(p["tip"], 0.7))
    s.ellipse(15.6, 26, 1.6, 1.4, p["body"])                              # paws
    s.ellipse(22.4, 26, 1.6, 1.4, p["body"])


def stumpkin(s, p, phase=0):
    cx = 21
    bark = lambda x, y: p["body"] if I(x) % 5 else p["lo"]
    for sx in (-1, 1):                                                   # roots
        s.polygon([(cx + sx * 12, 28), (cx + sx * 19, 34.5), (cx + sx * 8, 34)], p["lo"])
    s.polygon([(cx - 6, 30), (cx, 35), (cx + 6, 30)], p["lo"])
    s.polygon([(cx - 12, 12), (cx + 12, 12), (cx + 14, 32), (cx - 14, 32)], bark)
    s.rect(cx - 13, 14, cx - 11, 31, p["hi"])
    s.rect(cx + 11, 14, cx + 13, 31, darker(p["lo"], 0.8))
    s.ellipse(cx - 9, 25, 3.4, 5, p["accent"])                            # moss
    s.ellipse(cx - 9.5, 23.5, 2, 2.6, p["mark"])
    s.ellipse(cx, 12, 12.5, 4.2, p["belly"])                              # cut top with rings
    s.ellipse(cx, 12, 8, 2.6, p["mark"])
    s.ellipse(cx, 12, 4, 1.3, p["belly"])
    dk = p.get("dark")
    if dk:                                                               # splintered where it broke
        for (x, dx, dy, half) in ((cx - 8, -1, -7, 2), (cx - 3, 0.5, -9.5, 2.2), (cx + 3, -0.5, -6, 1.8), (cx + 8, 1.5, -8, 2)):
            spike(s, x, 10.5, dx, dy, half, p["body"])
            s.line(x, 10.5, x + dx, 10.5 + dy, p["lo"])
        for sx in (-1, 1):                                               # bare branches, like claws
            s.thick_line(cx + sx * 13, 19, cx + sx * 18.5, 13, 0.8, p["lo"])
            s.line(cx + sx * 16.5, 15.2, cx + sx * 20, 16.5, p["lo"])
            s.line(cx + sx * 18.5, 13, cx + sx * 19.5, 9.5, p["lo"])
            s.line(cx + sx * 18.5, 13, cx + sx * 20.6, 12, p["lo"])
    else:
        s.thick_line(cx + 5, 11, cx + 8, 5, 0.8, p["lo"])                 # sprout
        s.ellipse(cx + 11, 4.5, 3.2, 1.7, p["accent"])
        s.ellipse(cx + 6, 3.2, 2.6, 1.5, lighter(p["accent"], 0.3))
    s.ellipse(cx + 12.5, 22, 2.6, 1.6, p["tip"])                          # mushroom
    s.rect(cx + 12, 23, cx + 12, 25, p["belly"])
    if not p.get("dark"):
        s.set(cx + 12, 21.5, (255, 255, 255))
    _eyes(s, p, ((cx - 4.5, 20.5), (cx + 4.5, 20.5)), 2.1, 2.6)
    s.ellipse(cx - 8, 24.5, 1.4, 1.0, p["cheek"])
    s.ellipse(cx + 8, 24.5, 1.4, 1.0, p["cheek"])
    if dk:                                                               # a jagged hollow for a mouth
        s.polygon([(cx - 4.5, 24.5), (cx - 3, 27.5), (cx - 1.5, 25.6), (cx, 28), (cx + 1.5, 25.6), (cx + 3, 27.5),
                   (cx + 4.5, 24.5), (cx, 23.6)], p["outline"])
    else:
        _smile(s, cx, 25, darker(p["lo"], 0.5))


def whirlet(s, p, phase=0):
    cx = 20
    up = int(phase * 4) % 2 == 0
    for sx in (-1, 1):                                                   # blurred wings
        wy = 13 if up else 19
        s.ellipse(cx + sx * 11.5, wy, 7.5, 2.8, p["accent"])
        s.line(cx + sx * 6, wy, cx + sx * 17, wy - 1, p["accent_lo"])
        s.polygon([(cx + sx * 1, 10), (cx + sx * 8, 1.5), (cx + sx * 4.5, 1)], p["accent_lo"])   # seed-wing crest
    dk = p.get("dark")
    if dk:
        s.polygon([(cx - 1.8, 10.5), (cx, 0), (cx + 1.8, 10.5)], p["accent_lo"])
        s.polygon([(cx - 3, 26.5), (cx - 4.2, 32.4), (cx - 0.4, 28)], p["lo"])   # forked tail
        s.polygon([(cx + 3, 26.5), (cx + 4.2, 32.4), (cx + 0.4, 28)], p["lo"])
    else:
        s.polygon([(cx - 2.5, 27), (cx, 32), (cx + 2.5, 27)], p["lo"])    # tail
    s.ellipse(cx, 18, 7.5, 8, ball_shader(cx, 18, 7.5, 8, p["body"], p["hi"], p["lo"]))
    s.ellipse(cx, 21.5, 4.6, 4.2, p["belly"])
    _eyes(s, p, ((cx - 3.2, 15.5), (cx + 3.2, 15.5)), 1.9, 2.3)
    for sx in (-1, 1):
        s.ellipse(cx + sx * 6, 18.5, 1.3, 0.9, p["cheek"])
    s.polygon([(cx - 1.3, 17.5), (cx + 1.3, 17.5), (cx, 26.5 if dk else 23)], p["tip"])   # needle beak


def driftpuff(s, p, phase=0):
    cx, cy = 22, 16
    sway = math.sin(phase * math.tau) * 0.8
    s.thick_line(cx, 24, cx, 33, 1.0, p["accent_lo"])                    # stem
    for sx in (-1, 1):
        s.ellipse(cx + sx * 5, 34.5, 4.6, 1.8, p["accent"])               # leaf feet
        s.ellipse(cx + sx * 4, 29, 3.2, 1.4, p["accent"])
    for deg in range(0, 360, 20):                                        # fluff
        a = math.radians(deg)
        x1, y1 = cx + math.cos(a) * 15 + sway, cy + math.sin(a) * 14
        s.line(cx + math.cos(a) * 8, cy + math.sin(a) * 8, x1, y1, p["lo"])
        if p.get("dark"):                                                # thorns where the fluff was
            spike(s, x1 - math.cos(a), y1 - math.sin(a), math.cos(a) * 4.2, math.sin(a) * 4.2, 1.5, p["hi"])
        else:
            s.ellipse(x1, y1, 1.5, 1.5, p["hi"])
    for deg in range(10, 360, 40):
        a = math.radians(deg)
        s.ellipse(cx + math.cos(a) * 11 + sway, cy + math.sin(a) * 10.5, 1.2, 1.2, p["mark"])
    s.ellipse(cx, cy + 0.5, 8.6, 8.4, ball_shader(cx, cy + 0.5, 8.6, 8.4, p["body"], p["hi"], p["lo"]))
    _eyes(s, p, ((cx - 3.4, cy - 0.5), (cx + 3.4, cy - 0.5)), 1.9, 2.4)
    for sx in (-1, 1):
        s.ellipse(cx + sx * 6, cy + 3, 1.4, 1.0, p["cheek"])
    _smile(s, cx, cy + 3, darker(p["lo"], 0.5), p)


def dusthop(s, p, phase=0):
    cx = 19
    s.thick_line(26, 30, 35, 27, 0.9, p["lo"])                           # long tail with a tuft
    s.thick_line(35, 27, 40, 17, 0.9, p["lo"])
    s.ellipse(40, 14.5, 2.6, 3, p["accent"])
    dk = p.get("dark")
    if dk:                                                               # a spiked club for a tail
        for deg in (-150, -95, -40, 15):
            a = math.radians(deg)
            spike(s, 40 + math.cos(a) * 2, 14.5 + math.sin(a) * 2.4, math.cos(a) * 3.4, math.sin(a) * 3.4, 1.2, p["accent"])
    for sx in (-1, 1):                                                   # tall ears
        s.ellipse(cx + sx * 6, 6, 2.8, 6.4, p["body"])
        s.ellipse(cx + sx * 6, 6.5, 1.4, 4.6, p["tip"])
        s.ellipse(cx + sx * 6, 34.4, 5.2, 1.6, p["lo"])                   # long hind feet
    s.ellipse(cx, 25, 8.4, 8.2, ball_shader(cx, 25, 8.4, 8.2, p["body"], p["hi"], p["lo"]))
    s.ellipse(cx, 27, 5, 5.4, p["belly"])
    s.ellipse(cx, 15, 8, 6.8, ball_shader(cx, 15, 8, 6.8, p["body"], p["hi"], p["lo"]))
    s.ellipse(cx, 17.6, 4.4, 3, p["belly"])
    _eyes(s, p, ((cx - 4, 14), (cx + 4, 14)), 2.1, 2.6)
    s.ellipse(cx, 16.8, 1.1, 0.9, p["tip"])
    for sx in (-1, 1):
        s.ellipse(cx + sx * 7, 17.5, 1.4, 1.0, p["cheek"])
        s.line(cx + sx * 3, 18, cx + sx * 9, 19.4, p["mark"])
        s.ellipse(cx + sx * 3, 24.5, 1.5, 1.3, p["body"])                 # small front paws
    _smile(s, cx, 18.6, darker(p["lo"], 0.6), p)
    if dk:
        for sx in (-1, 1):
            s.polygon([(cx + sx * 2.3, 19.4), (cx + sx * 1.5, 22.6), (cx + sx * 0.7, 19.4)], lighter(p["belly"], 0.22))


def pebblit(s, p, phase=0):
    cx = 22

    def rock(x, y, rx, ry):
        pts = [(x - rx, y - ry * 0.3), (x - rx * 0.5, y - ry), (x + rx * 0.6, y - ry * 0.9), (x + rx, y - ry * 0.1),
               (x + rx * 0.8, y + ry * 0.8), (x - rx * 0.2, y + ry), (x - rx * 0.9, y + ry * 0.6)]
        s.polygon(pts, ball_shader(x, y, rx, ry, p["body"], p["hi"], p["lo"]))
    rock(15, 32, 5.5, 3)
    rock(29, 32, 5.5, 3)
    rock(7, 22, 4.8, 4.4)
    rock(37, 22, 4.8, 4.4)
    rock(cx, 21.5, 12.5, 10.5)
    rock(cx, 9, 7.6, 6.4)
    dk = p.get("dark")
    for pts in (((16, 15), (20, 20), (18, 25)), ((27, 17), (30, 23)), ((20, 20), (25, 21))):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            s.line(x0, y0, x1, y1, darker(p["mark"], 0.6) if dk else p["mark"])      # deeper cracks
    if dk:                                                               # shards breaking out all over
        s.polygon([(4, 20), (1.5, 10.5), (9.5, 18.5)], p["accent_lo"])
        s.polygon([(7, 19), (7.5, 13), (11, 18.5)], p["accent"])
        s.polygon([(34, 13), (39.5, 2.5), (40, 14.5)], p["accent"])
        s.polygon([(38, 19), (43, 12), (42, 21)], p["accent_lo"])
        s.polygon([(cx - 4, 3.6), (cx - 2, 0), (cx - 0.5, 3.2)], p["accent"])
        s.polygon([(cx + 0.5, 3.2), (cx + 3.5, 0.3), (cx + 4, 4)], p["accent_lo"])
    s.polygon([(29, 12), (32, 6), (34, 12)], p["accent"])                # crystals
    s.polygon([(32, 13), (35.5, 9), (36, 14)], p["accent_lo"])
    s.set(31.5, 9, lighter(p["accent"], 0.6))
    _eyes(s, p, ((cx - 3.2, 8.4), (cx + 3.2, 8.4)), 1.6, 1.9)
    if dk:                                                               # a cracked, jagged mouth
        for (x0, y0), (x1, y1) in zip(((cx - 3, 12), (cx - 1.5, 13.4), (cx, 12.2), (cx + 1.5, 13.4), (cx + 3, 12)),
                                      ((cx - 1.5, 13.4), (cx, 12.2), (cx + 1.5, 13.4), (cx + 3, 12), (cx + 3, 12))):
            s.line(x0, y0, x1, y1, p["outline"])
    else:
        s.line(cx - 2, 12.5, cx + 2, 12.5, p["mark"])


def flashfly(s, p, phase=0):
    cx = 20
    bright = int(phase * 4) % 2 == 0
    for sx in (-1, 1):
        s.ellipse(cx + sx * 9.5, 12, 7.5, 4, p["mark"])                   # wings
        s.line(cx + sx * 4, 13, cx + sx * 15, 10.5, darker(p["mark"], 0.8))
        if p.get("dark"):                                                # hooked wing-tips
            s.polygon([(cx + sx * 14, 9), (cx + sx * 19.6, 5), (cx + sx * 17, 12.5)], p["mark"])
            s.polygon([(cx + sx * 12, 15), (cx + sx * 17, 19), (cx + sx * 9, 16)], p["mark"])
        s.line(cx + sx * 2, 7, cx + sx * 5, 2, p["lo"])                   # antennae
        s.set(cx + sx * 5, 1.5, p["accent"])
        for ly in (19, 23):                                              # little legs
            s.line(cx + sx * 4, ly, cx + sx * 7.5, ly + 3, p["lo"])
    glow = p["tip"] if bright else p["accent"]
    if bright:                                                           # halo
        for deg in range(0, 360, 45):
            a = math.radians(deg)
            s.set(cx + math.cos(a) * 9.5, 26 + math.sin(a) * 8.5, p["accent"])
    s.ellipse(cx, 26, 6.4, 6.6, ball_shader(cx, 26, 6.4, 6.6, p["accent"], glow, p["accent_lo"]))
    s.line(cx - 5, 24, cx + 5, 24, p["accent_lo"])
    s.line(cx - 5.5, 27.5, cx + 5.5, 27.5, p["accent_lo"])
    if p.get("dark"):                                                    # a stinger
        s.polygon([(cx - 2, 31.2), (cx, 34), (cx + 2, 31.2)], p["lo"])
    s.ellipse(cx, 17.5, 5, 4.6, ball_shader(cx, 17.5, 5, 4.6, p["body"], p["hi"], p["lo"]))
    face = p["face"]                                                     # a paler head, so plain dark eyes show
    s.ellipse(cx, 10.5, 5.4, 4.8, ball_shader(cx, 10.5, 5.4, 4.8, face, lighter(face, 0.25), darker(face, 0.75)))
    _eyes(s, p, ((cx - 2.6, 10.4), (cx + 2.6, 10.4)), 1.6, 2.0, darker(face, 0.75))
    for sx in (-1, 1):
        s.set(cx + sx * 4.6, 12.6, p["cheek"])
        if p.get("dark"):                                                # mandibles
            s.polygon([(cx + sx * 2.6, 14), (cx + sx * 0.8, 17.6), (cx + sx * 0.6, 14.4)], p["outline"])


def rumblehorn(s, p, phase=0):
    dark = p["lo"]
    for lx in (13, 19, 31, 37):                                          # legs and hooves
        s.rect(lx - 1, 27, lx + 1, 33, dark)
        s.rect(lx - 1, 33, lx + 1, 34, darker(dark, 0.6))
    s.thick_line(42, 16, 46, 20, 0.9, dark)                              # tail with a spark
    spark = int(phase * 4) % 2 == 0
    s.polygon([(45, 19), (48, 21), (46, 22), (48.5, 25), (44, 22), (46, 21)], p["tip"] if spark else p["accent"])
    s.ellipse(27, 19, 16.5, 10.5, ball_shader(27, 19, 16.5, 10.5, p["body"], p["hi"], p["lo"]))
    s.polygon([(31, 14), (34, 17), (32, 17.5), (35, 22), (30, 18.5), (32, 18)], p["accent"])    # mark on its flank
    dk = p.get("dark")
    if dk:                                                               # spines along its back
        for (x, y, dx, dy) in ((24, 6, 1.5, -6), (30, 8, 2.5, -6.5), (36, 10.5, 3.5, -5.5), (40.5, 14, 4, -3.5)):
            spike(s, x, y, dx, dy, 2.2, darker(p["belly"], 0.75))
    for (x, y, r) in ((20, 10, 6), (13, 11, 5.6), (26, 9, 5), (16, 16, 5), (9, 15, 4.4)):       # storm-cloud mane
        s.ellipse(x, y, r, r * 0.85, ball_shader(x, y, r, r * 0.85, p["belly"], p["mark"], darker(p["belly"], 0.8)))
    for sx in (-1, 1):                                                   # horns
        s.polygon([(11 + sx * 4.5, 17), (11 + sx * 10, 9.5), (11 + sx * 6.5, 12.5), (11 + sx * 3, 15.5)],
                  lambda x, y: p["accent"] if y < 13 else p["accent_lo"])
        if dk:                                                           # longer, and curving in
            s.polygon([(11 + sx * 7.5, 13), (11 + sx * 12.5, 3), (11 + sx * 8.5, 1), (11 + sx * 9.5, 5.5), (11 + sx * 5.5, 12)],
                      p["accent_lo"])
    face = p["face"]                                                     # a paler face, so plain dark eyes show
    s.ellipse(11, 22, 7, 7, ball_shader(11, 22, 7, 7, face, lighter(face, 0.2), darker(face, 0.75)))
    s.ellipse(11, 25.5, 4.2, 3, lighter(face, 0.3))
    _eyes(s, p, ((11 - 3.2, 20.3), (11 + 3.2, 20.3)), 1.7, 2.0, darker(face, 0.75))
    for sx in (-1, 1):
        s.set(11 + sx * 1.4, 26, darker(dark, 0.6))


# species id -> (draw function, box width, box height, anchor x, foot y, animation frames)
SPECS = {
    "glidefin": (glidefin, 48, 31, 24, 30.5, 4),
    "shellby": (shellby, 42, 34, 21, 33.5, 1),
    "flaremoth": (flaremoth, 46, 33, 23, 32.5, 4),
    "coalback": (coalback, 48, 32, 24, 31.5, 4),
    "twigtail": (twigtail, 44, 37, 21, 36.8, 1),
    "stumpkin": (stumpkin, 42, 36, 21, 35.5, 1),
    "whirlet": (whirlet, 40, 33, 20, 32.5, 4),
    "driftpuff": (driftpuff, 44, 37, 22, 36.6, 4),
    "dusthop": (dusthop, 44, 37, 20, 36.4, 1),
    "pebblit": (pebblit, 44, 36, 22, 35.5, 1),
    "flashfly": (flashfly, 40, 34, 20, 33.5, 4),
    "rumblehorn": (rumblehorn, 50, 35, 25, 34.6, 4),
}
