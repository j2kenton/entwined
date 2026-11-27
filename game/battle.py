"""The battle scene: two creatures on a backdrop, menus and animations.

A Battle stays on screen while creatures come and go, so one scene can cover
a whole team fight, or a Citadel floor where different trainers step in.
"""
import math
import random

from . import rules as R
from .art import backdrops, creatures
from .engine.canvas import darker, draw_mini, mini_width, mix
from .engine.ui import DIM, GREY, RED, WHITE, message_rows

W, H = backdrops.W, backdrops.H
ENEMY_FOOT = (76, 30.5)
PLAYER_FOOT = (24, 55.5)
ENEMY_C, PLAYER_C = (76, 15), (25, 36)
ENEMY_MOUTH, PLAYER_MOUTH = (66, 18), (40, 29)
PLAIN_SPARKS = [(255, 255, 255), (230, 230, 240), (190, 190, 205), (255, 245, 200)]
HEAL_SPARKS = [(150, 255, 170), (255, 255, 255), (110, 220, 140)]
BOND_SPARKS = [(255, 170, 200), (255, 220, 235), (255, 255, 255), (255, 120, 170)]


def el_colour(element):
    return tuple(R.ELEMENTS["colour"][element])


def sparks(element):
    if element is None:
        return PLAIN_SPARKS
    return [tuple(c) for c in R.ELEMENTS["sparks"][element]]


def ease(t):
    return 1 - (1 - t) ** 3


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "r", "col", "g", "drag")

    def __init__(self, x, y, vx, vy, life, r, col, g=0.0, drag=1.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.r, self.col, self.g, self.drag = life, r, col, g, drag


class Side:
    """One creature's place on the field."""

    def __init__(self, far):
        self.far = far
        self.mon = None
        self.frames = []
        self.white = None
        self.on = False
        self.dx = self.dy = 0.0      # offset from its spot, in logical pixels
        self.flash = 0
        self.sink = 0
        self.hp_shown = 0.0          # what the health bar shows now
        self.hp_target = 0.0         # what it is moving towards (set when a hit lands)

    @property
    def foot(self):
        return ENEMY_FOOT if self.far else PLAYER_FOOT

    @property
    def centre(self):
        return ENEMY_C if self.far else PLAYER_C

    @property
    def mouth(self):
        return ENEMY_MOUTH if self.far else PLAYER_MOUTH

    @property
    def dir(self):
        return -1 if self.far else 1


class Battle:
    def __init__(self, ui, backdrop, rng=None, weather=None):
        self.ui = ui
        self.S = ui.S
        self.bg = backdrops.backdrop(backdrop, self.S)
        self.rng = rng or random.Random()
        self.weather = weather               # an element whose attacks hit harder today
        self.fx = random.Random(4)           # for particle scatter only
        self.enemy, self.player = Side(True), Side(False)
        self.parts = []
        self.shake = 0
        self.reveal = 1.0
        self.banner = None
        self.panels = False
        self.cursor = {}                     # remembered menu position per creature
        self.after_send = None               # called with a creature when you send it in
        self.team, self.foes, self.wild, self.bag, self.party = [], [], False, None, None
        self.fought = []             # your creatures that have faced the foe now out
        self.can_call = False        # may a companion be called in mid-fight?
        self.reset_stats()

    def reset_stats(self):
        self.stats = dict(turns=0, elem_hits=0, plain_hits=0, guards=0, misses=0,
                          min_ratio=1.0, finisher=None, fainted=0)

    # =====================================================================
    # Drawing
    # =====================================================================
    def set_look(self, side):
        """(Re)build a side's sprites from its creature's current look."""
        mon = side.mon
        other = None
        variant = mon.variant
        if mon.variant == "hybrid":
            if mon.shown_forms > 1:
                other = [f for f in mon.forms if f != mon.element][0]
            else:
                variant = "shadow"           # until it shows its second nature
        frames = creatures.frames(mon.sid, variant, other, self.S, 34 if side.far else 44)
        side.frames = frames if side.far else [f.flipped() for f in frames]
        side.white = side.frames[0].silhouette((255, 255, 255))

    def draw(self):
        """Advance the animation one frame and return the picture."""
        S = self.S
        tick = self.ui.tick
        alive = []
        for p in self.parts:
            p.x += p.vx
            p.y += p.vy
            p.vy += p.g
            if p.drag != 1.0:
                p.vx *= p.drag
                p.vy *= p.drag
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.parts = alive
        for side in (self.enemy, self.player):
            if side.mon:
                side.hp_shown += (side.hp_target - side.hp_shown) * 0.14
                if abs(side.hp_target - side.hp_shown) < 0.004:
                    side.hp_shown = side.hp_target
            side.flash = max(0, side.flash - 1)
        self.shake = max(0, self.shake - 1)
        if self.ui.headless and tick % 40:
            return None                      # tests: draw only now and then

        cv = self.bg.copy()
        bob = 1 if (tick // 12) % 2 else 0
        for side in (self.enemy, self.player):
            if not side.on:
                continue
            spr = side.white if (side.flash and side.flash % 4 < 2) else side.frames[(tick // 3) % len(side.frames)]
            fx, fy = side.foot
            b = bob if side.far else 1 - bob
            x = int(round((fx + side.dx) * S))
            y = int(round((fy + side.dy + b + side.sink) * S))
            clip = int(round((fy + 1.5) * S)) if side.sink else None
            spr.blit(cv, x, y, clip_y=clip)
        for p in self.parts:
            if p.r <= 0.7:
                cv.set(p.x, p.y, p.col)
            else:
                cv.ellipse(p.x, p.y, p.r, p.r, p.col)
        if self.panels:
            self.draw_panels(cv)
        if self.banner:
            txt, col = self.banner
            tw = mini_width(txt)
            x0 = (W - tw) // 2
            cv.rect(x0 - 4, 22, x0 + tw + 3, 30, (20, 14, 26))
            cv.rect(x0 - 4, 22, x0 + tw + 3, 22, col)
            cv.rect(x0 - 4, 30, x0 + tw + 3, 30, col)
            draw_mini(cv, x0, 24, txt, col, shadow=darker(col, 0.3))
        if self.shake:
            dx = int((2 if self.shake % 2 else -2) * S)
            pad = [(8, 6, 10)] * abs(dx)
            cv.px = [(pad + row[:-dx]) if dx > 0 else (row[-dx:] + pad) for row in cv.px]
        if self.reveal < 1.0:
            blank = [(8, 6, 10)] * cv.w
            for y in range(cv.h):
                if (int(y / S) % 6) / 6 >= self.reveal:
                    cv.px[y] = blank
        return cv

    def draw_panels(self, cv):
        def panel(x0, y0, x1, y1, accent):
            cv.rect(x0, y0, x1, y1, (22, 16, 30))
            cv.rect(x0, y0, x1, y0, accent)
            cv.rect(x0, y1, x1, y1, darker(accent, 0.6))
            cv.rect(x0, y0, x0, y1, darker(accent, 0.8))
            cv.rect(x1, y0, x1, y1, darker(accent, 0.6))

        def bar(x0, y, width, t):
            cv.rect(x0 - 1, y - 1, x0 + width, y + 2, (10, 8, 14))
            cv.rect(x0, y, x0 + width - 1, y + 1, (60, 50, 62))
            n = int(round(width * max(0.0, min(1.0, t))))
            if n > 0:
                col = (96, 222, 112) if t > 0.5 else ((250, 206, 70) if t > 0.2 else (240, 72, 60))
                cv.rect(x0, y, x0 + n - 1, y + 1, col)
                cv.rect(x0, y, x0 + n - 1, y, mix(col, (255, 255, 255), 0.35))

        e, p = self.enemy, self.player
        if e.on or (e.mon and e.sink):
            col = el_colour(e.mon.element)
            panel(2, 2, 52, 13, col)
            draw_mini(cv, 5, 4, e.mon.name, (255, 240, 220), shadow=(40, 30, 40))
            cv.rect(46, 4, 49, 7, col)
            cv.set(47, 5, mix(col, (255, 255, 255), 0.6))
            draw_mini(cv, 5, 9, "HP", (255, 200, 80))
            bar(13, 10, 24, e.hp_shown)
            draw_mini(cv, 40, 9, "L%d" % e.mon.level, (200, 196, 210))
        if p.on or (p.mon and p.sink):
            col = el_colour(p.mon.element)
            panel(48, 43, 98, 58, col)
            cv.rect(51, 45, 54, 48, col)
            cv.set(52, 46, mix(col, (255, 255, 255), 0.6))
            draw_mini(cv, 57, 45, p.mon.name, (230, 244, 255), shadow=(20, 30, 50))
            draw_mini(cv, 51, 50, "HP", (255, 200, 80))
            bar(59, 51, 36, p.hp_shown)
            draw_mini(cv, 51, 54, "L%d" % p.mon.level, (200, 206, 220))
            txt = "%d/%d" % (round(p.hp_shown * p.mon.max_hp), p.mon.max_hp)
            draw_mini(cv, 96 - mini_width(txt), 54, txt, (220, 230, 240))

    # =====================================================================
    # Small helpers
    # =====================================================================
    rows = ()        # what the text box shows while an animation plays

    def land(self, side):
        """The moment a hit (or a heal) lands: let the health bar catch up."""
        side.hp_target = side.mon.ratio

    def wait(self, n, fn=None):
        for i in range(n):
            if fn:
                fn(i)
            self.ui.frame(self.draw(), self.rows)

    def say(self, text, speaker=None, wait=False, hold=14):
        self.ui.say(self.draw, text, speaker=speaker, wait=wait, hold=hold)
        self.rows = message_rows(text, len(text), speaker)

    def burst(self, at, cols, n=24, speed=1.6, g=0.0, life=(10, 20), r=(0.5,)):
        fx = self.fx
        for _ in range(n):
            a = fx.uniform(0, math.tau)
            v = fx.uniform(0.4, speed)
            self.parts.append(Particle(at[0], at[1], math.cos(a) * v, math.sin(a) * v,
                                       int(fx.uniform(*life)), fx.choice(r), fx.choice(cols), g=g))

    def open(self, frames=16):
        self.ui.battle = self
        self.reveal = 0.0
        self.wait(frames, lambda i: setattr(self, "reveal", (i + 1) / frames))
        self.reveal = 1.0

    def close(self, frames=14):
        self.wait(frames, lambda i: setattr(self, "reveal", 1 - (i + 1) / frames))
        self.reveal = 0.0
        self.ui.battle = None

    # =====================================================================
    # Creatures coming and going
    # =====================================================================
    def send_enemy(self, mon, text=None):
        e = self.enemy
        e.mon, e.sink, e.dx, e.dy = mon, 0, 0, 0
        e.hp_shown = e.hp_target = mon.ratio
        mon.clear_status()
        self.set_look(e)
        if text:
            self.say(text, hold=0)
        e.on, e.flash = True, 10
        self.burst(ENEMY_C, sparks(mon.element), 30)
        self.panels = True
        self.wait(18)

    def send_player(self, mon, text=None):
        p = self.player
        p.mon, p.sink, p.dy = mon, 0, 0
        p.hp_shown = p.hp_target = mon.ratio
        mon.clear_status()
        self.set_look(p)
        if text:
            self.say(text, hold=0)
        p.on = True
        self.wait(14, lambda i: setattr(p, "dx", -58 * (1 - ease((i + 1) / 14))))
        p.dx = 0
        self.burst((26, 40), sparks(mon.element), 24)
        self.panels = True
        self.wait(10)
        if self.after_send:
            self.after_send(mon)

    def recall_player(self, text=None):
        p = self.player
        if not p.on:
            return
        if text:
            self.say(text, hold=0)
        p.flash = 8
        self.wait(8)
        self.wait(10, lambda i: setattr(p, "dx", -58 * ease((i + 1) / 10)))
        p.on, p.dx = False, 0

    def faint(self, side):
        side.flash = 8
        self.wait(8)
        depth = 38 if side.far else 50
        self.wait(24, lambda i: setattr(side, "sink", int(ease((i + 1) / 24) * depth)))
        side.on, side.sink = False, 0

    def morph_enemy(self, new_element):
        """A hybrid shifts to its other form."""
        e = self.enemy
        mon = e.mon
        both = sparks(mon.forms[0]) + sparks(mon.forms[1])
        for i in range(22):
            if i % 2 == 0:
                self.burst(ENEMY_C, both, 8, speed=2.2)
            e.flash = 4
            self.ui.frame(self.draw(), self.rows)
        mon.set_form(new_element)
        self.set_look(e)
        e.flash = 10
        self.shake = 6
        self.burst(ENEMY_C, both, 40, speed=2.6)
        self.wait(18)

    # =====================================================================
    # Move animations (all work in either direction)
    # =====================================================================
    def anim_stream(self, att, tgt, hit, cols, big=False):
        fx = self.fx
        sx, sy = att.mouth
        tx, ty = tgt.centre
        self.wait(5, lambda i: setattr(att, "dx", att.dir * [1, 2, 3, 2, 1][i]))
        att.dx = 0

        def spray(i):
            for _ in range(7 if big else 5):
                life = int(fx.uniform(12, 16))
                t = fx.uniform(0.9, 1.1)
                self.parts.append(Particle(sx + fx.uniform(-1, 1), sy + fx.uniform(-2, 2),
                                           (tx - sx) / life * t, (ty - sy) / life * t - 0.9 + fx.uniform(-0.4, 0.4),
                                           life, fx.choice([0.5, 1.0, 1.4]), fx.choice(cols), g=0.12))
        self.wait(22 if big else 16, spray)
        self.wait(6)
        if not hit:
            for _ in range(10):
                self.parts.append(Particle(tx - att.dir * fx.uniform(6, 14), ty + 12, fx.uniform(-0.6, 0.6),
                                           fx.uniform(-1.2, -0.4), 10, 0.5, fx.choice(cols), g=0.15))
            return
        tgt.flash, self.shake = 14, 8
        self.land(tgt)
        self.burst(tgt.centre, cols, 40 if big else 28, speed=2.2, g=0.15, life=(8, 18), r=(0.5, 1.0, 1.3))

    def anim_dash(self, att, tgt, hit, cols):
        fx = self.fx
        reach = (-24, 22) if att.far else (30, -17)

        def go(t):
            att.dx, att.dy = reach[0] * t, reach[1] * t
            cx, cy = att.centre
            for _ in range(4):
                self.parts.append(Particle(cx + att.dx + fx.uniform(-6, 6), cy + att.dy + fx.uniform(-4, 6),
                                           fx.uniform(-0.3, 0.3), fx.uniform(-0.9, -0.2),
                                           int(fx.uniform(8, 14)), fx.choice([0.5, 1.0, 1.4]), fx.choice(cols)))
        self.wait(4, lambda i: setattr(att, "dx", -att.dir * [1, 2, 1, 0][i]))
        self.wait(9, lambda i: go(ease(i / 8)))
        if hit:
            tgt.flash, self.shake = 12, 6
            self.land(tgt)
            self.burst(tgt.centre, cols, 26, speed=1.8, g=0.05, r=(0.5, 1.0, 1.3))
        self.wait(3)
        self.wait(10, lambda i: go(1 - ease(i / 9)))
        att.dx = att.dy = 0

    def anim_strike(self, att, tgt, hit, cols):
        reach = (-12, 9) if att.far else (10, -6)
        for t in (0.25, 0.6, 0.9, 1.0):
            att.dx, att.dy = reach[0] * t, reach[1] * t
            self.ui.frame(self.draw(), self.rows)
        if hit:
            tgt.flash, self.shake = 10, 5
            self.land(tgt)
            cx, cy = tgt.centre
            for k in range(3):                 # three claw-mark streaks
                for j in range(9):
                    self.parts.append(Particle(cx - 8 + k * 5 + j * 1.3, cy - 8 + j * 1.6, 0, 0,
                                               9 + j // 3, 0.5, cols[0] if j % 3 else cols[-1]))
        self.wait(3)
        for t in (0.75, 0.45, 0.2, 0.0):
            att.dx, att.dy = reach[0] * t, reach[1] * t
            self.ui.frame(self.draw(), self.rows)
        self.wait(6)

    def anim_guard(self, side, cols):
        fx = self.fx
        cx, cy = side.centre

        def ring(i):
            if i < 14:
                for _ in range(3):
                    a = fx.uniform(0, math.tau)
                    r = fx.uniform(12, 18) * (0.8 if side.far else 1.0)
                    self.parts.append(Particle(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8, 0,
                                               fx.uniform(-0.35, -0.1), int(fx.uniform(18, 30)),
                                               fx.choice([1.0, 1.3]), fx.choice(cols)))
        self.wait(26, ring)

    def anim_rise(self, side, cols, flash=False, frames=26):
        fx = self.fx
        cx, cy = side.centre

        def rise(i):
            for _ in range(3):
                self.parts.append(Particle(cx + fx.uniform(-13, 13), cy + fx.uniform(-2, 14),
                                           fx.uniform(-0.2, 0.2), fx.uniform(-1.2, -0.4),
                                           int(fx.uniform(10, 18)), fx.choice([0.5, 1.0]), fx.choice(cols)))
            if flash and i == 8:
                side.flash = 6
        self.wait(frames, rise)

    def anim_cloud(self, att, tgt, cols):
        fx = self.fx
        sx, sy = att.centre
        tx, ty = tgt.centre

        def puff(i):
            if i < 16:
                for _ in range(3):
                    self.parts.append(Particle(sx + fx.uniform(-4, 4), sy + fx.uniform(-3, 3),
                                               (tx - sx) / 12 + fx.uniform(-0.3, 0.3), (ty - sy) / 12 + fx.uniform(-0.3, 0.3),
                                               int(fx.uniform(26, 36)), fx.choice([1.4, 1.9, 2.3]), fx.choice(cols), drag=0.92))
        self.wait(30, puff)

    # =====================================================================
    # Choosing what to do
    # =====================================================================
    def describe(self, mon, move, foe):
        el = mon.move_element(move)
        left = "" if not move.max_pp else "  %d left." % mon.pp[move.key]
        if move.kind == "attack":
            first = " Strikes first." if move.priority > 0 else ""
            if el is None:
                return "Plain attack, power %d. Never misses.%s" % (move.power, first)
            word = R.effect_word(R.mult(el, foe.element))
            miss = " Often misses." if move.acc < 0.8 else ""
            return "%s attack, power %d. %s against %s.%s%s%s" % (
                R.el_name(el), move.power, word.capitalize(), foe.name, first, miss, left)
        if move.kind == "guard":
            return "Goes first. Halves the damage taken this turn.%s" % left
        if move.kind == "heal":
            return "Recovers %d%% of its health.%s" % (round(move.heal * 100), left)
        if move.kind == "boost":
            return "Powers up: its next attack hits half again as hard.%s" % left
        return "Lowers the foe's accuracy, so its attacks miss more often.%s" % left

    def choose_action(self, controller=None):
        """Returns ("move", Move), ("switch", Mon), ("item", key), ("reach",) or ("run",)."""
        p, e = self.player.mon, self.enemy.mon
        while True:
            cells, acts = [], []
            for m in p.moves:
                el = p.move_element(m)
                ok = p.can_use(m)
                uses = ("%d/%d" % (p.pp[m.key], m.max_pp)) if m.max_pp else ""
                cells.append([(WHITE if ok else DIM, m.name.ljust(14)),
                              (el_colour(el) if (el and ok) else (GREY if ok else DIM), (R.el_name(el) if el else "Plain").ljust(10)),
                              (GREY if ok else DIM, uses.ljust(6))])
                acts.append(("move", m))
            rows = [cells[i:i + 2] for i in range(0, len(cells), 2)]
            extra, extra_acts = [], []
            if len(R.living(self.team)) > 1:
                extra.append([(WHITE, "TEAM")])
                extra_acts.append(("team",))
            if self.bag is not None and any(self.bag.get(k, 0) for k in ("remedy", "tonic", "charm")):
                extra.append([(WHITE, "SATCHEL")])
                extra_acts.append(("satchel",))
            if self.can_call:
                extra.append([(WHITE, "COMPANION")])
                extra_acts.append(("call",))
            if self.wild:
                extra.append([(DIM if self.lure_problem(e) else WHITE, "OFFER A LURE")])
                extra_acts.append(("lure",))
                extra.append([(WHITE, "RUN")])
                extra_acts.append(("run",))
            if extra:
                rows.append(extra)
            n_move_rows = len(rows) - (1 if extra else 0)

            def act_at(r, c):
                return acts[r * 2 + c] if r < n_move_rows else extra_acts[c]

            def desc(r, c):
                a = act_at(r, c)
                if a[0] == "move":
                    return [(GREY if p.can_use(a[1]) else DIM, "  " + self.describe(p, a[1], e))]
                text = {"team": "Swap in another creature. It uses your turn.",
                        "satchel": "Use something from your satchel. It uses your turn.",
                        "call": "Hand the fight to someone else in your party. It uses your turn.",
                        "run": "Slip away from this fight.",
                        "lure": self.lure_problem(e) or
                        "Hold out a lure. The weaker it is, and the tastier the lure, the likelier it joins."}[a[0]]
                return [(GREY, "  " + text)]

            def blocked(r, c):
                a = act_at(r, c)
                if a[0] == "move" and not p.can_use(a[1]):
                    return "%s has no uses left!" % a[1].name
                if a[0] == "lure":
                    return self.lure_problem(e)
                return None

            start = self.cursor.get(id(p), (0, 0))
            if controller:
                pick = R.choose_ai(p, e, self.rng, careful=True)
                i = p.moves.index(pick)
                start = (i // 2, i % 2)
                head = [(controller[1], "  %s: " % controller[0]),
                        (WHITE, "I think I'll go with %s. What do you think?" % pick.name)]
            else:
                head = [(GREY, "  What will "), (el_colour(p.element), p.name), (GREY, " do?")]
                if p.acc_stage < 0:
                    head.append((RED, "     Its accuracy is down %d%%." % round((1 - 0.75 ** -p.acc_stage) * 100)))
            r, c = self.ui.grid_menu(self.draw, head, rows, desc=desc, start=start, blocked=blocked,
                                     tag=("action", self, act_at, [len(row) for row in rows]))
            self.cursor[id(p)] = (r, c)
            a = act_at(r, c)
            if a[0] == "team":
                mon = self.choose_teammate(forced=False)
                if mon:
                    return ("switch", mon)
            elif a[0] == "satchel":
                key = self.choose_item()
                if key:
                    return ("item", key)
            elif a[0] == "lure":
                key = self.choose_lure(e)
                if key:
                    return ("lure", key)
            else:
                return a

    # ----- befriending ----------------------------------------------------
    def keeper(self, wild):
        """Who in your party could take this wild creature in: the trainer of its nature."""
        return next((m for m in (self.party or []) if m.element == wild.element), None)

    def lure_problem(self, wild):
        """Why a lure can't be offered right now (None if it can)."""
        el = R.el_name(wild.element)
        who = self.keeper(wild)
        if who is None:
            return "It won't come near. Only a %smaster could win its trust." % el
        if len(who.team) >= R.TEAM_MAX:
            return "%s already %s %d creatures. Any more and they'd turn on each other." % (
                "You" if who.is_hero else who.name, "keep" if who.is_hero else "keeps", R.TEAM_MAX)
        if not R.lures_for(wild.element, self.bag or {}):
            return "You've no %s lure to offer. They're sold where %s creatures live." % (el, el)
        return None

    def choose_lure(self, wild):
        keys = R.lures_for(wild.element, self.bag)
        if len(keys) == 1:
            return keys[0]
        opts = [[(WHITE, R.ITEMS[k]["name"].ljust(20)), (GREY, "x%d" % self.bag[k])] for k in keys] + [[(GREY, "Back")]]

        def desc(i):
            if i >= len(keys):
                return [(GREY, "  Go back.")]
            odds = R.bond_chance(wild, R.LURES[keys[i]][2])
            word = "A long shot" if odds < 0.25 else "It might work" if odds < 0.5 else \
                "A fair chance" if odds < 0.75 else "It looks ready"
            return [(GREY, "  %s, as weak as it is now." % word)]
        i = self.ui.menu(self.draw, [(GREY, "  Which lure?")], opts, cols=2, desc=desc, tag=("lure", keys))
        return keys[i] if i < len(keys) else None

    def team_cells(self, m):
        ok = m.alive
        return [(WHITE if ok else DIM, m.name.ljust(11)), (GREY if ok else DIM, ("L%d" % m.level).ljust(5)),
                ((120, 220, 130) if ok else DIM, ("%d/%d" % (m.hp, m.max_hp) if ok else "fainted").ljust(9))]

    def choose_teammate(self, forced, stay=False):
        """Pick a creature from your team. Returns it, or None for "back".
        stay: the one already out there can be chosen too (to leave things as they are)."""
        team = self.team
        e = self.enemy.mon
        opts = [self.team_cells(m) for m in team]
        if not forced:
            opts.append([(GREY, "Back")])

        def blocked(i):
            if i >= len(team):
                return None
            if not team[i].alive:
                return "%s has fainted." % team[i].name
            if team[i] is self.player.mon and self.player.on and not stay:
                return "%s is already out there." % team[i].name
            return None

        def desc(i):
            if i >= len(team):
                return [(GREY, "  Go back.")]
            m = team[i]
            return [(GREY, "  %s.  Knows: %s" % (R.el_name(m.element), ", ".join(mv.name.title() for mv in m.moves)))]
        head = [(GREY, "  Who goes in against "), (el_colour(e.element), e.name), (GREY, "?")]
        i = self.ui.menu(self.draw, head, opts, cols=2, desc=desc, blocked=blocked,
                         tag=("teammate", team, self, forced))
        return team[i] if i < len(team) else None

    def choose_item(self):
        bag = self.bag
        keys = [k for k in ("remedy", "tonic", "charm") if bag.get(k, 0)]
        p, e = self.player.mon, self.enemy.mon
        opts = [[(WHITE, R.ITEMS[k]["name"].ljust(10)), (GREY, "x%d" % bag[k])] for k in keys] + [[(GREY, "Back")]]

        def blocked(i):
            if i >= len(keys):
                return None
            k = keys[i]
            if k == "remedy" and p.hp >= p.max_hp:
                return "%s is already at full health." % p.name
            if k == "tonic" and all(p.pp[m.key] >= m.max_pp for m in p.moves):
                return "%s's moves are all fresh." % p.name
            if k == "charm" and p.boosted:
                return "%s is already powered up." % p.name
            return None
        i = self.ui.menu(self.draw, [(GREY, "  Your satchel")], opts, cols=2, blocked=blocked,
                         desc=lambda i: [(GREY, "  " + (R.ITEMS[keys[i]]["text"] if i < len(keys) else "Go back."))],
                         tag=("item", keys, self))
        return keys[i] if i < len(keys) else None

    # =====================================================================
    # Turns
    # =====================================================================
    def act(self, res):
        mv, user, target = res["move"], res["user"], res["target"]
        mine = user is self.player.mon
        att = self.player if mine else self.enemy
        tgt = self.enemy if mine else self.player
        cols = sparks(res["element"])
        self.say("%s used %s!" % (user.name, mv.name), hold=4)
        if mv.kind == "attack":
            if mv.anim == "stream":
                self.anim_stream(att, tgt, res["hit"], cols, big=res["crit"] or mv.big)
            elif mv.anim == "dash":
                self.anim_dash(att, tgt, res["hit"], cols)
            else:
                self.anim_strike(att, tgt, res["hit"], cols)
            if not res["hit"]:
                if mine:
                    self.stats["misses"] += 1
                self.say("But it missed!")
                return
            self.land(tgt)
            self.wait(16)
            if res["boosted"]:
                self.say("The power-up lands!", hold=10)
            if res["crit"]:
                self.say("A critical hit!", hold=10)
            m = res["mult"]
            if res["element"] and m != 1.0:
                word = R.effect_word(m)
                tail = "... it barely hurt." if m <= 0.5 else ("!" if m >= 2 else ".")
                self.say("%s is %s against %s%s" % (R.el_name(res["element"]), word, R.el_name(target.element), tail))
            if res["guarded"]:
                self.say("%s's guard softened the blow!" % target.name)
            if mine:
                key = "elem" if res["element"] else "plain"
                self.stats[key + "_hits"] += 1
                self.stats["finisher"] = key
        elif mv.kind == "guard":
            if mine:
                self.stats["guards"] += 1
            self.anim_guard(att, cols)
            self.say("%s braces itself!" % user.name)
        elif mv.kind == "heal":
            self.anim_rise(att, HEAL_SPARKS)
            self.land(att)
            self.wait(10)
            self.say("%s recovered %d HP!" % (user.name, res["heal"]) if res["heal"]
                     else "But %s is already at full health!" % user.name)
        elif mv.kind == "boost":
            self.anim_rise(att, cols, flash=True)
            self.say("%s can't power up any further!" % user.name if res["no_effect"]
                     else "%s is powering up! Its next attack will hit harder." % user.name)
        elif mv.kind == "hinder":
            self.anim_cloud(att, tgt, mv.tint or cols)
            self.say("%s's accuracy can't fall any lower!" % target.name if res["no_effect"]
                     else "%s gets in %s's eyes! Its accuracy fell!" % (mv.what or "It", target.name))

    def give_xp(self, beaten):
        """Experience for a beaten creature: to each of yours that faced it and is still standing."""
        gain = R.xp_for(beaten, trainer=not self.wild)
        for m in [m for m in self.fought if m.alive]:
            for kind, what in m.gain_xp(gain):
                if kind == "level":
                    if m is self.player.mon:
                        self.land(self.player)
                        self.burst(PLAYER_C, PLAIN_SPARKS, 20)
                    self.say("%s grew to level %d!" % (m.name, what), hold=12)
                else:
                    self.say("%s learned %s!" % (m.name, what.name), hold=14)

    def enter(self, mon, text):
        """Send one of yours in, and note that it has faced the foe now out."""
        self.send_player(mon, text)
        if mon not in self.fought:
            self.fought.append(mon)

    def fight(self, team, foes, controller=None, foe_owner=None, wild=False, bag=None, party=None,
              xp=False, stop_on_faint=False, can_call=False, foe_first=False, pick_fresh=False):
        """Fight `foes` with `team` until one side has nobody left.

        controller     None for your own team; an ally's (NAME, colour) when
                       they fight and you advise
        foe_owner      the other trainer's name (None for a wild creature)
        party          everyone travelling with you (decides who a wild creature could join)
        stop_on_faint  hand back as soon as one of yours faints, so someone else can be chosen
        can_call       offer "COMPANION": hand the fight to another trainer
        foe_first      the creature you send in takes a blow before it can act
                       (it came in for someone else mid-fight: the swap used your turn)
        pick_fresh     when the foe is newly out and one of yours is still standing there,
                       ask which of yours should meet it (changing costs nothing)
        Returns "win", "lose", "ran", "bonded", "fainted" or "call".
        """
        self.team, self.foes, self.wild, self.bag, self.party = team, foes, wild, bag, party
        self.can_call = can_call and any(m.standing for m in (party or []) if m.team is not team)
        go = "Go, %s!" if controller is None else controller[0].title() + " sends in %s!"
        new_foe = False
        if not (self.enemy.on and self.enemy.mon in foes and self.enemy.mon.alive):
            nxt = R.living(foes)[0]
            self.fought = []
            new_foe = True
            self.send_enemy(nxt, ("A wild %s appears!" % nxt.name) if wild
                            else "%s sends out %s!" % (foe_owner, nxt.name))
        if not (self.player.on and self.player.mon in team and self.player.mon.alive):
            if self.player.on:
                self.recall_player("%s, come back!" % self.player.mon.name)
            first = R.living(team)[0]
            if stop_on_faint and len(R.living(team)) > 1:
                first = self.choose_teammate(forced=True)
            self.enter(first, go % first.name)
            if foe_first:
                p, e = self.player.mon, self.enemy.mon
                self.act(R.use_move(e, p, R.choose_ai(e, p, self.rng), self.rng, self.weather))
                e.guard = False
                if not p.alive:
                    self.stats["fainted"] += 1
                    self.faint(self.player)
                    self.say("%s can't battle any more!" % p.name)
                    return "fainted" if R.living(team) else "lose"
        elif pick_fresh and new_foe and len(R.living(team)) > 1:
            first = self.choose_teammate(forced=True, stay=True)
            if first is not self.player.mon:
                self.recall_player("%s, come back!" % self.player.mon.name)
                self.enter(first, go % first.name)
        if self.player.mon not in self.fought:
            self.fought.append(self.player.mon)
        while True:
            p, e = self.player.mon, self.enemy.mon
            self.stats["turns"] += 1
            action = self.choose_action(controller)
            em = R.choose_ai(e, p, self.rng)
            order = [(e, em, p)]
            if action[0] == "run":
                self.say("You slip away.", hold=10)
                return "ran"
            if action[0] == "call":
                return "call"
            if action[0] == "move":
                order = R.turn_order(p, action[1], e, em)
            elif action[0] == "switch":
                self.recall_player("%s, come back!" % p.name)
                self.enter(action[1], go % action[1].name)
                p, e = self.player.mon, self.enemy.mon
                order = [(e, em, p)]
            elif action[0] == "item":
                key = action[1]
                self.bag[key] -= 1
                msg = R.use_item(key, p)
                self.anim_rise(self.player, sparks(p.element) if key == "charm" else HEAL_SPARKS, flash=key == "charm")
                self.land(self.player)
                self.say(msg or "Nothing happened.")
            elif action[0] == "lure":
                key = action[1]
                who = self.keeper(e)
                self.bag[key] -= 1
                self.say("%s out a lure to %s..." % ("You hold" if who.is_hero else who.name + " holds", e.name), hold=10)
                self.anim_cloud(self.player, self.enemy, BOND_SPARKS)
                self.wait(10)
                if self.rng.random() < R.bond_chance(e, R.LURES[key][2]):
                    self.anim_rise(self.enemy, BOND_SPARKS, flash=True, frames=34)
                    self.say("%s eats from %s hand. It trusts %s!" % (
                        e.name, "your" if who.is_hero else who.name + "'s", "you" if who.is_hero else who.name), wait=True)
                    return "bonded"
                self.say("%s snatches the lure and backs away." % e.name)
            for user, mv, target in order:
                if user.alive and target.alive:
                    self.act(R.use_move(user, target, mv, self.rng, self.weather))
                    self.stats["min_ratio"] = min(self.stats["min_ratio"], p.ratio)
            p.guard = e.guard = False
            if not e.alive:
                self.faint(self.enemy)
                self.say("%s can't battle any more!" % e.name)
                if xp:
                    self.give_xp(e)
                left = R.living(foes)
                if not left:
                    return "win"
                self.fought = [p] if p.alive else []
                self.send_enemy(left[0], "%s sends out %s!" % (foe_owner, left[0].name))
            if not p.alive:
                self.stats["fainted"] += 1
                self.faint(self.player)
                self.say("%s can't battle any more!" % p.name)
                if not R.living(team):
                    return "lose"
                if stop_on_faint:
                    return "fainted"
                nxt = self.choose_teammate(forced=True)
                self.enter(nxt, go % nxt.name)
