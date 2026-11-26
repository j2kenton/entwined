"""Entwined battle rules: creatures, moves, the element wheel, damage, AI.

Pure logic, no drawing, so battles can be simulated for balancing.
"""
import random

WHEEL = ["water", "fire", "nature", "air", "earth", "lightning"]

# gap on the wheel (attacker -> defender) -> damage multiplier
GAP_MULT = {0: 1.0, 1: 2.0, 2: 1.25, 3: 1.0, 4: 0.8, 5: 0.5}

DAMAGE_K = 0.3      # global damage scale (tuned by simulation)


def element_mult(att, dfn):
    if att is None or dfn is None:
        return 1.0
    gap = (WHEEL.index(dfn) - WHEEL.index(att)) % 6
    return GAP_MULT[gap]


class Move:
    def __init__(self, key, name, element, kind, power=0, acc=1.0, pp=10,
                 crit=1 / 16, priority=0, desc=""):
        self.key, self.name, self.element, self.kind = key, name, element, kind
        self.power, self.acc, self.max_pp, self.crit = power, acc, pp, crit
        self.priority, self.desc = priority, desc


class Mon:
    def __init__(self, name, element, hp, atk, df, spd, moves, level):
        self.name, self.element, self.level = name, element, level
        self.max_hp, self.atk, self.df, self.spd = hp, atk, df, spd
        self.moves = moves
        self.reset()

    def reset(self):
        self.hp = self.max_hp
        self.pp = {m.key: m.max_pp for m in self.moves}
        self.acc_stage = 0      # 0, -1, -2 (smoke)
        self.kindled = False
        self.guard = False

    @property
    def ratio(self):
        return self.hp / self.max_hp


def ripplefin():
    return Mon("RIPPLEFIN", "water", hp=52, atk=14, df=12, spd=14, level=14, moves=[
        Move("tidal", "TIDAL BURST", "water", "attack", power=40, acc=0.9, pp=6,
             desc="Water attack, power 40. Strong against Fire."),
        Move("splash", "SPLASH FIN", None, "attack", power=30, acc=1.0, pp=15, crit=0.25,
             desc="Plain attack, power 30. Never misses, even through smoke. Often a critical hit."),
        Move("guard", "BUBBLE GUARD", "water", "guard", pp=5, priority=1,
             desc="Goes first. Halves the damage you take this turn."),
        Move("rest", "REST", None, "heal", pp=2,
             desc="Recover 22 HP. Only twice per battle."),
    ])


def emberkit():
    return Mon("EMBERKIT", "fire", hp=64, atk=16, df=12, spd=17, level=16, moves=[
        Move("dash", "FLAME DASH", "fire", "attack", power=45, acc=0.95, pp=10),
        Move("claw", "EMBER CLAW", None, "attack", power=35, acc=0.95, pp=15),
        Move("kindle", "KINDLE", "fire", "kindle", pp=5),
        Move("smoke", "SMOKESCREEN", "fire", "smoke", pp=5),
    ])


def use_move(user, target, move, rng):
    """Apply a move. Returns a dict describing what happened."""
    user.pp[move.key] -= 1
    res = {"move": move, "user": user, "target": target, "hit": True,
           "dmg": 0, "mult": 1.0, "crit": False, "kindled": False,
           "guarded": False, "heal": 0, "no_effect": False}
    if move.kind == "attack":
        # perfect-accuracy moves cut straight through smoke
        acc = 1.0 if move.acc >= 1.0 else move.acc * (0.75 ** -user.acc_stage)
        if rng.random() > acc:
            res["hit"] = False
            return res
        mult = element_mult(move.element, target.element)
        crit = rng.random() < move.crit
        dmg = move.power * user.atk / target.df * DAMAGE_K * mult
        dmg *= rng.uniform(0.85, 1.0)
        if crit:
            dmg *= 1.5
        if user.kindled:
            dmg *= 1.5
            user.kindled = False
            res["kindled"] = True
        if target.guard:
            dmg *= 0.5
            res["guarded"] = True
        dmg = max(1, int(round(dmg)))
        dmg = min(dmg, target.hp)
        target.hp -= dmg
        res.update(dmg=dmg, mult=mult, crit=crit)
    elif move.kind == "guard":
        user.guard = True
    elif move.kind == "heal":
        heal = min(22, user.max_hp - user.hp)
        user.hp += heal
        res["heal"] = heal
    elif move.kind == "kindle":
        if user.kindled:
            res["no_effect"] = True
        user.kindled = True
    elif move.kind == "smoke":
        if target.acc_stage <= -2:
            res["no_effect"] = True
        else:
            target.acc_stage -= 1
    return res


def kael_ai(me, foe, rng):
    """Kael: proud of his fire, but not stupid."""
    m = {mv.key: mv for mv in me.moves}
    if not me.kindled and me.pp["kindle"] and rng.random() < 0.3:
        return m["kindle"]
    if foe.acc_stage > -1 and me.pp["smoke"] and rng.random() < 0.22:
        return m["smoke"]
    if rng.random() < 0.7 and me.pp["claw"]:
        return m["claw"]
    return m["dash"]


def turn_order(p, pm, e, em):
    if pm.priority != em.priority:
        return [(p, pm, e), (e, em, p)] if pm.priority > em.priority else [(e, em, p), (p, pm, e)]
    return [(p, pm, e), (e, em, p)] if p.spd >= e.spd else [(e, em, p), (p, pm, e)]


# ----- balancing -------------------------------------------------------
def simulate(strategy, n=20000, seed=1):
    rng = random.Random(seed)
    wins, hp_left, turns_total = 0, 0.0, 0
    for _ in range(n):
        p, e = ripplefin(), emberkit()
        turns = 0
        while p.hp > 0 and e.hp > 0 and turns < 40:
            turns += 1
            pm = strategy(p, e)
            em = kael_ai(e, p, rng)
            for user, mv, target in turn_order(p, pm, e, em):
                if user.hp <= 0 or target.hp <= 0:
                    continue
                use_move(user, target, mv, rng)
            p.guard = False
        if e.hp <= 0 and p.hp > 0:
            wins += 1
            hp_left += p.ratio
        turns_total += turns
    return wins / n, (hp_left / max(1, wins)), turns_total / n


def naive(p, e):
    m = {mv.key: mv for mv in p.moves}
    return m["tidal"] if p.pp["tidal"] else m["splash"]


def mashing_splash(p, e):
    return p.moves[1]


def sensible(p, e):
    m = {mv.key: mv for mv in p.moves}
    if p.ratio < 0.35 and p.pp["rest"]:
        return m["rest"]
    if p.acc_stage <= -2:
        return m["splash"]
    return m["tidal"] if p.pp["tidal"] else m["splash"]


if __name__ == "__main__":
    for name, strat in (("always Tidal Burst", naive), ("only Splash Fin", mashing_splash),
                        ("sensible (heals, adapts to smoke)", sensible)):
        w, hp, t = simulate(strat)
        print("%-36s win %5.1f%%   HP left when winning %4.0f%%   avg turns %.1f"
              % (name, w * 100, hp * 100, t))
