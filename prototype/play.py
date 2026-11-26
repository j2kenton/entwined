"""Entwined: a playable battle against Kael, Lord of Ember Peaks.

    python play.py

Arrow keys (or WASD) choose, Enter (or Space) confirms, Esc quits.
Enter or Down moves the text along (Down matches the flashing arrow).
Needs a terminal at least 100 wide and 36 tall; if it's smaller, the game
says how to fix it and starts as soon as the window fits.
"""
import math
import os
import random
import sys
import time
from collections import deque

import battle as B
from battle import RNG, FIRE, WATER, Particle, sparkle, ease
from rules import emberkit, kael_ai, ripplefin, turn_order, use_move

# ----- colours for the text box ------------------------------------------
GREY = (170, 170, 182)
DIM = (95, 95, 105)
WHITE = (240, 240, 245)
BLUE = (120, 200, 255)
GOLD = (255, 220, 120)
ORANGE = (255, 150, 60)
RED = (255, 110, 100)
KAEL = ("KAEL", ORANGE)
ELEMENT_LABEL = {"water": ("Water", (90, 170, 255)), "fire": ("Fire", ORANGE), None: ("Plain", GREY)}


# =========================================================================
# Keyboard
# =========================================================================
class Keys:
    """Non-blocking key reader for Windows (msvcrt) and Mac/Linux (termios)."""

    def __init__(self):
        self.win = os.name == "nt"
        if not self.win:
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)

    def close(self):
        if not self.win:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    def poll(self):
        keys = []
        if self.win:
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    keys.append({"H": "up", "P": "down", "K": "left", "M": "right"}.get(msvcrt.getwch()))
                else:
                    keys.append(self._plain(ch))
        else:
            import select
            while select.select([sys.stdin], [], [], 0)[0]:
                data = os.read(self.fd, 64).decode(errors="ignore")
                for seq, name in (("\x1b[A", "up"), ("\x1b[B", "down"), ("\x1b[D", "left"), ("\x1b[C", "right")):
                    while seq in data:
                        keys.append(name)
                        data = data.replace(seq, "", 1)
                keys += [self._plain(ch) for ch in data]
        return [k for k in keys if k]

    @staticmethod
    def _plain(ch):
        return {"\r": "enter", "\n": "enter", " ": "enter", "\x1b": "quit", "w": "up", "s": "down", "a": "left", "d": "right",
                "W": "up", "S": "down", "A": "left", "D": "right"}.get(ch)


class Game(B.Player):
    """The clip engine, but listening to the keyboard."""

    def __init__(self, st, out, keys):
        super().__init__(st, out)
        self.keys = keys
        self.pending = deque()

    def check_keys(self):
        for k in self.keys.poll():
            if k == "quit":
                raise B.Stop()
            self.pending.append(k)

    def take(self):
        ks = list(self.pending)
        self.pending.clear()
        return ks

    def advanced(self):
        """Enter or Down (the flashing arrow) moves the text along."""
        return any(k in ("enter", "down") for k in self.take())

    def say(self, text, speaker=None, wait=False, hold=16, speed=2):
        st = self.st
        st.rows = None
        st.speaker, st.text, st.shown = speaker, text, 0
        self.take()
        while st.shown < len(text):
            st.shown = min(len(text), st.shown + speed)
            self.step()
            if self.advanced():
                st.shown = len(text)
        if wait:
            self.wait_enter()
        else:
            for _ in range(hold):
                self.step()
                if self.advanced():
                    break

    def wait_enter(self):
        self.take()
        while True:
            self.step()
            if self.advanced():
                return


# =========================================================================
# Move animations
# =========================================================================
def splash_fin(g, hit):
    st = g.st
    home = B.PLAYER_HOME[0]
    for dx in (2, 5, 8, 10):
        st.px_ = home + dx
        for _ in range(3):
            st.parts.append(Particle(44 + dx, 28 + RNG.uniform(-3, 3), 4.5, -0.9 + RNG.uniform(-0.3, 0.3),
                                     7, RNG.choice([0.5, 1.0]), RNG.choice(WATER)))
        g.step()
    if hit:
        st.e_flash = 10
        st.shake = 4
        for _ in range(16):
            a = RNG.uniform(0, math.tau)
            st.parts.append(Particle(76, 18, math.cos(a) * 1.4, math.sin(a) * 1.4, 10, 0.5,
                                     RNG.choice(WATER + [(255, 255, 255)])))
    for dx in (8, 5, 2, 0):
        st.px_ = home + dx
        g.step()
    g.wait(8)


def bubble_guard(g):
    st = g.st
    for i in range(26):
        if i < 14:
            for _ in range(3):
                a = RNG.uniform(0, math.tau)
                r = RNG.uniform(14, 20)
                st.parts.append(Particle(24 + math.cos(a) * r, 36 + math.sin(a) * r * 0.8,
                                         0, RNG.uniform(-0.35, -0.1), int(RNG.uniform(18, 30)),
                                         RNG.choice([1.0, 1.3]),
                                         RNG.choice([(170, 225, 255), (230, 248, 255), (110, 190, 250)])))
        g.step()


def rest(g):
    st = g.st
    for i in range(30):
        if i % 6 == 0:
            for _ in range(10):
                st.parts.append(Particle(RNG.uniform(8, 42), RNG.uniform(30, 52), 0,
                                         RNG.uniform(-0.8, -0.3), int(RNG.uniform(12, 22)), 0.5,
                                         RNG.choice([(150, 255, 170), (255, 255, 255), (110, 220, 140)])))
        g.step()


def ember_claw(g, hit):
    st = g.st
    hx, hy = B.ENEMY_HOME
    for t in (0.25, 0.55, 0.85, 1.0):
        st.ex, st.ey = hx - 14 * t, hy + 10 * t
        g.step()
    if hit:
        st.p_flash = 10
        st.shake = 5
        for k in range(3):
            x0, y0 = 16 + k * 5, 24
            for j in range(9):
                st.parts.append(Particle(x0 + j * 1.3, y0 + j * 1.6, 0, 0, 9 + j // 3, 0.5,
                                         (255, 250, 220) if j % 3 else ORANGE))
    g.wait(3)
    for t in (0.75, 0.45, 0.2, 0.0):
        st.ex, st.ey = hx - 14 * t, hy + 10 * t
        g.step()
    g.wait(6)


def kindle(g):
    st = g.st
    for i in range(24):
        for _ in range(4):
            st.parts.append(Particle(76 + RNG.uniform(-12, 12), 24 + RNG.uniform(-6, 6),
                                     RNG.uniform(-0.2, 0.2), RNG.uniform(-1.3, -0.5),
                                     int(RNG.uniform(8, 16)), RNG.choice([0.5, 1.0]), RNG.choice(FIRE)))
        if i == 8:
            st.e_flash = 6
        g.step()


def smokescreen(g):
    st = g.st
    for i in range(28):
        if i < 16:
            for _ in range(3):
                life = int(RNG.uniform(26, 36))
                st.parts.append(Particle(70 + RNG.uniform(-4, 4), 20 + RNG.uniform(-3, 3),
                                         (24 - 70) / 16 + RNG.uniform(-0.3, 0.3),
                                         (36 - 20) / 16 + RNG.uniform(-0.3, 0.3),
                                         life, RNG.choice([1.4, 1.9, 2.3]),
                                         RNG.choice([(120, 112, 120), (90, 84, 92), (150, 142, 150)])))
        for p in st.parts:      # smoke slows down as it arrives
            if p.r >= 1.4:
                p.vx *= 0.9
                p.vy *= 0.9
        g.step()


def faint_enemy(g):
    st = g.st
    st.e_flash = 8
    g.wait(8)
    g.wait(26, lambda i: setattr(st, "e_sink", int(ease((i + 1) / 26) * 34)))
    st.enemy_on, st.e_sink = False, 0


def faint_player(g):
    st = g.st
    st.p_flash = 8
    g.wait(8)
    g.wait(24, lambda i: setattr(st, "p_sink", int(ease((i + 1) / 24) * 46)))
    st.player_on, st.p_sink = False, 0


# =========================================================================
# Move menu
# =========================================================================
def menu_rows(st, p, sel, note=None):
    blink = (st.tick // 6) % 2 == 0

    def cell(i):
        m = p.moves[i]
        left = p.pp[m.key]
        name_col = WHITE if left else DIM
        if i == sel:
            name_col = GOLD if left else RED
        label, lcol = ELEMENT_LABEL[m.element]
        cur = "▶ " if (i == sel and blink) else "  "
        return [(GOLD, "   " + cur), (name_col, m.name.ljust(14)), (lcol if left else DIM, label.ljust(7)),
                (GREY if left else DIM, ("%d/%d" % (left, m.max_pp)).ljust(8))]

    head = [(GREY, "  What will "), (BLUE, "RIPPLEFIN"), (GREY, " do?")]
    if p.acc_stage < 0:
        head.append((ORANGE, "      Smoke in its eyes: accuracy down %d%%" %
                     round((1 - 0.75 ** -p.acc_stage) * 100)))
    desc = note or p.moves[sel].desc
    return [head,
            cell(0) + [(GREY, "     ")] + cell(1),
            cell(2) + [(GREY, "     ")] + cell(3),
            [(RED if note else DIM, "  " + desc)]]


def choose_move(g, p, sel):
    st = g.st
    note = None
    g.take()
    while True:
        st.rows = menu_rows(st, p, sel, note)
        g.step()
        for k in g.take():
            note = None
            col, row = sel % 2, sel // 2
            if k in ("left", "right"):
                col = 1 - col
            elif k in ("up", "down"):
                row = 1 - row
            elif k == "enter":
                m = p.moves[sel]
                if p.pp[m.key] > 0:
                    st.rows = None
                    return sel
                note = "%s has no uses left!" % m.name
            sel = row * 2 + col


# =========================================================================
# Battle flow
# =========================================================================
def effect_text(res):
    m = res["mult"]
    el = res["target"].element.capitalize()
    if m >= 2:
        return "It's strong against %s!" % el
    if m > 1:
        return "It's slightly strong against %s." % el
    if m <= 0.5:
        return "It's weak against %s... it barely hurt." % el
    if m < 1:
        return "It's slightly weak against %s." % el
    return None


def act(g, res, p, e, stats):
    st = g.st
    mv, user = res["move"], res["user"]
    mine = user is p
    g.say("%s used %s!" % (user.name, mv.name), hold=4)
    if mv.kind == "attack":
        if mine and mv.key == "tidal":
            B.tidal_burst(g, big=res["crit"], hit=res["hit"])
        elif mine:
            splash_fin(g, res["hit"])
        elif mv.key == "dash":
            B.flame_dash(g, hit=res["hit"])
        else:
            ember_claw(g, res["hit"])
        if not res["hit"]:
            if mine:
                stats["misses"] += 1
            g.say("But it missed!")
            return
        st.e_hp, st.p_hp = e.ratio, p.hp
        g.wait(16)
        if res["kindled"]:
            g.say("The kindled flames roar!", hold=10)
        if res["crit"]:
            stats["crits"] += mine
            g.say("A critical hit!", hold=10)
        txt = effect_text(res)
        if txt:
            g.say(txt)
        if res["guarded"]:
            g.say("The bubbles softened the blow!")
        if mine:
            stats["tidal_hits" if mv.key == "tidal" else "splash_hits"] += 1
            stats["finisher"] = mv.key
    elif mv.kind == "guard":
        stats["guards"] += 1
        bubble_guard(g)
        g.say("RIPPLEFIN is wrapped in a shield of bubbles!")
    elif mv.kind == "heal":
        stats["rests"] += 1
        rest(g)
        st.p_hp = p.hp
        g.wait(10)
        if res["heal"]:
            g.say("RIPPLEFIN rested and recovered %d HP!" % res["heal"])
        else:
            g.say("But RIPPLEFIN is already at full health!")
    elif mv.kind == "kindle":
        kindle(g)
        g.say("EMBERKIT is already blazing!" if res["no_effect"] else
              "EMBERKIT's flames burn hotter! Its next attack will hit harder.")
    elif mv.kind == "smoke":
        smokescreen(g)
        g.say("The smoke can't get any thicker!" if res["no_effect"] else
              "Smoke fills the air! RIPPLEFIN's accuracy fell!")


def kael_comment(stats):
    """The specific half of the Lord's comment: why you won."""
    if stats["min_ratio"] < 0.3:
        return "I had you on the ropes. How are you still standing?"
    if stats["turns"] <= 3:
        return "That was over before I'd even warmed up. I've never lost that fast."
    if stats["guards"] >= 2:
        return "Every time I struck, your bubbles were already there. You read me perfectly."
    if stats["finisher"] == "splash" or stats["splash_hits"] > stats["tidal_hits"]:
        return "You didn't even lean on your water. That was pure skill."
    if stats["misses"] >= 2:
        return "Smoke in your eyes, and you still kept coming."
    return "Your water went straight through my flames. I never stood a chance."


def run_battle(g, first):
    st = g.st
    rng = random.Random()
    p, e = ripplefin(), emberkit()
    stats = dict(turns=0, tidal_hits=0, splash_hits=0, guards=0, rests=0,
                 misses=0, crits=0, min_ratio=1.0, finisher=None)
    st.p_hp_max = p.max_hp
    st.p_hp = st.p_hp_shown = p.hp
    st.e_hp = st.e_hp_shown = 1.0

    # --- intro ---
    st.reveal = 0.0
    g.wait(16, lambda i: setattr(st, "reveal", (i + 1) / 16))
    if first:
        g.say("Kael, Lord of Ember Peaks, blocks the path!")
        g.say("Nobody crosses into my land without a battle. Nobody.", speaker=KAEL, wait=True)
    else:
        g.say("Back for more? Fine. Let's go again.", speaker=KAEL, wait=True)
    g.say("Kael sends out EMBERKIT!", hold=0)
    st.enemy_on, st.e_flash = True, 10
    sparkle(st, 76, 16, FIRE, 30)
    g.wait(18)
    g.say("Go, RIPPLEFIN!", hold=0)
    st.player_on = True
    g.wait(14, lambda i: setattr(st, "px_", -56 + (B.PLAYER_HOME[0] + 56) * ease((i + 1) / 14)))
    sparkle(st, 26, 40, WATER, 24)
    st.panels = True
    g.wait(12)

    # --- turns ---
    sel = 0
    while True:
        stats["turns"] += 1
        sel = choose_move(g, p, sel)
        pm = p.moves[sel]
        em = kael_ai(e, p, rng)
        for user, mv, target in turn_order(p, pm, e, em):
            if user.hp <= 0 or target.hp <= 0:
                continue
            act(g, use_move(user, target, mv, rng), p, e, stats)
            stats["min_ratio"] = min(stats["min_ratio"], p.ratio)
        p.guard = False
        if e.hp <= 0:
            faint_enemy(g)
            g.say("EMBERKIT can't battle any more!")
            g.say(kael_comment(stats), speaker=KAEL, wait=True)
            g.say("You Tidewell folk are calmer than I gave you credit for.", speaker=KAEL, wait=True)
            g.say("...The Citadel? You're going after the Citadel? Then I'm coming with you.",
                  speaker=KAEL, wait=True)
            st.banner = ("KAEL JOINED YOUR PARTY!", (255, 200, 90))
            for _ in range(3):
                sparkle(st, RNG.uniform(20, 80), RNG.uniform(10, 30), FIRE + WATER, 30)
                g.wait(10)
            g.say("You won in %d turns! Kael's comment depends on HOW you win, so try a "
                  "different way. Press Enter to play again, or Esc to quit." % stats["turns"], wait=True)
            return True
        if p.hp <= 0:
            faint_player(g)
            g.say("RIPPLEFIN can't battle any more!")
            g.say("Not today. Come back when you're stronger.", speaker=KAEL, wait=True)
            g.say("Tip: Water beats Fire, and Bubble Guard always goes first. "
                  "Press Enter to try again, or Esc to quit.", wait=True)
            return False


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if os.name == "nt":
        os.system("")
    B.load_assets()
    keys = Keys()
    out = sys.stdout
    out.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    try:
        first = True
        while True:
            st = B.State()
            g = Game(st, out, keys)
            g.wait_for_size()        # shows "make the window bigger" until it fits
            run_battle(g, first)
            first = False
    except (B.Stop, KeyboardInterrupt):
        pass
    finally:
        keys.close()
        out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        out.flush()
    print("Thanks for playing Entwined! Run it again with:  python play.py")


if __name__ == "__main__":
    main()
