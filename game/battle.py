"""The battle scene: two creatures on a backdrop, move menus and animations.

A Battle stays on screen while creatures come and go, so one scene can cover
a Citadel floor (first creature, then the hidden sixth, with allies stepping in).
"""
import math
import random

from . import rules as R
from .art import backdrops, creatures
from .engine.canvas import Canvas, darker, draw_mini, mini_width, mix
from .engine.ui import DIM, GREY, RED, WHITE, message_rows

W, H = backdrops.W, backdrops.H
ENEMY_FOOT = (76, 30.5)
PLAYER_FOOT = (24, 55.5)
ENEMY_C, PLAYER_C = (76, 15), (25, 36)
ENEMY_MOUTH, PLAYER_MOUTH = (66, 18), (40, 29)
PLAIN_SPARKS = [(255, 255, 255), (230, 230, 240), (190, 190, 205), (255, 245, 200)]
HEAL_SPARKS = [(150, 255, 170), (255, 255, 255), (110, 220, 140)]


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
        self.hp_shown = 0.0      # what the health bar shows now
        self.hp_target = 0.0     # what it is moving towards (set when a hit lands)

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
        """Which way this side faces: -1 for the far creature, +1 for the near one."""
        return -1 if self.far else 1


class Battle:
    def __init__(self, ui, backdrop, rng=None):
        self.ui = ui
        self.S = ui.S
        self.bg = backdrops.backdrop(backdrop, self.S)
        self.rng = rng or random.Random()
        self.fx = random.Random(4)           # for particle scatter only
        self.enemy, self.player = Side(True), Side(False)
        self.parts = []
        self.shake = 0
        self.reveal = 1.0
        self.banner = None
        self.panels = False
        self.cursor = {}                     # remembered menu position per creature
        self.reset_stats()

    def reset_stats(self):
        self.stats = dict(turns=0, elem_hits=0, plain_hits=0, guards=0, misses=0,
                          min_ratio=1.0, finisher=None)

    # =====================================================================
    # Drawing
    # =====================================================================
    def set_look(self, side):
        """(Re)build a side's sprites from its creature's current look."""
        mon = side.mon
        other = None
        if mon.variant == "hybrid":
            other = [f for f in mon.forms if f != mon.element][0] if mon.shown_forms > 1 else None
        variant = mon.variant if (mon.variant != "hybrid" or mon.shown_forms > 1) else "shadow"
        frames = creatures.frames(mon.species, variant, other, self.S, 34 if side.far else 44)
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
                target = side.hp_target
                side.hp_shown += (target - side.hp_shown) * 0.14
                if abs(target - side.hp_shown) < 0.004:
                    side.hp_shown = target
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
            bar(13, 10, 36, e.hp_shown)
        if p.on or (p.mon and p.sink):
            col = el_colour(p.mon.element)
            panel(48, 43, 98, 58, col)
            cv.rect(51, 45, 54, 48, col)
            cv.set(52, 46, mix(col, (255, 255, 255), 0.6))
            draw_mini(cv, 57, 45, p.mon.name, (230, 244, 255), shadow=(20, 30, 50))
            draw_mini(cv, 51, 50, "HP", (255, 200, 80))
            bar(59, 51, 36, p.hp_shown)
            txt = "%d/%d" % (round(p.hp_shown * p.mon.max_hp), p.mon.max_hp)
            draw_mini(cv, 96 - mini_width(txt), 54, txt, (220, 230, 240))

    # =====================================================================
    # Small helpers
    # =====================================================================
    def land(self, side):
        """The moment a hit (or a heal) lands: let the health bar catch up."""
        side.hp_target = side.mon.ratio

    def wait(self, n, fn=None):
        for i in range(n):
            if fn:
                fn(i)
            self.ui.frame(self.draw(), self.rows)

    rows = ()        # what the text box shows while an animation plays

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
        self.reveal = 0.0
        self.wait(frames, lambda i: setattr(self, "reveal", (i + 1) / frames))
        self.reveal = 1.0

    def close(self, frames=14):
        self.wait(frames, lambda i: setattr(self, "reveal", 1 - (i + 1) / frames))
        self.reveal = 0.0

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

    def recall_player(self, text=None):
        p = self.player
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
        mon.element = new_element
        mon.species = new_element
        mon.shown_forms = 2
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

    def anim_rise(self, side, cols, flash=False):
        fx = self.fx
        cx, cy = side.centre

        def rise(i):
            for _ in range(3):
                self.parts.append(Particle(cx + fx.uniform(-13, 13), cy + fx.uniform(-2, 14),
                                           fx.uniform(-0.2, 0.2), fx.uniform(-1.2, -0.4),
                                           int(fx.uniform(10, 18)), fx.choice([0.5, 1.0]), fx.choice(cols)))
            if flash and i == 8:
                side.flash = 6
        self.wait(26, rise)

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
    # Turns
    # =====================================================================
    def describe(self, mon, move, foe):
        el = mon.move_element(move)
        left = "" if not move.max_pp else "  %d left." % mon.pp[move.key]
        if move.kind == "attack":
            if el is None:
                return "Plain attack, power %d. Never misses, and often lands a critical hit." % move.power
            word = R.effect_word(R.mult(el, foe.element))
            return "%s attack, power %d. %s against %s (%s).%s" % (
                R.el_name(el), move.power, word.capitalize(), foe.name, R.el_name(foe.element), left)
        if move.kind == "guard":
            return "Goes first. Halves the damage taken this turn.%s" % left
        if move.kind == "heal":
            return "Recovers %d%% of its health.%s" % (round(move.heal * 100), left)
        if move.kind == "boost":
            return "Powers up: its next attack hits half again as hard.%s" % left
        return "Lowers the foe's accuracy, so its attacks miss more often.%s" % left

    def choose_move(self, controller=None):
        """controller: None when it's your own creature; otherwise the ally
        (name, colour) who suggests a move and waits for your say."""
        p, e = self.player.mon, self.enemy.mon
        options = []
        for m in p.moves:
            el = p.move_element(m)
            ok = p.can_use(m)
            label = R.el_name(el) if el else "Plain"
            lcol = el_colour(el) if el else GREY
            uses = ("%d/%d" % (p.pp[m.key], m.max_pp)) if m.max_pp else ""
            options.append([(WHITE if ok else DIM, m.name.ljust(14)),
                            (lcol if ok else DIM, label.ljust(10)), (GREY if ok else DIM, uses.ljust(6))])
        start = self.cursor.get(id(p), 0)
        if controller:
            pick = R.choose_ai(p, e, self.rng, careful=True)
            start = p.moves.index(pick)
            head = [(controller[1], "  %s: " % controller[0]),
                    (WHITE, "I think I'll go with %s. What do you think?" % pick.name)]
        else:
            head = [(GREY, "  What will "), (el_colour(p.element), p.name), (GREY, " do?")]
            if p.acc_stage < 0:
                head.append((RED, "     Its accuracy is down %d%%." % round((1 - 0.75 ** -p.acc_stage) * 100)))
        sel = self.ui.menu(
            self.draw, head, options, cols=2, start=start,
            desc=lambda i: [(DIM if not p.can_use(p.moves[i]) else GREY, "  " + self.describe(p, p.moves[i], e))],
            blocked=lambda i: None if p.can_use(p.moves[i]) else "%s has no uses left!" % p.moves[i].name,
            tag=("move", p, e))
        self.cursor[id(p)] = sel
        return p.moves[sel]

    def act(self, res):
        mv, user, target = res["move"], res["user"], res["target"]
        mine = user is self.player.mon
        att = self.player if mine else self.enemy
        tgt = self.enemy if mine else self.player
        cols = sparks(res["element"])
        self.say("%s used %s!" % (user.name, mv.name), hold=4)
        if mv.kind == "attack":
            anim = {"stream": self.anim_stream, "dash": self.anim_dash, "strike": self.anim_strike}[mv.anim]
            if mv.anim == "stream":
                anim(att, tgt, res["hit"], cols, big=res["crit"])
            else:
                anim(att, tgt, res["hit"], cols)
            if not res["hit"]:
                if mine:
                    self.stats["misses"] += 1
                self.say("But it missed!")
                return
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

    def fight(self, controller=None):
        """Trade turns until one creature faints. Returns "win" or "lose"."""
        p, e = self.player.mon, self.enemy.mon
        while True:
            self.stats["turns"] += 1
            pm = self.choose_move(controller)
            em = R.choose_ai(e, p, self.rng)
            for user, mv, target in R.turn_order(p, pm, e, em):
                if user.alive and target.alive:
                    self.act(R.use_move(user, target, mv, self.rng))
                    self.stats["min_ratio"] = min(self.stats["min_ratio"], p.ratio)
            p.guard = e.guard = False
            if not e.alive:
                self.faint(self.enemy)
                self.say("%s can't battle any more!" % e.name)
                return "win"
            if not p.alive:
                self.faint(self.player)
                self.say("%s can't battle any more!" % p.name)
                return "lose"
