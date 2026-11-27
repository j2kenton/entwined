"""What a journey remembers: the party, the satchel, where you are. Saved as JSON."""
import json
import os

from . import rules as R

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".entwined")
SAVE_PATH = os.path.join(SAVE_DIR, "journey.json")
SATCHEL_SLOTS = 8
PER_SLOT = 3


class Member:
    """Someone in your party: the hero or an ally, with their team of creatures."""

    def __init__(self, element, team, is_hero=False):
        self.element = element
        self.data = R.HEROES[element]
        self.name = self.data["name"]
        self.is_hero = is_hero
        self.team = team

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
        self.floor = 0            # Citadel floor reached (0-5)
        self.bag = {"remedy": 2}
        self.coins = 20
        self.lord_beaten = False  # in the current land
        self.camp_used = False
        self.picked = []          # things already collected in the current land
        self.pos = None           # where you last rested in the current land
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

    def land(self):
        """The element of the land you're in."""
        return self.hero if self.stage == 0 else self.order[self.stage - 1]

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
        for m in self.party:
            for mon in m.team:
                mon.restore()

    # ----- saving ---------------------------------------------------------
    def to_dict(self):
        return {
            "version": 1, "hero": self.hero, "stage": self.stage, "floor": self.floor,
            "bag": self.bag, "coins": self.coins, "lord_beaten": self.lord_beaten,
            "camp_used": self.camp_used, "picked": self.picked, "pos": self.pos,
            "weather": self.weather, "losses": self.losses, "turns": self.turns,
            "party": [{"element": m.element, "team": [mon.to_dict() for mon in m.team]} for m in self.party],
        }

    @classmethod
    def from_dict(cls, d):
        s = cls(d["hero"])
        s.party = [Member(p["element"], [R.Mon.from_dict(m) for m in p["team"]], is_hero=(i == 0))
                   for i, p in enumerate(d["party"])]
        for k in ("stage", "floor", "bag", "coins", "lord_beaten", "camp_used", "picked", "pos",
                  "weather", "losses", "turns"):
            setattr(s, k, d[k])
        if s.pos:
            s.pos = tuple(s.pos)
        return s

    def save(self, path=None):
        path = path or SAVE_PATH
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f)
            os.replace(tmp, path)
            return True
        except OSError:
            return False


def load(path=None):
    """The saved journey, or None if there isn't one (or it can't be read)."""
    path = path or SAVE_PATH
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("version") != 1:
            return None
        return State.from_dict(d)
    except (OSError, ValueError, KeyError, StopIteration):
        return None


def erase(path=None):
    try:
        os.remove(path or SAVE_PATH)
    except OSError:
        pass
