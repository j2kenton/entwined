"""Pixel art for the walking map: people, ground, growth, trees, buildings, things to find.

Everything here is drawn at sixteen "units" to a tile (so two units to one of
the engine's logical pixels). In HD that is one real pixel per unit, the size
classic handheld games drew their maps at. The smaller pictures are written
as little grids of letters, each letter a colour.
"""
from ..engine.canvas import Canvas, Sprite, darker, lighter, mix

U = 16                    # units to a tile
INK = (24, 22, 40)


class Painter:
    """Draws in units on a canvas of any scale."""

    def __init__(self, cv, S):
        self.cv = cv
        self.k = S / 2.0

    def px(self, u, v, col):
        self.rect(u, v, u, v, col)

    def rect(self, u0, v0, u1, v1, col):
        """Fill units u0..u1, v0..v1. A line one unit thick is never lost, even at half size."""
        if col is None:
            return
        k = self.k
        cv = self.cv
        x0, y0 = int(u0 * k), int(v0 * k)
        x1, y1 = max(x0 + 1, int((u1 + 1) * k)), max(y0 + 1, int((v1 + 1) * k))
        for py in range(max(0, y0), min(cv.h, y1)):
            row = cv.px[py]
            for px in range(max(0, x0), min(cv.w, x1)):
                row[px] = col

    def frame(self, u0, v0, u1, v1, col):
        self.rect(u0, v0, u1, v0, col)
        self.rect(u0, v1, u1, v1, col)
        self.rect(u0, v0, u0, v1, col)
        self.rect(u1, v0, u1, v1, col)

    def stamp(self, u, v, rows, pal):
        if self.k < 1:                                      # half size: each 2 x 2 becomes its commonest letter
            rows = _halve(rows)
            k2 = self.k * 2
            for j, row in enumerate(rows):
                for i, ch in enumerate(row):
                    if ch != ".":
                        x0, y0 = int((u // 2 + i) * k2), int((v // 2 + j) * k2)
                        for py in range(y0, int((v // 2 + j + 1) * k2)):
                            for px in range(x0, int((u // 2 + i + 1) * k2)):
                                self.cv.setp(px, py, pal[ch])
            return
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch != ".":
                    self.px(u + i, v + j, pal[ch])


_HALVED = {}


def _halve(rows):
    """A grid at half size: each 2 x 2 block becomes whichever letter fills most of it
    (ties go to the top-left one, so outlines survive)."""
    key = id(rows)
    if key not in _HALVED:
        out = []
        for j in range(0, len(rows) - 1, 2):
            line = ""
            for i in range(0, len(rows[j]) - 1, 2):
                four = [rows[j][i], rows[j][i + 1], rows[j + 1][i], rows[j + 1][i + 1]]
                line += max(four, key=lambda c: (four.count(c), -four.index(c)))
            out.append(line)
        _HALVED[key] = (rows, out)                          # (keeps `rows` alive, so its id stays its own)
    return _HALVED[key][1]


def _check(rows, w=16):
    assert all(len(r) == w for r in rows), [(i, len(r)) for i, r in enumerate(rows) if len(r) != w]
    return rows


# =========================================================================
# People
# =========================================================================
_HEAD_FRONT = [
    "....OOOOOOOO....",
    "...OHHHHHHHHO...",
    "..OHHHHHHHHHHO..",
    "..OHHhHHHHhHHO..",
    "..OHhSSSSSShHO..",
    "..OHSSSSSSSSHO..",
    "..OSSESSSSESSO..",
    "..OSSESSSSESSO..",
    "...OSSSssSSSO...",
    "....OSSSSSSO....",
]
_HEAD_BACK = [
    "....OOOOOOOO....",
    "...OHHHHHHHHO...",
    "..OHHHHHHHHHHO..",
    "..OHHHHHHHHHHO..",
    "..OHHHHHHHHHHO..",
    "..OHHHHHHHHHHO..",
    "..OHHHHHHHHHHO..",
    "..OhHHHHHHHHhO..",
    "...OhhHHHHhhO...",
    "....OSSSSSSO....",
]
_HEAD_SIDE = [
    "....OOOOOOOO....",
    "...OHHHHHHHHO...",
    "..OHHHHHHHHHHO..",
    "..OHHHHHHHHHHO..",
    "..OSSSHHHHHHHO..",
    "..OSSSSSHHHHHO..",
    "..OSESSSSHHHHO..",
    "..OSESSSSHHHhO..",
    "..OSSSSSSSHhO...",
    "...OSSSSSSOO....",
]
_BODY_FRONT = [
    "...OTTTTTTTTO...",
    "..OCCTWWWWTCCO..",
    ".OCCCCWWWWCCCCO.",
    ".OSCCCWWWWCCCSO.",
    ".OSOCCCCCCCCOSO.",
    "..OOCCCCCCCCOO..",
    "...OccccccccO...",
]
_BODY_BACK = [
    "...OTTTTTTTTO...",
    "..OCCCCCCCCCCO..",
    ".OCCCCCCCCCCCCO.",
    ".OSCCCCCCCCCCSO.",
    ".OSOCCCCCCCCOSO.",
    "..OOCCCCCCCCOO..",
    "...OccccccccO...",
]
_BODY_SIDE = [
    "....OTTTTTTO....",
    "....OCCCCCCO....",
    "...OCCCCCCCCO...",
    "...OCCSSCCCCO...",
    "...OCCSSCCCCO...",
    "...OCCCCCCCCO...",
    "....OccccccO....",
]
_LEGS = {
    ("front", 0): ["...OLLLOOLLLO...", "...OBBBOOBBBO...", "....OOO..OOO...."],
    ("front", 1): ["...OLLLOOLLLO...", "...OBBBO.OOO....", "....OOO........."],
    ("side", 0): ["....OLLLLLLO....", "....OBBBOBBO....", ".....OOO.OO....."],
    ("side", 1): ["...OLLLOOLLLO...", "..OBBBO..OBBBO..", "...OOO....OOO..."],
}
for _rows in (_HEAD_FRONT, _HEAD_BACK, _HEAD_SIDE, _BODY_FRONT, _BODY_BACK, _BODY_SIDE, *_LEGS.values()):
    _check(_rows)


# The same people for the retro (text-block) mode: eight units wide and ten tall,
# one unit to a block, drawn by hand so the face and the feet come out even.
_SMALL = {
    "down": ["..OOOO..", ".OHHHHO.", ".OHHHHO.", ".OESSEO.", ".OSSSSO.", "..OTTO..", ".OCWWCO.", "OSCCCCSO"],
    "up": ["..OOOO..", ".OHHHHO.", ".OHHHHO.", ".OHHHHO.", ".OhHHhO.", "..OTTO..", ".OCCCCO.", "OSCCCCSO"],
    "left": ["..OOOO..", ".OHHHHO.", ".OSHHHO.", ".OESHHO.", ".OSSSHO.", "..OTTO..", "..OCCO..", "..OSCO.."],
}
_SMALL_LEGS = {
    ("front", 0): [".OLOOLO.", ".OB..BO."],
    ("front", 1): [".OLOOLO.", ".OB....."],
    ("side", 0): ["..OLLO..", "..OBBO.."],
    ("side", 1): [".OLOOLO.", ".OB..BO."],
}
_SMALL_ITEMS = {
    "chest": ["........", ".OOOOOO.", ".OllllO.", ".OOggOO.", ".ObggbO.", ".ObbbbO.", ".OOOOOO.", "........"],
    "herb": ["...f....", "..fyf...", "...f.l..", ".l.g.Ll.", ".Ll.gL..", "..LgL...", "...g....", "........"],
    "shard": ["...O....", "..OpO...", "..OpPO..", ".OpPPDO.", ".OpPDDO.", "..OPDO..", "...OO...", "........"],
    "coins": ["........", "........", "...OO...", "..OyYO..", ".OOYYOO.", "OyYOOYYO", "OYYO.OO.", ".OO....."],
    "bundle": ["........", "...OO...", "..OttO..", "...rr...", "..OLLO..", ".OlLLDO.", ".OLLDDO.", "..OOOO.."],
}
_SMALL_SIGN = ["........", "OOOOOOOO", "ObbbbbbO", "ObddddbO", "ObbbbbbO", "OOOOOOOO", "...pp...", "...pp..."]
for _rows in (*_SMALL.values(), *_SMALL_LEGS.values(), *_SMALL_ITEMS.values(), _SMALL_SIGN):
    _check(_rows, 8)


def _small_hatted(head, style, side):
    rows = list(head)
    covered = {"tricorn": (1,), "cap": (1,), "crown": (1,), "tophat": (1,), "band": (2,), "hood": (1, 2, 3, 4)}.get(style, ())
    for r in covered:
        rows[r] = "".join("K" if ch in "Hh" else ch for ch in rows[r])
    return rows


def _hatted(head, style):
    """Put the look's hat (or hood, or band) on a head."""
    rows = list(head)

    def swap(r, new):
        rows[r] = "".join(new if ch in "Hh" else ch for ch in rows[r])
    if style in ("tricorn", "cap", "crown", "tophat"):
        swap(1, "K")
        swap(2, "K")
        swap(3, "k")
        if style == "tricorn":
            rows[3] = ".OkkkkkkkkkkkkO."
    elif style == "hood":
        for r in range(1, len(rows)):
            swap(r, "K")
    elif style == "band":
        swap(3, "K")
    return rows


def walker(look, direction, frame, S):
    """Someone on the map, sixteen units wide and twenty tall, facing one of four ways."""
    hair, coat, skin = tuple(look["hair"]), tuple(look["coat"]), tuple(look["skin"])
    hat = tuple(look["hat"]) if look.get("hat") else None
    pal = {"O": INK, "H": hair, "h": darker(hair, 0.7), "S": skin, "s": darker(skin, 0.85), "E": (30, 30, 50),
           "C": coat, "c": darker(coat, 0.7), "T": tuple(look["scarf"]), "W": (236, 238, 246),
           "L": tuple(look.get("legs", (226, 228, 238))), "B": tuple(look.get("boots", (92, 56, 36))),
           "K": hat or hair, "k": darker(hat or hair, 0.75)}
    side = direction in ("left", "right")
    if S < 2:                                               # retro mode: the hand-drawn small figure
        style = look.get("hat_style", "none") if hat else "none"
        rows = _small_hatted(_SMALL["left" if side else direction], style, side) + _SMALL_LEGS[("side" if side else "front", frame % 2)]
        if direction == "right":
            rows = [r[::-1] for r in rows]
        cv = Canvas(8, 10, scale=S)
        Painter(cv, S * 2).stamp(0, 0, rows, pal)
        return Sprite.from_canvas(cv, (int(4 * S), int(10 * S)))
    head = _HEAD_SIDE if side else (_HEAD_BACK if direction == "up" else _HEAD_FRONT)
    body = _BODY_SIDE if side else (_BODY_BACK if direction == "up" else _BODY_FRONT)
    rows = _hatted(head, look.get("hat_style", "none") if hat else "none") + body + _LEGS[("side" if side else "front", frame % 2)]
    if direction == "right":
        rows = [r[::-1] for r in rows]
    cv = Canvas(8, 10, scale=S)
    Painter(cv, S).stamp(0, 0, rows, pal)
    return Sprite.from_canvas(cv, (int(4 * S), int(10 * S)))


# =========================================================================
# Things to find
# =========================================================================
_CHEST = _check([
    "................",
    "................",
    "..OOOOOOOOOOOO..",
    ".OllllllllllllO.",
    ".OlLLLLLLLLLLlO.",
    ".OLLLLLLLLLLLLO.",
    ".OOOOOOggOOOOOO.",
    ".ObbbbOggObbbbO.",
    ".ObBBBBggBBBBbO.",
    ".ObBBBBBBBBBBbO.",
    ".ObBBBBBBBBBBbO.",
    ".ObbbbbbbbbbbbO.",
    ".OOOOOOOOOOOOOO.",
    "................",
    "................",
    "................",
])
_HERB = _check([
    "................",
    "......ff........",
    ".....fyyf.......",
    "......ff..ll....",
    "...ll..g.lLLl...",
    "..lLLl.g.lLl....",
    "..lLLLlgglL.....",
    "...lLLLgLl......",
    "....lLgggl......",
    "..ll..gg..ll....",
    ".lLLl.gg.lLLl...",
    ".lLLLlgglLLLl...",
    "..lLLLggLLLl....",
    "...llLggLll.....",
    "......gg........",
    "................",
])
_SHARD = _check([
    "................",
    ".......O........",
    "......OpO.......",
    "......OpPO......",
    ".....OppPO......",
    ".....OpPPO..O...",
    "..O..OpPPDOOpO..",
    ".OpO.OpPPDOpPO..",
    ".OpPOOpPPDOpPDO.",
    ".OpPDOpPPDOpPDO.",
    ".OpPDOpPPDOpPDO.",
    ".OpPDOpPDDOPDDO.",
    "..OOOOOOOOOOOO..",
    "................",
    "................",
    "................",
])
_COINS = _check([
    "................",
    "................",
    "................",
    "................",
    ".....OOOO.......",
    "....OyYYYO......",
    "....OYYYYO.OOO..",
    "....OYYYdOOyYYO.",
    ".OOOOOdddOYYYYO.",
    "OyYYYYOOOOYYYdO.",
    "OYYYYYYOOOOdddO.",
    "OYYYYYdO..OOOO..",
    ".OdddddO........",
    "..OOOOO.........",
    "................",
    "................",
])
_BUNDLE = _check([
    "................",
    "................",
    "......OOOO......",
    ".....OttttO.....",
    "......OttO......",
    ".....OOrrOO.....",
    "....OllLLLLO....",
    "...OllLLLLLDO...",
    "...OlLLLLLLDO...",
    "..OllLLLLLLDDO..",
    "..OlLLLLLLLDDO..",
    "..OlLLLLLLDDDO..",
    "..OLLLLLLDDDDO..",
    "...OOOOOOOOOO...",
    "................",
    "................",
])
_ITEMS = {
    "chest": (_CHEST, {"O": INK, "l": (214, 160, 92), "L": (176, 122, 66), "b": (170, 116, 62), "B": (140, 92, 50),
                       "g": (250, 210, 90)}),
    "herb": (_HERB, {"f": (255, 236, 244), "y": (250, 206, 90), "l": (190, 240, 150), "L": (60, 150, 80), "g": (40, 100, 56)}),
    "shard": (_SHARD, {"O": (70, 30, 100), "p": (236, 180, 255), "P": (190, 110, 240), "D": (130, 60, 190)}),
    "coins": (_COINS, {"O": (110, 76, 20), "y": (255, 240, 150), "Y": (250, 206, 80), "d": (200, 150, 40)}),
    "bundle": (_BUNDLE, {"O": INK, "t": (214, 190, 150), "r": (200, 70, 60), "l": (226, 206, 170), "L": (196, 170, 130),
                         "D": (150, 124, 92)}),
}


def item_sprite(kind, S):
    rows, pal = _ITEMS[kind]
    cv = Canvas(8, 8, scale=S)
    if S < 2:
        Painter(cv, S * 2).stamp(0, 0, _SMALL_ITEMS[kind], pal)
    else:
        Painter(cv, S).stamp(0, 0, rows, pal)
    return Sprite.from_canvas(cv, (int(4 * S), int(8 * S)))


# =========================================================================
# The land
# =========================================================================
_TREE = _check([
    "......OOOO......",
    "....OOllLLOO....",
    "...OlllLLLLLO...",
    "..OlllLLLLLLDO..",
    ".OllLLLLLLLLDDO.",
    ".OlLLLLLLLLLDDO.",
    "OlLLLLLLLLLLDDDO",
    "OLLLLLLLLLLDDDDO",
    "OLLLLLLLLLDDDDDO",
    ".OLLLLLLDDDDDDO.",
    ".ODLLDDDDDDDDDO.",
    "..OODDDDDDDDOO..",
    "....OOtTTOOO....",
    "......tTT.......",
    ".....sttTTs.....",
    "....ssssssss....",
])
_PALM = _check([
    "................",
    "..OOO....OOO....",
    ".OlLLO..OLLlO...",
    "OlLLLLOOLLLLLO..",
    "OLLOOLLLLOOLLLO.",
    ".OO.OLLLLLO.OLLO",
    "...OLLOLLOLLO.OO",
    "..OLLO.tT.OLLO..",
    "..OLO..tT..OLO..",
    "...O...tT...O...",
    ".......tTT......",
    "........tT......",
    "........tTT.....",
    ".........tT.....",
    ".......sstTss...",
    "......ssssssss..",
])
_ROCK = _check([
    "................",
    "................",
    ".....OOOOO......",
    "...OOlllLLOO....",
    "..OlllLLLLLLO...",
    ".OllLLLLLLLLDO..",
    ".OlLLLLLLLLDDDO.",
    "OlLLLLLLLLLDDDO.",
    "OLLLLLLLLLDDDDDO",
    "OLLLLLLLDDDDDDDO",
    "OLLLLDDDDDDDDDDO",
    ".ODDDDDDDDDDDDO.",
    "..OOODDDDDDOOO..",
    ".....OOOOOO.....",
    "...ssssssssss...",
    "................",
])
_SPIRE = _check([
    ".......OO.......",
    "......OlLO......",
    "......OlLDO.....",
    ".....OllLDO.....",
    ".....OlLLDDO....",
    "....OllLLDDO....",
    "....OlLLLDDDO...",
    "...OllLLLDDDO...",
    "...OlLLLLDDDDO..",
    "..OllLLLLDDDDO..",
    "..OlLLLLLDDDDDO.",
    ".OllLLLLLDDDDDO.",
    ".OlLLLLLLDDDDDDO",
    "OOOOOOOOOOOOOOOO",
    "..ssssssssssss..",
    "................",
])
_BLOCKS = {"tree": _TREE, "palm": _PALM, "rock": _ROCK, "spire": _SPIRE}
_CLUMP = ["g....g", "gG..Gg", ".gGGg.", ".gGGg.", "..GG..", "..dd.."]
_SIGN = _check([
    "................",
    "................",
    ".OOOOOOOOOOOOOO.",
    ".ObbbbbbbbbbbbO.",
    ".ObBBBBBBBBBBbO.",
    ".ObBdddBddddBbO.",
    ".ObBBBBBBBBBBbO.",
    ".ObBddddBdddBbO.",
    ".ObBBBBBBBBBBbO.",
    ".ObbbbbbbbbbbbO.",
    ".OOOOOOOOOOOOOO.",
    "......OppO......",
    "......OppO......",
    "......OppO......",
    "....ssOppOss....",
    ".....ssssss.....",
])
_GLYPH = {"I": ["###", ".#.", ".#.", ".#.", "###"], "N": ["#..#", "##.#", "#.##", "#..#", "#..#"]}


def _h(x, y, n):
    """A steady pseudo-random number 0..n-1 for a tile."""
    return ((x * 73856093) ^ (y * 19349663) ^ 0x5F3759DF) % n


def paint_land(land, S, navigator, gate_open, th, MW, MH):
    """The whole map as one picture."""
    cv = Canvas(MW * 8, MH * 8, scale=S)
    p = Painter(cv, S)
    g = land.grid
    el = land.element
    ground, ground2, path = th["ground"], th["ground2"], th["path"]
    shade = darker(ground, 0.8)

    def near_ground(x, y):
        return any(land.tile(x + dx, y + dy) != "#" for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def lay_ground(x, y):
        X, Y = x * U, y * U
        p.rect(X, Y, X + 15, Y + 15, ground)
        for k in range(4):                                  # a little grain, so it isn't flat
            p.px(X + _h(x + k, y, 16), Y + _h(x, y + k * 3, 16), ground2 if k % 2 else lighter(ground, 0.12))
        if _h(x, y, 4) == 0:                                # and now and then a tuft
            tx, ty = X + 2 + _h(y, x, 10), Y + 3 + _h(x, y + 5, 9)
            tuft = mix(ground, th["habitat"], 0.55)
            p.px(tx, ty, tuft)
            p.px(tx + 1, ty + 1, tuft)
            p.px(tx + 2, ty, tuft)

    def lay_block(x, y, kind):
        X, Y = x * U, y * U
        leaf, trunk = th["leaf"], th["trunk"]
        pal = {"O": darker(leaf, 0.45), "l": lighter(leaf, 0.3), "L": leaf, "D": darker(leaf, 0.72),
               "t": lighter(trunk, 0.15), "T": darker(trunk, 0.8), "s": shade}
        if kind in ("rock", "spire"):
            pal.update(l=lighter(leaf, 0.35), L=mix(leaf, trunk, 0.35), D=trunk)
        p.stamp(X, Y, _BLOCKS[kind], pal)
        if kind == "rock" and el in ("flame", "lightning") and _h(x, y, 3) == 0:      # something glowing in the cracks
            glow = th["water"] if el == "flame" else (255, 230, 110)
            for du, dv in ((6, 7), (7, 8), (8, 8), (9, 9)):
                p.px(X + du, Y + dv, glow)

    def lay_deep(x, y):
        X, Y = x * U, y * U
        deep = th["deep"]
        p.rect(X, Y, X + 15, Y + 15, deep)
        if el in ("wave", "breeze"):
            hi = lighter(deep, 0.45)
            if _h(x, y, 2) == 0:
                p.rect(X + 2, Y + 4, X + 6, Y + 4, hi)
                p.rect(X + 9, Y + 11, X + 13, Y + 11, hi)
            if el == "breeze" and _h(x, y, 5) == 0:         # a cloud below the cliffs
                p.rect(X + 3, Y + 8, X + 12, Y + 11, (255, 255, 255))
                p.rect(X + 5, Y + 6, X + 10, Y + 7, (255, 255, 255))
                p.rect(X + 3, Y + 12, X + 12, Y + 12, (220, 230, 246))
        elif el == "flame":
            if _h(x, y, 3) == 0:
                for i in range(6):
                    p.px(X + 3 + i * 2, Y + 4 + (i * 5) % 9, th["water"])

    def road_like(x, y):
        return land.tile(x, y) in "=GW_IMS"

    for y in range(MH):
        for x in range(MW):
            ch = g[y][x]
            X, Y = x * U, y * U
            if ch == "#":
                # near the open ground, trees or rocks; further off, sea, sky or lava where the land has
                # them, and otherwise more of the same forest or rock
                if near_ground(x, y) or el not in ("wave", "breeze", "flame"):
                    lay_ground(x, y)
                    lay_block(x, y, th["block"])
                else:
                    lay_deep(x, y)
                continue
            lay_ground(x, y)
            if ch in "=GW":
                p.rect(X, Y, X + 15, Y + 15, path)
                for k in range(5):                          # worn stones
                    p.px(X + _h(x + k, y, 15), Y + _h(y + k, x, 15), darker(path, 0.88))
                p.px(X + _h(y, x, 14), Y + _h(x, y + 4, 14), lighter(path, 0.3))
                edge = darker(path, 0.8)
                if not road_like(x, y - 1):
                    p.rect(X, Y, X + 15, Y, edge)
                if not road_like(x, y + 1):
                    p.rect(X, Y + 15, X + 15, Y + 15, edge)
                if not road_like(x - 1, y) and x > 0:
                    p.rect(X, Y, X, Y + 15, edge)
                if not road_like(x + 1, y) and x < MW - 1:
                    p.rect(X + 15, Y, X + 15, Y + 15, edge)
            if ch == '"':                                   # long growth: where the wild creatures are
                hab = th["habitat"]
                pal = {"g": lighter(hab, 0.25), "G": hab, "d": darker(hab, 0.7)}
                p.rect(X, Y, X + 15, Y + 15, mix(ground, hab, 0.3))
                for cu, cv_ in ((1, 1), (9, 2), (5, 9), (12, 9), (-3, 9)):
                    p.stamp(X + cu, Y + cv_, _CLUMP, pal)
            elif ch == "~":
                water = th["water"]
                p.rect(X, Y, X + 15, Y + 15, water)
                hi = lighter(water, 0.5)
                o = _h(x, y, 5)
                p.rect(X + 2 + o, Y + 4, X + 5 + o, Y + 4, hi)
                p.rect(X + 8 - o, Y + 11, X + 12 - o, Y + 11, hi)
                if land.tile(x, y - 1) != "~":              # a bank along the top
                    p.rect(X, Y, X + 15, Y + 1, darker(water, 0.75))
            elif ch == "_":                                 # the town's paving
                floor = th["floor"]
                line = darker(floor, 0.86)
                p.rect(X, Y, X + 15, Y + 15, floor)
                for v in (7, 15):
                    p.rect(X, Y + v, X + 15, Y + v, line)
                for u, v0 in ((3, 0), (11, 0), (7, 8), (15, 8)):
                    p.rect(X + u, Y + v0, X + u, Y + v0 + 7, line)
            elif ch == "?":
                if navigator:                               # a way through, once you know where to look
                    for du, dv in ((4, 4), (10, 9), (6, 12), (12, 3)):
                        p.px(X + du, Y + dv, darker(ground, 0.75))
                else:                                       # looks solid, almost
                    lay_block(x, y, th["block"])
            elif ch == "S":
                sign_pal = {"O": INK, "b": (226, 190, 130), "B": (200, 160, 104), "d": (110, 76, 48),
                            "p": (150, 104, 62), "s": shade}
                if S < 2:
                    Painter(cv, S * 2).stamp(X // 2, Y // 2, _SMALL_SIGN, sign_pal)
                else:
                    p.stamp(X, Y, _SIGN, sign_pal)
            if ch in "GW":                                  # a border gate: two stone posts, and bars when it's shut
                stone, stone_hi, stone_lo = (150, 146, 160), (196, 192, 206), (104, 100, 118)
                for u0 in (0, 12):
                    p.rect(X + u0, Y, X + u0 + 3, Y + 15, stone)
                    p.rect(X + u0, Y, X + u0, Y + 15, stone_hi)
                    p.rect(X + u0 + 3, Y, X + u0 + 3, Y + 15, stone_lo)
                    p.rect(X + u0, Y, X + u0 + 3, Y + 1, stone_hi)
                    p.rect(X + u0, Y + 14, X + u0 + 3, Y + 15, stone_lo)
                if ch == "G" and not gate_open:
                    for v in (4, 10):
                        p.rect(X + 4, Y + v, X + 11, Y + v + 1, (150, 96, 54))
                        p.rect(X + 4, Y + v + 2, X + 11, Y + v + 2, (96, 60, 36))
                    for i in range(8):
                        p.px(X + 4 + i, Y + 6 + i // 2, (120, 76, 44))

    _market(p, land.market[0] * U, land.market[1] * U, shade)
    _inn(p, land.inn[0] * U, land.inn[1] * U, th["roof"], shade)
    return cv


def _inn(p, X, Y, roof, shade):
    """A house two tiles wide and two tall, with its roof rising a little above them."""
    roof_hi, roof_lo = lighter(roof, 0.25), darker(roof, 0.72)
    wall, wall_lo = (242, 230, 204), (214, 198, 168)
    wood, wood_hi = (112, 74, 46), (156, 108, 66)
    p.rect(X + 2, Y + 31, X + 29, Y + 32, shade)
    # chimney
    p.rect(X + 22, Y - 8, X + 27, Y - 1, (170, 92, 74))
    p.rect(X + 22, Y - 8, X + 27, Y - 7, (206, 130, 104))
    p.frame(X + 21, Y - 9, X + 28, Y, INK)
    # walls
    p.rect(X + 1, Y + 13, X + 30, Y + 30, wall)
    p.rect(X + 1, Y + 13, X + 30, Y + 15, wall_lo)
    for v in (20, 25):
        p.rect(X + 1, Y + v, X + 30, Y + v, wall_lo)
    p.rect(X + 1, Y + 28, X + 30, Y + 30, (164, 154, 150))
    p.rect(X + 1, Y + 28, X + 30, Y + 28, (196, 188, 184))
    p.frame(X, Y + 12, X + 31, Y + 31, INK)
    # roof: rows of shingles, narrowing to the ridge
    for r in range(-4, 13):
        inset = 4 if r < -3 else 3 if r < -1 else 2 if r < 1 else 1 if r < 4 else 0
        band = (r + 4) % 4
        col = roof_hi if band == 0 else roof_lo if band == 3 else roof
        p.rect(X - 2 + inset, Y + r, X + 33 - inset, Y + r, col)
        if band in (1, 2):
            for u in range(X - 2 + inset + (3 if ((r + 4) // 4) % 2 else 0), X + 33 - inset, 6):
                p.px(u, Y + r, roof_lo)
        p.px(X - 3 + inset, Y + r, INK)
        p.px(X + 34 - inset, Y + r, INK)
    p.rect(X + 2, Y - 5, X + 29, Y - 5, INK)
    p.rect(X - 2, Y + 13, X + 33, Y + 13, INK)
    # windows
    for wx in (3, 21):
        p.rect(X + wx, Y + 17, X + wx + 7, Y + 24, (150, 206, 240))
        p.rect(X + wx + 1, Y + 18, X + wx + 2, Y + 19, (230, 246, 255))
        p.rect(X + wx + 3, Y + 17, X + wx + 4, Y + 24, wall)
        p.rect(X + wx, Y + 20, X + wx + 7, Y + 21, wall)
        p.frame(X + wx - 1, Y + 16, X + wx + 8, Y + 25, wood)
        p.rect(X + wx - 1, Y + 26, X + wx + 8, Y + 26, wood_hi)
    # door, and a board over it
    p.rect(X + 12, Y + 21, X + 19, Y + 30, wood_hi)
    p.rect(X + 13, Y + 22, X + 18, Y + 25, wood)
    p.rect(X + 13, Y + 27, X + 18, Y + 29, wood)
    p.frame(X + 11, Y + 20, X + 20, Y + 31, INK)
    p.px(X + 18, Y + 26, (250, 210, 90))
    p.rect(X + 8, Y + 13, X + 23, Y + 19, wood)
    p.frame(X + 8, Y + 13, X + 23, Y + 19, INK)
    if p.k < 1:
        p.rect(X + 11, Y + 15, X + 20, Y + 17, (255, 226, 130))
        return
    u = X + 10
    for ch in "INN":
        for j, row in enumerate(_GLYPH[ch]):
            for i, bit in enumerate(row):
                if bit == "#":
                    p.px(u + i, Y + 14 + j, (255, 226, 130))
        u += len(_GLYPH[ch][0]) + 1


def _market(p, X, Y, shade):
    """A stall two tiles wide: a striped awning over a counter of goods."""
    wood, wood_hi, wood_lo = (150, 104, 62), (196, 146, 92), (104, 68, 40)
    red, white = (220, 70, 60), (248, 244, 236)
    p.rect(X + 1, Y + 15, X + 30, Y + 16, shade)
    for u0 in (1, 28):                                      # posts
        p.rect(X + u0, Y - 2, X + u0 + 2, Y + 15, wood)
        p.rect(X + u0, Y - 2, X + u0, Y + 15, wood_hi)
    # counter
    p.rect(X + 1, Y + 7, X + 30, Y + 15, wood)
    p.rect(X + 1, Y + 7, X + 30, Y + 8, wood_hi)
    for u in range(X + 6, X + 30, 6):
        p.rect(u, Y + 9, u, Y + 15, wood_lo)
    p.frame(X, Y + 6, X + 31, Y + 15, INK)
    # goods: a loaf, three apples, a green bottle, a blue jar
    p.rect(X + 4, Y + 4, X + 8, Y + 6, (226, 170, 96))
    p.rect(X + 5, Y + 3, X + 7, Y + 3, (244, 204, 130))
    for u in (11, 14, 17):
        p.rect(X + u, Y + 4, X + u + 1, Y + 6, (226, 60, 60))
        p.px(X + u, Y + 4, (255, 150, 140))
        p.px(X + u + 1, Y + 3, (90, 150, 80))
    p.rect(X + 21, Y + 2, X + 22, Y + 6, (90, 180, 110))
    p.px(X + 21, Y + 1, (60, 130, 80))
    p.rect(X + 25, Y + 3, X + 27, Y + 6, (120, 170, 240))
    p.rect(X + 25, Y + 2, X + 27, Y + 2, (236, 226, 200))
    # awning: stripes, with a scalloped edge
    for i in range(8):
        col = red if i % 2 == 0 else white
        p.rect(X + i * 4, Y - 10, X + i * 4 + 3, Y - 3, col)
        p.rect(X + i * 4, Y - 3, X + i * 4 + 3, Y - 3, darker(col, 0.8))
        p.rect(X + i * 4, Y - 2, X + i * 4 + 3, Y - 1, col)
        p.px(X + i * 4, Y - 1, None)
        p.px(X + i * 4 + 3, Y - 1, None)
    p.rect(X - 1, Y - 11, X + 32, Y - 11, INK)
    p.rect(X - 1, Y - 11, X - 1, Y - 2, INK)
    p.rect(X + 32, Y - 11, X + 32, Y - 2, INK)
