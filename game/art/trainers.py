"""One trainer figure, varied by a "look": colours, hat style and hair style.

Heroes, nemeses and sweethearts are all this drawing with different looks
(set in data/heroes.json).
"""
from ..engine.canvas import Canvas, Sprite, ball_shader, darker, lighter

OUTLINE = (16, 18, 38)
BOX_W, BOX_H = 42, 60
ANCHOR = (20.5, 57)


def _face_retro(s, look, strand):
    lash, iris = (24, 28, 60), tuple(look.get("eye", (46, 120, 210)))
    for ex in (16, 23):
        s.set(ex, 16, lash)
        s.set(ex + 1, 16, lash)
        s.set(ex, 17, (255, 255, 255))
        s.set(ex + 1, 17, iris)
        s.set(ex, 18, darker(iris, 0.7))
        s.set(ex + 1, 18, iris)
    brow = darker(tuple(look["hair"]), 0.6)
    for x in (15, 16, 24, 25):
        s.set(x, 14, brow)
    s.set(19, 21, (206, 104, 112))
    s.set(20, 21, (206, 104, 112))
    s.set(15, 20, (245, 150, 150))
    s.set(25, 20, (245, 150, 150))


def _face_hd(s, look, strand):
    """A finer face in real pixels (the head is centred on real pixel x=40)."""
    P = s.setp
    skin = tuple(look["skin"])
    iris = tuple(look.get("eye", (46, 120, 210)))
    cmap = {"L": (24, 28, 60), "W": (244, 244, 252), "H": (255, 255, 255), "I": iris,
            "P": darker(iris, 0.45), "l": lighter(iris, 0.45), "s": darker(skin, 0.93)}
    eye = ["LLLLL", "WHHIW", "WHPIW", "WIPIW", "WIllW", ".sss."]
    for x0, flick in ((31, -1), (45, 1)):
        for dy, row in enumerate(eye):
            for dx, ch in enumerate(row):
                if ch != ".":
                    P(x0 + dx, 32 + dy, cmap[ch])
        fx = x0 - 1 if flick < 0 else x0 + 5
        P(fx, 32, cmap["L"])
        P(fx + flick, 31, cmap["L"])
    brow = darker(tuple(look["hair"]), 0.6)
    for x in range(30, 36):
        P(x, 28, brow)
        P(x + 14, 28, brow)
    P(40, 39, cmap["s"])
    for x, y in ((37, 42), (38, 43), (39, 43), (40, 43), (41, 43), (42, 42)):
        P(x, y, (190, 92, 106))
    P(39, 44, (232, 150, 150))
    P(40, 44, (232, 150, 150))
    for x, y in ((29, 39), (31, 39), (30, 40), (32, 40), (48, 39), (50, 39), (49, 40), (51, 40)):
        P(x, y, (246, 156, 164))
    if strand:
        for (x0, y0, x1, y1) in ((14.5, 10.5, 15.5, 13.5), (17.2, 10, 18.2, 13.8),
                                 (21.6, 10, 22.4, 13.6), (25.6, 10.5, 25.2, 12.5)):
            s.line(x0, y0, x1, y1, strand)


def draw(s, look, hd):
    hair = tuple(look["hair"])
    hair_sh = ball_shader(20, 16, 10, 14, hair, lighter(hair, 0.5), darker(hair, 0.62))
    coat = tuple(look["coat"])
    coat_sh = ball_shader(20, 36, 12, 16, coat, lighter(coat, 0.3), darker(coat, 0.62))
    skin = tuple(look["skin"])
    skin_sh = ball_shader(20, 16, 7.5, 8, skin, lighter(skin, 0.4), darker(skin, 0.92), bands=(0.6, -0.8))
    trim = tuple(look["trim"])
    scarf = tuple(look["scarf"])
    scarf_sh = ball_shader(22, 26, 8, 4, scarf, lighter(scarf, 0.3), darker(scarf, 0.7))
    boot = (92, 56, 36)
    hat = tuple(look["hat"]) if look.get("hat") else None
    style = look.get("hat_style", "none")
    long_hair = look.get("hair_style") == "long"

    # behind the body: hood back, long hair, scarf tail
    if style == "hood":
        s.polygon([(10, 12), (20, 3), (30, 12), (31, 27), (9, 27)], darker(hat, 0.8))
    if long_hair:
        s.polygon([(13, 9), (27, 9), (28, 20), (26, 30), (20, 33), (13, 36),
                   (4, 39), (7, 33), (9, 25), (11, 15)], hair_sh)
        s.polygon([(10, 30), (3, 34), (1, 37), (6, 36)], hair_sh)
    s.polygon([(24, 25), (35, 22), (40, 25), (34, 27), (38, 31), (28, 29)], scarf_sh)
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
    s.polygon([(18, 28), (22, 28), (23, 48), (17, 48)], (232, 234, 244))
    s.rect(17, 38, 23, 39, (80, 50, 32))
    s.rect(19, 38, 21, 39, trim)
    s.line(18, 28, 17, 48, trim)
    s.line(22, 28, 23, 48, trim)
    s.line(9, 48, 31, 48, trim)
    for y in (31, 34, 42):
        s.set(15, y, trim)
        s.set(25, y, trim)
    s.polygon([(18, 27), (14, 29), (17, 33)], darker(coat, 0.72))
    s.polygon([(22, 27), (26, 29), (23, 33)], darker(coat, 0.6))
    # arms
    s.thick_line(12.5, 28, 9, 39, 2.2, coat_sh)
    s.rect(7, 38, 11, 39, trim)
    s.ellipse(9, 41.5, 2, 2, skin)
    s.thick_line(28, 28, 32, 34, 2.2, coat_sh)
    s.thick_line(32, 34, 27, 38, 1.7, coat_sh)
    s.rect(30, 34, 32, 35, trim)
    s.ellipse(26.5, 38.5, 1.7, 1.7, skin)
    # scarf, neck, head
    s.ellipse(20, 25.5, 6.2, 2.3, scarf_sh)
    s.ellipse(23.5, 27.5, 1.7, 1.7, darker(scarf, 0.8))
    s.rect(18, 22, 22, 24, darker(skin, 0.88))
    s.ellipse(20, 16, 7.6, 8, skin_sh)
    # hair on the head
    s.polygon([(12.4, 9), (27.6, 9), (27.6, 14), (25, 12), (23, 15), (21, 12),
               (18.5, 15), (16, 12), (13, 16)], hair_sh)
    if long_hair:
        s.polygon([(12.4, 10), (14.5, 10), (14.2, 22), (12, 25)], hair_sh)
        s.polygon([(25.6, 10), (27.6, 10), (28.4, 22), (26, 21)], hair_sh)
    else:
        s.polygon([(12.4, 10), (14.4, 10), (14, 17), (12.6, 18)], hair_sh)
        s.polygon([(25.6, 10), (27.6, 10), (27.4, 18), (26, 17)], hair_sh)
    if style in ("none", "band", "crown"):
        s.ellipse(20, 9.5, 7.8, 3.6, hair_sh)
    (_face_hd if hd else _face_retro)(s, look, lighter(hair, 0.7) if style != "hood" else None)

    # hats
    if style == "tricorn":
        hat_sh = ball_shader(20, 6, 9, 6, hat, lighter(hat, 0.3), darker(hat, 0.6))
        s.polygon([(13, 9), (15, 2), (20, 0.5), (25, 2), (27, 9)], hat_sh)
        s.ellipse(20, 8.6, 11.2, 2.6, hat_sh)
        s.line(9, 7, 13, 9, trim)
        s.line(13, 9, 27, 9, trim)
        s.line(27, 9, 31, 7, trim)
        s.ellipse(20, 5, 1.6, 1.6, trim)
    elif style == "band":
        s.rect(12, 10, 27, 11, hat)
        s.rect(12, 10, 27, 10, lighter(hat, 0.3))
        s.polygon([(27, 10), (31, 12), (30, 14), (27, 12)], hat)
    elif style == "hood":
        hood_sh = ball_shader(20, 10, 10, 9, hat, lighter(hat, 0.25), darker(hat, 0.7))
        s.polygon([(10.5, 22), (11, 11), (15, 5), (20, 3.5), (25, 5), (29, 11), (29.5, 22),
                   (27.4, 21), (27.6, 12), (24, 8.6), (20, 8), (16, 8.6), (12.4, 12), (12.6, 21)], hood_sh)
    elif style == "crown":
        s.rect(13, 6, 26, 8, hat)
        for x in (13, 16.5, 20, 23.5, 26):
            s.polygon([(x - 1.6, 6.5), (x, 2.5), (x + 1.6, 6.5)], hat)
        s.rect(13, 8, 26, 8, darker(hat, 0.7))
        s.set(19.5, 7, (220, 60, 80))
    elif style == "cap":
        cap_sh = ball_shader(20, 7, 9, 4, hat, lighter(hat, 0.3), darker(hat, 0.7))
        s.ellipse(20, 8, 8.4, 3.6, cap_sh)
        s.polygon([(11.5, 9), (20, 10.6), (17, 12), (10, 11)], darker(hat, 0.75))


_cache = {}


def sprite(look, S, flip=False):
    key = (id(look), S, flip)
    if key not in _cache:
        cv = Canvas(BOX_W, BOX_H, scale=S)
        draw(cv, look, hd=(S == 2))
        cv.outline(OUTLINE)
        sp = Sprite.from_canvas(cv, (int(round(ANCHOR[0] * S)), int(round(ANCHOR[1] * S))))
        _cache[key] = sp.flipped() if flip else sp
    return _cache[key]
