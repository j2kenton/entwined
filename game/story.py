"""The journey, start to finish.

Full journey:  title > intro > choose a hero > home land > five lands, each
kept by a Master > the Citadel (five floors, blocked ways, the top) > ending.
Quick taste:   one Master, one Citadel floor and the top, with no walking.

(In the code and the data files the five Masters are still called "lords":
it's what they were called when this was written.)

Everything hero-specific comes from data/heroes.json; every line of text
comes from data/story.json, with {placeholders} filled in for the chosen hero.
"""
import random

from . import rules as R
from . import state as S
from . import world as W
from .art import backdrops, creatures, trainers
from .battle import Battle, el_colour, sparks
from .engine.canvas import Canvas, darker, draw_text, mix, text_width
from .engine.ui import DIM, GOLD, GREY, INNER, WHITE, wrap

STORY = R.load("story")
T = R.TUNING
PRONOUNS = {"f": ("she", "her", "her"), "m": ("he", "him", "his")}
SHORT_WORD = {"strong": "strong", "slightly strong": "sl. strong", "even": "even",
              "slightly weak": "sl. weak", "weak": "weak"}


class Stage:
    """A story picture: a backdrop with up to three figures standing on it."""

    def __init__(self, ui, backdrop, title=None):
        self.ui = ui
        self.kind = backdrop
        self.title = title
        self.cv = None
        self.show()

    def show(self, *figures):
        """figures: ("trainer", look) or ("creature", species id)."""
        s = self.ui.S
        cv = backdrops.backdrop(self.kind, s, platforms=False).copy()
        spots = {0: [], 1: [50], 2: [28, 72], 3: [20, 50, 80]}[len(figures)]
        for i, ((kind, what), x) in enumerate(zip(figures, spots)):
            flip = len(figures) > 1 and i == len(figures) - 1
            cv.ellipse(x, 57, 11, 1.4, darker(cv.get(x, 58) or (40, 40, 40), 0.7))
            if kind == "trainer":
                trainers.sprite(what, s, flip=flip).blit(cv, int(x * s), int(57 * s))
            else:
                spr = creatures.frames(what, "normal", None, s, 30)[0]
                (spr.flipped() if not flip else spr).blit(cv, int(x * s), int(57 * s))
        if self.title:
            text, size, y, col = self.title
            x = (100 - text_width(text) * size) // 2
            draw_text(cv, x, y, text, col, shadow=(20, 10, 30), size=size)
        self.cv = cv

    def draw(self):
        return self.cv


class Game:
    def __init__(self, ui, rng=None, save_path=None):
        self.ui = ui
        self.rng = rng or random.Random()
        self.save_path = save_path
        self.st = None
        self.trial = False
        self.journal = None        # the journey's rest points
        self.entry = None          # which border you last came through ("west" / "east")
        self.pilot = None          # tests: a function (world) -> key, to walk the maps

    # =====================================================================
    # Text
    # =====================================================================
    def fmt(self, text, **extra):
        ctx = dict(self.ctx)
        ctx.update(extra)
        return text.format(**ctx)

    def setup(self, st):
        """Point the game at a journey (new or loaded)."""
        self.st = st
        self.hero = st.hero
        self.hero_data = h = R.HEROES[st.hero]
        ctx = {}

        def who(prefix, sex):
            for k, v in zip(("they", "them", "their"), PRONOUNS[sex]):
                ctx["%s_%s" % (prefix, k)] = v
                ctx["%s_%s" % (prefix.capitalize(), k)] = v.capitalize()
        who("hero", h["sex"])
        who("nem", h["sex"])
        ctx["nem_man"] = "woman" if h["sex"] == "f" else "man"
        who("sw", "m" if h["sex"] == "f" else "f")
        beater = R.beater_of(st.hero)
        ctx.update(hero=h["name"], land=h["land"], folk=h["folk"], element=R.el_name(st.hero),
                   creature=R.SPECIES[R.CREATURES["starter"][st.hero]]["name"],
                   nemesis=h["nemesis"]["name"], nem_first=h["nemesis"]["first"],
                   sweetheart=h["sweetheart"]["name"], sw_element=R.el_name(beater),
                   beater=R.el_name(beater), Beater=R.el_name(beater),
                   hybrid=R.CREATURES["hybrid"]["names"][st.hero],
                   sw_creature=R.SPECIES[h["sweetheart"]["creature"]]["name"])
        self.ctx = ctx

    no_save = False                # previews started from the command line don't touch your save

    def save(self):
        """Make (or replace) the rest point for where you are."""
        self.journal.put(self.st)

    def speaker(self, who, **alt):
        if who == "narr":
            return None
        if who == "hero":
            return self.st.me.speaker
        if who in alt:
            return alt[who]
        if who == "nemesis":
            return self.villain(self.hero)
        if who == "sweetheart":
            return (self.hero_data["sweetheart"]["name"].upper(), el_colour(R.beater_of(self.hero)))
        raise KeyError(who)

    def villain(self, element):
        n = R.HEROES[element]["nemesis"]
        return (n["first"].upper(), mix(el_colour(element), (255, 60, 90), 0.55))

    def figures(self, names):
        out = []
        for n in names:
            if n == "hero":
                out.append(("trainer", self.hero_data["look"]))
            elif n == "nemesis":
                out.append(("trainer", self.hero_data["nemesis"]["look"]))
            elif n == "sweetheart":
                out.append(("trainer", self.hero_data["sweetheart"]["look"]))
            elif n == "creature":
                out.append(("creature", R.CREATURES["starter"][self.hero]))
            elif n in ("ally", "ally2") and self.st.allies:        # the last to join, and the first
                out.append(("trainer", self.st.allies[-1 if n == "ally" else 0].data["look"]))
        return out

    def play(self, key, stage=None, battle=None, speakers=None, **extra):
        """Run a list of story lines, on a Stage or inside a Battle."""
        speakers = speakers or {}
        for entry in STORY[key]:
            who, text = entry[0], self.fmt(entry[1], **extra)
            sp = self.speaker(who, **speakers)
            if battle:
                battle.say(text, speaker=sp, wait=True)
            else:
                if len(entry) > 2 and isinstance(entry[2], str):
                    stage.cv = self.shot(entry[2])                 # a wide view, named in the story file
                elif len(entry) > 2:
                    stage.show(*self.figures(entry[2]))
                self.ui.say(stage.draw, text, speaker=sp)

    def shot(self, name):
        """A wide view of the Citadel's roof at night: the platform in the middle,
        you coming up from the stairs, and whoever is waiting.
        roof:far   someone on the platform, only a shape in the dark
        roof:near  you've come closer: it's your sweetheart
        roof:all   and your nemesis has stepped out beside them"""
        shots = getattr(self, "_shots", None)
        if shots is None:
            shots = self._shots = {}
        key = (name, self.hero, self.ui.S)
        if key not in shots:
            hero_x, lit, both = {"roof:far": (9, False, False), "roof:near": (31, True, False), "roof:all": (31, True, True)}[name]
            s = self.ui.S
            h = self.hero_data
            cv = backdrops.backdrop("roof_dais", s, platforms=False).copy()
            her = trainers.small(h["sweetheart"]["look"], s, 0.46, flip=True)
            if not lit:
                her = her.silhouette((10, 6, 20))
            her.blit(cv, int(49 * s), int(45.5 * s))
            if both:
                trainers.small(h["nemesis"]["look"], s, 0.46, flip=True).blit(cv, int(61 * s), int(45.5 * s))
            trainers.small(h["look"], s, 0.5).blit(cv, int(hero_x * s), int(58 * s))
            shots[key] = cv
        return shots[key]

    def ask(self, draw, question, options, start=0, tag=None):
        """A plain question with a few answers. Returns the index picked."""
        return self.ui.menu(draw, [(WHITE, "  " + question)], [[(WHITE, o)] for o in options], cols=1,
                            start=start, tag=tag)

    def voice(self, element):
        """How a gift's owner speaks up: by name if an ally, as narration if it's you."""
        m = next(m for m in self.st.party if m.element == element)
        return None if m.is_hero else m.speaker

    # =====================================================================
    # Shortcuts for testers (`play --test`, then T)
    # =====================================================================
    tester_who = 0                 # which line of "Applies to" is chosen

    def tester_options(self):
        """The tester's dials: (label, current value, lower, raise) for each line.
        One thing at a time, for one trainer or everyone, up or down."""
        st = self.st
        if st is None:
            nothing = lambda: None
            return [("Nothing yet", "start or carry on a journey first", nothing, nothing)]
        b = self.ui.battle
        foe = b.enemy.mon if (b and b.enemy.on and b.enemy.mon.alive) else None
        targets = [("Everyone", [mon for m in st.party for mon in m.team], list(st.party))]
        targets += [(m.name, m.team, [m]) for m in st.party]
        if foe:
            targets.append(("The creature facing you", [foe], []))
        self.tester_who %= len(targets)
        name, mons, members = targets[self.tester_who]
        cap = T["level_cap"]
        uses = T["heal"]["uses"]
        steps = (0.0, 0.01, 0.25, 0.5, 0.75, 1.0)          # fainted, a sliver, then quarters

        def bars():
            if b:
                for side in (b.enemy, b.player):
                    if side.on:
                        side.hp_target = side.mon.ratio

        def who(d):
            self.tester_who = (self.tester_who + d) % len(targets)

        def level(d):
            for mon in mons:
                mon.set_level(max(1, min(cap, mon.level + d)))
            bars()

        def health(d):
            now = sum(mon.ratio for mon in mons) / len(mons)
            at = 0 if now <= 0 else 1 if now < 0.13 else 2 if now < 0.375 else 3 if now < 0.625 else 4 if now < 0.875 else 5
            goal = steps[max(0, min(len(steps) - 1, at + d))]
            for mon in mons:
                hp = int(round(mon.max_hp * goal))
                if goal > 0:
                    hp = max(1, hp)
                # a creature in the middle of a fight can be left with a sliver, never dropped where it stands
                if b and mon in (b.enemy.mon, b.player.mon) and (b.enemy.on or b.player.on):
                    hp = max(1, hp)
                mon.hp = hp
                if goal >= 1.0:
                    mon.restore()
            bars()

        def touches(d):
            for m in members:
                m.heals = max(0, min(uses, m.heals + d))

        def coins(d):
            st.coins = max(0, st.coins + d * 50)

        def satchel(d):
            if d < 0:
                st.bag = {}
                return
            st.bag = dict(st.bag, remedy=3, tonic=3, elixir=3, charm=3)
            for el in dict.fromkeys([st.land() if st.stage <= 5 else st.hero, st.hero]):
                st.add("lure_%s_3" % el, 3)

        lv = sorted(mon.level for mon in mons)
        level_now = "level %d" % lv[0] if lv[0] == lv[-1] else "levels %d to %d" % (lv[0], lv[-1])
        down = sum(1 for mon in mons if not mon.alive)
        health_now = "%d%%" % round(100 * sum(mon.ratio for mon in mons) / len(mons))
        if down:
            health_now += "  (%d fainted)" % down
        rows = [("Applies to", name, lambda: who(-1), lambda: who(1)),
                ("Level", level_now + "   (one at a time)", lambda: level(-1), lambda: level(1)),
                ("Health", health_now, lambda: health(-1), lambda: health(1))]
        if members:
            t = sorted(m.heals for m in members)
            rows.append(("Healing touches", ("%d of %d" % (t[0], uses)) if t[0] == t[-1] else "%d to %d of %d" % (t[0], t[-1], uses),
                         lambda: touches(-1), lambda: touches(1)))
        rows += [("Coins", "%d   (50 at a time)" % st.coins, lambda: coins(-1), lambda: coins(1)),
                 ("Satchel", "%d of %d bundles   (Left empties, Right fills)" % (st.slots_used(), S.SATCHEL_SLOTS),
                  lambda: satchel(-1), lambda: satchel(1))]
        return rows

    # =====================================================================
    # Title, intro, choosing a hero
    # =====================================================================
    def title_menu(self):
        st = Stage(self.ui, "title", title=("ENTWINED", 2, 20, (255, 214, 120)))
        m = STORY["menu"]
        journal = S.load(self.save_path)
        while True:
            keys = ["continue"] if journal else []
            if journal and journal.earlier(journal.current):
                keys.append("earlier")
            keys += ["new", "trial"]
            opts = [[(WHITE, m[k])] for k in keys]

            def desc(i):
                if keys[i] == "continue":
                    d = journal.points[journal.current]
                    where, who = S.describe(d)
                    return [(GREY, "  %s: %s, %s." % (R.HEROES[d["hero"]]["name"], where, who))]
                return [(DIM, "  " + m["hint"])]
            head = [(GREY, "  A creature-battling adventure, in your terminal.")]
            if self.ui.display.mode == "blocks":            # the coarse pictures: say there are better ones
                head.append((DIM, "   Retro pictures. For HD, see the README."))
            pick = keys[self.ui.menu(st.draw, head, opts, cols=2 if len(keys) > 3 else 1, desc=desc)]
            if pick == "new" and journal:
                if self.ask(st.draw, m["new_warning"], ["Begin again", "Go back"], start=1) == 1:
                    continue
            if pick == "earlier":
                key = self.choose_point(st.draw, journal, journal.earlier(journal.current))
                if key is None:
                    continue
                journal.current = key
                journal.write()
                pick = "continue"
            return pick, journal

    def choose_point(self, draw, journal, keys):
        """Pick a rest point to go back to, most recent first. Returns its key, or None."""
        keys = list(reversed(keys))
        page = 0
        while True:
            shown = keys[page * 4:page * 4 + 4]
            more = len(keys) > (page + 1) * 4
            cells = [[(WHITE, S.describe(journal.points[k])[0])] for k in shown]
            cells += ([[(GREY, "Further back")]] if more else []) + [[(GREY, "Never mind")]]

            def desc(i):
                if i < len(shown):
                    return [(GREY, "  %s." % S.describe(journal.points[shown[i]])[1].capitalize())]
                return [(GREY, "  ")]
            i = self.ui.menu(draw, [(GREY, "  " + STORY["menu"]["earlier_ask"])], cells, cols=2, desc=desc,
                             tag=("point", shown))
            if i < len(shown):
                return shown[i]
            if more and i == len(shown):
                page += 1
                continue
            return None

    def load_point(self, key):
        """Go back to a rest point. (What it cost you to learn better isn't forgotten.)"""
        old = self.st
        st = self.journal.get(key)
        st.losses, st.turns = old.losses, old.turns
        self.journal.current = key
        self.journal.write()
        self.setup(st)

    def intro(self):
        st = Stage(self.ui, "title")
        for who, text in STORY["intro"]:
            self.ui.say(st.draw, text)

    def choose_hero(self):
        ui = self.ui
        order = R.ORDER
        sel = 0
        stages = {}
        ui.take()
        while True:
            el = order[sel]
            h = R.HEROES[el]
            if el not in stages:
                st = Stage(ui, el)
                st.show(("trainer", h["look"]), ("creature", R.CREATURES["starter"][el]))
                stages[el] = st
            col = el_colour(el)
            journey = " > ".join(R.HEROES[o]["land"] for o in R.land_order(el))
            blink = (ui.tick // 8) % 2 == 0
            rows = [
                [(GREY, "  " + STORY["choose_hero"]), (GOLD, "      ◀ " if blink else "        "),
                 (WHITE, "%d of 6" % (sel + 1)), (GOLD, " ▶" if blink else "  "),
                 (DIM, "      Left / Right to look, Enter to choose")],
                [(col, "  " + h["name"].upper()), (WHITE, ", %s of %s" % (h["title"], h["land"]))],
                [(GREY, "  Nature: "), (col, R.el_name(el)), (GREY, "     Creature: "),
                 (col, R.SPECIES[R.CREATURES["starter"][el]]["name"]), (GREY, "     " + h["about"])],
                [(GREY, "  Strong against "), (el_colour(order[(sel + 1) % 6]), R.el_name(order[(sel + 1) % 6])),
                 (GREY, ".  Weak against "), (el_colour(R.beater_of(el)), R.el_name(R.beater_of(el))), (GREY, ".")],
                [(DIM, "  Road: " + journey)],
            ]
            ui.frame(stages[el].draw(), rows)
            for k in ui.take():
                if k == "left":
                    sel = (sel - 1) % 6
                elif k == "right":
                    sel = (sel + 1) % 6
                elif k == "enter":
                    return el

    # =====================================================================
    # Walking the lands
    # =====================================================================
    def explore(self):
        while self.st.stage <= 5:
            self.land_loop()

    def spawn_wild(self, world):
        st = self.st
        land = world.land
        # lands you've already passed keep pace with you: their wild creatures grow as you go on
        lo, hi = T["wild_levels"][min(5, max(st.stage, st.reached - 1))]
        spots = [p for p in land.habitat if p != (world.x, world.y)]
        self.rng.shuffle(spots)
        world.wild = []
        for x, y in spots[:7]:
            el = st.hero if (land.home or self.rng.random() < 0.25) else land.element
            sid = self.rng.choice(R.CREATURES["by_element"][el])
            world.wild.append(W.Wild(x, y, R.Mon(sid, self.rng.randint(lo, hi))))

    def new_day(self, world):
        """A rest: everyone heals, the wild fills up again, the weather turns."""
        st = self.st
        st.rest()
        st.weather = self.rng.choice(R.ORDER + [None, None])
        self.spawn_wild(world)
        self.save()

    def forecast(self, world):
        st = self.st
        if st.weather and st.has("lightning"):
            self.ui.say(world.draw, STORY["forecast"][st.weather], speaker=self.voice("lightning"))

    def hud(self, world):
        st = self.st
        land = R.HEROES[world.land.element]
        col = el_colour(world.land.element)

        def rows():
            alive = R.living(st.team)
            lead = alive[0] if alive else st.team[0]
            more = len(st.team) - 1
            bag = ", ".join("%s x%d" % (R.ITEMS[k]["name"], n) for k, n in st.bag.items() if n) or "empty"
            if world.land.home:
                goal = "East is the border. Off the road, wild creatures move in the long growth."
            elif not st.lord_beaten:
                goal = "Somewhere along this road, %s is waiting." % land["name"]
            else:
                goal = "The border gate stands open, to the east."
            top = [(col, "  " + land["land"].upper()), (GREY, "     Coins: %d" % st.coins)]
            if st.weather and st.has("lightning"):
                top.append((el_colour(st.weather), "     %s weather" % R.el_name(st.weather)))
            return [top,
                    [(WHITE, "  %s" % lead.name), (GREY, "  L%d  %d/%d" % (lead.level, lead.hp, lead.max_hp)),
                     (GREY, ("   and %d more" % more) if more else "")],
                    [(GREY, "  Satchel: " + bag)],
                    [(GREY, "  " + goal)],
                    [(DIM, "  Arrows walk.  Enter talks and looks.  M opens your pack.")]]
        return rows

    def land_loop(self):
        st, ui = self.st, self.ui
        el = st.land()
        home = st.stage == 0
        lord = R.HEROES[el]
        land = W.Land(el, R.ORDER.index(st.hero) * 100 + st.stage * 7 + 13, home=home)
        first_visit = st.pos is None
        entry, self.entry = self.entry, None
        if first_visit or entry == "west":
            at = land.start
        elif entry == "east":
            at = (land.gate[0] - 1, land.gate[1])
        else:
            at = st.pos
        world = W.World(ui, land, self.hero_data["look"], at,
                        navigator=st.has("wave"), gate_open=st.lord_beaten,
                        lord_look=None if st.lord_beaten else lord["look"], picked=st.here["picked"])
        if entry == "east":
            world.facing = "left"
        world.title = lord["land"].upper()
        world.pilot = self.pilot
        self.spawn_wild(world)
        rows = self.hud(world)
        extra = dict(lord=lord["name"], land=lord["land"], land_element=R.el_name(el), master=R.el_name(el) + "master")
        for k, v in zip(("they", "them", "their"), PRONOUNS[lord["sex"]]):
            extra["Lord_" + k] = v.capitalize()
        if first_visit:                                # reaching a land makes its rest point
            st.pos = land.start
            self.new_day(world)
            self.forecast(world)
        while True:
            ev = world.run(rows, self.rng)
            kind = ev[0]
            if kind == "wild":
                self.wild_battle(world, ev[1])
            elif kind == "lord":
                world.lord_seen = True
                if self.lord_encounter(st.stage - 1, el, world):
                    world.lord_look = None
                    world.gate_open = True
                    world.repaint()
                else:
                    world.x, world.y = st.pos
                    world.slide = None
            elif kind == "inn":
                if self.ask(world.draw, STORY["inn_ask"], ["Rest", "Not now"]) == 0:
                    st.pos = land.inn_door
                    self.new_day(world)
                    ui.say(world.draw, STORY["inn_done"])
                    self.forecast(world)
            elif kind == "market":
                self.market(world)
            elif kind == "sign":
                ui.say(world.draw, self.fmt(STORY["sign"], **extra))
            elif kind == "folk":
                lines = STORY["folk"]["home" if home else "away"]
                i = ev[1] if home else ev[1] + st.stage
                ui.say(world.draw, self.fmt(lines[i % len(lines)], **extra))
            elif kind == "pickup":
                self.pickup(world, ev[1], ev[2])
            elif kind == "hidden":
                ui.say(world.draw, STORY["navigator"], speaker=self.voice("wave"))
            elif kind == "warn":
                if st.has("breeze"):
                    ui.say(world.draw, STORY["lookout"], speaker=self.voice("breeze"))
            elif kind == "gate_shut":
                ui.say(world.draw, self.fmt(STORY["gate_shut"], **extra))
            elif kind == "menu":
                self.pack(world)
            elif kind == "gate":
                if st.stage == 5:
                    if self.citadel_gate(world):
                        st.stage = st.reached = 6
                        return
                elif self.ask(world.draw, self.fmt(STORY["gate_ask"], next_land=R.HEROES[st.order[st.stage]]["land"]),
                              ["Cross the border", "Stay a while longer"]) == 0:
                    st.stage += 1
                    st.reached = max(st.reached, st.stage)
                    self.entry = "west"
                    return
                world.x -= 1                           # step back from the gate
                world.slide = None
            elif kind == "gate_west":
                back = st.hero if st.stage == 1 else st.order[st.stage - 2]
                if self.ask(world.draw, self.fmt(STORY["gate_back"], prev_land=R.HEROES[back]["land"]),
                            ["Go back", "Stay here"], start=1, tag=("west",)) == 0:
                    st.stage -= 1
                    self.entry = "east"
                    return
                world.x += 1
                world.slide = None

    def pickup(self, world, kind, pos):
        st, ui = self.st, self.ui
        found = STORY["found"]
        if kind == "chest":
            got = [R.ITEMS[k]["name"].lower() + (" x%d" % n if n > 1 else "")
                   for k, n in (("remedy", 2), ("tonic", 1)) if st.add(k, n)]
            st.coins += 15
            ui.say(world.draw, found["chest"].format(loot=", ".join(got + ["15 coins"])))
        elif kind == "herb" and st.has("root"):
            if not st.add("remedy"):
                ui.say(world.draw, found["full"])
                return
            ui.say(world.draw, found["herb_brewed"] if self.voice("root")
                   else "A fragrant herb. You crush it into a remedy on the spot.")
        else:
            if not st.add(kind):
                ui.say(world.draw, found["full"])
                return
            ui.say(world.draw, found[kind])
        world.picked.add(pos)
        st.here["picked"] = [list(p) for p in world.picked]

    def pick_fighter(self, draw, foe, head, why):
        """Whose team takes this fight. Only asked once you have company."""
        st = self.st
        if not st.allies:
            return st.me
        m = self.choose_trainer(draw, st.party, foe, head, start=min(st.lead, len(st.party) - 1), why=why)
        st.lead = st.party.index(m)
        return m

    def wild_battle(self, world, w):
        st = self.st
        fighter = self.pick_fighter(world.draw, w.mon, self.fmt(STORY["who_wild"], creature=w.mon.name), "wild")
        b = Battle(self.ui, world.land.element, self.rng, weather=st.weather)
        b.open()
        result = b.fight(fighter.team, [w.mon], controller=self.controller(fighter), wild=True, bag=st.bag,
                         party=st.party, xp=True)
        st.turns += b.stats["turns"]
        if result == "bonded":
            keeper = st.member(w.mon.element)
            w.mon.clear_status()
            w.mon.restore()                            # its new trainer sees to its hurts
            keeper.team.append(w.mon)
            b.say(self.fmt(STORY["bonded"] if keeper.is_hero else STORY["bonded_ally"],
                           creature=w.mon.name, trainer=keeper.name), wait=True)
        b.close()
        if w in world.wild:
            world.wild.remove(w)
        if result == "lose":
            st.losses += 1
            st.rest()
            world.x, world.y = st.pos
            world.slide = None
            self.spawn_wild(world)
            self.ui.say(world.draw, STORY["blackout"])

    def market(self, world):
        st, ui = self.st, self.ui
        el = world.land.element
        m = STORY["market"]
        ctx = dict(element=R.el_name(el))
        lures = sorted(k for k in R.LURES if R.LURES[k][0] == el)
        sel = 0
        while True:
            sellable = sum(st.bag.get(k, 0) * R.ITEMS[k]["sell"] for k in ("herb", "shard"))
            opts = [[(WHITE, m["supplies"])], [(el_colour(el), m["lures"].format(**ctx))],
                    [(WHITE if sellable else DIM, "Sell herbs and shards"), (GOLD, "  +%d coins" % sellable)],
                    [(GREY, "Leave")]]
            about = [m["supplies_about"], m["lures_about"].format(**ctx), "Herbs fetch 4 coins, shards 6.",
                     "Back to the road."]
            head = [(WHITE, "  " + STORY["market_ask"]), (GOLD, "      You have %d coins." % st.coins)]
            sel = ui.menu(world.draw, head, opts, cols=2, start=sel,
                          blocked=lambda i: "You've nothing to sell." if (i == 2 and not sellable) else None,
                          desc=lambda i: [(GREY, "  " + about[i])], tag=("market", st, el))
            if sel == 0:
                self.shop(world, ["remedy", "tonic", "charm", "elixir"])
            elif sel == 1:
                self.shop(world, lures)
            elif sel == 2:
                st.coins += sellable
                st.bag["herb"] = st.bag["shard"] = 0
            else:
                return

    def shop(self, world, stock):
        st, ui = self.st, self.ui
        sel = 0
        while True:
            opts = [[(WHITE, R.ITEMS[k]["name"].ljust(20)), (GOLD, ("%d coins" % R.ITEMS[k]["price"]).ljust(10)),
                     (GREY, "have %d" % st.bag.get(k, 0))] for k in stock] + [[(GREY, "Back")]]
            head = [(WHITE, "  " + STORY["market_ask"]), (GOLD, "      You have %d coins." % st.coins)]

            def blocked(i):
                if i < len(stock):
                    if st.coins < R.ITEMS[stock[i]]["price"]:
                        return STORY["market_poor"]
                    if not st.can_carry(stock[i]):
                        return STORY["market_full"]
                return None
            sel = ui.menu(world.draw, head, opts, cols=2, start=sel, blocked=blocked,
                          desc=lambda i: [(GREY, "  " + (R.ITEMS[stock[i]]["text"] if i < len(stock) else "Go back."))],
                          tag=("shop", stock, st))
            if sel >= len(stock):
                return
            st.coins -= R.ITEMS[stock[sel]]["price"]
            st.add(stock[sel])

    def pack(self, world):
        st, ui = self.st, self.ui
        while True:
            opts = ["Teams" if st.allies else "Team", "Satchel", "Healing touch"]
            if st.allies:
                opts.append("Companions")
            if st.has("soil"):
                opts.append("Make camp")
            if st.has("flame") and st.bag.get("shard", 0) >= 2:
                opts.append("Forge a charm")
            opts.append("Back to the road")
            pick = opts[ui.menu(world.draw, [(GREY, "  Your pack")], [[(WHITE, o)] for o in opts], cols=2,
                                tag=("pack", opts))]
            if pick in ("Team", "Teams"):
                m = self.pick_member(world.draw, "Whose team?")
                if m:
                    self.pack_team(world.draw, m)
            elif pick == "Satchel":
                self.pack_satchel(world.draw)
            elif pick == "Healing touch":
                self.heal_touch(world.draw)
            elif pick == "Companions":
                allies = st.allies
                cells = [[(el_colour(m.element), m.name.ljust(9)), (GREY, STORY["gifts"][m.element][0])] for m in allies]
                ui.menu(world.draw, [(GREY, "  Travelling with you")], cells + [[(GREY, "Back")]], cols=2,
                        desc=lambda i: [(GREY, "  " + (STORY["gifts"][allies[i].element][1] if i < len(allies) else "Go back."))])
            elif pick == "Make camp":
                if st.here["camp_used"]:
                    ui.say(world.draw, STORY["camp_used"])
                else:
                    st.here["camp_used"] = True
                    st.pos = (world.x, world.y)
                    self.new_day(world)
                    ui.say(world.draw, STORY["camp"] if self.voice("soil") else STORY["camp_self"])
                    self.forecast(world)
            elif pick == "Forge a charm":
                if not st.can_carry("charm"):
                    ui.say(world.draw, STORY["found"]["full"])
                else:
                    st.bag["shard"] -= 2
                    st.add("charm")
                    ui.say(world.draw, STORY["forge"] if self.voice("flame") else STORY["forge_self"])
            else:
                return

    def pick_member(self, draw, head, note=None, why=None):
        """Choose someone in your party (None for "back"). Straight to you when you travel alone."""
        st = self.st
        if not st.allies:
            return st.me
        cells = []
        for m in st.party:
            cells.append([(el_colour(m.element), m.name.ljust(9)),
                          (GREY, note(m) if note else "%d of %d ready" % (m.standing, len(m.team)))])
        cells.append([(GREY, "Back")])
        i = self.ui.menu(draw, [(GREY, "  " + head)], cells, cols=3, col_width=32, tag=("member", st.party, why))
        return st.party[i] if i < len(st.party) else None

    def pack_team(self, draw, member):
        ui = self.ui
        while True:
            team = member.team
            cells = [[(WHITE if m.alive else DIM, m.name.ljust(11)), (GREY, ("L%d" % m.level).ljust(5)),
                      ((120, 220, 130) if m.alive else DIM, ("%d/%d" % (m.hp, m.max_hp)) if m.alive else "fainted")]
                     for m in team] + [[(GREY, "Back")]]

            def desc(i):
                if i >= len(team):
                    return [(GREY, "  Go back.")]
                m = team[i]
                nxt = "" if m.level >= T["level_cap"] else "  %d to next level." % (R.xp_to_next(m.level) - m.xp)
                return [(GREY, "  %s.%s  Knows: %s" % (R.el_name(m.element), nxt, ", ".join(v.name.title() for v in m.moves)))]
            whose = "Your team" if member.is_hero else member.name + "'s team"
            i = ui.menu(draw, [(GREY, "  %s. The first one goes into battle first." % whose)], cells, cols=2, desc=desc)
            if i >= len(team):
                return
            m = team[i]
            acts = ["Put it first"] + (["Let it go"] if len(team) > 1 else []) + ["Back"]
            a = acts[self.ask(draw, m.name, acts)]
            if a == "Put it first":
                team.remove(m)
                team.insert(0, m)
            elif a == "Let it go":
                if self.ask(draw, "Let %s go back to the wild? It won't return." % m.name,
                            ["Keep it", "Let it go"], tag=("release",)) == 1:
                    team.remove(m)

    def pack_satchel(self, draw):
        st, ui = self.st, self.ui
        while True:
            keys = [k for k, n in st.bag.items() if n]
            if not keys:
                ui.say(draw, "Your satchel is empty.")
                return
            cells = [[(WHITE, R.ITEMS[k]["name"].ljust(20)), (GREY, "x%d" % st.bag[k])] for k in keys] + [[(GREY, "Back")]]
            i = ui.menu(draw, [(GREY, "  Your satchel   (%d of %d bundles)" % (st.slots_used(), S.SATCHEL_SLOTS))],
                        cells, cols=3, col_width=32,
                        desc=lambda i: [(GREY, "  " + (R.ITEMS[keys[i]]["text"] if i < len(keys) else "Go back."))])
            if i >= len(keys):
                return
            k = keys[i]
            if k == "elixir":
                uses = T["heal"]["uses"]
                m = self.pick_member(draw, STORY["heal"]["elixir_who"],
                                     note=lambda m: "%d of %d touches" % (m.heals, uses))
                if m and m.heals >= uses:
                    ui.say(draw, self.fmt(STORY["heal"]["elixir_full"], trainer=m.name))
                elif m:
                    m.heals = uses
                    st.bag[k] -= 1
                    ui.say(draw, self.fmt(STORY["heal"]["elixir_done"], trainer=m.name))
                continue
            if k not in ("remedy", "tonic"):
                continue
            member = self.pick_member(draw, "Use the %s on whose creature?" % R.ITEMS[k]["name"].lower())
            if not member:
                continue
            team = member.team
            cells = [[(WHITE if m.alive else DIM, m.name.ljust(11)),
                      (GREY, ("%d/%d" % (m.hp, m.max_hp)) if m.alive else "fainted")] for m in team] + [[(GREY, "Back")]]
            j = ui.menu(draw, [(GREY, "  Use the %s on which creature?" % R.ITEMS[k]["name"].lower())], cells, cols=2)
            if j < len(team):
                msg = R.use_item(k, team[j])
                if msg:
                    st.bag[k] -= 1
                ui.say(draw, msg or "It would do %s no good right now." % team[j].name)

    def heal_touch(self, draw):
        """Each trainer can mend creatures of their own nature a few times between proper rests."""
        st, ui = self.st, self.ui
        text = STORY["heal"]
        uses = T["heal"]["uses"]
        while True:
            member = self.pick_member(draw, text["who"], note=lambda m: "%d of %d touches" % (m.heals, uses), why="heal")
            if member is None:
                return
            ctx = dict(trainer=member.name, their=PRONOUNS[member.data["sex"]][2])
            if member.heals <= 0:
                ui.say(draw, self.fmt(text["none"], **ctx))
            else:
                team = member.team
                hurt = [m for m in team if m.alive and m.hp < m.max_hp]
                if not hurt:
                    ui.say(draw, self.fmt(text["no_need"], **ctx))
                else:
                    cells = [[(WHITE, m.name.ljust(11)), (GREY, "%d/%d" % (m.hp, m.max_hp))] for m in hurt] + [[(GREY, "Back")]]
                    j = ui.menu(draw, [(GREY, "  " + self.fmt(text["which"], **ctx))],
                                cells, cols=2, tag=("heal", hurt))
                    if j < len(hurt):
                        mon = hurt[j]
                        n = min(mon.max_hp - mon.hp, int(round(mon.max_hp * T["heal"]["amount"])))
                        mon.hp += n
                        member.heals -= 1
                        ui.say(draw, self.fmt(text["done"], creature=mon.name, n=n, **ctx))
            if not st.allies:
                return

    # =====================================================================
    # Lords
    # =====================================================================
    def lord_comment(self, stats, lord_el):
        """The specific half of a Lord's comment: why you won."""
        p_el = self.hero
        if stats["min_ratio"] < 0.3 and stats["fainted"] == 0:
            key = "clutch"
        elif stats["turns"] <= 3 * len(self.st.team):
            key = "fast"
        elif R.mult(lord_el, p_el) > 1.0:
            key = "uphill"
        elif stats["guards"] >= 2:
            key = "guard"
        elif stats["plain_hits"] > stats["elem_hits"]:
            key = "plain"
        elif stats["misses"] >= 2:
            key = "misses"
        elif R.mult(p_el, lord_el) > 1.0:
            key = "advantage"
        else:
            key = "default"
        return self.fmt(STORY["win_specific"][key], p_noun=R.ELEMENTS["noun"][p_el],
                        e_noun=R.ELEMENTS["noun"][lord_el], creature=self.st.team[0].name)

    def trainer_cells(self, member, foe):
        ok = member.standing > 0
        word = SHORT_WORD[R.effect_word(R.mult(member.element, foe.element))]
        return [(WHITE if ok else DIM, member.name.ljust(9)),
                (el_colour(member.element) if ok else DIM, R.el_name(member.element).ljust(10)),
                (GREY if ok else DIM, ("%d of %d ready" % (member.standing, len(member.team))).ljust(15)),
                (GOLD if ok else DIM, word if ok else "")]

    def choose_trainer(self, draw, members, foe, head, start=0, why="citadel"):
        """Pick whose team goes in. Returns the Member. (`why` is only for test robots.)"""
        def desc(i):
            m = members[i]
            if not m.standing:
                return [(DIM, "  %s's creatures have all fainted." % m.name)]
            mine = R.effect_word(R.mult(m.element, foe.element))
            theirs = R.effect_word(R.mult(foe.element, m.element))
            own = "Your own team. " if m.is_hero else ""
            return [(GREY, "  %s%s attacks: %s.   %s's %s attacks back: %s." % (
                own, R.el_name(m.element), mine, foe.name, R.el_name(foe.element), theirs))]
        i = self.ui.menu(draw, [(GREY, "  " + head)], [self.trainer_cells(m, foe) for m in members],
                         cols=2, desc=desc, start=start, tag=("trainer", members, foe, why),
                         blocked=lambda i: None if members[i].standing else "%s has nobody left standing." % members[i].name)
        return members[i]

    def controller(self, member):
        return None if member.is_hero else member.speaker

    def lord_encounter(self, i, lord_el, world=None):
        """Meet and battle a Lord. True if they joined; False if you fell back."""
        st, ui = self.st, self.ui
        lord = R.HEROES[lord_el]
        lord_sp = (lord["name"].upper(), el_colour(lord_el))
        extra = dict(lord=lord["name"], LORD=lord["name"].upper(), land=lord["land"], blurb=lord["blurb"],
                     master=R.el_name(lord_el) + "master")
        stg = Stage(ui, lord_el)
        if world is None:
            stg.show(("trainer", self.hero_data["look"]))
            self.play("land_enter", stage=stg, **extra)
        stg.show(("trainer", self.hero_data["look"]), ("trainer", lord["look"]))
        self.play("lord_appears", stage=stg, **extra)
        ui.say(stg.draw, lord["challenge"], speaker=lord_sp)
        if self.trial:
            lord_team = [R.make_mon(lord_el, level=T["trial"]["lord_level"])]
        else:
            lord_team = R.make_team(lord_el, T["lords"]["levels"][i], T["lords"]["sizes"][i])
        fighter = st.me
        if st.allies and not self.trial:
            fighter = self.pick_fighter(stg.draw, lord_team[0], self.fmt(STORY["who_lord"], **extra), "lord")
        while True:
            b = Battle(ui, lord_el, self.rng, weather=st.weather)
            b.open()
            for m in lord_team:
                m.restore()
            result = b.fight(fighter.team, lord_team, controller=self.controller(fighter), foe_owner=lord["name"],
                             bag=None if self.trial else st.bag, party=st.party, xp=not self.trial)
            st.turns += b.stats["turns"]
            if result == "win":
                break
            st.losses += 1
            self.play("lord_wins", battle=b, speakers={"lord": lord_sp}, **extra)
            b.close()
            st.rest()
            fighter = st.me
            choices = ["Try again"] if world is None else [STORY["lord_fall_back"]]
            if st.allies:
                choices.append(STORY["lord_ally"])
            pick = self.ui.menu(stg.draw, [(WHITE, "  %s is still in the way." % lord["name"])],
                                [[(WHITE, c)] for c in choices], cols=1, tag=("after_loss", choices))
            if pick == 1:
                fighter = self.choose_trainer(stg.draw, st.allies, lord_team[0], "Who takes on %s?" % lord["name"])
                ui.say(stg.draw, self.fmt(STORY["ally_offers"][0][1], **extra), speaker=fighter.speaker)
            elif world is not None:
                return False

        if fighter.is_hero:
            b.say(self.lord_comment(b.stats, lord_el), speaker=lord_sp, wait=True)
            b.say(self.fmt(STORY["win_general"], trait=R.ELEMENTS["trait"][self.hero]), speaker=lord_sp, wait=True)
        else:
            self.play("win_by_ally", battle=b, speakers={"lord": lord_sp}, ally=fighter.name,
                      ally_they=PRONOUNS[fighter.data["sex"]][0], ally_s="s", **extra)
        self.play("tell_quest", battle=b, **extra)
        b.say(lord["join"], speaker=lord_sp, wait=True)
        b.banner = (self.fmt(STORY["joined"], **extra), (255, 200, 90))
        for _ in range(3):
            b.burst((b.fx.uniform(20, 80), b.fx.uniform(10, 30)), sparks(lord_el) + sparks(self.hero), 30)
            b.wait(10)
        b.wait(20)
        b.banner = None
        hint = STORY["lord_hints"].get(str(i))
        if hint:
            b.say(self.fmt(hint[1], **extra), speaker=lord_sp, wait=True)
        if not self.trial:
            gift = STORY["gifts"][lord_el]
            b.say(self.fmt(STORY["gift_joins"], lord=lord["name"], gift=gift[0].lower(), what=gift[1]), wait=True)
        b.close()
        st.party.append(S.Member(lord_el, lord_team))
        st.coins += 30 + 10 * i
        st.rest()
        self.save()
        return True

    # =====================================================================
    # The Citadel
    # =====================================================================
    def readiness(self):
        """How ready the party looks for the Citadel: 0 fine, 1 worth a word, 2 plainly not."""
        st, c = self.st, T["citadel"]
        mons = [m for p in st.party for m in p.team]
        core = sorted((m.level for m in mons), reverse=True)[:12]        # about two good creatures each
        avg = sum(core) / len(core)
        mine = max(m.level for m in st.team)
        worn = any(m.hp < m.max_hp for m in mons) or any(p.heals < T["heal"]["uses"] for p in st.party)
        if mine < c["final_level"] - 4 or avg < c["nemesis_level"] - 4 or len(mons) < 10:
            return 2
        if worn or mine < c["final_level"] - 1 or avg < c["nemesis_level"] - 2 or len(st.team) < 4 or len(mons) < 18:
            return 1
        return 0

    def citadel_gate(self, world):
        """At the last border. A companion speaks up if the party doesn't look ready; it's still your call."""
        st = self.st
        doubt = self.readiness()
        if doubt and st.allies:
            self.ui.say(world.draw, self.fmt(STORY["ready"]["no" if doubt == 2 else "rest"]), speaker=st.allies[-1].speaker)
        return self.ask(world.draw, STORY["gate_citadel"], ["Go in", "Not yet"], start=1 if doubt else 0,
                        tag=("citadel", doubt)) == 0

    def citadel(self):
        """The climb. True once the top is won; False if you went back to a rest point in the lands."""
        ui = self.ui
        cfg = T["trial"] if self.trial else T["citadel"]
        if not self.st.climbing:
            st = self.st
            st.stage = st.reached = 6
            st.climbing, st.floor = True, 0
            self.play("citadel_intro", stage=Stage(ui, "title"))
        ways = list(R.ORDER)
        random.Random(R.ORDER.index(self.st.hero) + 5).shuffle(ways)
        while self.st.floor < 6:
            st = self.st
            k = st.floor
            self.save()                                # reaching a floor makes its rest point
            if self.trial and k == 1:
                self.play("trial_top", stage=Stage(ui, "rooftop"))
                st.floor = 5
                continue
            cleared = self.floor(k, cfg) if k < 5 else self.top_floor(cfg)
            if cleared:
                if k < 5 and not self.trial:
                    self.blocked_way(ways[k])
                    self.breather()
                st.floor = k + 1
                continue
            st.losses += 1
            hall = Stage(ui, "hall")
            hall.show(("trainer", self.hero_data["look"]))
            here = st.key()
            earlier = self.journal.earlier(here)
            lower = [e for e in earlier if e.startswith("floor")]
            opts = [("Try this floor again", here)]
            if lower:
                opts.append(("Go back down a floor", lower[-1]))
            if len(earlier) > len(lower[-1:]):
                opts.append(("Go back further", None))
            while True:
                pick = opts[self.ask(hall.draw, "What now?", [o[0] for o in opts],
                                     tag=("after_loss", [o[0] for o in opts]))][1]
                if pick is None:
                    pick = self.choose_point(hall.draw, self.journal, earlier)
                if pick is not None:
                    break
            self.load_point(pick)
            if self.st.stage < 6:
                return False
        return True

    def breather(self):
        """Between floors there's no rest, but there is a moment to use what you carry."""
        st, ui = self.st, self.ui
        hall = Stage(ui, "hall")
        hall.show(("trainer", self.hero_data["look"]))
        t = STORY["breather"]
        opts = [t["satchel"], t["heal"], t["teams"], t["go"]]
        sel = 3
        while True:
            sel = ui.menu(hall.draw, [(GREY, "  " + t["ask"])], [[(WHITE, o)] for o in opts], cols=2, start=sel,
                          tag=("breather", st))
            if sel == 0:
                self.pack_satchel(hall.draw)
            elif sel == 1:
                self.heal_touch(hall.draw)
            elif sel == 2:
                m = self.pick_member(hall.draw, "Whose team?")
                if m:
                    self.pack_team(hall.draw, m)
            else:
                return

    def face(self, b, foe, owner, first=None, member=None):
        """One enemy creature, until it falls (True) or nobody is left to face it (False).

        first    the trainer who has to meet it first: companions may only come in
                 once one of that trainer's creatures has fallen to it
        member   whoever has already been chosen to face it (for the creatures
                 you get to see before deciding)
        """
        st = self.st
        must = bool(first and first.standing)
        if must:
            member = first
        elif member is None:
            if not (b.enemy.on and b.enemy.mon is foe):
                b.send_enemy(foe, "%s sends out %s!" % (owner, foe.name))
            member = self.choose_trainer(b.draw, st.party, foe, self.fmt(
                STORY["choose_sender"], enemy=foe.name, enemy_element=R.el_name(foe.element)))
        foe_first = False
        fresh = True                                   # the foe has only just come out
        while True:
            result = b.fight(member.team, [foe], controller=self.controller(member), foe_owner=owner,
                             bag=None if self.trial else st.bag, party=st.party, xp=not self.trial,
                             stop_on_faint=True, can_call=not must, foe_first=foe_first, pick_fresh=fresh)
            fresh = False
            st.turns += b.stats["turns"]
            b.stats["turns"] = 0
            if result == "win":
                return True
            must = False
            if not any(m.standing for m in st.party):
                return False
            head = STORY["call_who"] if result == "call" else self.fmt(STORY["takes_over"], creature=b.player.mon.name)
            nxt = self.choose_trainer(b.draw, st.party, foe, head, start=st.party.index(member))
            foe_first = result == "call" and nxt is not member
            member = nxt

    def floor(self, k, cfg):
        st, ui = self.st, self.ui
        ally = st.party[k + 1]
        nem = ally.data["nemesis"]
        nem_sp = self.villain(ally.element)
        beater = R.beater_of(ally.element)
        extra = dict(floor=k + 1, ally=ally.name, nemesis=nem["name"], nem_first=nem["first"],
                     element=R.el_name(ally.element), beater=R.el_name(beater), Beater=R.el_name(beater),
                     creature=ally.team[0].name)
        speakers = {"ally": ally.speaker, "nemesis": nem_sp}
        stg = Stage(ui, "hall")
        stg.show(("trainer", self.hero_data["look"]), ("trainer", ally.data["look"]), ("trainer", nem["look"]))
        self.play("floor_enter", stage=stg, **extra)
        ui.say(stg.draw, self.fmt(nem["taunt"], **extra), speaker=nem_sp)
        self.play("ally_claims" if ally.standing else "ally_out", stage=stg, speakers=speakers, **extra)
        if k == 0 and ally.standing:
            self.play("own_first", stage=stg, **extra)

        b = Battle(ui, "hall", self.rng)
        b.open()
        size = 1 if self.trial else cfg["nemesis_sizes"][k]
        for foe in R.make_team(ally.element, cfg["nemesis_level"], size, "shadow"):
            if not self.face(b, foe, nem["first"], first=ally):
                return self.floor_lost(b)

        # the one more that shouldn't be possible: here you see it before you choose
        self.play("first_down", battle=b, speakers=speakers, **extra)
        sixth = R.make_mon(beater, "shadow", cfg["sixth_level"])
        b.send_enemy(sixth, "%s sends out %s!" % (nem["first"], sixth.name))
        self.play("sixth_reveal_first" if k == 0 else "sixth_reveal_later", battle=b, speakers=speakers, **extra)
        now = next((m for m in st.party if b.player.mon in m.team), st.me)
        choice = self.choose_trainer(b.draw, st.party, sixth, self.fmt(
            STORY["choose_sender"], enemy=sixth.name, enemy_element=R.el_name(sixth.element)),
            start=st.party.index(now))
        if not self.face(b, sixth, nem["first"], member=choice):
            return self.floor_lost(b)
        b.say(nem["beaten"], speaker=nem_sp, wait=True)
        hint = STORY["floor_hints"].get(str(k))       # something noticed on the way up
        if hint and not self.trial:
            b.say(self.fmt(hint[1], **extra), speaker=speakers[hint[0]], wait=True)
        self.play("floor_clear", battle=b, **extra)
        b.close()
        return True

    def floor_lost(self, b):
        self.play("floor_lost", battle=b)
        b.close()
        return False

    def blocked_way(self, answer):
        """Between floors: something bars the way, and one nature's power clears it."""
        st, ui = self.st, self.ui
        cv = backdrops.blocked(answer, ui.S)
        text = STORY["blocked"][answer]

        def draw():
            return cv
        ui.say(draw, text["scene"])
        while True:
            cells = [[(WHITE, m.name.ljust(9)), (el_colour(m.element), R.el_name(m.element))] for m in st.party]
            i = ui.menu(draw, [(GREY, "  " + STORY["blocked_ask"])], cells, cols=2,
                        desc=lambda i: [(GREY, "  " + text["scene"])], tag=("blocked", st.party, answer))
            m = st.party[i]
            if m.element == answer:
                ui.say(draw, text["done"])
                return
            for mon in m.team:
                if mon.alive:
                    mon.hp = max(1, mon.hp - max(1, mon.max_hp // 10))
            ui.say(draw, self.fmt(STORY["blocked_fail"], trainer=m.name))

    def top_floor(self, cfg):
        st, ui = self.st, self.ui
        nem = self.hero_data["nemesis"]
        nem_sp = self.villain(self.hero)
        speakers = {"nemesis": nem_sp}
        stg = Stage(ui, "rooftop")
        self.play("final_enter", stage=stg, speakers=speakers)
        if st.me.standing:
            self.play("own_first", stage=stg, ally=self.hero_data["name"], nem_first=nem["first"])
        else:
            self.play("final_no_creature", stage=stg, speakers=speakers)

        b = Battle(ui, "rooftop", self.rng)
        b.open()
        size = 1 if self.trial else cfg["final_size"]
        for foe in R.make_team(self.hero, cfg["final_level"], size, "shadow"):
            if not self.face(b, foe, nem["first"], first=st.me):
                return self.floor_lost(b)

        # the hybrid: like the others' one more, you see it before you choose
        self.play("final_first_down", battle=b, speakers=speakers)
        hybrid = R.make_hybrid(self.hero, cfg["hybrid_level"])
        b.send_enemy(hybrid, "%s sends out %s!" % (nem["first"], hybrid.name))
        now = next((m for m in st.party if b.player.mon in m.team), st.me)
        choice = self.choose_trainer(b.draw, st.party, hybrid, self.fmt(
            STORY["choose_sender"], enemy=hybrid.name, enemy_element=R.el_name(hybrid.element)),
            start=st.party.index(now))
        first = R.living(choice.team)[0]
        if b.player.mon is not first or not b.player.on:
            b.recall_player("%s, come back!" % b.player.mon.name)
            b.send_player(first, ("Go, %s!" if choice.is_hero else choice.name + " sends in %s!") % first.name)
        lines = STORY["hybrid_reveal"]
        b.say(self.fmt(lines[0][1]), wait=True)
        b.morph_enemy(hybrid.best_form(first.element))
        for who, text in lines[1:]:
            b.say(self.fmt(text), speaker=self.speaker(who, **speakers), wait=True)
        if st.allies:
            b.say(self.fmt(STORY["final_ally_cheer"][0][1]), speaker=st.allies[-1].speaker, wait=True)

        def reshape(mon):
            form = hybrid.best_form(mon.element)
            if hybrid.alive and form != hybrid.element:
                b.say("%s shifts again!" % hybrid.name, hold=6)
                b.morph_enemy(form)
        b.after_send = reshape
        won = self.face(b, hybrid, nem["first"], member=choice)
        b.after_send = None
        if not won:
            return self.floor_lost(b)
        b.wait(10)
        b.close()
        return True

    # =====================================================================
    # Endings
    # =====================================================================
    def outro(self):
        st = self.st
        speakers = {"nemesis": self.villain(self.hero)}
        if st.allies:
            speakers.update(ally=st.allies[-1].speaker, ally2=st.allies[0].speaker)
        self.play("outro", stage=Stage(self.ui, "rooftop"), speakers=speakers)
        if st.allies:
            self.play("outro_stairs", stage=Stage(self.ui, "hall"), speakers=speakers)
        self.wedding()

    def wedding_looks(self):
        """Everyone's best clothes and best mood. (Kept, so each figure is only drawn once.)"""
        if getattr(self, "_wedding", None) is None:
            hero, other = self.hero_data, self.hero_data["sweetheart"]
            white, black = [250, 248, 252], [30, 30, 40]

            def bride(look):
                return dict(look, mood="happy", coat=white, shirt=[255, 255, 255], belt=[238, 214, 150], trim=[238, 214, 150],
                            scarf=white, scarf_tail=False, gown=True, hat=white, hat_style="veil", boots=white)

            def groom(look):
                return dict(look, mood="happy", coat=black, shirt=[250, 250, 255], belt=[60, 60, 74], trim=[96, 96, 112],
                            scarf=[20, 20, 28], scarf_tail=False, legs=[44, 44, 56], boots=[18, 18, 24], hat=black,
                            hat_style="tophat")
            hero_look = bride(hero["look"]) if hero["sex"] == "f" else groom(hero["look"])
            other_look = groom(other["look"]) if hero["sex"] == "f" else bride(other["look"])
            self._wedding = (hero_look, other_look, [dict(m.data["look"], mood="happy") for m in self.st.allies][:5])
        return self._wedding

    def wedding_scene(self):
        """The last picture: the same rooftop, in spring. Everyone came back."""
        st = self.st
        s = self.ui.S
        cv = backdrops.backdrop("wedding", s, platforms=False).copy()
        hero_look, other_look, friends = self.wedding_looks()
        pets = [R.CREATURES["starter"][m.element] for m in st.allies][:5]
        shade = (150, 136, 160)

        def person(look, x, y, k, left):
            cv.ellipse(x, y + 0.5, 8 * k, 1.1, shade)
            trainers.small(look, s, k, flip=left).blit(cv, int(x * s), int(y * s))

        def pet(sid, x, y, h, left):
            spr = creatures.frames(sid, "normal", None, s, h)[0]
            (spr if left else spr.flipped()).blit(cv, int(x * s), int(y * s))

        # the five guests stand below, to either side; nobody stands behind the couple
        # (x, feet y, size, faces left, where their creature sits)
        guests = [(6, 58.5, 0.5, False, (11.5, 59.7, 8)), (17, 57.5, 0.47, False, (22.5, 59.7, 8)),
                  (93.5, 58.5, 0.5, True, (88, 59.7, 8)), (82, 57.5, 0.47, True, (70.5, 52.6, 7)),
                  (28, 56.8, 0.45, False, (35, 59.7, 8))]
        placed = sorted(zip(guests, friends, pets), key=lambda t: t[0][1])
        for (x, y, k, left, at), look, sid in placed:
            person(look, x, y, k, left)
        for (x, y, k, left, (px, py, ph)), look, sid in placed:
            pet(sid, px, py, ph, left)
        person(hero_look, 45, 45.5, 0.46, False)
        person(other_look, 55, 45.5, 0.46, True)
        mine, theirs = R.CREATURES["starter"][self.hero], self.hero_data["sweetheart"]["creature"]
        pet(mine, 36.5, 46, 8, False)
        pet(theirs, 63.5, 46, 8, True)
        # and at the foot of the steps, a young one that takes after both of them
        creatures.frames(theirs, "kin", self.hero, s, 9)[0].blit(cv, int(50 * s), int(59.8 * s))
        # the bride's flowers
        bx = 45 + 2.8 if self.hero_data["sex"] == "f" else 55 - 2.8
        for dx, dy, col in ((0, 0, (250, 150, 170)), (-1, -1, (255, 246, 214)), (1, -1, (255, 236, 240)), (0, 1, (110, 170, 110))):
            cv.set(bx + dx, 37 + dy, col)
        return cv

    def wedding(self):
        """No words. The screen goes dark, and comes back on the wedding."""
        ui = self.ui
        dark = Canvas(100, 60, scale=ui.S, fill=(0, 0, 0))
        ui.take()
        ui.pause(lambda: dark, 26, [])
        self.last_scene = self.wedding_scene()
        ui.pause(lambda: self.last_scene, 60, [])
        ui.take()

    def closing(self, title, lines, last):
        st = Stage(self.ui, "title", title=(title, 2, 20, (255, 214, 120)))
        rows = [[(WHITE, "  " + line)] for line in lines][:4]
        rows += [[]] * (4 - len(rows)) + [[(GOLD, "  " + last)]]
        self.ui.take()
        self.ui.pause(st.draw, 20, rows)
        self.ui.take()
        while True:
            self.ui.frame(st.draw(), rows)
            if self.ui.advanced():
                return

    def end(self):
        """THE END, under the wedding. The picture says the rest."""
        end = STORY["end"]
        scene = self.last_scene
        rows = [[], [(GOLD, "  " + end["title"])], [],
                [(GREY, "  " + end["stats"].format(losses=self.st.losses, turns=self.st.turns))],
                [(GOLD, "  " + end["again"])]]
        self.ui.take()
        while True:
            self.ui.frame(scene, rows)
            if self.ui.advanced():
                return

    # =====================================================================
    # The two ways to play
    # =====================================================================
    def play_trial(self, hero):
        self.trial = True
        self.journal = S.Journal()                     # kept in memory only
        try:
            st = S.State(hero)
            cfg = T["trial"]
            st.party[0].team = [R.make_mon(hero, level=cfg["hero_level"])]
            self.setup(st)
            self.play("trial_start", stage=Stage(self.ui, hero))
            self.lord_encounter(0, st.order[0])
            st.party[1].team = [R.make_mon(st.order[0], level=cfg["hero_level"])]
            for el in st.order[1:]:
                st.party.append(S.Member(el, [R.make_mon(el, level=cfg["hero_level"])]))
            st.rest()
            self.play("trial_bridge", stage=Stage(self.ui, "title"))
            self.citadel()
            self.outro()
            end = STORY["trial_end"]
            self.closing(end["title"], wrap(end["line"], INNER - 4)[:3], end["again"])
        finally:
            self.trial = False

    def play_journey(self, journal, st=None, intro=False):
        """journal: where the rest points are kept. st: a journey to start from
        (otherwise carry on from the journal's current rest point)."""
        self.trial = False
        self.journal = journal
        self.entry = None
        self.setup(st or journal.get())
        if intro:
            stg = Stage(self.ui, self.st.hero)
            self.play("hero_intro", stage=stg)
            self.play("home", stage=stg)
        while True:
            self.explore()
            if self.citadel():
                break
        self.outro()
        self.end()
        if journal.path:
            S.erase(journal.path)

    def run(self):
        """One visit to the title screen and whatever is chosen there."""
        pick, journal = self.title_menu()
        if pick == "continue":
            self.play_journey(journal)
        elif pick == "trial":
            self.play_trial(self.choose_hero())
        else:
            self.intro()
            fresh = S.Journal(None if self.no_save else (self.save_path or S.SAVE_PATH))
            self.play_journey(fresh, S.State(self.choose_hero()), intro=True)
