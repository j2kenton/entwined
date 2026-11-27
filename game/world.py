"""The lands you walk through: map building, tile art, and the walking scene.

Each land is built from a seed, so it's the same every time you come back to
it: a road from west to east, a town with an inn and a market, clearings where
wild creatures roam, a hidden nook, and (except at home) a Lord on the road.
"""
import random

from .art import creatures, trainers
from .engine.canvas import Canvas, I, Sprite, ball_shader, darker, draw_mini, lighter, mini_width, mix

MW, MH = 46, 24          # map size in tiles
T = 8                    # tile size in logical pixels
VIEW_W, VIEW_H = 100, 60
WALKABLE = set('.="_')
DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

THEMES = {
    "wave": dict(ground=(236, 216, 164), ground2=(226, 202, 148), path=(250, 236, 196), habitat=(120, 190, 150),
                 water=(70, 160, 226), block="palm", leaf=(70, 160, 96), trunk=(150, 104, 62),
                 deep=(46, 132, 208), floor=(214, 190, 150), roof=(60, 110, 190)),
    "flame": dict(ground=(118, 66, 56), ground2=(104, 56, 50), path=(160, 104, 82), habitat=(214, 110, 60),
                  water=(250, 130, 40), block="rock", leaf=(84, 48, 50), trunk=(60, 34, 38),
                  deep=(66, 34, 40), floor=(140, 96, 84), roof=(190, 70, 40)),
    "root": dict(ground=(98, 164, 86), ground2=(86, 150, 78), path=(190, 160, 110), habitat=(52, 124, 64),
                 water=(70, 150, 200), block="tree", leaf=(44, 110, 62), trunk=(104, 70, 44),
                 deep=(30, 80, 52), floor=(170, 150, 116), roof=(150, 90, 50)),
    "breeze": dict(ground=(206, 212, 226), ground2=(192, 200, 216), path=(232, 236, 244), habitat=(150, 210, 200),
                   water=(170, 214, 250), block="spire", leaf=(150, 162, 190), trunk=(110, 124, 156),
                   deep=(178, 214, 250), floor=(184, 190, 208), roof=(90, 170, 190)),
    "soil": dict(ground=(196, 128, 86), ground2=(182, 114, 76), path=(226, 172, 124), habitat=(160, 150, 80),
                 water=(90, 150, 170), block="rock", leaf=(160, 92, 62), trunk=(120, 66, 46),
                 deep=(134, 76, 52), floor=(170, 124, 96), roof=(120, 76, 50)),
    "lightning": dict(ground=(94, 88, 132), ground2=(84, 78, 120), path=(140, 132, 180), habitat=(150, 130, 200),
                      water=(50, 56, 110), block="rock", leaf=(64, 58, 100), trunk=(44, 40, 74),
                      deep=(40, 36, 70), floor=(116, 110, 150), roof=(230, 200, 80)),
}


def _h(x, y, n):
    """A steady pseudo-random number 0..n-1 for a tile."""
    return ((x * 73856093) ^ (y * 19349663) ^ 0x5F3759DF) % n


# =========================================================================
# Building a land
# =========================================================================
class Land:
    def __init__(self, element, seed, home=False):
        self.element = element
        self.home = home
        r = random.Random(seed)
        g = [["#"] * MW for _ in range(MH)]

        def carve(x, y, ch=".", only="#"):
            if 1 <= x < MW - 1 and 1 <= y < MH - 1 and (only is None or g[y][x] in only):
                g[y][x] = ch

        # the road, west to east
        y = MH // 2
        path = []
        for x in range(1, MW - 1):
            path.append((x, y))
            straight = abs(x - int(MW * 0.78)) <= 4 or abs(x - int(MW * 0.33)) <= 6
            if 4 < x < MW - 5 and not straight and r.random() < 0.34:
                y2 = max(7, min(MH - 7, y + r.choice([-1, 1]) * r.randint(1, 2)))
                for yy in range(min(y, y2), max(y, y2) + 1):
                    path.append((x, yy))
                y = y2
        for x, y in path:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    carve(x + dx, y + dy)
        for x, y in path:
            g[y][x] = "="
        self.path = path
        by_x = {}
        for x, y in path:
            by_x.setdefault(x, y)

        def road_y(x):
            return by_x[max(1, min(MW - 2, x))]

        # clearings off the road, some with tall growth where creatures live
        self.habitat = []
        nx = int(MW * 0.78)                                  # where the hidden nook will go
        nook_side = -1 if road_y(nx) > MH // 2 else 1
        fractions = [0.11, 0.52, 0.65, 0.91]
        for i, f in enumerate(fractions):
            cx = int(MW * f)
            ry_road = road_y(cx)
            side = -1 if (i + (seed % 2)) % 2 else 1
            if i >= 2:
                side = -nook_side                           # keep clear of the nook
            cy = max(4, min(MH - 5, ry_road + side * r.randint(4, 5)))
            rx, ry = r.randint(4, 5), r.randint(2, 3)
            for yy in range(cy - ry, cy + ry + 1):
                for xx in range(cx - rx, cx + rx + 1):
                    d = ((xx - cx) / (rx + 0.3)) ** 2 + ((yy - cy) / (ry + 0.3)) ** 2
                    if d <= 1:
                        carve(xx, yy)
                        if d <= 0.55 and g[yy][xx] == ".":
                            g[yy][xx] = '"'
                            self.habitat.append((xx, yy))
            for yy in range(min(cy, ry_road), max(cy, ry_road) + 1):
                carve(cx, yy)
                carve(cx + 1, yy)
            if i == 1:                                      # a pond at the edge of one clearing
                for xx, yy in ((cx + rx - 1, cy), (cx + rx, cy), (cx + rx - 1, cy + side), (cx + rx, cy + side)):
                    if 1 <= xx < MW - 1 and 1 <= yy < MH - 1 and g[yy][xx] != "=":
                        g[yy][xx] = "~"
                        if (xx, yy) in self.habitat:
                            self.habitat.remove((xx, yy))

        # the town: a small square above the road with an inn and a market
        tx = int(MW * 0.33)
        ty = road_y(tx)
        for yy in range(ty - 5, ty):
            for xx in range(tx - 4, tx + 5):
                carve(xx, yy, "_", only=None)
        g[ty - 5][tx - 4] = g[ty - 5][tx - 3] = g[ty - 4][tx - 4] = g[ty - 4][tx - 3] = "I"
        g[ty - 5][tx + 2] = g[ty - 5][tx + 3] = "M"
        g[ty - 2][tx + 4] = "S"
        self.inn = (tx - 4, ty - 5)
        self.inn_door = (tx - 4, ty - 3)                    # where you stand to go in
        self.market = (tx + 2, ty - 5)
        self.sign = (tx + 4, ty - 2)
        self.folk = [(tx, ty - 4), (tx - 1, ty - 2)]

        # a hidden nook off the road, behind what looks like solid ground cover
        ny = road_y(nx)
        side = nook_side
        for yy in range(ny + side * 2, ny + side * 7, side):  # solid ground cover around it
            for xx in range(nx - 2, nx + 3):
                if 0 < yy < MH - 1:
                    g[yy][xx] = "#"
        self.hidden = [(nx, ny + side * 2), (nx, ny + side * 3)]
        for hx, hy in self.hidden:
            g[hy][hx] = "?"
        for yy in (ny + side * 4, ny + side * 5):
            for xx in (nx - 1, nx, nx + 1):
                carve(xx, yy, ".", only=None)
        self.habitat = [q for q in self.habitat if g[q[1]][q[0]] == chr(34)]
        self.chest = (nx, ny + side * 5)

        # the border gate at the east end
        gx, gy = path[-1]
        g[gy][gx] = "G"
        self.gate = (gx, gy)
        self.start = path[0]
        self.lord_x = int(MW * 0.72)
        self.lord_spot = (self.lord_x, road_y(self.lord_x))

        # things to find
        free = [(x, y) for y in range(1, MH - 1) for x in range(1, MW - 1)
                if g[y][x] == "." and all(g[y + dy][x + dx] != "=" for dx, dy in DIRS.values())
                and abs(x - nx) > 2]
        r.shuffle(free)
        self.pickups = {}
        for i, kind in enumerate(["herb", "herb", "herb", "shard", "shard"]):
            if i < len(free):
                self.pickups[free[i]] = kind
        self.pickups[self.chest] = "chest"
        self.grid = g

    def tile(self, x, y):
        if 0 <= x < MW and 0 <= y < MH:
            return self.grid[y][x]
        return "#"


# =========================================================================
# Tile art
# =========================================================================
def paint_land(land, S, navigator, gate_open):
    """The whole map as one picture."""
    th = THEMES[land.element]
    cv = Canvas(MW * T, MH * T, scale=S)
    g = land.grid

    def near_ground(x, y):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if land.tile(x + dx, y + dy) != "#":
                    return True
        return False

    def ground(x, y):
        X, Y = x * T, y * T
        cv.rect(X, Y, X + 7, Y + 7, th["ground"] if _h(x, y, 3) else th["ground2"])
        for k in range(2):
            cv.set(X + _h(x, y + k * 7, 8), Y + _h(x + k * 5, y, 8), mix(th["ground"], (0, 0, 0), 0.12))

    def block(x, y, kind):
        X, Y = x * T, y * T
        if kind in ("tree", "palm"):
            cv.rect(X + 3, Y + 4, X + 4, Y + 7, th["trunk"])
            if kind == "tree":
                cv.ellipse(X + 4, Y + 3.2, 3.9, 3.4, ball_shader(X + 4, Y + 3.2, 3.9, 3.4, th["leaf"], lighter(th["leaf"], 0.3), darker(th["leaf"], 0.7)))
            else:
                for dx, dy in ((-3.5, 1.5), (3.5, 1.5), (-2.5, -1.5), (2.5, -1.5), (0, -2.5)):
                    cv.thick_line(X + 4, Y + 3, X + 4 + dx, Y + 3 + dy, 0.9, th["leaf"])
                cv.set(X + 4, Y + 3, lighter(th["leaf"], 0.4))
        elif kind == "spire":
            cv.polygon([(X + 0.5, Y + 8), (X + 3, Y + 0.5), (X + 5, Y + 1.5), (X + 7.5, Y + 8)],
                       lambda px, py: th["leaf"] if px < X + 4 else th["trunk"])
            cv.line(X + 3, Y + 2, X + 2, Y + 6, lighter(th["leaf"], 0.4))
        else:
            cv.polygon([(X + 0.5, Y + 7.5), (X + 1.5, Y + 3), (X + 4, Y + 1), (X + 6.5, Y + 2.5), (X + 7.5, Y + 7.5)],
                       lambda px, py: th["leaf"] if (px - X) + (py - Y) < 8 else th["trunk"])
            cv.set(X + 3, Y + 3, lighter(th["leaf"], 0.35))
            if land.element in ("flame", "lightning") and _h(x, y, 3) == 0:
                cv.set(X + 5, Y + 5, th["water"] if land.element == "flame" else (255, 230, 110))

    def deep(x, y):
        X, Y = x * T, y * T
        cv.rect(X, Y, X + 7, Y + 7, th["deep"])
        el = land.element
        if el in ("wave", "breeze"):
            if _h(x, y, 3) == 0:
                cv.line(X + 1, Y + 3, X + 4, Y + 3, lighter(th["deep"], 0.45))
            if el == "breeze" and _h(x, y, 5) == 0:
                cv.ellipse(X + 4, Y + 5, 3.4, 1.6, (255, 255, 255))
        elif el == "flame":
            if _h(x, y, 4) == 0:
                cv.line(X + 1, Y + 2, X + 5, Y + 6, th["water"])
        elif el == "root":
            cv.ellipse(X + 4, Y + 4, 3.8, 3.6, darker(th["leaf"], 0.8 if _h(x, y, 2) else 0.65))
        else:
            cv.polygon([(X, Y + 8), (X + 4, Y + 1), (X + 8, Y + 8)], darker(th["leaf"], 0.8))

    for y in range(MH):
        for x in range(MW):
            ch = g[y][x]
            X, Y = x * T, y * T
            if ch == "#":
                if near_ground(x, y):
                    ground(x, y)
                    block(x, y, th["block"])
                else:
                    deep(x, y)
                continue
            ground(x, y)
            if ch == "=":
                cv.rect(X, Y, X + 7, Y + 7, th["path"])
                cv.set(X + _h(x, y, 7), Y + _h(y, x, 7), darker(th["path"], 0.86))
                cv.set(X + _h(y, x + 3, 7), Y + _h(x, y + 9, 7), darker(th["path"], 0.9))
            elif ch == '"':
                for k in range(3):
                    bx = X + 1 + k * 2.5 + _h(x + k, y, 2)
                    by = Y + 3 + _h(x, y + k, 4)
                    cv.line(bx, by + 3, bx - 1, by, th["habitat"])
                    cv.line(bx, by + 3, bx + 1, by, darker(th["habitat"], 0.8))
            elif ch == "~":
                cv.rect(X, Y, X + 7, Y + 7, th["water"])
                cv.line(X + 1, Y + 2 + _h(x, y, 4), X + 4, Y + 2 + _h(x, y, 4), lighter(th["water"], 0.5))
            elif ch == "_":
                cv.rect(X, Y, X + 7, Y + 7, th["floor"])
                cv.rect(X, Y + 7, X + 7, Y + 7, darker(th["floor"], 0.88))
                cv.rect(X + (3 if y % 2 else 7), Y, X + (3 if y % 2 else 7), Y + 7, darker(th["floor"], 0.88))
            elif ch == "?":
                if navigator:                               # a spotted way through
                    cv.set(X + 2, Y + 2, darker(th["ground"], 0.75))
                    cv.set(X + 5, Y + 5, darker(th["ground"], 0.75))
                    cv.set(X + 3, Y + 6, darker(th["ground"], 0.8))
                else:                                       # looks solid, almost
                    block(x, y, th["block"])
                    cv.set(X + 1, Y + 7, th["ground"])
            elif ch == "S":
                cv.rect(X + 3, Y + 4, X + 4, Y + 7, (110, 76, 48))
                cv.rect(X + 1, Y + 1, X + 6, Y + 4, (200, 160, 110))
                cv.rect(X + 2, Y + 2, X + 5, Y + 2, (110, 76, 48))
            elif ch == "G":
                cv.rect(X, Y, X + 7, Y + 7, th["path"])
                cv.rect(X, Y, X + 1, Y + 7, (90, 60, 40))
                cv.rect(X + 6, Y, X + 7, Y + 7, (90, 60, 40))
                if not gate_open:
                    cv.rect(X, Y + 2, X + 7, Y + 3, (200, 60, 50))
                    cv.rect(X, Y + 5, X + 7, Y + 5, (160, 44, 40))

    # the inn (2 x 2 tiles) and the market stall (2 x 1)
    ix, iy = land.inn[0] * T, land.inn[1] * T
    cv.rect(ix, iy + 6, ix + 15, iy + 15, (236, 222, 190))
    cv.polygon([(ix - 1, iy + 7), (ix + 8, iy - 1), (ix + 17, iy + 7)], th["roof"])
    cv.polygon([(ix + 1, iy + 7), (ix + 8, iy + 1), (ix + 15, iy + 7)], lighter(th["roof"], 0.25))
    cv.rect(ix + 6, iy + 10, ix + 9, iy + 15, (96, 62, 40))
    cv.set(ix + 9, iy + 13, (240, 200, 90))
    cv.rect(ix + 2, iy + 9, ix + 4, iy + 11, (150, 210, 240))
    cv.rect(ix + 11, iy + 9, ix + 13, iy + 11, (150, 210, 240))
    mx, my = land.market[0] * T, land.market[1] * T
    cv.rect(mx, my + 4, mx + 15, my + 7, (150, 104, 62))
    for k in range(8):
        cv.rect(mx + k * 2, my, mx + k * 2 + 1, my + 3, (220, 70, 60) if k % 2 else (245, 240, 230))
    for k, c in enumerate(((120, 220, 130), (250, 200, 90), (150, 190, 250))):
        cv.ellipse(mx + 3.5 + k * 4.5, my + 5, 1.3, 1.1, c)
    return cv


def walker(look, direction, frame, S):
    """A small trainer seen from above-ish, in one of four directions."""
    cv = Canvas(8, 11, scale=S)
    hair, coat, skin = tuple(look["hair"]), tuple(look["coat"]), tuple(look["skin"])
    scarf = tuple(look["scarf"])
    hat = tuple(look["hat"]) if look.get("hat") else None
    # legs
    step = frame % 2
    for lx, up in ((2, step), (5, 1 - step)):
        cv.rect(lx, 9, lx, 10 - up, (70, 44, 30))
    # body and arms
    cv.rect(2, 6, 5, 9, coat)
    cv.rect(1, 6, 1, 8, darker(coat, 0.8))
    cv.rect(6, 6, 6, 8, darker(coat, 0.8))
    cv.rect(2, 6, 5, 6, scarf)
    if direction == "down":
        cv.rect(3, 7, 4, 9, (232, 234, 244))
    # head
    cv.ellipse(4, 3.3, 3.1, 3.0, skin)
    if direction == "up":
        cv.ellipse(4, 3.2, 3.2, 3.1, hair)
    else:
        cv.ellipse(4, 1.9, 3.2, 1.9, hair)
        if direction == "down":
            cv.set(2, 3, (30, 30, 50))
            cv.set(5, 3, (30, 30, 50))
            cv.rect(0.6, 2, 0.6, 4, hair)
            cv.rect(7, 2, 7, 4, hair)
        else:
            ex = 5 if direction == "right" else 2
            cv.set(ex, 3, (30, 30, 50))
            bx = 1 if direction == "right" else 6
            cv.rect(bx - (0 if direction == "right" else 0), 2, bx, 5, hair)
    if hat:
        cv.rect(1, 0, 6, 1, hat)
        cv.rect(0, 1, 7, 1, darker(hat, 0.8))
    cv.outline((20, 20, 36))
    return Sprite.from_canvas(cv, (int(4 * S), int(11 * S)))


def item_sprite(kind, S):
    cv = Canvas(8, 8, scale=S)
    if kind == "herb":
        cv.line(4, 7, 4, 3, (60, 130, 70))
        cv.ellipse(2.5, 3.5, 1.8, 1.2, (110, 200, 110))
        cv.ellipse(5.5, 2.5, 1.8, 1.2, (140, 220, 120))
        cv.set(4, 1, (250, 240, 150))
    elif kind == "shard":
        cv.polygon([(4, 0.5), (6.5, 4), (4, 7.5), (1.5, 4)], lambda x, y: (220, 120, 255) if x < 4 else (150, 60, 200))
        cv.set(3, 3, (255, 230, 255))
    else:
        cv.rect(1, 3, 6, 7, (150, 100, 56))
        cv.rect(1, 2, 6, 3, (190, 136, 76))
        cv.rect(3, 4, 4, 5, (250, 210, 90))
    cv.outline((30, 24, 30))
    return Sprite.from_canvas(cv, (int(4 * S), int(8 * S)))


# =========================================================================
# The walking scene
# =========================================================================
class Wild:
    def __init__(self, x, y, mon):
        self.x, self.y, self.mon = x, y, mon


class World:
    """Walk around a land. `run()` returns as soon as something happens:

    ("wild", Wild)  ("lord",)  ("inn",)  ("market",)  ("sign",)  ("folk", i)
    ("pickup", kind, (x, y))  ("gate",)  ("gate_shut",)  ("menu",)  ("warn",)  ("hidden",)
    """

    def __init__(self, ui, land, look, pos, navigator=False, gate_open=False, lord_look=None, picked=()):
        self.ui, self.land, self.look = ui, land, look
        self.S = ui.S
        self.x, self.y = pos
        self.facing = "right"
        self.slide = None                   # (from_x, from_y, frames_left)
        self.step_count = 0
        self.navigator = navigator
        self.gate_open = gate_open
        self.lord_look = lord_look          # None once the Lord has joined (or at home)
        self.lord_seen = False              # after a first defeat, the Lord waits in view
        self.warned = False
        self.hidden_told = False
        self.wild = []
        self.picked = set(tuple(p) for p in picked)
        self.banner = 60                    # frames to show the land's name for
        self.pilot = None                   # tests: a function (world) -> key
        self.repaint()
        self.sprites = {}
        self.item_sprites = {k: item_sprite(k, self.S) for k in ("herb", "shard", "chest")}
        self.folk_looks = [dict(look, hair=(90 + 40 * i, 70, 50), coat=(150 - 30 * i, 120, 90 + 40 * i),
                                hat=None, hat_style="none") for i in range(len(land.folk))]

    def repaint(self):
        self.map = paint_land(self.land, self.S, self.navigator, self.gate_open)

    def walk_sprite(self, look, direction, frame):
        key = (id(look), direction, frame)
        if key not in self.sprites:
            self.sprites[key] = walker(look, direction, frame, self.S)
        return self.sprites[key]

    # ----- what's where ---------------------------------------------------
    def can_walk(self, x, y):
        ch = self.land.tile(x, y)
        if ch in WALKABLE:
            return True
        if ch == "?":
            return self.navigator
        if ch == "G":
            return self.gate_open
        return False

    def thing_at(self, x, y):
        """What you'd bump into or talk to at a tile."""
        ch = self.land.tile(x, y)
        if ch == "I":
            return ("inn",)
        if ch == "M":
            return ("market",)
        if ch == "S":
            return ("sign",)
        if ch == "G" and not self.gate_open:
            return ("gate_shut",)
        for i, pos in enumerate(self.land.folk):
            if pos == (x, y):
                return ("folk", i)
        if self.lord_look and self.lord_seen and (x, y) == self.land.lord_spot:
            return ("lord",)
        return None

    def wild_at(self, x, y):
        for w in self.wild:
            if (w.x, w.y) == (x, y):
                return w
        return None

    # ----- drawing --------------------------------------------------------
    def draw(self):
        S = self.S
        tick = self.ui.tick
        fx, fy = float(self.x), float(self.y)
        if self.slide:
            ox, oy, left = self.slide
            t = left / 4.0
            fx, fy = self.x + (ox - self.x) * t, self.y + (oy - self.y) * t
        cam_x = max(0, min(MW * T - VIEW_W, fx * T + T / 2 - VIEW_W / 2))
        cam_y = max(0, min(MH * T - VIEW_H, fy * T + T / 2 - VIEW_H / 2))
        x0, y0 = int(round(cam_x * S)), int(round(cam_y * S))
        cv = Canvas.__new__(Canvas)
        cv.S, cv.lw, cv.lh = S, VIEW_W, VIEW_H
        cv.w, cv.h = int(VIEW_W * S), int(VIEW_H * S)
        cv.px = [row[x0:x0 + cv.w] for row in self.map.px[y0:y0 + cv.h]]

        def at(tx, ty, dy=0.0):
            return (int(round((tx * T + T / 2) * S)) - x0, int(round((ty * T + T + dy) * S)) - y0)

        things = []
        for pos, kind in self.land.pickups.items():
            if pos not in self.picked:
                things.append((pos[1], self.item_sprites[kind], at(*pos)))
        for i, pos in enumerate(self.land.folk):
            things.append((pos[1], self.walk_sprite(self.folk_looks[i], "down", 0), at(*pos)))
        if self.lord_look and self.lord_seen:
            things.append((self.land.lord_spot[1], self.walk_sprite(self.lord_look, "left", 0), at(*self.land.lord_spot)))
        for w in self.wild:
            spr = creatures.frames(w.mon.sid, "normal", None, S, 9)[0]
            bob = -1 if ((tick // 8) + w.x) % 2 else 0
            things.append((w.y, spr, at(w.x, w.y, bob)))
        frame = (self.step_count % 2) if self.slide else 0
        things.append((fy + 0.01, self.walk_sprite(self.look, self.facing, frame), at(fx, fy)))
        for _, spr, (px, py) in sorted(things, key=lambda t: t[0]):
            spr.blit(cv, px, py)
        if self.banner > 0:
            self.banner -= 1
            name = self.title
            w = mini_width(name)
            cv.rect(2, 2, 6 + w, 10, (20, 16, 30))
            draw_mini(cv, 4, 4, name, (255, 230, 170))
        return cv

    title = ""

    # ----- moving ---------------------------------------------------------
    def move_wild(self, rng):
        for w in self.wild:
            if rng.random() < 0.5:
                continue
            dx, dy = rng.choice(list(DIRS.values()))
            nx, ny = w.x + dx, w.y + dy
            if self.land.tile(nx, ny) in '."' and not self.wild_at(nx, ny) and self.thing_at(nx, ny) is None:
                w.x, w.y = nx, ny
        return self.wild_at(self.x, self.y)

    def after_step(self):
        """Things that happen when you arrive on a tile."""
        pos = (self.x, self.y)
        w = self.wild_at(*pos)
        if w:
            return ("wild", w)
        if pos in self.land.pickups and pos not in self.picked:
            return ("pickup", self.land.pickups[pos], pos)
        if self.land.tile(*pos) == "G":
            return ("gate",)
        if self.land.tile(*pos) == "?" and not self.hidden_told:
            self.hidden_told = True
            return ("hidden",)
        if self.lord_look:
            if self.x >= self.land.lord_x and not self.lord_seen:
                return ("lord",)
            if not self.warned and 0 < self.land.lord_x - self.x <= 5:
                self.warned = True
                return ("warn",)
        return None

    def run(self, rows_fn, rng):
        """Walk until something happens. rows_fn() gives the text-box lines."""
        ui = self.ui
        ui.take()
        want = None
        while True:
            if self.slide:
                ox, oy, left = self.slide
                self.slide = (ox, oy, left - 1) if left > 1 else None
                if not self.slide:
                    ev = self.after_step()
                    if ev:
                        return ev
            keys = ui.take()
            if self.pilot:
                k = self.pilot(self)
                keys = [k] if k else []
            for k in keys:
                if k in DIRS or k in ("enter", "menu"):
                    want = k
            if not self.slide and want:
                k, want = want, None
                if k == "menu":
                    return ("menu",)
                dx, dy = DIRS[self.facing] if k == "enter" else DIRS[k]
                if k != "enter":
                    self.facing = k
                tx, ty = self.x + dx, self.y + dy
                thing = self.thing_at(tx, ty)
                if thing:
                    return thing
                w = self.wild_at(tx, ty)
                if k != "enter" and (w or self.can_walk(tx, ty)):
                    self.slide = (self.x, self.y, 4)
                    self.x, self.y = tx, ty
                    self.step_count += 1
            if ui.tick % 18 == 0 and not self.slide:
                w = self.move_wild(rng)
                if w:
                    return ("wild", w)
            ui.frame(self.draw(), rows_fn())
