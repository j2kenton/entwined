"""Record a short clip of the real game as an animated GIF (for the README).

    python tools/clip.py                 # writes screens/clip.gif

It runs the game's own code with scripted key presses: a wild creature is
worn down and befriended with a lure, then a companion faces a dark creature
inside the Citadel. The picture is exactly what the HD mode draws; the text
box underneath is redrawn in the game's built-in font, so it's in capitals.
"""
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import gif                                       # noqa: E402
from game import rules as R                      # noqa: E402
from game import state as S                      # noqa: E402
from game import world as W                      # noqa: E402
from game.battle import Battle                   # noqa: E402
from game.engine import canvas as C              # noqa: E402
from game.engine.display import Display          # noqa: E402
from game.engine.ui import BORDER, BOX_BG, UI    # noqa: E402
from game.story import Game, Stage               # noqa: E402
import game.__main__ as M                        # noqa: E402

ART_SCALE = 3                 # the picture is 200 x 120 real pixels; shown at 600 x 360
BOX_W, BOX_H = 600, 60
EVERY = 2                     # keep every second frame (12.5 a second)
FPS = 25

# a few signs the game's own font doesn't have (it only needs them here)
C._FONT.update({
    ",": "....." * 5 + "..#.." + ".#...",
    ">": "#...." "##..." "###.." "####." "###.." "##..." "#....",
    "<": "....#" "...##" "..###" ".####" "..###" "...##" "....#",
    "(": "...#." "..#.." ".#..." ".#..." ".#..." "..#.." "...#.",
    ")": ".#..." "..#.." "...#." "...#." "...#." "..#.." ".#...",
    "%": "##..#" "##.#." "...#." "..#.." ".#..." ".#.##" "#..##",
    "+": "....." "..#.." "..#.." "#####" "..#.." "..#.." ".....",
    '"': ".#.#." ".#.#." + "....." * 5,
})
SWAP = {"▶": ">", "◀": "<", "▼": "V"}


class Stop(Exception):
    pass


class Director:
    """Presses the keys, each a set number of frames after the one before."""

    def __init__(self):
        self.t = 0
        self.queue = []

    def after(self, n, key):
        base = max(self.t, self.queue[-1][0] if self.queue else 0)
        self.queue.append((base + n, key))

    def poll(self):
        self.t += 1
        out = []
        while self.queue and self.queue[0][0] <= self.t:
            out.append(self.queue.pop(0)[1])
        return out

    def close(self):
        pass


class RecUI(UI):
    """The real UI, with every frame kept and the menus answered from a plan."""

    def __init__(self, recording=True):
        # (when only trying a seed out, nothing needs drawing)
        UI.__init__(self, Display("null", None, scale=2), Director(), headless=not recording)
        self.recording = recording
        self.frames = []
        self.plan = []
        self.boxes = {}

    # ----- recording ------------------------------------------------------
    def box(self, rows):
        key = repr(rows)
        if key not in self.boxes:
            cv = C.Canvas(BOX_W, BOX_H, scale=1, fill=BOX_BG)
            cv.rect(0, 0, BOX_W - 1, 0, BORDER)
            cv.rect(0, BOX_H - 1, BOX_W - 1, BOX_H - 1, BORDER)
            cv.rect(0, 0, 0, BOX_H - 1, BORDER)
            cv.rect(BOX_W - 1, 0, BOX_W - 1, BOX_H - 1, BORDER)
            for i, seg in enumerate(list(rows)[:5]):
                x = 6
                for col, text in seg:
                    text = "".join(SWAP.get(ch, ch) for ch in text)
                    C.draw_text(cv, x, 7 + i * 10, text, col)
                    x += len(text) * 6
            self.boxes[key] = cv.px
        return self.boxes[key]

    def frame(self, cv, rows):
        self.tick += 1
        if self.recording and self.tick % EVERY == 0:
            self.frames.append(([row[:] for row in cv.px], self.box(rows)))
        self.poll()

    def cut(self, n=5):
        """A moment of black between two scenes."""
        dark = C.Canvas(100, 60, scale=2, fill=(0, 0, 0))
        for _ in range(n * EVERY):
            self.frame(dark, [])

    # ----- playing --------------------------------------------------------
    def next(self):
        if not self.plan:
            raise Stop()
        return self.plan.pop(0)

    def press(self, keys):
        for i, k in enumerate(keys):
            self.keys.after(18 if i == 0 else 8, k)

    def say(self, draw, text, speaker=None, wait=True, hold=14, speed=2):
        if wait:
            self.keys.after(len(text) // speed + 18 + len(text) // 5, "enter")
        return UI.say(self, draw, text, speaker, wait, hold, speed)

    def menu(self, draw, head, options, cols=2, desc=None, start=0, blocked=None, col_width=47, tag=None):
        want = self.next()
        keys = []
        dr, dc = want // cols - start // cols, want % cols - start % cols
        keys += ["down" if dr > 0 else "up"] * abs(dr)
        keys += ["right" if dc > 0 else "left"] * abs(dc)
        self.press(keys + ["enter"])
        return UI.menu(self, draw, head, options, cols, desc, start, blocked, col_width, tag)

    def pager(self, draw, rows, n, start=0, blocked=None, cancel=False, tag=None):
        want = self.next()                                  # a look at the next one along, then the one wanted
        look = ["right", "left"] if n > 1 else []
        for i, k in enumerate(look + ["right"] * ((want - start) % n) + ["enter"]):
            self.keys.after(34 if i == 0 else 22, k)        # a page wants longer to take in than a menu
        return UI.pager(self, draw, rows, n, start, blocked, cancel, tag)

    def grid_menu(self, draw, head, rows, desc=None, start=(0, 0), blocked=None, tag=None):
        want = self.next()
        _, b, act_at, _ = tag
        r, c = start
        r = max(0, min(r, len(rows) - 1))
        c = max(0, min(c, len(rows[r]) - 1))
        keys = []
        if want[0] != "accept":
            cells = [(ri, ci) for ri, row in enumerate(rows) for ci in range(len(row))]
            if want[0] == "move":
                tr, tc = next(cell for cell in cells if act_at(*cell)[0] == "move"
                              and act_at(*cell)[1] is b.player.mon.moves[want[1]])
            else:
                tr, tc = next(cell for cell in cells if act_at(*cell)[0] == want[0])
            while r != tr:                                  # the same steps the menu itself takes
                nr = r + (1 if tr > r else -1)
                old, new = len(rows[r]), len(rows[nr])
                c = int(round(c * (new - 1) / (old - 1))) if old > 1 else 0
                c = max(0, min(c, new - 1))
                keys.append("down" if tr > r else "up")
                r = nr
            keys += ["right" if tc > c else "left"] * abs(tc - c)
        self.press(keys + ["enter"])
        return UI.grid_menu(self, draw, head, rows, desc, start, blocked, tag)


# =========================================================================
# The two scenes
# =========================================================================
def befriend(ui, seed):
    """A wild creature of your own nature: wear it down, offer a lure. True if it joined."""
    g = Game(ui, rng=random.Random(seed))
    g.journal = S.Journal()
    st = M.preview_state("flame", "3")
    st.bag = {"remedy": 2, "lure_flame_3": 1}
    g.setup(st)
    land = W.Land("breeze", 313)
    world = W.World(ui, land, g.hero_data["look"], land.inn_door)
    best = max(land.habitat, key=lambda q: sum(1 for o in land.habitat if abs(o[0] - q[0]) <= 4 and abs(o[1] - q[1]) <= 3))
    world.x, world.y = best
    world.banner = 0
    near = [o for o in land.habitat if o != best and abs(o[0] - best[0]) <= 3 and abs(o[1] - best[1]) <= 2]
    wild = W.Wild(near[0][0], near[0][1], R.Mon("flaremoth", 11))
    world.wild = [wild] + [W.Wild(x, y, R.Mon(sid, 9)) for (x, y), sid in zip(near[1:], ["gustwing", "whirlet"])]
    before = len(st.team)
    # you, your first creature, two attacks, then the satchel and the lure in it
    ui.plan = [0, 0, ("move", 0), ("move", 0), ("satchel",), 1]
    ui.pause(world.draw, 14, g.hud(world)())
    g.wild_battle(world, wild)
    return len(st.team) == before + 1 and not ui.plan


def citadel(ui, seed):
    """Inside the Citadel: a companion meets their old friend's dark creature."""
    g = Game(ui, rng=random.Random(seed))
    g.journal = S.Journal()
    st = M.preview_state("flame", "citadel")
    g.setup(st)
    ally = st.party[1]
    nem = ally.data["nemesis"]
    stg = Stage(ui, "hall")
    stg.show(("trainer", g.hero_data["look"]), ("trainer", ally.data["look"]), ("trainer", nem["look"]))
    ui.say(stg.draw, "Floor 1. %s is waiting." % nem["name"])
    ui.say(stg.draw, g.fmt(nem["taunt"], ally=ally.name), speaker=g.villain(ally.element))
    b = Battle(ui, "hall", g.rng)
    b.open()
    foe = R.make_team(ally.element, R.TUNING["citadel"]["nemesis_level"], 1, "shadow")[0]
    ui.plan = [0, ("accept",), ("accept",)]
    try:
        g.face(b, foe, nem["first"], first=ally)
    except Stop:
        pass


def record(path):
    seed = next(s for s in range(1, 400) if try_seed(s))
    print("using seed", seed)
    ui = RecUI()
    befriend(ui, seed)
    ui.cut()
    citadel(ui, seed)
    for _ in range(30):                                     # hold the last picture a moment
        ui.frames.append(ui.frames[-1])
    encode(ui.frames, path)


def try_seed(seed):
    ui = RecUI(recording=False)
    try:
        return befriend(ui, seed)
    except Stop:
        return False


# =========================================================================
# Writing the GIF
# =========================================================================
def encode(frames, path):
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
        lookup = {c: min(range(len(palette)), key=lambda i: sum((a - b) ** 2 for a, b in zip(c, palette[i])))
                  for c in counts}
    print("colours used: %d -> palette %d" % (len(counts), len(palette)))
    k = ART_SCALE
    aw, ah = len(frames[0][0][0]), len(frames[0][0])
    GW, art_h = aw * k, ah * k
    GH = art_h + BOX_H
    delay = int(round(100 * EVERY / FPS))
    box_idx = {}
    out = []
    prev = None
    for art, box in frames:
        rows = []
        for row in art:
            line = bytes(lookup[c] for c in row for _ in range(k))
            rows += [line] * k
        if id(box) not in box_idx:
            box_idx[id(box)] = [bytes(lookup[c] for c in row) for row in box]
        rows += box_idx[id(box)]
        if prev is None:
            x0, y0, x1, y1 = 0, 0, GW - 1, GH - 1
        else:
            changed = [y for y in range(GH) if rows[y] is not prev[y] and rows[y] != prev[y]]
            if not changed:
                out[-1][5] += delay                         # nothing moved: hold the last frame longer
                continue
            y0, y1 = changed[0], changed[-1]
            x0, x1 = GW, -1
            for y in changed:
                a, b = rows[y], prev[y]
                lo = next(x for x in range(GW) if a[x] != b[x])
                hi = next(x for x in range(GW - 1, -1, -1) if a[x] != b[x])
                x0, x1 = min(x0, lo), max(x1, hi)
        prev = rows
        sub = b"".join(rows[y][x0:x1 + 1] for y in range(y0, y1 + 1))
        out.append([x0, y0, x1 - x0 + 1, y1 - y0 + 1, sub, delay])
    out[-1][5] += 150                                       # pause before it loops
    gif.write_gif(path, GW, GH, palette, [tuple(f) for f in out])
    print("saved %s  (%d x %d, %d frames, %.1f MB)" % (path, GW, GH, len(out), os.path.getsize(path) / 1e6))


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(HERE), "screens")
    os.makedirs(out_dir, exist_ok=True)
    record(os.path.join(out_dir, "clip.gif"))
