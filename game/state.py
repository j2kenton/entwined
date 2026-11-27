"""What a journey remembers: the party, the satchel, where you are.

A journey keeps one rest point for each land and one for each floor of the
Citadel. Reaching a place makes its rest point; resting there again replaces
it. You can always go back to an earlier one. They all live in one JSON file.
"""
import json
import os

from . import rules as R

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".entwined")
SAVE_PATH = os.path.join(SAVE_DIR, "journey.json")
SATCHEL_SLOTS = 8
PER_SLOT = 3
VERSION = 2


class Member:
    """Someone in your party: the hero or an ally, with their team of creatures."""

    def __init__(self, element, team, is_hero=False, heals=None):
        self.element = element
        self.data = R.HEROES[element]
        self.name = self.data["name"]
        self.is_hero = is_hero
        self.team = team
        self.heals = R.TUNING["heal"]["uses"] if heals is None else heals    # healing touches left

    @property
    def speaker(self):
        return (self.name.upper(), tuple(R.ELEMENTS["colour"][self.element]))

    @property
    def standing(self):
        return len(R.living(self.team))


class State:
    def __init__(self, hero):
        self.hero = hero
        self.order = R.land_order(hero)
        self.party = [Member(hero, [R.make_mon(hero)], is_hero=True)]
        self.stage = 0            # 0 = home land, 1-5 = the five lands, 6 = the Citadel
        self.reached = 0          # the furthest stage you've got to
        self.floor = 0            # Citadel floor reached (0-5)
        self.climbing = False     # inside the Citadel
        self.bag = {"remedy": 2}
        self.coins = 20
        self.lands = {}           # stage -> what's remembered about that land
        self.lead = 0             # who fought last (the menus start on them)
        self.weather = None
        self.losses = 0
        self.turns = 0

    @property
    def me(self):
        return self.party[0]

    @property
    def team(self):
        return self.party[0].team

    @property
    def allies(self):
        return self.party[1:]

    def has(self, element):
        """Is this hero in the party (as you or as an ally)? Used for gifts."""
        return any(m.element == element for m in self.party)

    def member(self, element):
        return next((m for m in self.party if m.element == element), None)

    def land(self):
        """The element of the land you're in."""
        return self.hero if self.stage == 0 else self.order[self.stage - 1]

    # ----- the land you're in ---------------------------------------------
    @property
    def here(self):
        return self.lands.setdefault(str(min(self.stage, 5)), {"pos": None, "picked": [], "camp_used": False})

    @property
    def pos(self):
        """Where you last rested in this land (None until you've arrived)."""
        p = self.here["pos"]
        return tuple(p) if p else None

    @pos.setter
    def pos(self, value):
        self.here["pos"] = list(value) if value else None

    @property
    def lord_beaten(self):
        """Has this land's Lord joined you? (They join in the order of the road.)"""
        return self.stage == 0 or len(self.party) > self.stage

    # ----- satchel --------------------------------------------------------
    def slots_used(self, bag=None):
        bag = self.bag if bag is None else bag
        return sum(-(-n // PER_SLOT) for n in bag.values() if n > 0)

    def can_carry(self, key, n=1):
        bag = dict(self.bag)
        bag[key] = bag.get(key, 0) + n
        return self.slots_used(bag) <= SATCHEL_SLOTS

    def add(self, key, n=1):
        """Put items in the satchel. Returns how many fitted."""
        got = 0
        for _ in range(n):
            if not self.can_carry(key):
                break
            self.bag[key] = self.bag.get(key, 0) + 1
            got += 1
        return got

    def rest(self):
        """A proper rest: every creature back on its feet, every healing touch restored."""
        for m in self.party:
            m.heals = R.TUNING["heal"]["uses"]
            for mon in m.team:
                mon.restore()

    # ----- saving ---------------------------------------------------------
    def key(self):
        """The name of the rest point you're at."""
        return "floor:%d" % self.floor if self.stage >= 6 else "land:%d" % self.stage

    def to_dict(self):
        return {
            "hero": self.hero, "stage": self.stage, "reached": self.reached, "floor": self.floor,
            "climbing": self.climbing, "bag": self.bag, "coins": self.coins, "lands": self.lands,
            "lead": self.lead, "weather": self.weather, "losses": self.losses, "turns": self.turns,
            "party": [{"element": m.element, "heals": m.heals, "team": [mon.to_dict() for mon in m.team]}
                      for m in self.party],
        }

    @classmethod
    def from_dict(cls, d):
        d = json.loads(json.dumps(d))            # a copy, so the stored rest point isn't touched
        s = cls(d["hero"])
        s.party = [Member(p["element"], [R.Mon.from_dict(m) for m in p["team"]], is_hero=(i == 0), heals=p["heals"])
                   for i, p in enumerate(d["party"])]
        for k in ("stage", "reached", "floor", "climbing", "bag", "coins", "lands", "lead",
                  "weather", "losses", "turns"):
            setattr(s, k, d[k])
        return s


def describe(d):
    """A rest point in a few words, for the "go back" list."""
    hero = d["hero"]
    best = max(m["level"] for p in d["party"] for m in p["team"])
    with_ = len(d["party"]) - 1
    company = "alone" if not with_ else ("with %d companion%s" % (with_, "" if with_ == 1 else "s"))
    if d["stage"] >= 6:
        where = "The Citadel, " + ("the top floor" if d["floor"] >= 5 else "floor %d" % (d["floor"] + 1))
    else:
        el = hero if d["stage"] == 0 else R.land_order(hero)[d["stage"] - 1]
        where = R.HEROES[el]["land"]
    return where, "%s, best creature level %d" % (company, best)


class Journal:
    """Every rest point of one journey. With no path it only lives in memory
    (the quick taste, and previews started from the command line)."""

    def __init__(self, path=None):
        self.path = path
        self.points = {}
        self.current = None

    def put(self, st):
        self.points[st.key()] = st.to_dict()
        self.current = st.key()
        return self.write()

    def get(self, key=None):
        return State.from_dict(self.points[key or self.current])

    def keys(self):
        """Rest points in the order of the journey."""
        return sorted(self.points, key=lambda k: (k.startswith("floor"), int(k.split(":")[1])))

    def earlier(self, key):
        """The rest points before this one."""
        ks = self.keys()
        return ks[:ks.index(key)] if key in ks else ks

    def write(self):
        if not self.path:
            return True
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"version": VERSION, "current": self.current, "points": self.points}, f)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False


def load(path=None):
    """The saved journey's rest points, or None if there aren't any (or they can't be read)."""
    path = path or SAVE_PATH
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("version") != VERSION or d["current"] not in d["points"]:
            return None
        j = Journal(path)
        j.points, j.current = d["points"], d["current"]
        j.get()                                  # make sure it can be read
        return j
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return None


def erase(path=None):
    try:
        os.remove(path or SAVE_PATH)
    except OSError:
        pass
