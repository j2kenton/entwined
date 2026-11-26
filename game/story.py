"""The campaign, start to finish:

title > intro > choose a hero > five Lords > the Citadel (five floors and the
top) > outro > end screen.

Everything hero-specific comes from data/heroes.json; every line of text
comes from data/story.json, with {placeholders} filled in for the chosen hero.
"""
import random

from . import rules as R
from .art import backdrops, creatures, trainers
from .battle import Battle, el_colour, sparks
from .engine.canvas import darker, draw_text, lighter, mix, text_width
from .engine.ui import DIM, GOLD, GREY, RED, WHITE

STORY = R.load("story")
T = R.TUNING
PRONOUNS = {"f": ("she", "her", "her"), "m": ("he", "him", "his")}
SHORT_WORD = {"strong": "strong", "slightly strong": "sl. strong", "even": "even",
              "slightly weak": "sl. weak", "weak": "weak"}


class Member:
    """Someone in your party: the hero or an ally, with their creature."""

    def __init__(self, element, power, is_hero=False):
        self.element = element
        self.data = R.HEROES[element]
        self.name = self.data["name"]
        self.is_hero = is_hero
        self.mon = R.make_mon(element, power=power)

    @property
    def speaker(self):
        return (self.name.upper(), el_colour(self.element))


class Stage:
    """A story picture: a backdrop with up to three figures standing on it."""

    def __init__(self, ui, backdrop, title=None):
        self.ui = ui
        self.kind = backdrop
        self.title = title
        self.cv = None
        self.show()

    def show(self, *figures):
        """figures: ("trainer", look) or ("creature", element)."""
        S = self.ui.S
        cv = backdrops.backdrop(self.kind, S, platforms=False).copy()
        spots = {0: [], 1: [50], 2: [28, 72], 3: [20, 50, 80]}[len(figures)]
        for i, ((kind, what), x) in enumerate(zip(figures, spots)):
            flip = len(figures) > 1 and i == len(figures) - 1
            cv.ellipse(x, 57, 11, 1.4, darker(cv.get(x, 58) or (40, 40, 40), 0.7))
            if kind == "trainer":
                trainers.sprite(what, S, flip=flip).blit(cv, int(x * S), int(57 * S))
            else:
                spr = creatures.frames(what, "normal", None, S, 30)[0]
                (spr.flipped() if not flip else spr).blit(cv, int(x * S), int(57 * S))
        if self.title:
            text, size, y, col = self.title
            x = (100 - text_width(text) * size) // 2
            draw_text(cv, x, y, text, col, shadow=(20, 10, 30), size=size)
        self.cv = cv

    def draw(self):
        return self.cv


class Game:
    def __init__(self, ui, rng=None):
        self.ui = ui
        self.rng = rng or random.Random()
        self.losses = 0
        self.turns = 0

    # =====================================================================
    # Text
    # =====================================================================
    def fmt(self, text, **extra):
        ctx = dict(self.ctx)
        ctx.update(extra)
        return text.format(**ctx)

    def base_ctx(self, element):
        h = R.HEROES[element]
        ctx = {}

        def who(prefix, sex):
            they, them, their = PRONOUNS[sex]
            for k, v in (("they", they), ("them", them), ("their", their)):
                ctx["%s_%s" % (prefix, k)] = v
                ctx["%s_%s" % (prefix.capitalize(), k)] = v.capitalize()
        other = "m" if h["sex"] == "f" else "f"
        who("hero", h["sex"])
        who("nem", h["sex"])
        who("sw", other)
        beater = R.beater_of(element)
        ctx.update(hero=h["name"], land=h["land"], folk=h["folk"], element=R.el_name(element),
                   creature=R.CREATURES["species"][element]["name"],
                   nemesis=h["nemesis"]["name"], nem_first=h["nemesis"]["first"],
                   sweetheart=h["sweetheart"]["name"], sw_element=R.el_name(beater),
                   beater=R.el_name(beater), Beater=R.el_name(beater),
                   hybrid=R.CREATURES["hybrid"]["names"][element])
        return ctx

    def speaker(self, who, **alt):
        """Map a story speaker key to (NAME, colour)."""
        if who == "narr":
            return None
        if who == "hero":
            return self.me.speaker
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

    def figures(self, names, **alt):
        out = []
        for n in names:
            if n == "hero":
                out.append(("trainer", self.hero_data["look"]))
            elif n == "nemesis":
                out.append(("trainer", alt.get("nemesis_look", self.hero_data["nemesis"]["look"])))
            elif n == "sweetheart":
                out.append(("trainer", self.hero_data["sweetheart"]["look"]))
            elif n == "creature":
                out.append(("creature", self.hero))
            elif n in alt:
                out.append(alt[n])
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
                    stage.show(*self.figures(entry[2], **speakers))
                self.ui.say(stage.draw, text, speaker=sp)

    # =====================================================================
    # Title, intro, choosing a hero
    # =====================================================================
    def title(self):
        st = Stage(self.ui, "title", title=("ENTWINED", 2, 20, (255, 214, 120)))
        rows = [[], [(WHITE, "  A creature-battling adventure, in your terminal.")], [],
                [(GREY, "  Arrow keys or WASD choose.  Enter confirms and moves text along.  Esc quits.")],
                [(GOLD, "  Press Enter to begin.")]]
        self.ui.take()
        while True:
            blink = (self.ui.tick // 10) % 2 == 0
            self.ui.frame(st.draw(), rows[:4] + [rows[4] if blink else []])
            if self.ui.advanced():
                return

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
                st.show(("trainer", h["look"]), ("creature", el))
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
                 (col, R.CREATURES["species"][el]["name"]), (GREY, "     " + h["about"])],
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

    def start(self, element):
        self.hero = element
        self.hero_data = R.HEROES[element]
        self.ctx = self.base_ctx(element)
        self.level = T["start_level"]
        self.me = Member(element, R.level_power(self.level), is_hero=True)
        self.party = [self.me]
        self.order = R.land_order(element)

    # =====================================================================
    # The journey: five Lords
    # =====================================================================
    def lord_comment(self, stats, lord_el):
        """The specific half of a Lord's comment: why you won."""
        p_el = self.hero
        if stats["min_ratio"] < 0.3:
            key = "clutch"
        elif stats["turns"] <= 3:
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
                        e_noun=R.ELEMENTS["noun"][lord_el])

    def hint_cells(self, member, foe, fainted_ok=False):
        mon = member.mon
        alive = mon.alive
        word = SHORT_WORD[R.effect_word(R.mult(mon.element, foe.element))]
        col = el_colour(mon.element)
        return [(WHITE if alive else DIM, mon.name.ljust(11)),
                (col if alive else DIM, R.el_name(mon.element).ljust(10)),
                (GREY if alive else DIM, ("%d/%d" % (mon.hp, mon.max_hp)).ljust(7)),
                (GOLD if alive else DIM, (word if alive else "fainted").ljust(11))]

    def choose_sender(self, draw, members, foe, head, start=0):
        """Pick which party member's creature goes in. Returns the Member."""
        def desc(i):
            m = members[i]
            if not m.mon.alive:
                return [(DIM, "  %s has fainted." % m.mon.name)]
            mine = R.effect_word(R.mult(m.mon.element, foe.element))
            theirs = R.effect_word(R.mult(foe.element, m.mon.element))
            own = "Yours. " if m.is_hero else "%s's. " % m.name
            return [(GREY, "  %sIts %s attacks: %s.   %s's %s attacks on it: %s." % (
                own, R.el_name(m.mon.element), mine, foe.name, R.el_name(foe.element), theirs))]
        i = self.ui.menu(draw, [(GREY, "  " + head)], [self.hint_cells(m, foe) for m in members],
                         cols=2, desc=desc, start=start, tag=("sender", members, foe),
                         blocked=lambda i: None if members[i].mon.alive else "%s has fainted." % members[i].mon.name)
        return members[i]

    def controller(self, member):
        return None if member.is_hero else member.speaker

    def journey(self):
        for i, lord_el in enumerate(self.order):
            self.lord_fight(i, lord_el)

    def lord_fight(self, i, lord_el):
        ui = self.ui
        lord = R.HEROES[lord_el]
        lord_sp = (lord["name"].upper(), el_colour(lord_el))
        extra = dict(lord=lord["name"], LORD=lord["name"].upper(), land=lord["land"], blurb=lord["blurb"])
        for m in self.party:
            m.mon.restore()

        st = Stage(ui, lord_el)
        st.show(("trainer", self.hero_data["look"]))
        self.play("land_enter", stage=st, **extra)
        st.show(("trainer", self.hero_data["look"]), ("trainer", lord["look"]))
        self.play("lord_appears", stage=st, **extra)
        ui.say(st.draw, lord["challenge"], speaker=lord_sp)

        fighter = self.me
        while True:
            b = Battle(ui, lord_el, self.rng)
            b.open()
            foe = R.make_mon(lord_el, power=T["lord_power"][i])
            b.send_enemy(foe, "%s sends out %s!" % (lord["name"], foe.name))
            fighter.mon.restore()
            b.send_player(fighter.mon, "Go, %s!" % fighter.mon.name)
            result = b.fight(self.controller(fighter))
            self.turns += b.stats["turns"]
            if result == "win":
                break
            self.losses += 1
            self.play("lord_wins", battle=b, speakers={"lord": lord_sp}, **extra)
            b.close()
            fighter = self.me
            allies = [m for m in self.party if not m.is_hero]
            if allies:
                pick = ui.menu(st.draw, [(GREY, "  %s is still in the way." % lord["name"])],
                               [[(WHITE, "Try again yourself")], [(WHITE, "Let an ally try")]], cols=1)
                if pick == 1:
                    for m in allies:
                        m.mon.restore()
                    fighter = self.choose_sender(st.draw, allies, foe, "Who takes on %s's %s (%s)?" % (
                        lord["name"], foe.name, R.el_name(lord_el)))
                    ui.say(st.draw, self.fmt(STORY["ally_offers"][0][1], **extra), speaker=fighter.speaker)

        # the Lord's two-part comment, then they join
        if fighter.is_hero:
            b.say(self.lord_comment(b.stats, lord_el), speaker=lord_sp, wait=True)
            b.say(self.fmt(STORY["win_general"], trait=R.ELEMENTS["trait"][self.hero]), speaker=lord_sp, wait=True)
        else:
            they = PRONOUNS[fighter.data["sex"]][0]
            self.play("win_by_ally", battle=b, speakers={"lord": lord_sp}, ally=fighter.name,
                      ally_they=they, ally_s="s", **extra)
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
        self.level += 1
        self.party.append(Member(lord_el, R.level_power(self.level)))
        for m in self.party:
            m.mon.set_power(R.level_power(self.level), keep_ratio=False)
        b.say(self.fmt(STORY["level_up"], level=self.level), wait=True)
        b.close()

    # =====================================================================
    # The Citadel
    # =====================================================================
    def citadel(self, first_floor=0):
        ui = self.ui
        for m in self.party:
            m.mon.restore()
        st = Stage(ui, "title")
        self.play("citadel_intro", stage=st)
        rested = {m.element: m.mon.snapshot() for m in self.party}
        snaps = {}
        k = first_floor
        while k < 6:
            snaps[k] = {m.element: m.mon.snapshot() for m in self.party}
            if (self.floor(k) if k < 5 else self.top_floor()):
                k += 1
                continue
            self.losses += 1
            hall = Stage(ui, "hall")
            hall.show(("trainer", self.hero_data["look"]))
            opts = [("Retry this floor", k)]
            if k > 0:
                opts.append(("Go back down a floor", k - 1))
                opts.append(("Start the Citadel again, fully rested", 0))
            pick = ui.menu(hall.draw, [(GREY, "  What now?")], [[(WHITE, o[0])] for o in opts], cols=1)
            k = opts[pick][1]
            for m in self.party:
                m.mon.load_snapshot(snaps.get(k, rested)[m.element])

    def fight_through(self, b, member, foe, on_send=None, allow_swap=True, first_text=None):
        """Fight `foe`, with party members stepping in as creatures faint."""
        while True:
            who = "Go, %s!" if member.is_hero else member.name + " sends in %s!"
            b.send_player(member.mon, first_text or who % member.mon.name)
            first_text = None
            if on_send:
                on_send(member)
            result = b.fight(self.controller(member))
            self.turns += b.stats["turns"]
            b.stats["turns"] = 0
            if result == "win":
                return True
            if not allow_swap or not any(m.mon.alive for m in self.party):
                return False
            member = self.choose_sender(b.draw, self.party, foe, "%s is down. Who steps in against %s (%s)?" % (
                member.mon.name, foe.name, R.el_name(foe.element)))

    def floor(self, k):
        ui = self.ui
        ally = self.party[k + 1]
        nem = ally.data["nemesis"]
        nem_sp = self.villain(ally.element)
        beater = R.beater_of(ally.element)
        extra = dict(floor=k + 1, ally=ally.name, nemesis=nem["name"], nem_first=nem["first"],
                     element=R.el_name(ally.element), beater=R.el_name(beater), Beater=R.el_name(beater),
                     creature=ally.mon.name)
        speakers = {"ally": ally.speaker, "nemesis": nem_sp}

        st = Stage(ui, "hall")
        st.show(("trainer", self.hero_data["look"]), ("trainer", ally.data["look"]), ("trainer", nem["look"]))
        self.play("floor_enter", stage=st, **extra)
        ui.say(st.draw, self.fmt(nem["taunt"], **extra), speaker=nem_sp)
        if ally.mon.alive:
            self.play("ally_claims", stage=st, speakers=speakers, **extra)
        else:
            self.play("ally_out", stage=st, speakers=speakers, **extra)

        b = Battle(ui, "hall", self.rng)
        b.open()
        first = R.make_mon(ally.element, "shadow", T["citadel_first_power"])
        b.send_enemy(first, "%s sends out %s!" % (nem["name"], first.name))
        fighter = ally if ally.mon.alive else self.choose_sender(
            b.draw, self.party, first, self.fmt(STORY["choose_sender"], enemy=first.name,
                                                enemy_element=R.el_name(first.element)))
        if not self.fight_through(b, fighter, first):
            return self.floor_lost(b)
        fighter = next(m for m in self.party if m.mon is b.player.mon)

        # the hidden sixth creature
        self.play("first_down", battle=b, speakers=speakers, **extra)
        sixth = R.make_mon(beater, "shadow", T["citadel_sixth_power"])
        b.send_enemy(sixth, "%s sends out %s!" % (nem["name"], sixth.name))
        self.play("sixth_reveal_first" if k == 0 else "sixth_reveal_later", battle=b, speakers=speakers, **extra)
        choice = self.choose_sender(b.draw, self.party, sixth, self.fmt(
            STORY["choose_sender"], enemy=sixth.name, enemy_element=R.el_name(sixth.element)),
            start=self.party.index(fighter))
        if choice is fighter:
            won = b.fight(self.controller(fighter)) == "win"
            self.turns += b.stats["turns"]
            b.stats["turns"] = 0
            if not won:
                if not any(m.mon.alive for m in self.party):
                    return self.floor_lost(b)
                nxt = self.choose_sender(b.draw, self.party, sixth, "%s is down. Who steps in against %s (%s)?" % (
                    fighter.mon.name, sixth.name, R.el_name(sixth.element)))
                won = self.fight_through(b, nxt, sixth)
        else:
            b.recall_player("%s, come back!" % fighter.mon.name)
            won = self.fight_through(b, choice, sixth)
        if not won:
            return self.floor_lost(b)
        b.say(nem["beaten"], speaker=nem_sp, wait=True)
        self.play("floor_clear", battle=b, **extra)
        b.close()
        return True

    def floor_lost(self, b):
        self.play("floor_lost", battle=b)
        b.close()
        return False

    def top_floor(self):
        ui = self.ui
        nem = self.hero_data["nemesis"]
        nem_sp = self.villain(self.hero)
        speakers = {"nemesis": nem_sp}
        st = Stage(ui, "rooftop")
        self.play("final_enter", stage=st, speakers=speakers)
        if not self.me.mon.alive:
            self.play("final_no_creature", stage=st, speakers=speakers)
            return False

        b = Battle(ui, "rooftop", self.rng)
        b.open()
        first = R.make_mon(self.hero, "shadow", T["nemesis_first_power"])
        b.send_enemy(first, "%s sends out %s!" % (nem["name"], first.name))
        if not self.fight_through(b, self.me, first, allow_swap=False):
            return self.floor_lost(b)

        # the hybrid
        self.play("final_first_down", battle=b, speakers=speakers)
        hybrid = R.make_hybrid(self.hero, T["hybrid_power"])
        b.send_enemy(hybrid, "%s sends out %s!" % (nem["name"], hybrid.name))
        choice = self.choose_sender(b.draw, self.party, hybrid, self.fmt(
            STORY["choose_sender"], enemy=hybrid.name, enemy_element=R.el_name(hybrid.element)),
            start=0)
        if choice is not self.me:
            b.recall_player("%s, come back!" % self.me.mon.name)
            b.send_player(choice.mon, "%s sends in %s!" % (choice.name, choice.mon.name))
        lines = STORY["hybrid_reveal"]
        b.say(self.fmt(lines[0][1]), wait=True)
        b.morph_enemy(hybrid.best_form(choice.mon.element))
        for who, text in lines[1:]:
            b.say(self.fmt(text), speaker=self.speaker(who, **speakers), wait=True)
        allies = [m for m in self.party if not m.is_hero]
        if allies:
            b.say(self.fmt(STORY["final_ally_cheer"][0][1]), speaker=allies[-1].speaker, wait=True)

        def reshape(member):
            form = hybrid.best_form(member.mon.element)
            if form != hybrid.element:
                b.say("%s shifts again!" % hybrid.name, hold=6)
                b.morph_enemy(form)

        won = b.fight(self.controller(choice)) == "win"
        self.turns += b.stats["turns"]
        b.stats["turns"] = 0
        if not won:
            if not any(m.mon.alive for m in self.party):
                return self.floor_lost(b)
            nxt = self.choose_sender(b.draw, self.party, hybrid, "%s is down. Who steps in against %s?" % (
                choice.mon.name, hybrid.name))
            won = self.fight_through(b, nxt, hybrid, on_send=reshape)
        if not won:
            return self.floor_lost(b)
        b.wait(10)
        b.close()
        return True

    # =====================================================================
    # Ending
    # =====================================================================
    def outro(self):
        st = Stage(self.ui, "rooftop")
        self.play("outro", stage=st, speakers={"nemesis": self.villain(self.hero)})

    def end(self):
        end = STORY["end"]
        st = Stage(self.ui, "title", title=(end["title"], 2, 20, (255, 214, 120)))
        home = self.hero_data["land"]
        from .engine.ui import INNER, wrap
        story = wrap(self.fmt(end["line"], land=home), INNER - 4)[:2]
        rows = [[(WHITE, "  " + line)] for line in story] + [[]] * (3 - len(story))
        rows += [[(GREY, "  " + end["stats"].format(losses=self.losses, turns=self.turns))],
                 [(GOLD, "  " + end["again"])]]
        self.ui.take()
        self.ui.pause(st.draw, 20, rows)
        self.ui.take()
        while True:
            self.ui.frame(st.draw(), rows)
            if self.ui.advanced():
                return

    def run(self):
        self.title()
        self.intro()
        self.start(self.choose_hero())
        st = Stage(self.ui, self.hero)
        self.play("hero_intro", stage=st)
        self.journey()
        self.citadel()
        self.outro()
        self.end()
