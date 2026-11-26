"""The six creatures, one per element, drawn from shapes.

Each has a palette, so the same drawing gives the normal creature, a villain's
dark "shadow" version, and a hybrid (dark body, accents of a second element).
"""
import math

from ..engine.canvas import Canvas, I, Sprite, ball_shader, darker, lighter, mix
from ..rules import ELEMENTS

PALETTES = {
    "wave": dict(body=(66, 150, 232), hi=(130, 200, 250), lo=(34, 92, 176), belly=(196, 238, 250),
                 accent=(110, 226, 214), accent_lo=(70, 180, 190), tip=(246, 140, 186),
                 eye=(18, 30, 66), mark=(210, 248, 255), outline=(14, 34, 78), cheek=(246, 150, 190)),
    "flame": dict(body=(238, 118, 44), hi=(255, 172, 92), lo=(176, 66, 28), belly=(255, 228, 184),
                  accent=(255, 140, 40), accent_lo=(230, 60, 30), tip=(255, 224, 96),
                  eye=(44, 20, 22), mark=(255, 220, 90), outline=(54, 20, 16), cheek=(250, 150, 110)),
    "root": dict(body=(156, 114, 72), hi=(196, 156, 104), lo=(108, 74, 46), belly=(238, 216, 172),
                 accent=(96, 176, 72), accent_lo=(52, 124, 58), tip=(244, 128, 160),
                 eye=(30, 24, 20), mark=(200, 240, 130), outline=(40, 30, 22), cheek=(240, 150, 130)),
    "breeze": dict(body=(226, 242, 246), hi=(255, 255, 255), lo=(160, 204, 216), belly=(255, 250, 236),
                   accent=(110, 200, 212), accent_lo=(60, 150, 172), tip=(255, 200, 70),
                   eye=(24, 40, 60), mark=(170, 235, 230), outline=(30, 60, 80), cheek=(250, 170, 170)),
    "soil": dict(body=(150, 106, 68), hi=(192, 150, 104), lo=(100, 68, 44), belly=(218, 186, 146),
                 accent=(238, 226, 198), accent_lo=(150, 150, 162), tip=(240, 140, 150),
                 eye=(26, 20, 18), mark=(110, 110, 126), outline=(44, 28, 20), cheek=(224, 134, 122)),
    "lightning": dict(body=(232, 230, 244), hi=(255, 255, 255), lo=(176, 172, 208), belly=(72, 66, 100),
                      accent=(255, 225, 80), accent_lo=(222, 162, 40), tip=(255, 250, 180),
                      eye=(255, 240, 150), mark=(190, 150, 255), outline=(40, 34, 64), cheek=(230, 130, 160)),
}


def _shade(c):
    return mix(darker(c, 0.5), (48, 28, 70), 0.3)


def palette(element, variant="normal", other=None):
    p = dict(PALETTES[element])
    p["glint"] = (255, 255, 255)
    if variant == "normal":
        return p
    q = {k: _shade(v) for k, v in p.items()}
    q["outline"] = (10, 6, 16)
    # dark eyes with a red glint (Nimbleat's face is dark, so its small eyes glow instead)
    q["eye"] = (14, 8, 22) if element != "lightning" else (255, 90, 110)
    q["glint"] = (255, 70, 90) if element != "lightning" else (255, 220, 225)
    q["belly"] = mix(darker(p["belly"], 0.62), (60, 40, 80), 0.3)
    if element == "lightning":
        q["belly"] = (34, 26, 48)
    q["tip"] = (200, 80, 210)
    if variant == "hybrid" and other:
        oc = tuple(ELEMENTS["colour"][other])
        q["body"] = mix(q["body"], oc, 0.22)
        q["hi"] = mix(q["hi"], oc, 0.3)
        q["accent"] = oc
        q["accent_lo"] = darker(oc, 0.65)
        q["mark"] = lighter(oc, 0.5)
        q["tip"] = lighter(oc, 0.6)
        if element == "lightning":
            q["eye"] = lighter(oc, 0.3)
        else:
            q["glint"] = lighter(oc, 0.3)
        q["cheek"] = darker(oc, 0.8)
    return q


# =========================================================================
# The drawings (logical coordinates inside each creature's own box)
# =========================================================================
def ripplefin(s, p, phase=0):
    body_sh = ball_shader(24, 30, 11, 9, p["body"], p["hi"], p["lo"])
    head_sh = ball_shader(19, 17, 12, 10, p["body"], p["hi"], p["lo"])
    frill, frill_lo = p["accent"], p["accent_lo"]
    frill_sh = lambda x, y: frill if (I(x) + I(y)) % 5 else frill_lo
    # tail curling up behind
    pts = [(32, 33), (39, 31), (44, 25), (45, 18), (42, 13)]
    for (x0, y0), (x1, y1), r0 in zip(pts, pts[1:], [4.2, 3.4, 2.6, 1.9, 1.3]):
        s.thick_line(x0, y0, x1, y1, r0, body_sh)
    s.polygon([(42, 14), (48, 6), (49, 14), (45, 19)], frill_sh)
    s.polygon([(44, 24), (50, 20), (47, 28)], frill_sh)
    # back fins
    s.polygon([(28, 23), (32, 16), (34, 25)], frill_sh)
    s.polygon([(33, 26), (38, 21), (37, 30)], frill_sh)
    # body + belly
    s.ellipse(24, 31, 11, 9, body_sh)
    s.ellipse(23, 34, 7, 6, ball_shader(23, 34, 7, 6, p["belly"], lighter(p["belly"], 0.6), darker(p["belly"], 0.85)))
    # feet
    for fx, fy in ((16, 39.5), (29, 40)):
        s.ellipse(fx, fy, 3.4, 2.2, ball_shader(fx, fy, 3.4, 2.2, p["body"], p["hi"], p["lo"]))
        for tx in (-2, 0, 2):
            s.set(fx + tx, fy + 1.5, p["belly"])
    # gill frills fanning out, three per side
    for (x0, y0, x1, y1) in ((9, 13, 2, 6), (8, 17, 0, 16), (9, 21, 2, 27),
                             (29, 13, 36, 6), (30, 17, 38, 16), (29, 21, 36, 27)):
        s.thick_line(x0, y0, x1, y1, 2.1, frill_sh)
        s.ellipse(x1, y1, 1.8, 1.8, p["tip"])
    # head
    s.ellipse(19, 17, 12, 10, head_sh)
    s.ellipse(19, 21.5, 7, 4, mix(p["body"], p["belly"], 0.75))
    # droplet mark on forehead
    s.polygon([(19, 6.5), (21, 10), (19, 12), (17, 10)], p["mark"])
    s.set(18, 9, lighter(p["mark"], 0.7))
    # big eyes
    for ex in (13.5, 24.5):
        s.ellipse(ex, 16.5, 3.1, 3.6, p["eye"])
        s.set(ex - 1.5, 14.5, p["glint"])
        s.set(ex - 0.5, 14.5, p["glint"])
        s.set(ex - 1.5, 15.5, p["glint"])
        s.set(ex + 0.8, 18.6, mix(p["eye"], p["glint"], 0.5))
    s.ellipse(10.5, 21, 1.6, 1.2, p["cheek"])
    s.ellipse(27.5, 21, 1.6, 1.2, p["cheek"])
    mouth = darker(p["lo"], 0.6)
    for x, y in ((17, 22), (18, 23), (19, 23), (20, 23), (21, 22)):
        s.set(x, y, mouth)


def emberkit(s, p, phase=0):
    body_sh = ball_shader(19, 24, 9, 7, p["body"], p["hi"], p["lo"])
    head_sh = ball_shader(17, 13, 10, 8.5, p["body"], p["hi"], p["lo"])
    cream = p["belly"]
    a = phase * math.tau
    # flame tail
    s.thick_line(25, 27, 32, 20, 2.6, body_sh)
    s.thick_line(32, 20, 34, 15, 2.0, body_sh)
    fx, fy = 34.5 + math.sin(a) * 0.8, 11
    for col, sc in ((p["accent_lo"], 1.0), (p["accent"], 0.7), (p["tip"], 0.42)):
        s.polygon([(fx - 5 * sc, fy + 6 * sc),
                   (fx - 3 * sc + math.sin(a + 1) * 1.5, fy - 2 * sc),
                   (fx + math.sin(a * 2) * 1.2, fy - 9 * sc),
                   (fx + 3 * sc + math.cos(a) * 1.5, fy - 2 * sc),
                   (fx + 5 * sc, fy + 6 * sc)], col)
    # body, belly, legs
    s.ellipse(19, 24, 9, 7, body_sh)
    s.ellipse(18, 26, 5, 4.5, cream)
    for lx in (13, 24):
        s.ellipse(lx, 30.5, 3, 2, darker(p["body"], 0.82))
        s.set(lx - 1, 31, cream)
        s.set(lx + 1, 31, cream)
    # ears
    inner = darker(p["lo"], 0.68)
    s.polygon([(9, 9), (7, 0), (14.5, 6)], body_sh)
    s.polygon([(20, 6), (27, 0), (25, 9)], body_sh)
    s.polygon([(9.5, 7), (8.4, 2.5), (12.5, 6)], inner)
    s.polygon([(22, 6), (25.6, 2.5), (24.4, 7)], inner)
    # head + cheek tufts + muzzle
    s.polygon([(8, 13), (3.5, 15), (8, 17.5)], body_sh)
    s.polygon([(26, 13), (30.5, 15), (26, 17.5)], body_sh)
    s.ellipse(17, 13, 10, 8.5, head_sh)
    s.ellipse(17, 16.8, 5, 3, cream)
    s.polygon([(17, 5), (18.6, 7.5), (17, 9), (15.4, 7.5)], p["mark"])
    for ex in (12.5, 21.5):
        s.ellipse(ex, 12.5, 2.3, 2.8, p["eye"])
        s.set(ex - 1, 11, p["glint"])
        s.set(ex + 0.6, 14, mix(p["eye"], p["glint"], 0.45))
    dark = darker(p["lo"], 0.45)
    s.set(17, 15, dark)
    for x, y in ((15, 17), (16, 18), (17, 18), (18, 17)):
        s.set(x, y, dark)
    s.set(16, 19, (255, 255, 255))


def bramblehog(s, p, phase=0):
    cx, cy = 23, 21
    # leafy spikes all round the back
    for i, deg in enumerate(range(-178, 0, 15)):
        a = math.radians(deg)
        nx, ny = math.cos(a), math.sin(a)
        bx, by = cx + 13.5 * nx, cy + 10 * ny
        tx, ty = cx + 21 * nx, cy + 17.5 * ny
        px, py = -ny * 2.6, nx * 2.6
        s.polygon([(bx + px, by + py), (tx, ty), (bx - px, by - py)],
                  p["accent"] if i % 2 else p["accent_lo"])
    # a little flower caught in the spikes
    s.ellipse(33, 7.5, 2.2, 2.2, p["tip"])
    s.set(33, 7, lighter(p["tip"], 0.6))
    # body
    s.ellipse(cx, cy + 1, 15, 11, ball_shader(cx, cy + 1, 15, 11, p["body"], p["hi"], p["lo"]))
    # ears
    for sx in (-1, 1):
        s.ellipse(cx + sx * 10, 14.5, 2.6, 2.4, p["lo"])
        s.ellipse(cx + sx * 10, 15, 1.4, 1.3, p["cheek"])
    # face
    s.ellipse(cx, 25, 10, 7.5, ball_shader(cx, 25, 10, 7.5, p["belly"], lighter(p["belly"], 0.5), darker(p["belly"], 0.86)))
    for sx in (-1, 1):
        s.ellipse(cx + sx * 4.5, 22.5, 1.9, 2.3, p["eye"])
        s.set(cx + sx * 4.5 - 1, 21.5, p["glint"])
        s.ellipse(cx + sx * 7.5, 26.5, 1.6, 1.1, p["cheek"])
    s.ellipse(cx, 26.5, 1.8, 1.4, darker(p["lo"], 0.5))
    s.set(cx - 0.5, 26, lighter(p["lo"], 0.3))
    mouth = darker(p["lo"], 0.6)
    for x, y in ((cx - 2, 29), (cx - 1, 30), (cx, 30), (cx + 1, 29)):
        s.set(x, y, mouth)
    # sprout on its head
    s.thick_line(cx, 12, cx, 8, 0.7, p["accent_lo"])
    s.ellipse(cx - 2.6, 7, 2.6, 1.5, p["mark"])
    s.ellipse(cx + 2.6, 6.4, 2.6, 1.5, p["accent"])
    # feet
    for sx in (-1, 1):
        s.ellipse(cx + sx * 7, 33.2, 3.4, 1.9, p["lo"])
        s.set(cx + sx * 7 - 1, 34, p["belly"])
        s.set(cx + sx * 7 + 1, 34, p["belly"])


def gustwing(s, p, phase=0):
    cx = 22
    wing_sh = lambda x, y: p["accent"] if (I(x) - I(y)) % 4 else p["accent_lo"]
    flap = math.sin(phase * math.tau) * 1.2
    # tail feathers
    s.polygon([(cx - 4, 29), (cx - 7, 35.5), (cx - 2, 32)], p["accent_lo"])
    s.polygon([(cx + 4, 29), (cx + 7, 35.5), (cx + 2, 32)], p["accent_lo"])
    s.polygon([(cx - 2, 30), (cx, 36), (cx + 2, 30)], p["accent"])
    # wings
    for sx in (-1, 1):
        s.polygon([(cx + sx * 9, 17), (cx + sx * 21, 8 + flap), (cx + sx * 18.5, 16),
                   (cx + sx * 21.5, 19 + flap), (cx + sx * 17, 22), (cx + sx * 19, 26),
                   (cx + sx * 10, 26)], wing_sh)
    # body
    s.ellipse(cx, 21, 11.5, 11, ball_shader(cx, 21, 11.5, 11, p["body"], p["hi"], p["lo"]))
    s.ellipse(cx, 26, 7, 5.5, p["belly"])
    # swirl marks on the belly
    for x, y in ((cx - 2, 26), (cx - 1, 25), (cx, 25), (cx + 1, 26), (cx, 27), (cx + 3, 28), (cx + 4, 27)):
        s.set(x, y, p["mark"])
    # crest
    s.thick_line(cx - 1, 11, cx + 2, 5.5, 1.7, p["accent"])
    s.thick_line(cx + 2, 5.5, cx + 6.5, 5, 1.3, p["accent"])
    s.ellipse(cx + 7, 6.5, 1.3, 1.3, p["accent_lo"])
    # face
    for sx in (-1, 1):
        s.ellipse(cx + sx * 4.6, 18, 2.3, 2.7, p["eye"])
        s.set(cx + sx * 4.6 - 1, 16.5, p["glint"])
        s.set(cx + sx * 4.6, 16.5, p["glint"])
        s.ellipse(cx + sx * 8, 21.5, 1.6, 1.1, p["cheek"])
    s.polygon([(cx - 2.2, 20), (cx + 2.2, 20), (cx, 24)], p["tip"])
    s.line(cx - 1.5, 21.5, cx + 1.5, 21.5, darker(p["tip"], 0.7))
    # feet
    for sx in (-1, 1):
        s.rect(cx + sx * 3.5 - 0.5, 31, cx + sx * 3.5 - 0.5, 33, darker(p["tip"], 0.8))
        s.ellipse(cx + sx * 3.5, 34, 2.2, 1.1, p["tip"])


def loamkin(s, p, phase=0):
    cx = 23
    # stones along its back
    for (x, y, r) in ((13, 9.5, 3.2), (22.5, 7, 3.8), (32, 9.5, 2.9)):
        s.ellipse(x, y, r, r, ball_shader(x, y, r, r, p["accent_lo"], lighter(p["accent_lo"], 0.4), p["mark"]))
    # body
    s.ellipse(cx, 19, 16.5, 10.5, ball_shader(cx, 19, 16.5, 10.5, p["body"], p["hi"], p["lo"]))
    s.ellipse(cx, 24, 9.5, 5.5, p["belly"])
    # big digging paws
    for sx in (-1, 1):
        s.ellipse(cx + sx * 15, 25.5, 5.2, 3.6, ball_shader(cx + sx * 15, 25.5, 5.2, 3.6, p["lo"], p["body"], darker(p["lo"], 0.8)))
        for k in (0, 1, 2):
            bx = cx + sx * (12 + k * 3)
            s.polygon([(bx - 1.3, 27), (bx + sx * 1.2, 31.5), (bx + 1.3, 27)], p["accent"])
    # snout
    s.ellipse(cx, 19.5, 5.5, 4, lighter(p["body"], 0.25))
    s.ellipse(cx, 17.4, 2, 1.6, p["tip"])
    s.set(cx - 1, 17, lighter(p["tip"], 0.6))
    mouth = darker(p["lo"], 0.55)
    for x, y in ((cx - 2, 21), (cx - 1, 22), (cx, 22), (cx + 1, 21)):
        s.set(x, y, mouth)
    # tiny eyes, cheeks, whiskers
    for sx in (-1, 1):
        s.ellipse(cx + sx * 7, 15, 1.3, 1.5, p["eye"])
        s.set(cx + sx * 7 - 0.5, 14.3, p["glint"])
        s.ellipse(cx + sx * 9.5, 19.5, 1.6, 1.1, p["cheek"])
        s.line(cx + sx * 5, 19, cx + sx * 9, 17.8, mouth)
    # back feet
    for sx in (-1, 1):
        s.ellipse(cx + sx * 6, 29.6, 3, 1.6, p["lo"])


def nimbleat(s, p, phase=0):
    cx = 22
    dark = p["belly"]
    # legs and hooves
    for x in (14, 18.5, 25.5, 30):
        s.rect(x - 1, 29, x, 35, dark)
        s.rect(x - 1, 35, x, 36, darker(dark, 0.6))
    # cloud wool
    for (x, y, r) in ((cx, 22, 12), (11.5, 21, 5.4), (32.5, 21, 5.4), (15, 14.5, 5.4), (29, 14.5, 5.4),
                      (cx, 12.5, 6), (13.5, 27.5, 4.8), (30.5, 27.5, 4.8), (cx, 29, 5.4)):
        s.ellipse(x, y, r, r * 0.86, ball_shader(x, y, r, r * 0.86, p["body"], p["hi"], p["lo"]))
    # zigzag horns
    for sx in (-1, 1):
        s.polygon([(cx + sx * 6, 13.5), (cx + sx * 11.5, 8.5), (cx + sx * 8.5, 8.5), (cx + sx * 13.5, 2),
                   (cx + sx * 5.5, 9.5), (cx + sx * 8.5, 9.5), (cx + sx * 4, 13.5)],
                  lambda x, y: p["accent"] if y < 9 else p["accent_lo"])
    # face
    for sx in (-1, 1):
        s.ellipse(cx + sx * 7.5, 19.5, 2.8, 1.6, dark)
    s.ellipse(cx, 21.5, 6.2, 6.6, ball_shader(cx, 21.5, 6.2, 6.6, dark, lighter(dark, 0.18), darker(dark, 0.8)))
    s.ellipse(cx, 15.6, 4.2, 2.6, p["hi"])
    for sx in (-1, 1):
        s.ellipse(cx + sx * 2.6, 20.6, 1.4, 1.7, p["eye"])
        s.set(cx + sx * 2.6 - 0.5, 20, p["glint"])
        s.set(cx + sx * 4.6, 23.6, p["cheek"])
    s.set(cx - 0.5, 24, p["cheek"])
    s.set(cx + 0.5, 24, p["cheek"])
    s.set(cx - 0.5, 25.5, lighter(dark, 0.4))
    s.set(cx + 0.5, 25.5, lighter(dark, 0.4))
    # sparks in the wool (they flicker)
    k = int(phase * 4) % 4
    for i, (x, y) in enumerate(((9, 15), (35, 16), (31, 31), (12, 31), (36, 25), (7, 24))):
        if (i + k) % 2 == 0:
            s.set(x, y, p["tip"])
            s.set(x + 1, y - 1, p["accent"])
            s.set(x - 1, y + 1, p["accent"])


# element -> (draw function, box width, box height, anchor x, foot y, animation frames)
SPECS = {
    "wave": (ripplefin, 52, 44, 24, 42.5, 1),
    "flame": (emberkit, 40, 34, 18.5, 33.5, 6),
    "root": (bramblehog, 46, 36, 23, 35.5, 1),
    "breeze": (gustwing, 44, 37, 22, 36, 4),
    "soil": (loamkin, 46, 33, 23, 32, 1),
    "lightning": (nimbleat, 44, 38, 22, 37.5, 4),
}

_cache = {}


def frames(element, variant, other, S, height):
    """Sprites for a creature, `height` logical pixels tall on a scale-S canvas."""
    key = (element, variant, other, S, height)
    if key not in _cache:
        draw, w, h, ax, foot, n = SPECS[element]
        z = S * height / h
        pal = palette(element, variant, other)
        out = []
        for i in range(n):
            cv = Canvas(w, h, scale=z)
            draw(cv, pal, i / n)
            cv.outline(pal["outline"])
            out.append(Sprite.from_canvas(cv, (int(round(ax * z)), int(round(foot * z)))))
        _cache[key] = out
    return _cache[key]
