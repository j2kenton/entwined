"""Robot playtest: plays the whole game with no screen, for every hero.

    python tools/playtest.py            # all six heroes, retro and HD art
    python tools/playtest.py wave 2     # one hero, at art scale 2

The robot plays sensibly most of the time (best move, best match-up) and
randomly the rest, so every path gets exercised: losses, retries, allies
stepping in, the hybrid, the ending. It checks the game reaches the end
screen without errors; it isn't a test of balance (see `python -m game.sim`).
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import rules as R                     # noqa: E402
from game.engine.display import Display         # noqa: E402
from game.engine.ui import UI, Quit             # noqa: E402
from game.story import Game, Stage              # noqa: E402


class Robot:
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
        if r.random() < 0.15:
            return UI.menu(self, draw, head, options, cols, desc, start, blocked, col_width, tag)
        self.frame(draw(), [head(0) if callable(head) else head])
        if desc:
            for i in range(len(options)):
                desc(i)
        valid = [i for i in range(len(options)) if not (blocked and blocked(i))]
        if tag is None or r.random() < 0.15:
            return r.choice(valid)
        if tag[0] == "move":
            _, p, e = tag
            return p.moves.index(R.choose_ai(p, e, r, careful=True))
        _, members, foe = tag
        return max(valid, key=lambda i: R.matchup_score(members[i].mon, foe.element)
                   * (0.35 + 0.65 * members[i].mon.ratio))


def run(hero, scale, seed=1, limit=3_000_000):
    ui = RobotUI(Display("null", None, scale=scale), Robot(seed, limit), headless=True)
    g = Game(ui, rng=random.Random(seed))
    t = time.time()
    g.title()
    g.intro()
    g.choose_hero()
    g.start(hero)
    g.play("hero_intro", stage=Stage(ui, hero))
    g.journey()
    g.citadel()
    g.outro()
    g.end()
    return g, ui.tick, time.time() - t


if __name__ == "__main__":
    heroes = [sys.argv[1]] if len(sys.argv) > 1 else R.ORDER
    scales = [int(sys.argv[2])] if len(sys.argv) > 2 else [1, 2]
    for scale in scales:
        for hero in heroes:
            g, frames, secs = run(hero, scale)
            print("scale %d  %-10s finished: %3d losses, %4d turns, %7d frames, %5.1fs"
                  % (scale, R.HEROES[hero]["name"], g.losses, g.turns, frames, secs))
    print("All playthroughs reached the end screen.")
