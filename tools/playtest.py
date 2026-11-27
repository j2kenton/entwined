"""Robot playtest: plays the game with no screen, to catch errors.

    python tools/playtest.py                 # every hero: the quick taste and the full journey
    python tools/playtest.py wave            # one hero
    python tools/playtest.py wave 2 7        # one hero, art scale 2, random seed 7

The robot plays sensibly most of the time (best move, best match-up, rests
when hurt, trains when under-levelled) and randomly the rest, so every path
gets exercised: losses, retries, allies stepping in, bonding, the market, the
blocked ways, the hybrid, saving and loading. It checks the game reaches the
end without errors; it isn't a test of balance (see `python -m game.sim`).
"""
import os
import random
import sys
import tempfile
import time
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import rules as R                     # noqa: E402
from game import state as S                     # noqa: E402
from game import world as W                     # noqa: E402
from game.engine.display import Display         # noqa: E402
from game.engine.ui import UI                   # noqa: E402
from game.story import Game                     # noqa: E402

T = R.TUNING


class Robot:
    """Stands in for the keyboard: mostly Enter, now and then an arrow."""

    def __init__(self, seed, limit):
        self.r = random.Random(seed)
        self.polls = 0
        self.limit = limit

    def poll(self):
        self.polls += 1
        if self.polls > self.limit:
            raise RuntimeError("robot ran out of patience (%d frames)" % self.limit)
        x = self.r.random()
        if x < 0.30:
            return ["enter"]
        if x < 0.34:
            return [self.r.choice(["up", "down", "left", "right"])]
        return []

    def close(self):
        pass


class RobotUI(UI):
    """Answers menus itself: usually sensibly, sometimes at random, and
    sometimes by mashing keys through the real menu code."""

    def menu(self, draw, head, options, cols=2, desc=None, start=0, blocked=None, col_width=47, tag=None):
        r = self.keys.r
        if r.random() < 0.1:
            return UI.menu(self, draw, head, options, cols, desc, start, blocked, col_width, tag)
        self.frame(draw(), [head(0) if callable(head) else head])
        n = len(options)
        if desc:
            for i in range(n):
                desc(i)
        valid = [i for i in range(n) if not (blocked and blocked(i))]
        kind = tag[0] if tag else None
        if kind == "trainer" and r.random() > 0.1:
            _, members, foe = tag
            return max(valid, key=lambda i: R.matchup_score(members[i].team[0], foe.element)
                       * (0.3 + 0.7 * members[i].standing / len(members[i].team)))
        if kind == "blocked" and r.random() > 0.3:
            return next(i for i, m in enumerate(tag[1]) if m.element == tag[2])
        if kind == "market":
            _, stock, st = tag
            if 0 in valid and st.bag.get("remedy", 0) < 3:
                return 0
            if 3 in valid and st.bag.get("lure", 0) < 1 and len(st.team) < 3:
                return 3
            return n - 2 if (n - 2) in valid and r.random() < 0.5 else n - 1
        if kind == "pack" and r.random() > 0.35:
            return n - 1
        if kind == "after_loss" and n > 1 and r.random() > 0.3:
            return 1
        if kind == "teammate":
            return valid[0]
        if kind == "release" and r.random() > 0.05:
            return 0
        return r.choice(valid)

    def grid_menu(self, draw, head, rows, desc=None, start=(0, 0), blocked=None, tag=None):
        r = self.keys.r
        if r.random() < 0.1:
            return UI.grid_menu(self, draw, head, rows, desc, start, blocked, tag)
        self.frame(draw(), [head])
        cells = [(ri, ci) for ri, row in enumerate(rows) for ci in range(len(row))]
        if desc:
            for cell in cells:
                desc(*cell)
        valid = [c for c in cells if not (blocked and blocked(*c))]
        _, b, act_at, _ = tag
        acts = {c: act_at(*c) for c in valid}
        if r.random() < 0.08:
            return r.choice(valid)
        e, p = b.enemy.mon, b.player.mon
        if b.wild and e.element == b.hero_element and e.ratio < 0.6:
            for c, a in acts.items():
                if a[0] == "reach":
                    return c
        want = R.choose_ai(p, e, r, careful=True)
        for c, a in acts.items():
            if a[0] == "move" and a[1] is want:
                return c
        return next(c for c, a in acts.items() if a[0] == "move")


def make_pilot(game, robot):
    """Walks the maps: rest when hurt, train when under-levelled, then head east."""
    memo = {"target": 0, "losses": 0, "stage": -1}

    def path_step(world, goals, bump=None):
        land = world.land
        start = (world.x, world.y)
        if start in goals:
            return bump
        prev = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur in goals:
                while prev[cur] != start:
                    cur = prev[cur]
                dx, dy = cur[0] - start[0], cur[1] - start[1]
                return {(1, 0): "right", (-1, 0): "left", (0, 1): "down", (0, -1): "up"}[(dx, dy)]
            for dx, dy in W.DIRS.values():
                n = (cur[0] + dx, cur[1] + dy)
                if n not in prev and world.can_walk(*n) and world.thing_at(*n) is None:
                    prev[n] = cur
                    q.append(n)
        return None

    def pilot(world):
        st = game.st
        if robot.r.random() < 0.004:
            return robot.r.choice(["up", "down", "left", "right", "enter", "enter", "menu"])
        if memo["stage"] != st.stage:
            memo.update(stage=st.stage, losses=st.losses,
                        target=7 if st.stage == 0 else T["expected"]["levels"][st.stage - 1])
        if st.losses > memo["losses"]:                 # lost a fight: train a little higher
            memo["target"] += st.losses - memo["losses"]
            memo["losses"] = st.losses
        land = world.land
        team = st.team
        hurt = any(not m.alive for m in team) or R.living(team)[0].ratio < 0.45
        low = max(m.level for m in team) < min(memo["target"], T["level_cap"])
        want_more = land.home and len(team) < 2
        if hurt or ((low or want_more) and not world.wild):
            return path_step(world, {land.inn_door}, bump="up")
        if (low or want_more) and world.wild:
            return path_step(world, {(w.x, w.y) for w in world.wild})
        if world.lord_look:                            # the Lord is still ahead on the road
            x, y = land.lord_spot
            if world.lord_seen:
                return path_step(world, {(x - 1, y)}, bump="right")
            return path_step(world, {(x, y)})
        return path_step(world, {land.gate})
    return pilot


def run_trial(hero, scale, seed, limit=2_000_000):
    robot = Robot(seed, limit)
    ui = RobotUI(Display("null", None, scale=scale), robot, headless=True)
    g = Game(ui, rng=random.Random(seed), save_path=os.path.join(tempfile.gettempdir(), "entwined_test_none.json"))
    g.intro()
    g.choose_hero()
    g.play_trial(hero)
    return g, ui.tick


def run_journey(hero, scale, seed, limit=6_000_000):
    """A full journey, saved and reloaded part-way to check saving works."""
    path = os.path.join(tempfile.gettempdir(), "entwined_test_%s_%d.json" % (hero, seed))
    S.erase(path)
    robot = Robot(seed, limit)
    ui = RobotUI(Display("null", None, scale=scale), robot, headless=True)
    g = Game(ui, rng=random.Random(seed), save_path=path)
    g.pilot = make_pilot(g, robot)
    g.setup(S.State(hero))
    g.play("hero_intro", stage=__import__("game.story", fromlist=["Stage"]).Stage(ui, hero))
    while g.st.stage <= 2:                       # home and the first two lands
        g.land_loop()
    saved = S.load(path)                         # carry on from the save file, as "Continue" would
    assert saved is not None and saved.hero == hero, "save file missing"
    assert saved.stage >= 2 and len(saved.party) >= 2, "save file out of date"
    g2 = Game(ui, rng=random.Random(seed + 1), save_path=path)
    g2.pilot = make_pilot(g2, robot)
    g2.play_journey(saved, fresh=False)
    assert S.load(path) is None, "finished journey should clear its save"
    return g2, ui.tick


if __name__ == "__main__":
    args = sys.argv[1:]
    heroes = [args[0]] if args else R.ORDER
    scale = int(args[1]) if len(args) > 1 else 1
    seed = int(args[2]) if len(args) > 2 else 1
    for hero in heroes:
        t = time.time()
        g, frames = run_trial(hero, scale, seed)
        print("quick taste   %-8s ok: %2d losses, %4d turns, %7d frames, %5.1fs"
              % (R.HEROES[hero]["name"], g.st.losses, g.st.turns, frames, time.time() - t))
    for hero in heroes:
        t = time.time()
        g, frames = run_journey(hero, scale, seed)
        st = g.st
        print("full journey  %-8s ok: %2d losses, %4d turns, team of %d (top level %d), %8d frames, %5.1fs"
              % (R.HEROES[hero]["name"], st.losses, st.turns, len(st.team), max(m.level for m in st.team),
                 frames, time.time() - t))
    print("Every playthrough reached the end.")
