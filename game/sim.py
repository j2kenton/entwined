"""Balance check: simulate the campaign's battles for every hero.

    python -m game.sim            (from the repo root)
    python -m game.sim 300        (fewer or more runs per number)

The Citadel's creatures are at fixed levels, so how hard it is depends on how
well you've trained. This prints, for parties of different strengths, how
often each land's Master is beaten and how often the Citadel is cleared in one climb.
It assumes careful play, the healing touches used between floors, and no
satchel items.
"""
import random
import sys

from . import rules as R

T = R.TUNING


def duel(p, e, rng, max_turns=80):
    """One creature against another until one faints."""
    p.clear_status()
    turns = 0
    while p.alive and e.alive and turns < max_turns:
        turns += 1
        pm = R.choose_ai(p, e, rng, careful=True)
        em = R.choose_ai(e, p, rng)
        for user, mv, target in R.turn_order(p, pm, e, em):
            if user.alive and target.alive:
                R.use_move(user, target, mv, rng)
        p.guard = e.guard = False


def team_fight(team, foes, rng):
    """Team against team, each sending creatures in order. True if `team` wins."""
    while R.living(team) and R.living(foes):
        p, e = R.living(team)[0], R.living(foes)[0]
        if e.forms:
            e.set_form(e.best_form(p.element))
        duel(p, e, rng)
    return bool(R.living(team))


def hero_team(hero, i):
    return R.make_team(hero, T["expected"]["levels"][i] - 1, T["expected"]["team"][i])


def lord_team(el, i):
    return R.make_team(el, T["lords"]["levels"][i], T["lords"]["sizes"][i])


def journey(hero, n, rng):
    """Each Lord: win rate with your own team, and with whichever team suits best."""
    order = R.land_order(hero)
    solo, best = [], []
    for i, lord_el in enumerate(order):
        w_solo = w_best = 0
        # companions so far, each grown to three creatures a little behind yours
        allies = {order[a]: T["expected"]["levels"][i] - 2 for a in range(i)}
        for _ in range(n):
            if team_fight(hero_team(hero, i), lord_team(lord_el, i), rng):
                w_solo += 1
                w_best += 1
            elif allies:
                el = max(allies, key=lambda a: R.mult(a, lord_el) / R.mult(lord_el, a))
                w_best += team_fight(R.make_team(el, allies[el], 3), lord_team(lord_el, i), rng)
        solo.append(w_solo / n)
        best.append(w_best / n)
    return order, solo, best


# =========================================================================
# The Citadel
# =========================================================================
def make_party(hero, level, size):
    """A trained party: your team at `level`, each companion's a level behind."""
    party = {hero: R.make_team(hero, level - 1, size)}
    for el in R.land_order(hero):
        party[el] = R.make_team(el, level - 2, size)
    return party


def pick(party, foe):
    """Whose team goes in against `foe`: the best match-up among those still standing."""
    alive = [el for el, team in party.items() if R.living(team)]
    if not alive:
        return None

    def score(el):
        target = foe.best_form(el) if foe.forms else foe.element
        fit = sum(m.ratio for m in party[el]) / len(party[el])
        return R.mult(el, target) / R.mult(target, el) * (0.35 + 0.65 * fit)
    return max(alive, key=score)


def face(party, foe, rng, first=None):
    """One enemy creature. `first`: the trainer who must meet it before anyone else can."""
    el = first if (first and R.living(party[first])) else pick(party, foe)
    while el is not None and foe.alive:
        p = R.living(party[el])[0]
        if foe.forms:
            foe.set_form(foe.best_form(p.element))
        duel(p, foe, rng)
        if foe.alive:
            el = pick(party, foe)
    return not foe.alive


def breather(party, touches):
    """Between floors: each trainer mends their most hurt creatures while their touches last."""
    amount = T["heal"]["amount"]
    for el, team in party.items():
        while touches[el] > 0:
            hurt = [m for m in team if m.alive and m.ratio <= 1 - amount]
            if not hurt:
                break
            m = min(hurt, key=lambda m: m.ratio)
            m.hp = min(m.max_hp, m.hp + int(round(m.max_hp * amount)))
            touches[el] -= 1


def citadel(hero, rng, level=None, size=4):
    """One climb. Returns (cleared, floor reached 1-6, creatures still standing)."""
    c = T["citadel"]
    party = make_party(hero, level or c["nemesis_level"], size)
    touches = {el: T["heal"]["uses"] for el in party}
    for k, ally in enumerate(R.land_order(hero)):
        for foe in R.make_team(ally, c["nemesis_level"], c["nemesis_sizes"][k], "shadow"):
            if not face(party, foe, rng, first=ally):
                return False, k + 1, 0
        if not face(party, R.make_mon(R.beater_of(ally), "shadow", c["sixth_level"]), rng):
            return False, k + 1, 0
        breather(party, touches)
    for foe in R.make_team(hero, c["final_level"], c["final_size"], "shadow"):
        if not face(party, foe, rng, first=hero):
            return False, 6, 0
    if not face(party, R.make_hybrid(hero, c["hybrid_level"]), rng):
        return False, 6, 0
    return True, 7, sum(len(R.living(t)) for t in party.values())


def citadel_rate(n, rng, level, size):
    return sum(citadel(hero, rng, level, size)[0] for hero in R.ORDER for _ in range(n)) / (6 * n)


def trial(hero, rng):
    """The quick taste: (beat the Lord, cleared the floor and the top)."""
    c = T["trial"]
    order = R.land_order(hero)
    lord_won = team_fight([R.make_mon(hero, level=c["hero_level"])], [R.make_mon(order[0], level=c["lord_level"])], rng)
    party = {el: [R.make_mon(el, level=c["hero_level"])] for el in [hero] + order}
    ally = order[0]
    ok = face(party, R.make_mon(ally, "shadow", c["nemesis_level"] + 1), rng, first=ally)
    ok = ok and face(party, R.make_mon(R.beater_of(ally), "shadow", c["sixth_level"]), rng)
    ok = ok and face(party, R.make_mon(hero, "shadow", c["final_level"] + 1), rng, first=hero)
    ok = ok and face(party, R.make_hybrid(hero, c["hybrid_level"]), rng)
    return lord_won, ok


def main(n=300):
    rng = random.Random(7)
    c = T["citadel"]
    print("THE FIVE MASTERS  (win % with your own team / with whichever team suits best)")
    print("  They have %s creatures at levels %s; you arrive with %s at levels %s."
          % (T["lords"]["sizes"], T["lords"]["levels"], T["expected"]["team"], T["expected"]["levels"]))
    for hero in R.ORDER:
        order, solo, best = journey(hero, n, rng)
        cells = ["%-9s %3.0f/%3.0f" % (R.el_name(o), s * 100, a * 100) for o, s, a in zip(order, solo, best)]
        print("  %-10s %s" % (R.el_name(hero), "   ".join(cells)))

    print()
    print("CITADEL  (chance of clearing it in one climb, by how well the party is trained)")
    print("  Its creatures: floors %d, the one more %d, your nemesis %d, the hybrid %d."
          % (c["nemesis_level"], c["sixth_level"], c["final_level"], c["hybrid_level"]))
    sizes = (3, 4, 5)
    print("  your best level   " + "   ".join("%d creatures each" % s for s in sizes))
    for level in range(c["nemesis_level"] - 3, min(T["level_cap"], c["nemesis_level"] + 3) + 1):
        print("  %10d        " % level + "   ".join("%14.0f%%  " % (citadel_rate(n // 6 or 1, rng, level, s) * 100) for s in sizes))

    print()
    print("  By hero, for a party at level %d with 4 creatures each (clear %%, and where the rest fell: floors 1-5, top)"
          % c["nemesis_level"])
    for hero in R.ORDER:
        res = [citadel(hero, rng, c["nemesis_level"], 4) for _ in range(n)]
        ends = [sum(1 for r in res if not r[0] and r[1] == f) * 100 // n for f in range(1, 7)]
        wins = [r for r in res if r[0]]
        print("  %-10s %3.0f   left standing %4.1f   %s" % (
            R.el_name(hero), len(wins) * 100 / n, sum(r[2] for r in wins) / max(1, len(wins)), ends))

    print()
    print("QUICK TASTE  (% who beat the Master first time, % who clear the Citadel part first time)")
    for hero in R.ORDER:
        res = [trial(hero, rng) for _ in range(n)]
        print("  %-10s %3.0f   %3.0f" % (R.el_name(hero), sum(r[0] for r in res) * 100 / n, sum(r[1] for r in res) * 100 / n))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
