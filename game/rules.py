"""Battle rules: the element chart, creatures, moves, damage and the AI.

Pure logic with no drawing, so whole campaigns can be simulated for balance.
All the numbers come from the JSON files in data/.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load(name):
    with open(os.path.join(DATA_DIR, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


ELEMENTS = load("elements")
CREATURES = load("creatures")
HEROES = load("heroes")
TUNING = load("tuning")

ORDER = ELEMENTS["order"]
_EXC = {(e["attacker"], e["defender"]): e["mult"] for e in ELEMENTS["exceptions"]}
_PATTERN = {int(k): v for k, v in ELEMENTS["pattern"].items()}


def mult(att, dfn):
    """Damage multiplier for an `att`-element attack on a `dfn`-element creature."""
    if att is None or dfn is None:
        return 1.0
    if (att, dfn) in _EXC:
        return _EXC[(att, dfn)]
    if att == dfn:
        return ELEMENTS["same"]
    return _PATTERN[(ORDER.index(dfn) - ORDER.index(att)) % 6]


def effect_word(m):
    if m >= 2:
        return "strong"
    if m > 1:
        return "slightly strong"
    if m <= 0.5:
        return "weak"
    if m < 1:
        return "slightly weak"
    return "even"


def beater_of(element):
    """The element that strongly beats this one (the one before it on the wheel)."""
    return ORDER[(ORDER.index(element) - 1) % 6]


def land_order(hero_element):
    """The other five elements, from the one this hero finds easiest to hardest."""
    others = [e for e in ORDER if e != hero_element]
    return sorted(others, key=lambda o: -(mult(hero_element, o) / mult(o, hero_element)))


def el_name(element):
    return ELEMENTS["names"][element]


# =========================================================================
# Moves and creatures
# =========================================================================
class Move:
    def __init__(self, key, d):
        self.key = key
        self.name = d["name"]
        self.element = d.get("element")
        self.kind = d["kind"]
        self.power = d.get("power", 0)
        self.acc = d.get("acc", 1.0)
        self.max_pp = d.get("pp", 0)          # 0 = unlimited
        self.crit = d.get("crit", 1 / 16)
        self.priority = d.get("priority", 0)
        self.heal = d.get("heal", 0)
        self.anim = d.get("anim", "strike")
        self.tint = [tuple(c) for c in d.get("tint", [])]
        self.what = d.get("what", "")


MOVES = {k: Move(k, d) for k, d in CREATURES["moves"].items()}


class Mon:
    def __init__(self, name, element, hp, atk, df, spd, moves, species, variant="normal",
                 forms=None, power=1.0):
        self.name, self.element = name, element
        self.species = species            # which creature's body to draw
        self.variant = variant            # "normal", "shadow" or "hybrid"
        self.forms = forms                # hybrid: its two elements
        self.shown_forms = 1              # hybrid: how many forms it has revealed
        self.base = (hp, atk, df, spd)
        self.moves = [MOVES[k] for k in moves]
        self.power = power
        self.level = None
        self._apply()
        self.hp = self.max_hp
        self.pp = {m.key: m.max_pp for m in self.moves}
        self.clear_status()

    def _apply(self):
        hp, atk, df, spd = self.base
        self.max_hp = int(round(hp * self.power))
        self.atk = atk * self.power
        self.df, self.spd = df, spd

    def set_power(self, power, keep_ratio=True):
        ratio = self.hp / self.max_hp
        self.power = power
        self._apply()
        self.hp = max(1, int(round(self.max_hp * ratio))) if keep_ratio else self.max_hp

    def clear_status(self):
        self.acc_stage = 0      # 0, -1, -2
        self.boosted = False
        self.guard = False

    def restore(self):
        self.hp = self.max_hp
        self.pp = {m.key: m.max_pp for m in self.moves}
        self.clear_status()

    def snapshot(self):
        return (self.hp, dict(self.pp))

    def load_snapshot(self, snap):
        self.hp, self.pp = snap[0], dict(snap[1])
        self.clear_status()

    @property
    def ratio(self):
        return self.hp / self.max_hp

    @property
    def alive(self):
        return self.hp > 0

    def can_use(self, move):
        return move.max_pp == 0 or self.pp[move.key] > 0

    def move_element(self, move):
        return self.element if move.element == "form" else move.element

    # ----- hybrids --------------------------------------------------------
    def best_form(self, foe_element):
        """The form that does best against a foe: hits hardest, takes least."""
        return max(self.forms, key=lambda f: mult(f, foe_element) / mult(foe_element, f))


def level_power(level):
    return 1.0 + TUNING["growth_per_level"] * (level - TUNING["start_level"])


def make_mon(element, variant="normal", power=1.0):
    sp = CREATURES["species"][element]
    name = sp["shadow"] if variant == "shadow" else sp["name"]
    return Mon(name, element, sp["hp"], sp["atk"], sp["df"], sp["spd"], sp["moves"],
               species=element, variant=variant, power=power)


def make_hybrid(hero_element, power=1.0):
    """A nemesis's bred creature: the hero's own element plus the one that beats it.
    It first appears in the form that beats the hero."""
    h = CREATURES["hybrid"]
    beater = beater_of(hero_element)
    return Mon(h["names"][hero_element], beater, h["hp"], h["atk"], h["df"], h["spd"], h["moves"],
               species=beater, variant="hybrid", forms=[hero_element, beater], power=power)


# =========================================================================
# Using a move
# =========================================================================
def use_move(user, target, move, rng):
    """Apply a move. Returns a dict describing what happened."""
    if move.max_pp:
        user.pp[move.key] -= 1
    res = {"move": move, "user": user, "target": target, "hit": True, "dmg": 0,
           "mult": 1.0, "crit": False, "boosted": False, "guarded": False,
           "heal": 0, "no_effect": False, "element": user.move_element(move)}
    if move.kind == "attack":
        acc = 1.0 if move.acc >= 1.0 else move.acc * (0.75 ** -user.acc_stage)
        if rng.random() > acc:
            res["hit"] = False
            return res
        m = mult(res["element"], target.element)
        crit = rng.random() < move.crit
        dmg = move.power * user.atk / target.df * TUNING["damage_k"] * m
        dmg *= rng.uniform(0.85, 1.0)
        if crit:
            dmg *= 1.5
        if user.boosted:
            dmg *= 1.5
            user.boosted = False
            res["boosted"] = True
        if target.guard:
            dmg *= 0.5
            res["guarded"] = True
        dmg = min(max(1, int(round(dmg))), target.hp)
        target.hp -= dmg
        res.update(dmg=dmg, mult=m, crit=crit)
    elif move.kind == "guard":
        user.guard = True
    elif move.kind == "heal":
        heal = min(int(round(user.max_hp * move.heal)), user.max_hp - user.hp)
        user.hp += heal
        res["heal"] = heal
    elif move.kind == "boost":
        if user.boosted:
            res["no_effect"] = True
        user.boosted = True
    elif move.kind == "hinder":
        if target.acc_stage <= -2:
            res["no_effect"] = True
        else:
            target.acc_stage -= 1
    return res


def expected(user, target, move):
    """Rough expected damage of an attack (for the AI and for hints)."""
    acc = 1.0 if move.acc >= 1.0 else move.acc * (0.75 ** -user.acc_stage)
    return move.power * mult(user.move_element(move), target.element) * acc * (1 + move.crit * 0.5)


def best_attack(user, target):
    attacks = [m for m in user.moves if m.kind == "attack" and user.can_use(m)]
    return max(attacks, key=lambda m: expected(user, target, m))


def choose_ai(me, foe, rng, careful=False):
    """Pick a move. `careful` is the steadier version used for an ally's suggestion
    and for balance simulations; the default has a bit of swagger and mistakes."""
    by_kind = {}
    for m in me.moves:
        if me.can_use(m):
            by_kind.setdefault(m.kind, m)
    best = best_attack(me, foe)
    if "heal" in by_kind and me.ratio < 0.35 and (careful or rng.random() < 0.7):
        return by_kind["heal"]
    if careful:
        return best
    if "boost" in by_kind and not me.boosted and rng.random() < 0.25:
        return by_kind["boost"]
    if "hinder" in by_kind and foe.acc_stage > -1 and rng.random() < 0.2:
        return by_kind["hinder"]
    if "guard" in by_kind and rng.random() < 0.1:
        return by_kind["guard"]
    if rng.random() < 0.82:
        return best
    return rng.choice([m for m in me.moves if m.kind == "attack" and me.can_use(m)])


def turn_order(p, pm, e, em):
    """Who acts first: priority moves, then speed (ties go to the player)."""
    if pm.priority != em.priority:
        first_p = pm.priority > em.priority
    else:
        first_p = p.spd >= e.spd
    return [(p, pm, e), (e, em, p)] if first_p else [(e, em, p), (p, pm, e)]


def matchup_score(mine, foe_element):
    """How well a creature's element does against a foe's (for the send-in menu)."""
    return mult(mine.element, foe_element) / mult(foe_element, mine.element)
