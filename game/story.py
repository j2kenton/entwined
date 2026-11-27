"""The journey, start to finish.

Full journey:  title > intro > choose a hero > home land > five lands, each
with a Lord > the Citadel (five floors, blocked ways, the top) > ending.
Quick taste:   one Lord, one Citadel floor and the top, with no walking.

Everything hero-specific comes from data/heroes.json; every line of text
comes from data/story.json, with {placeholders} filled in for the chosen hero.
"""
import random

from . import rules as R
from . import state as S
from . import world as W
from .art import backdrops, creatures, trainers
from .battle import Battle, el_colour, sparks
from .engine.canvas import darker, draw_text, mix, text_width
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
        who("sw", "m" if h["sex"] == "f" else "f")
        beater = R.beater_of(st.hero)
        ctx.update(hero=h["name"], land=h["land"], folk=h["folk"], element=R.el_name(st.hero),
                   creature=R.SPECIES[R.CREATURES["starter"][st.hero]]["name"],
                   nemesis=h["nemesis"]["name"], nem_first=h["nemesis"]["first"],
                   sweetheart=h["sweetheart"]["name"], sw_element=R.el_name(beater),
                   beater=R.el_name(beater), Beater=R.el_name(beater),
                   hybrid=R.CREATURES["hybrid"]["names"][st.hero])
        self.ctx = ctx

    no_save = False                # previews started from the command line don't touch your save

    def save(self):
        if not self.trial and not self.no_save:
            self.st.save(self.save_path)

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
                if len(entry) > 2:
                    stage.show(*self.figures(entry[2]))
                self.ui.say(stage.draw, text, speaker=sp)

    def ask(self, draw, question, options, start=0, tag=None):
        """A plain question with a few answers. Returns the index picked."""
        return self.ui.menu(draw, [(WHITE, "  " + question)], [[(WHITE, o)] for o in options], cols=1,
                            start=start, tag=tag)

    def voice(self, element):
        """How a gift's owner speaks up: by name if an ally, as narration if it's you."""
        m = next(m for m in self.st.party if m.element == element)
        return None if m.is_hero else m.speaker

    # =====================================================================
    # Title, intro, choosing a hero
    # =====================================================================
    def title_menu(self):
        st = Stage(self.ui, "title", title=("ENTWINED", 2, 20, (255, 214, 120)))
        m = STORY["menu"]
        saved = S.load(self.save_path)
        while True:
            keys = (["continue"] if saved else []) + ["new", "trial"]
            opts = [[(WHITE, m[k])] for k in keys]

            def desc(i):
                if keys[i] == "continue":
                    h = R.HEROES[saved.hero]
                    where = "the Citadel" if saved.stage >= 6 else R.HEROES[saved.land()]["land"]
                    return [(GREY, "  %s, in %s." % (h["name"], where))]
                return [(DIM, "  " + m["hint"])]
            pick = keys[self.ui.menu(st.draw, [(GREY, "  A creature-battling adventure, in your terminal.")],
                                     opts, cols=1, desc=desc)]
            if pick == "new" and saved:
                if self.ask(st.draw, m["new_warning"], ["Begin again", "Go back"], start=1) == 1:
                    continue
            return pick, saved

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
        lo, hi = T["wild_levels"][st.stage]
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
        world = W.World(ui, land, self.hero_data["look"], st.pos or land.start,
                        navigator=st.has("wave"), gate_open=home or st.lord_beaten,
                        lord_look=None if (home or st.lord_beaten) else lord["look"], picked=st.picked)
        world.title = lord["land"].upper()
        world.pilot = self.pilot
        self.spawn_wild(world)
        rows = self.hud(world)
        extra = dict(lord=lord["name"], land=lord["land"], land_element=R.el_name(el))
        for k, v in zip(("they", "them", "their"), PRONOUNS[lord["sex"]]):
            extra["Lord_" + k] = v.capitalize()
        if first_visit:
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
                ui.say(world.draw, STORY["gate_shut"])
            elif kind == "menu":
                self.pack(world)
            elif kind == "gate":
                q = STORY["gate_citadel"] if st.stage == 5 else self.fmt(
                    STORY["gate_ask"], next_land=R.HEROES[st.order[st.stage]]["land"])
                if self.ask(world.draw, q, ["Cross the border", "Stay a while longer"]) == 0:
                    st.stage += 1
                    st.pos, st.picked, st.lord_beaten, st.camp_used = None, [], False, False
                    return
                world.x -= 1                           # step back from the gate
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
        st.picked = [list(p) for p in world.picked]

    def wild_battle(self, world, w):
        st = self.st
        b = Battle(self.ui, world.land.element, self.rng, weather=st.weather)
        b.open()
        result = b.fight(st.team, [w.mon], wild=True, bag=st.bag, hero_element=st.hero, xp=True)
        st.turns += b.stats["turns"]
        if result == "bonded":
            w.mon.clear_status()
            st.team.append(w.mon)
            b.say(self.fmt(STORY["bonded"], creature=w.mon.name), wait=True)
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

    # ----- the market -----------------------------------------------------
    def market(self, world):
        st, ui = self.st, self.ui
        stock = ["remedy", "tonic", "charm", "lure"]
        sel = 0
        while True:
            sellable = sum(st.bag.get(k, 0) * R.ITEMS[k]["sell"] for k in ("herb", "shard"))
            opts = [[(WHITE, R.ITEMS[k]["name"].ljust(10)), (GOLD, ("%d coins" % R.ITEMS[k]["price"]).ljust(11)),
                     (GREY, "you have %d" % st.bag.get(k, 0))] for k in stock]
            opts.append([(WHITE if sellable else DIM, "Sell herbs and shards"), (GOLD, "  +%d coins" % sellable)])
            opts.append([(GREY, "Leave")])
            head = [(WHITE, "  " + STORY["market_ask"]), (GOLD, "      You have %d coins." % st.coins)]

            def blocked(i):
                if i < len(stock):
                    if st.coins < R.ITEMS[stock[i]]["price"]:
                        return STORY["market_poor"]
                    if not st.can_carry(stock[i]):
                        return STORY["market_full"]
                elif i == len(stock) and not sellable:
                    return "You've nothing to sell."
                return None

            def desc(i):
                if i < len(stock):
                    return [(GREY, "  " + R.ITEMS[stock[i]]["text"])]
                return [(GREY, "  Herbs fetch 4 coins, shards 6." if i == len(stock) else "  Back to the road.")]
            sel = ui.menu(world.draw, head, opts, cols=2, start=sel, blocked=blocked, desc=desc,
                          tag=("market", stock, st))
            if sel < len(stock):
                st.coins -= R.ITEMS[stock[sel]]["price"]
                st.add(stock[sel])
            elif sel == len(stock):
                st.coins += sellable
                st.bag["herb"] = st.bag["shard"] = 0
            else:
                return

    # ----- your pack (the M key) -------------------------------------------
    def pack(self, world):
        st, ui = self.st, self.ui
        while True:
            opts = ["Team", "Satchel"]
            if st.allies:
                opts.append("Companions")
            if st.has("soil"):
                opts.append("Make camp")
            if st.has("flame") and st.bag.get("shard", 0) >= 2:
                opts.append("Forge a charm")
            opts.append("Back to the road")
            pick = opts[ui.menu(world.draw, [(GREY, "  Your pack")], [[(WHITE, o)] for o in opts], cols=2,
                                tag=("pack", opts))]
            if pick == "Team":
                self.pack_team(world)
            elif pick == "Satchel":
                self.pack_satchel(world)
            elif pick == "Companions":
                allies = st.allies
                cells = [[(el_colour(m.element), m.name.ljust(9)), (GREY, STORY["gifts"][m.element][0])] for m in allies]
                ui.menu(world.draw, [(GREY, "  Travelling with you")], cells + [[(GREY, "Back")]], cols=2,
                        desc=lambda i: [(GREY, "  " + (STORY["gifts"][allies[i].element][1] if i < len(allies) else "Go back."))])
            elif pick == "Make camp":
                if st.camp_used:
                    ui.say(world.draw, STORY["camp_used"])
                else:
                    st.camp_used = True
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

    def pack_team(self, world):
        st, ui = self.st, self.ui
        while True:
            team = st.team
            cells = [[(WHITE if m.alive else DIM, m.name.ljust(11)), (GREY, ("L%d" % m.level).ljust(5)),
                      ((120, 220, 130) if m.alive else DIM, ("%d/%d" % (m.hp, m.max_hp)) if m.alive else "fainted")]
                     for m in team] + [[(GREY, "Back")]]

            def desc(i):
                if i >= len(team):
                    return [(GREY, "  Go back.")]
                m = team[i]
                nxt = "" if m.level >= T["level_cap"] else "  %d to next level." % (R.xp_to_next(m.level) - m.xp)
                return [(GREY, "  %s.%s  Knows: %s" % (R.el_name(m.element), nxt, ", ".join(v.name.title() for v in m.moves)))]
            i = ui.menu(world.draw, [(GREY, "  Your team. The first one goes into battle first.")], cells, cols=2, desc=desc)
            if i >= len(team):
                return
            m = team[i]
            acts = ["Put it first"] + (["Let it go"] if len(team) > 1 else []) + ["Back"]
            a = acts[self.ask(world.draw, m.name, acts)]
            if a == "Put it first":
                team.remove(m)
                team.insert(0, m)
            elif a == "Let it go":
                if self.ask(world.draw, "Let %s go back to the wild? It won't return." % m.name,
                            ["Keep it", "Let it go"], tag=("release",)) == 1:
                    team.remove(m)

    def pack_satchel(self, world):
        st, ui = self.st, self.ui
        while True:
            keys = [k for k, n in st.bag.items() if n]
            if not keys:
                ui.say(world.draw, "Your satchel is empty.")
                return
            cells = [[(WHITE, R.ITEMS[k]["name"].ljust(11)), (GREY, "x%d" % st.bag[k])] for k in keys] + [[(GREY, "Back")]]
            i = ui.menu(world.draw, [(GREY, "  Your satchel   (%d of %d bundles)" % (st.slots_used(), S.SATCHEL_SLOTS))],
                        cells, cols=2,
                        desc=lambda i: [(GREY, "  " + (R.ITEMS[keys[i]]["text"] if i < len(keys) else "Go back."))])
            if i >= len(keys):
                return
            k = keys[i]
            if k not in ("remedy", "tonic"):
                continue
            team = st.team
            cells = [[(WHITE if m.alive else DIM, m.name.ljust(11)),
                      (GREY, ("%d/%d" % (m.hp, m.max_hp)) if m.alive else "fainted")] for m in team] + [[(GREY, "Back")]]
            j = ui.menu(world.draw, [(GREY, "  Use the %s on which creature?" % R.ITEMS[k]["name"].lower())], cells, cols=2)
            if j < len(team):
                msg = R.use_item(k, team[j])
                if msg:
                    st.bag[k] -= 1
                ui.say(world.draw, msg or "It would do %s no good right now." % team[j].name)

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

    def choose_trainer(self, draw, members, foe, head, start=0):
        """Pick whose team goes in. Returns the Member."""
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
                         cols=2, desc=desc, start=start, tag=("trainer", members, foe),
                         blocked=lambda i: None if members[i].standing else "%s has nobody left standing." % members[i].name)
        return members[i]

    def controller(self, member):
        return None if member.is_hero else member.speaker

    def lord_encounter(self, i, lord_el, world=None):
        """Meet and battle a Lord. True if they joined; False if you fell back."""
        st, ui = self.st, self.ui
        lord = R.HEROES[lord_el]
        lord_sp = (lord["name"].upper(), el_colour(lord_el))
        extra = dict(lord=lord["name"], LORD=lord["name"].upper(), land=lord["land"], blurb=lord["blurb"])
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
        while True:
            b = Battle(ui, lord_el, self.rng, weather=st.weather)
            b.open()
            for m in lord_team:
                m.restore()
            result = b.fight(fighter.team, lord_team, controller=self.controller(fighter), foe_owner=lord["name"],
                             bag=None if self.trial else st.bag, hero_element=st.hero,
                             xp=fighter.is_hero and not self.trial)
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
        st.lord_beaten = True
        st.coins += 30 + 10 * i
        st.rest()
        self.save()
        return True

    # =====================================================================
    # The Citadel
    # =====================================================================
    def level(self, wanted):
        """A Citadel level: as written for a well-trained party, lower if yours isn't."""
        if self.trial:
            return wanted
        top = max(m.level for m in self.st.team)
        return max(5, min(wanted, top + wanted - T["citadel"]["ally_level"]))

    def citadel(self):
        st, ui = self.st, self.ui
        cfg = T["trial"] if self.trial else T["citadel"]
        if self.trial:
            self.play("citadel_intro", stage=Stage(ui, "title"))
        elif st.stage < 6 or st.pos is None:
            st.stage = 6
            top = max(m.level for m in st.team)
            for ally in st.allies:
                for mon in ally.team:
                    mon.set_level(max(mon.level, top))
            st.rest()
            st.pos = (0, 0)                     # marks "inside the Citadel"
            st.floor = 0
            stg = Stage(ui, "title")
            self.play("allies_ready", stage=stg)
            self.play("citadel_intro", stage=stg)
        snaps = {}
        ways = list(R.ORDER)
        random.Random(R.ORDER.index(st.hero) + 5).shuffle(ways)
        k = st.floor
        while k < 6:
            if k not in snaps:
                snaps[k] = ({m.element: [mon.snapshot() for mon in m.team] for m in st.party}, dict(st.bag))
            st.floor = k
            self.save()
            if self.trial and k == 1:
                self.play("trial_top", stage=Stage(ui, "rooftop"))
                k = 5
                continue
            cleared = self.floor(k, cfg) if k < 5 else self.top_floor(cfg)
            if cleared:
                if k < 5 and not self.trial:
                    self.blocked_way(ways[k])
                snaps.pop(k + 1, None)
                k += 1
                continue
            st.losses += 1
            hall = Stage(ui, "hall")
            hall.show(("trainer", self.hero_data["look"]))
            opts = [("Try this floor again", k)]
            lower = [f for f in snaps if f < k]
            if lower:
                opts.append(("Go back down a floor", max(lower)))
                if min(lower) != max(lower):
                    opts.append(("Go back to floor %d" % (min(lower) + 1), min(lower)))
            k = opts[self.ask(hall.draw, "What now?", [o[0] for o in opts])][1]
            snap, bag = snaps[k]
            for m in st.party:
                for mon, s in zip(m.team, snap[m.element]):
                    mon.load_snapshot(s)
            st.bag = dict(bag)
            for f in [f for f in snaps if f > k]:
                del snaps[f]

    def fight_on(self, b, member, foes, foe_owner):
        """Fight `foes`; when a trainer's team is all down, choose who takes over."""
        st = self.st
        while True:
            result = b.fight(member.team, foes, controller=self.controller(member), foe_owner=foe_owner,
                             bag=None if self.trial else st.bag, hero_element=st.hero)
            st.turns += b.stats["turns"]
            b.stats["turns"] = 0
            if result == "win":
                return True
            if not any(m.standing for m in st.party):
                return False
            member = self.choose_trainer(b.draw, st.party, b.enemy.mon,
                                         "%s's creatures are all down. Who takes over?" % member.name)

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

        b = Battle(ui, "hall", self.rng)
        b.open()
        size = 1 if self.trial else cfg["nemesis_size"]
        foes = R.make_team(ally.element, self.level(cfg["nemesis_level"]), size, "shadow")
        fighter = ally
        if not ally.standing:
            b.send_enemy(foes[0], "%s sends out %s!" % (nem["name"], foes[0].name))
            fighter = self.choose_trainer(b.draw, st.party, foes[0], self.fmt(
                STORY["choose_sender"], enemy=foes[0].name, enemy_element=R.el_name(foes[0].element)))
        if not self.fight_on(b, fighter, foes, nem["name"]):
            return self.floor_lost(b)

        # the hidden extra creature
        self.play("first_down", battle=b, speakers=speakers, **extra)
        sixth = R.make_mon(beater, "shadow", self.level(cfg["sixth_level"]))
        b.send_enemy(sixth, "%s sends out %s!" % (nem["name"], sixth.name))
        self.play("sixth_reveal_first" if k == 0 else "sixth_reveal_later", battle=b, speakers=speakers, **extra)
        now = next((m for m in st.party if b.player.mon in m.team), st.me)
        choice = self.choose_trainer(b.draw, st.party, sixth, self.fmt(
            STORY["choose_sender"], enemy=sixth.name, enemy_element=R.el_name(sixth.element)),
            start=st.party.index(now))
        if not self.fight_on(b, choice, [sixth], nem["name"]):
            return self.floor_lost(b)
        b.say(nem["beaten"], speaker=nem_sp, wait=True)
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
        if not st.me.standing:
            self.play("final_no_creature", stage=stg, speakers=speakers)
            return False

        b = Battle(ui, "rooftop", self.rng)
        b.open()
        size = 1 if self.trial else cfg["final_size"]
        foes = R.make_team(self.hero, self.level(cfg["final_level"]), size, "shadow")
        result = b.fight(st.team, foes, foe_owner=nem["name"], bag=None if self.trial else st.bag, hero_element=st.hero)
        st.turns += b.stats["turns"]
        b.stats["turns"] = 0
        if result != "win":
            return self.floor_lost(b)

        # the hybrid
        self.play("final_first_down", battle=b, speakers=speakers)
        hybrid = R.make_hybrid(self.hero, self.level(cfg["hybrid_level"]))
        b.send_enemy(hybrid, "%s sends out %s!" % (nem["name"], hybrid.name))
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
        won = self.fight_on(b, choice, [hybrid], nem["name"])
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
        self.play("outro", stage=Stage(self.ui, "rooftop"), speakers={"nemesis": self.villain(self.hero)})

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
        end = STORY["end"]
        lines = wrap(self.fmt(end["line"], land=self.hero_data["land"]), INNER - 4)[:2]
        lines += [""] * (3 - len(lines)) + [end["stats"].format(losses=self.st.losses, turns=self.st.turns)]
        self.closing(end["title"], lines, end["again"])

    # =====================================================================
    # The two ways to play
    # =====================================================================
    def play_trial(self, hero):
        self.trial = True
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

    def play_journey(self, st, fresh):
        self.trial = False
        self.setup(st)
        if fresh:
            stg = Stage(self.ui, st.hero)
            self.play("hero_intro", stage=stg)
            self.play("home", stage=stg)
        self.explore()
        self.citadel()
        self.outro()
        self.end()
        if not self.no_save:
            S.erase(self.save_path)

    def run(self):
        """One visit to the title screen and whatever is chosen there."""
        pick, saved = self.title_menu()
        if pick == "continue":
            self.play_journey(saved, fresh=False)
        elif pick == "trial":
            self.play_trial(self.choose_hero())
        else:
            self.intro()
            self.play_journey(S.State(self.choose_hero()), fresh=True)
