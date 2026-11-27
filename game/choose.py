"""Before a fight: a page to choose which master goes in, and a page to choose
which of their creatures goes first.

Both pages share one layout, so the second reads as a closer look at the first:
on the left, whoever is being considered; on the right, that master's creatures
with their level and health; along the top, what they'd be up against.
"""
from . import rules as R
from .art import backdrops, creatures, trainers
from .engine.canvas import darker, draw_mini, lighter, mini_width, mix
from .engine.ui import DIM, GOLD, GREY, RED, WHITE

INK = (14, 10, 22)
CARD = (24, 18, 34)
LEFT, RIGHT = 34, 98            # the column of creature cards
LINE = 96                       # characters that fit on one line of the text box


def colour(element):
    return tuple(R.ELEMENTS["colour"][element])


# =====================================================================
# The picture
# =====================================================================
_grounds = {}
BANNER = (58, 20, 30)           # the strip that names the foe: a colour nothing else on the page has
ROW = 10                        # every creature's row is this tall, whether there is one or five


def _ground(element, S):
    """That master's own land, dimmed, under the banner that names the foe."""
    key = (element, S)
    if key not in _grounds:
        cv = backdrops.backdrop(element, S, platforms=False).copy()
        for row in cv.px:
            for x, c in enumerate(row):
                if c is not None:
                    row[x] = mix(c, INK, 0.58)
        cv.rect(0, 0, 99, 7, BANNER)
        cv.rect(0, 8, 99, 8, darker(BANNER, 0.5))
        _grounds[key] = cv
    return _grounds[key]


def _look(mon):
    return "shadow" if mon.variant == "hybrid" else mon.variant


def _meter(cv, x0, y, x1, mon):
    cv.rect(x0, y, x1, y, (58, 48, 62))
    if mon.alive:
        t = mon.ratio
        n = max(1, int(round((x1 - x0 + 1) * t)))
        cv.rect(x0, y, x0 + n - 1, y, (96, 222, 112) if t > 0.5 else ((250, 206, 70) if t > 0.2 else (240, 72, 60)))


def _cards(cv, team, S, sel=None):
    """A row for each creature: picture, name, level, health. `sel` is the one under the cursor."""
    for i, mon in enumerate(team):
        y = 10 + i * ROW
        ok = mon.alive
        col = colour(mon.element)
        bottom = y + ROW - 2
        cv.rect(LEFT, y, RIGHT, bottom, CARD)
        cv.rect(LEFT, y, LEFT, bottom, col if ok else darker(col, 0.4))
        if i == sel:
            gold = (255, 214, 120)
            cv.rect(LEFT - 1, y - 1, RIGHT + 1, y - 1, gold)
            cv.rect(LEFT - 1, bottom + 1, RIGHT + 1, bottom + 1, gold)
            cv.rect(LEFT - 1, y - 1, LEFT - 1, bottom + 1, gold)
            cv.rect(RIGHT + 1, y - 1, RIGHT + 1, bottom + 1, gold)
        spr = creatures.frames(mon.sid, _look(mon), None, S, 7)[0]
        if spr.w > 8 * S:                           # a broad one: smaller, so it stays clear of its name
            spr = creatures.frames(mon.sid, _look(mon), None, S, max(4, int(7 * 8 * S / spr.w)))[0]
        spr = spr.flipped()
        if not ok:
            spr = spr.silhouette((70, 62, 80))
        spr.blit(cv, int((LEFT + 5.5) * S) - spr.w // 2 + spr.anchor[0], int((bottom - 1) * S))
        tx = LEFT + 10
        name_col = ((255, 236, 170) if i == sel else (232, 230, 240)) if ok else (120, 112, 130)
        level = "L%d" % mon.level
        draw_mini(cv, tx, y + 1, mon.name, name_col)
        draw_mini(cv, RIGHT - 1 - mini_width(level), y + 1, level, (176, 172, 190) if ok else (110, 104, 120))
        _meter(cv, tx, y + 7, RIGHT - 1, mon)


def _banner(cv, foe, wild):
    """Across the top, in its own colour: what they'd be up against."""
    name = "%s L%d" % (foe.name, foe.level)
    for label, kind in (("AGAINST", "WILD " if wild else ""), ("AGAINST", ""), ("VS", "")):
        if mini_width(label + " " + kind + name) <= 96:
            break
    draw_mini(cv, 2, 1, label, (236, 200, 204))
    draw_mini(cv, 2 + mini_width(label + " "), 1, kind + name, lighter(colour(foe.element), 0.25))


def master_picture(members, sel, foe, wild, S):
    m = members[sel]
    cv = _ground(m.element, S).copy()
    _banner(cv, foe, wild)
    # the master at full size, from the knees up: closer than on the page where you first met them
    trainers.sprite(m.data["look"], S).blit(cv, int(16 * S), int(64 * S))
    _cards(cv, m.team, S)
    return cv


def creature_picture(team, sel, foe, wild, owner, S):
    mon = team[sel]
    cv = _ground(owner.element if owner else mon.element, S).copy()
    _banner(cv, foe, wild)
    tall = 32
    spr = creatures.frames(mon.sid, _look(mon), None, S, tall)[0]
    if spr.w > 31 * S:                              # a broad one: smaller, so all of it shows
        tall = int(tall * 31 * S / spr.w)
        spr = creatures.frames(mon.sid, _look(mon), None, S, tall)[0]
    spr = spr.flipped()
    if not mon.alive:
        spr = spr.silhouette((70, 62, 80))
    feet = 51 if owner else 55
    cv.ellipse(16, feet, 13, 1.6, darker(cv.get(16, feet + 1) or INK, 0.6))
    spr.blit(cv, int(16 * S) - spr.w // 2 + spr.anchor[0], int(feet * S))
    if owner:                                       # under it: whose team this is
        label = "YOURS" if owner.is_hero else owner.name.upper()
        draw_mini(cv, 16 - mini_width(label) // 2, 54, label, colour(owner.element), shadow=INK)
    _cards(cv, team, S, sel)
    return cv


# =====================================================================
# The words under it
# =====================================================================
def _first_line(head, sel, n, blink, cancel):
    """The question, where you are among the choices, and which keys do what."""
    count = "%d of %d" % (sel + 1, n)
    for hint in ("Left / Right to look, Enter to choose" + (", Esc back" if cancel else ""),
                 "Enter to choose" + (", Esc to go back" if cancel else ""), ""):
        if 2 + len(head) + 5 + len(count) + 2 + 4 + len(hint) <= LINE:
            break
    return [(GREY, "  " + head), (GOLD, "   ◀ " if blink else "     "), (WHITE, count),
            (GOLD, " ▶" if blink else "  "), (DIM, "    " + hint)]


def _matchup(mine, foe):
    return "%s attacks: %s.   %s's %s attacks back: %s." % (
        R.el_name(mine), R.effect_word(R.mult(mine, foe.element)),
        foe.name, R.el_name(foe.element), R.effect_word(R.mult(foe.element, mine)))


def _joins(foe, party):
    """A wild creature: whose team it could join, whoever does the fighting."""
    el = R.el_name(foe.element)
    keeper = next((m for m in party if m.element == foe.element), None)
    if keeper is None:
        return "No %smaster travels with you, so it can't be befriended." % el
    whose = "your" if keeper.is_hero else keeper.name + "'s"
    if len(keeper.team) >= R.TEAM_MAX:
        return "It can't be befriended while %s team is full." % whose
    return "If it's befriended it joins %s team, whoever does the fighting." % whose


def master(ui, members, foe, head, party=None, wild=False, tag=None):
    """Which master's team goes in. Opens on you (or, if yours are all down, the first who can fight)."""
    pictures = {}

    def draw(sel):
        if sel not in pictures:
            pictures[sel] = master_picture(members, sel, foe, wild, ui.S)
        return pictures[sel]

    def blocked(sel):
        m = members[sel]
        return None if m.standing else "%s nobody left standing." % ("You have" if m.is_hero else m.name + " has")

    def rows(sel, blink, note):
        m = members[sel]
        col = colour(m.element)
        ready = "%d of %d ready" % (m.standing, len(m.team)) if m.standing else "all fainted"
        out = [_first_line(head, sel, len(members), blink, False),
               [(col, "  " + m.name.upper()), (WHITE, " (you)" if m.is_hero else ""),
                (WHITE, ", %s of %s" % (m.data["title"], m.data["land"])),
                (GREY, "     Creatures: "), (WHITE if m.standing else RED, ready)],
               [(GREY, "  " + _matchup(m.element, foe))]]
        if wild:
            out.append([(GREY, "  " + _joins(foe, party or members))])
        if note:
            out.append([(RED, "  " + note)])
        else:
            uses = R.TUNING["heal"]["uses"]
            out.append([(DIM, "  Healing touches left: %d of %d" % (m.heals, uses))])
        return out

    ready = [i for i, m in enumerate(members) if m.standing]
    start = next((i for i in ready if members[i].is_hero), ready[0] if ready else 0)
    return members[ui.pager(draw, rows, len(members), start=start, blocked=blocked, tag=tag)]


def creature(ui, team, foe, head, owner=None, wild=False, cancel=False, blocked=None, tag=None):
    """Which of a team's creatures goes in. Opens on the first one still standing.
    Returns the creature, or None for "back" (only when `cancel`)."""
    pictures = {}
    cap = R.TUNING["level_cap"]

    def draw(sel):
        if sel not in pictures:
            pictures[sel] = creature_picture(team, sel, foe, wild, owner, ui.S)
        return pictures[sel]

    def no(sel):
        if not team[sel].alive:
            return "%s has fainted." % team[sel].name
        return blocked(sel) if blocked else None

    def rows(sel, blink, note):
        mon = team[sel]
        col = colour(mon.element)
        health = [(GREY, "     Health: "), (WHITE, "%d/%d" % (mon.hp, mon.max_hp))] if mon.alive else [(RED, "     Fainted")]
        out = [_first_line(head, sel, len(team), blink, cancel),
               [(col, "  " + mon.name), (WHITE, "   level %d" % mon.level), (GREY, "     Nature: "),
                (col, R.el_name(mon.element))] + health,
               [(GREY, "  Knows: " + ", ".join(mv.name.title() for mv in mon.moves))],
               [(GREY, "  " + _matchup(mon.element, foe))]]
        if note:
            out.append([(RED, "  " + note)])
        elif mon.level < cap:
            out.append([(DIM, "  %d to next level." % (R.xp_to_next(mon.level) - mon.xp))])
        return out

    start = next((i for i in range(len(team)) if not no(i)), 0)
    i = ui.pager(draw, rows, len(team), start=start, blocked=no, cancel=cancel, tag=tag)
    return None if i is None else team[i]
