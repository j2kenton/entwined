"""Battle rules: the element chart, creatures, levels, moves, damage and the AI.

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
SPECIES = CREATURES["species"]
ITEMS = CREATURES["items"]
TEAM_MAX = 5
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
# Moves
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
        self.big = d.get("big", False)
        self.tint = [tuple(c) for c in d.get("tint", [])]
        self.what = d.get("what", "")


MOVES = {k: Move(k, d) for k, d in CREATURES["moves"].items()}


# =========================================================================
# Creatures
# =========================================================================
def stat_scale(level):
    return 1.0 + TUNING["growth_per_level"] * (level - TUNING["start_level"])


def xp_to_next(level):
    return 10 + 5 * (level - TUNING["start_level"])


def xp_for(enemy, trainer=False):
    """Experience for beating a creature."""
    base = 6 + 2 * max(0, enemy.level - TUNING["start_level"])
    return int(base * (1.5 if trainer else 1.0))


class Mon:
    """One creature. `sid` is its species, which also picks its picture."""

    def __init__(self, sid, level, variant="normal"):
        sp = SPECIES[sid]
        self.sid = sid
        self.variant = variant            # "normal", "shadow" or "hybrid"
        self.name = sp["shadow"] if variant == "shadow" else sp["name"]
        self.element = sp["element"]
        self.base = (sp["hp"], sp["atk"], sp["df"], sp["spd"])
        self.learn = sp["learn"]
        self.forms = None                 # hybrids: their two elements
        self.shown_forms = 1
        self.level = level
        self.xp = 0
        self.moves = [MOVES[k] for k, lv in self.learn if lv <= level][:4]
        self._apply()
        self.hp = self.max_hp
        self.pp = {m.key: m.max_pp for m in self.moves}
        self.clear_status()

    def _apply(self):
        hp, atk, df, spd = self.base
        scale = stat_scale(self.level)
        self.max_hp = int(round(hp * scale))
        self.atk = atk * scale
        self.df, self.spd = df, spd

    # ----- state ----------------------------------------------------------
    def clear_status(self):
        self.acc_stage = 0      # 0, -1, -2
        self.boosted = False
        self.guard = False
        self.lured = False

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

    # ----- growing --------------------------------------------------------
    def set_level(self, level):
        """Jump to a level (keeps the share of health it had)."""
        ratio = self.ratio
        self.level = min(level, TUNING["level_cap"])
        self._apply()
        self.hp = max(1 if ratio > 0 else 0, int(round(self.max_hp * ratio)))
        for k, lv in self.learn:
            if lv <= self.level and len(self.moves) < 4 and MOVES[k] not in self.moves:
                self.moves.append(MOVES[k])
                self.pp[k] = MOVES[k].max_pp

    def gain_xp(self, amount):
        """Returns what happened: ("level", n) and ("move", Move) events."""
        events = []
        if self.level >= TUNING["level_cap"]:
            return events
        self.xp += amount
        while self.level < TUNING["level_cap"] and self.xp >= xp_to_next(self.level):
            self.xp -= xp_to_next(self.level)
            known = list(self.moves)
            old_max = self.max_hp
            self.set_level(self.level + 1)
            if self.hp > 0:
                self.hp = min(self.max_hp, self.hp + (self.max_hp - old_max))
            events.append(("level", self.level))
            events += [("move", m) for m in self.moves if m not in known]
        return events

    # ----- hybrids --------------------------------------------------------
    def best_form(self, foe_element):
        """The form that does best against a foe: hits hardest, takes least."""
        return max(self.forms, key=lambda f: mult(f, foe_element) / mult(foe_element, f))

    def set_form(self, element):
        self.element = element
        self.sid = CREATURES["starter"][element]
        self.shown_forms = 2

    # ----- saving ---------------------------------------------------------
    def to_dict(self):
        return {"sid": self.sid, "level": self.level, "xp": self.xp, "hp": self.hp, "pp": self.pp}

    @classmethod
    def from_dict(cls, d):
        m = cls(d["sid"], d["level"])
        m.xp = d.get("xp", 0)
        m.hp = min(d.get("hp", m.max_hp), m.max_hp)
        for k, v in d.get("pp", {}).items():
            if k in m.pp:
                m.pp[k] = v
        return m


def make_mon(element, variant="normal", level=None, role="starter"):
    """A creature of a nature: its starter by default, or its quick / sturdy one."""
    level = level or TUNING["start_level"]
    sid = next(s for s in CREATURES["by_element"][element] if SPECIES[s]["role"] == role)
    return Mon(sid, level, variant)


def make_team(element, level, size, variant="normal"):
    """A trainer's team: starter first (a level higher), then sturdy, then quick."""
    roles = ["starter", "sturdy", "quick", "starter", "sturdy"][:size]
    return [make_mon(element, variant, level + (1 if i == 0 else 0), r) for i, r in enumerate(roles)]


def make_hybrid(hero_element, level):
    """A nemesis's bred creature: the hero's own element plus the one that beats it.
    It first appears in the form that beats the hero."""
    h = CREATURES["hybrid"]
    beater = beater_of(hero_element)
    m = Mon(CREATURES["starter"][beater], level, "hybrid")
    m.name = h["names"][hero_element]
    m.base = (h["hp"], h["atk"], h["df"], h["spd"])
    m.moves = [MOVES[k] for k in h["moves"]]
    m.forms = [hero_element, beater]
    m._apply()
    m.restore()
    return m


def living(team):
    return [m for m in team if m.alive]


# =========================================================================
# Using a move
# =========================================================================
def use_move(user, target, move, rng, weather=None):
    """Apply a move. Returns a dict describing what happened."""
    if move.max_pp:
        user.pp[move.key] -= 1
    res = {"move": move, "user": user, "target": target, "hit": True, "dmg": 0,
           "mult": 1.0, "crit": False, "boosted": False, "guarded": False,
           "heal": 0, "no_effect": False, "element": user.move_element(move), "weather": False}
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
        if weather and res["element"] == weather:
            dmg *= TUNING["weather_boost"]
            res["weather"] = True
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


def use_item(key, mon):
    """Use a satchel item on a creature. Returns a message, or None if it would do nothing."""
    if not mon.alive:
        return None
    if key == "remedy":
        if mon.hp >= mon.max_hp:
            return None
        heal = min(int(round(mon.max_hp * 0.4)), mon.max_hp - mon.hp)
        mon.hp += heal
        return "%s recovered %d HP." % (mon.name, heal)
    if key == "tonic":
        if all(mon.pp[m.key] >= m.max_pp for m in mon.moves):
            return None
        mon.pp = {m.key: m.max_pp for m in mon.moves}
        return "%s is ready to use every move again." % mon.name
    if key == "charm":
        if mon.boosted:
            return None
        mon.boosted = True
        return "%s glows. Its next attack will hit harder." % mon.name
    return None


def bond_chance(wild):
    """How likely a wild creature of your own nature is to accept you."""
    return min(0.95, 0.2 + 0.65 * (1 - wild.ratio) + (0.3 if wild.lured else 0.0))


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
