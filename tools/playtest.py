"""Robot playtest: plays the game with no screen, to catch errors.

    python tools/playtest.py                 # every hero: the quick taste and the full journey
    python tools/playtest.py wave            # one hero
    python tools/playtest.py wave 2 7        # one hero, art scale 2, random seed 7
    python tools/playtest.py wave 1 1 -v     # ...and say what happens along the way

The robot plays like a sensible beginner most of the time and randomly the
rest, so every path gets exercised: it trains each trainer's creatures, buys
lures and befriends wild creatures, rests when hurt, heeds the warning at the
Citadel's border, and when the Citadel beats it, goes back to an earlier rest
point to train some more. It checks the game reaches the end without errors;
it isn't a test of balance (see `python -m game.sim`).
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
from game.story import Game, Stage              # noqa: E402

T = R.TUNING
VERBOSE = "-v" in sys.argv


def note(*a):
    if VERBOSE:
        print("   ", *a, flush=True)


def top(member):
    return max(m.level for m in member.team)


class Robot:
    """Stands in for the keyboard: mostly Enter, now and then an arrow."""

    def __init__(self, seed, limit):
        self.r = random.Random(seed)
        self.polls = 0
        self.limit = limit
        self.floor_losses = {}      # Citadel floor -> losses there since the robot last trained
        self.extra = 0              # how much harder to train after being sent back
        self.lord_losses = {}       # stage -> times that land's Lord has beaten the robot
        self.game = None

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


def health(m):
    """A trainer's team, from 0 (all fainted) to 1 (all fresh)."""
    return sum(c.ratio for c in m.team if c.alive) / len(m.team)


def fighter_score(m, foe):
    """How good a pick a trainer's team is against a foe (bigger is better)."""
    alive = R.living(m.team)
    if not alive:
        return 0
    lvl = max(a.level for a in alive)
    health = sum(a.ratio for a in alive) / len(m.team)
    return R.matchup_score(alive[0], foe.element) * (0.2 + 0.8 * health) * (1.12 ** (lvl - foe.level))


class RobotUI(UI):
    """Answers menus itself: usually sensibly, sometimes at random, and
    sometimes by mashing keys through the real menu code."""

    def menu(self, draw, head, options, cols=2, desc=None, start=0, blocked=None, col_width=47, tag=None):
        robot = self.keys
        r = robot.r
        if r.random() < 0.06:
            return UI.menu(self, draw, head, options, cols, desc, start, blocked, col_width, tag)
        self.frame(draw(), [head(0) if callable(head) else head])
        n = len(options)
        if desc:
            for i in range(n):
                desc(i)
        valid = [i for i in range(n) if not (blocked and blocked(i))]
        kind = tag[0] if tag else None
        sensible = r.random() > 0.08
        st = robot.game.st if robot.game else None

        if kind == "trainer" and sensible:
            _, members, foe, why = tag
            if why == "wild":
                # train whoever is furthest behind, if they have a fair chance
                fair = [i for i in valid if fighter_score(members[i], foe) >= 0.75 and health(members[i]) > 0.5]
                if fair:
                    return min(fair, key=lambda i: top(members[i]))
            return max(valid, key=lambda i: fighter_score(members[i], foe))
        if kind == "blocked" and r.random() > 0.3:
            return next(i for i, m in enumerate(tag[1]) if m.element == tag[2])
        if kind == "market" and sensible:
            _, st, el = tag
            keeper = st.member(el)
            if keeper and len(keeper.team) < R.TEAM_MAX and not R.lures_for(el, st.bag) and st.coins >= 6:
                return 1
            if st.bag.get("remedy", 0) < 2 and st.coins >= R.ITEMS["remedy"]["price"] + 12 and st.can_carry("remedy"):
                return 0
            if 2 in valid:
                return 2
            return 3
        if kind == "item" and getattr(robot, "want_lure", False):
            robot.want_lure = False
            _, keys, b = tag
            right = [i for i, k in enumerate(keys) if k in R.LURES and R.LURES[k][0] == b.enemy.mon.element and i in valid]
            return right[-1] if right else n - 1
        if kind == "sell":
            _, keys, st = tag
            for i, k in enumerate(keys):
                if k in ("herb", "shard"):
                    return i
            return n - 1
        if kind == "shop" and sensible:
            _, stock, st = tag
            if stock[0] == "remedy":
                return 0 if (0 in valid and st.bag.get("remedy", 0) < 2) else n - 1
            have = sum(st.bag.get(k, 0) for k in stock)
            if have < 2:
                for i in (1, 0, 2):
                    if i in valid:
                        return i
            return n - 1
        if kind == "pack" and r.random() > 0.3:
            return n - 1
        if kind == "member" and sensible:
            _, party, why = tag
            if why == "heal":
                for i, m in enumerate(party):
                    if m.heals > 0 and any(c.alive and c.ratio < 0.6 for c in m.team):
                        return i
                return n - 1
            return r.choice(valid) if r.random() < 0.5 else n - 1
        if kind == "breather" and sensible:
            st = tag[1]
            if any(m.heals > 0 and any(c.alive and c.ratio < 0.6 for c in m.team) for m in st.party):
                return 1
            return 3
        if kind == "heal":
            return min(range(len(tag[1])), key=lambda i: tag[1][i].ratio)
        if kind == "after_loss":
            names = tag[1]
            if names[0] == "Try this floor again":
                k = st.floor
                robot.floor_losses[k] = robot.floor_losses.get(k, 0) + 1
                total = sum(robot.floor_losses.values())
                note("lost on floor", k + 1, "(%d losses in the Citadel since training)" % total)
                if "Go back further" in names and total >= 4:
                    return names.index("Go back further")
                if "Go back down a floor" in names and robot.floor_losses[k] >= 2:
                    return names.index("Go back down a floor")
                return 0
            robot.lord_losses[st.stage] = robot.lord_losses.get(st.stage, 0) + 1
            note("lost to the Lord of stage", st.stage, "(%d times)" % robot.lord_losses[st.stage])
            return 1 if (n > 1 and robot.lord_losses[st.stage] % 2 == 1) else 0     # an ally tries once, then train
        if kind == "point":
            lands = [i for i, k in enumerate(tag[1]) if k.startswith("land")]
            if lands:
                robot.floor_losses.clear()
                robot.extra += 1
                note("going back to", tag[1][lands[0]], "to train harder (+%d)" % robot.extra)
                return lands[0]
            return n - 2 if n - 2 >= len(tag[1]) else n - 1          # "Further back", else never mind
        if kind == "citadel":
            return 0 if (tag[1] < 2 and sensible) or r.random() < 0.03 else 1
        if kind == "west":
            return 0 if r.random() < 0.08 else 1
        if kind == "teammate":
            _, team, b, forced = tag
            mine = [i for i in valid if i < len(team)]
            if b is None and mine:                  # before a fight: whoever the robot has put first leads,
                return mine[0]                      # (the one that most needs the practice)
            return max(mine, key=lambda i: (team[i].level, team[i].ratio)) if mine else n - 1
        if kind == "lure":
            return len(tag[1]) - 1
        if kind == "release" and r.random() > 0.05:
            return 0
        return r.choice(valid)

    def pager(self, draw, rows, n, start=0, blocked=None, cancel=False, tag=None):
        r = self.keys.r
        if r.random() < 0.06:                       # now and then, through the real page with real keys
            return UI.pager(self, draw, rows, n, start, blocked, cancel, tag)
        for i in (range(n) if r.random() < 0.1 else [start]):
            cv = draw(i)
            rows(i, True, blocked(i) if blocked else None)
        options = [[(None, "x")]] * n + ([[(None, "Back")]] if cancel else [])
        i = self.menu(lambda: cv, [], options, blocked=lambda i: blocked(i) if blocked and i < n else None, tag=tag)
        return None if i >= n else i

    def grid_menu(self, draw, head, rows, desc=None, start=(0, 0), blocked=None, tag=None):
        r = self.keys.r
        if r.random() < 0.06:
            return UI.grid_menu(self, draw, head, rows, desc, start, blocked, tag)
        self.frame(draw(), [head])
        cells = [(ri, ci) for ri, row in enumerate(rows) for ci in range(len(row))]
        if desc:
            for cell in cells:
                desc(*cell)
        valid = [c for c in cells if not (blocked and blocked(*c))]
        _, b, act_at, _ = tag
        acts = {c: act_at(*c) for c in valid}
        if r.random() < 0.05:
            return r.choice(valid)
        e, p = b.enemy.mon, b.player.mon

        def cell(kind):
            return next((c for c, a in acts.items() if a[0] == kind), None)
        if b.wild and cell("satchel") and b.lure_problem(e) is None:
            if e.ratio < 0.45:
                self.keys.want_lure = True
                return cell("satchel")
            # wear it down gently: the lightest touch it has, so it doesn't faint first
            soft = [(c, a[1]) for c, a in acts.items() if a[0] == "move" and a[1].kind == "attack"]
            if soft:
                return min(soft, key=lambda ca: R.expected(p, e, ca[1]))[0]
        # a much weaker creature leads only to earn its share: swap in someone who can win
        stronger = [m for m in b.team if m.alive and m is not p and m.level >= p.level + 2]
        if cell("team") and stronger and p.level + 2 <= e.level and (b.wild or p.ratio < 0.5):
            return cell("team")
        want = R.choose_ai(p, e, r, careful=True)
        for c, a in acts.items():
            if a[0] == "move" and a[1] is want:
                return c
        return next(c for c, a in acts.items() if a[0] == "move")


def make_pilot(game, robot):
    """Walks the maps: rest when hurt, buy lures, befriend and train, then move on."""
    robot.game = game

    def path_step(world, goals, bump=None):
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
                if n not in prev and world.can_walk(*n) and world.thing_at(*n) is None and world.land.tile(*n) != "W":
                    prev[n] = cur
                    q.append(n)
        return None

    seen = {"n": 0}

    def pilot(world):
        st = game.st
        r = robot.r
        seen["n"] += 1
        if VERBOSE and seen["n"] % 20000 == 0:
            note("stage %d%s, wild %d, coins %d, losses %d, turns %d | %s" % (
                st.stage, " (Lord joined)" if st.lord_beaten else "", len(world.wild), st.coins, st.losses, st.turns,
                "  ".join("%s %s" % (m.name[:3], ",".join("%d%s" % (c.level, "" if c.alive else "x") for c in m.team))
                          for m in st.party)))
        if r.random() < 0.004:
            return r.choice(["up", "down", "left", "right", "enter", "enter", "menu"])
        land = world.land
        stage = st.stage
        goal = 7 if stage == 0 else T["expected"]["levels"][stage - 1]
        if stage == 5 and st.lord_beaten:                   # the last stop before the Citadel
            goal = T["citadel"]["nemesis_level"]
        goal = min(T["level_cap"], goal + robot.extra + (0 if st.lord_beaten else robot.lord_losses.get(stage, 0)))
        # (stands in for "Put it first" in the pack: the one that most needs the practice leads)
        for m in st.party:
            alive = R.living(m.team)
            if len(alive) > 1:
                first = min(alive, key=lambda c: c.level)
                if m.team[0] is not first:
                    m.team.remove(first)
                    m.team.insert(0, first)

        mons = [c for m in st.party for c in m.team]
        wild_lo = T["wild_levels"][min(5, max(stage, st.reached - 1))][0]
        # who still needs practice here, and could get it (someone far behind the wild creatures can't)
        trainees = [m for m in st.party if top(m) >= wild_lo - 2
                    and any(c.level < goal - (0 if m.is_hero else 1) for c in m.team)]
        fit = [m for m in st.party if health(m) > 0.5]
        fainted = sum(1 for c in mons if not c.alive)
        keeper = st.member(land.element)
        size_goal = 4 if (keeper and keeper.is_hero) else 3
        can_lure = bool(R.lures_for(land.element, st.bag)) or st.coins >= T["lures"][0]["price"]
        want_more = bool(keeper) and len(keeper.team) < size_goal and can_lure
        ready = not (stage == 5 and st.lord_beaten) or game.readiness() < 2
        busy = bool(trainees) or want_more or not ready
        hurt = fainted >= max(1, len(mons) // 3) or len(fit) * 2 < len(st.party)
        if busy and trainees and not any(m in fit for m in trainees):
            hurt = True
        if world.lord_look and not busy and len(fit) < len(st.party):
            hurt = True                                     # go to meet the Lord rested
        if hurt or (busy and not world.wild):
            return path_step(world, {land.inn_door}, bump="up")
        if want_more and not R.lures_for(land.element, st.bag) and st.coins >= T["lures"][0]["price"]:
            return path_step(world, {(land.market[0], land.market[1] + 1)}, bump="up")
        if busy and world.wild:
            return path_step(world, {(w.x, w.y) for w in world.wild})
        if world.lord_look:                                 # the Lord is still ahead on the road
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
    robot.game = g
    g.intro()
    g.choose_hero()
    g.play_trial(hero)
    return g, ui.tick


def run_journey(hero, scale, seed, limit=40_000_000):
    """A full journey, saved and reloaded part-way to check saving works."""
    path = os.path.join(tempfile.gettempdir(), "entwined_test_%s_%d.json" % (hero, seed))
    S.erase(path)
    robot = Robot(seed, limit)
    ui = RobotUI(Display("null", None, scale=scale), robot, headless=True)
    g = Game(ui, rng=random.Random(seed), save_path=path)
    g.pilot = make_pilot(g, robot)
    g.journal = S.Journal(path)
    g.setup(S.State(hero))
    g.play("hero_intro", stage=Stage(ui, hero))
    while g.st.reached <= 2:                     # home and the first two lands
        g.land_loop()
    note("reloading from the save file at stage", g.st.stage)
    journal = S.load(path)                       # carry on from the save file, as "Carry on" would
    assert journal is not None and journal.get().hero == hero, "save file missing"
    assert len(journal.points) >= 3 and len(journal.get().party) >= 2, "save file out of date"
    g2 = Game(ui, rng=random.Random(seed + 1), save_path=path)
    g2.pilot = make_pilot(g2, robot)
    g2.play_journey(journal)
    assert S.load(path) is None, "finished journey should clear its save"
    return g2, ui.tick


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    heroes = [args[0]] if args else R.ORDER
    scale = int(args[1]) if len(args) > 1 else 1
    seed = int(args[2]) if len(args) > 2 else 1
    for hero in heroes:
        t = time.time()
        g, frames = run_trial(hero, scale, seed)
        print("quick taste   %-8s ok: %2d losses, %4d turns, %7d frames, %5.1fs"
              % (R.HEROES[hero]["name"], g.st.losses, g.st.turns, frames, time.time() - t), flush=True)
    for hero in heroes:
        t = time.time()
        g, frames = run_journey(hero, scale, seed)
        st = g.st
        sizes = "/".join(str(len(m.team)) for m in st.party)
        tops = "/".join(str(top(m)) for m in st.party)
        print("full journey  %-8s ok: %2d losses, %5d turns, teams %s, best levels %s, %8d frames, %5.1fs"
              % (R.HEROES[hero]["name"], st.losses, st.turns, sizes, tops, frames, time.time() - t), flush=True)
    print("Every playthrough reached the end.")
