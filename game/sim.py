"""Balance check: simulate the campaign's battles for every hero.

    python -m game.sim            (from the repo root)

It assumes a player who arrives at each Lord with the team in tuning.json's
"expected" (levels and team sizes), plays carefully, and uses no items.
Prints the win rate of each Lord fight (alone, and with the best ally stepping
in after a loss), and how often the party then clears the Citadel.
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
    order = R.land_order(hero)
    solo, with_ally = [], []
    for i, lord_el in enumerate(order):
        w_solo = w_ally = 0
        for _ in range(n):
            if team_fight(hero_team(hero, i), lord_team(lord_el, i), rng):
                w_solo += 1
                w_ally += 1
            elif i > 0:
                k = max(range(i), key=lambda a: R.mult(order[a], lord_el) / R.mult(lord_el, order[a]))
                w_ally += team_fight(lord_team(order[k], k), lord_team(lord_el, i), rng)
        solo.append(w_solo / n)
        with_ally.append(w_ally / n)
    return order, solo, with_ally


def pick(party, foe, smart=True):
    """Whose team goes in against `foe`: the best match-up among those still standing."""
    alive = [el for el, team in party.items() if R.living(team)]
    if not alive:
        return None

    def score(el):
        target = foe.best_form(el) if (foe.forms and smart) else foe.element
        fit = sum(m.ratio for m in party[el]) / len(party[el])
        return R.mult(el, target) / R.mult(target, el) * (0.35 + 0.65 * fit)
    return max(alive, key=score)


def fight_on(party, first, foes, rng, smart=True):
    el = first
    while True:
        if team_fight(party[el], foes, rng):
            return True
        el = pick(party, R.living(foes)[0], smart)
        if el is None:
            return False


def citadel(hero, rng, smart=True):
    """Returns (cleared, floor reached, trainers still standing)."""
    c = T["citadel"]
    order = R.land_order(hero)
    party = {hero: hero_team(hero, 4)}
    top = max(m.level for m in party[hero])
    for k, el in enumerate(order):
        party[el] = lord_team(el, k)
        for m in party[el]:
            m.set_level(max(m.level, top))
            m.restore()
    for k, ally in enumerate(order):
        foes = R.make_team(ally, c["nemesis_level"], c["nemesis_size"], "shadow")
        first = ally if R.living(party[ally]) else pick(party, foes[0], smart)
        if first is None or not fight_on(party, first, foes, rng, smart):
            return False, k + 1, 0
        sixth = R.make_mon(R.beater_of(ally), "shadow", c["sixth_level"])
        who = pick(party, sixth, smart)
        if who is None or not fight_on(party, who, [sixth], rng, smart):
            return False, k + 1, 0
    if not R.living(party[hero]):
        return False, 6, 0
    if not team_fight(party[hero], R.make_team(hero, c["final_level"], c["final_size"], "shadow"), rng):
        return False, 6, 0
    hybrid = R.make_hybrid(hero, c["hybrid_level"])
    who = pick(party, hybrid, smart)
    if who is None or not fight_on(party, who, [hybrid], rng, smart):
        return False, 6, 0
    return True, 7, sum(1 for t in party.values() if R.living(t))


def trial(hero, rng):
    """The quick taste: (beat the Lord, cleared the floor and the top)."""
    c = T["trial"]
    order = R.land_order(hero)
    lord_won = team_fight([R.make_mon(hero, level=c["hero_level"])], [R.make_mon(order[0], level=c["lord_level"])], rng)
    party = {el: [R.make_mon(el, level=c["hero_level"])] for el in [hero] + order}
    ally = order[0]
    ok = fight_on(party, ally, [R.make_mon(ally, "shadow", c["nemesis_level"])], rng)
    sixth = R.make_mon(R.beater_of(ally), "shadow", c["sixth_level"])
    ok = ok and fight_on(party, pick(party, sixth), [sixth], rng)
    ok = ok and bool(R.living(party[hero])) and team_fight(party[hero], [R.make_mon(hero, "shadow", c["final_level"])], rng)
    if ok:
        hybrid = R.make_hybrid(hero, c["hybrid_level"])
        ok = fight_on(party, pick(party, hybrid), [hybrid], rng)
    return lord_won, ok


def main(n=600):
    rng = random.Random(7)
    print("LORD FIGHTS  (win % alone / win % with the best ally stepping in after a loss)")
    for hero in R.ORDER:
        order, solo, ally = journey(hero, n, rng)
        cells = ["%-9s %3.0f/%3.0f" % (R.el_name(o), s * 100, a * 100) for o, s, a in zip(order, solo, ally)]
        print("  %-10s %s" % (R.el_name(hero), "   ".join(cells)))
    print("\nCITADEL  (clear %, trainers still standing, % of runs lost on floors 1-5 and the top)")
    for hero in R.ORDER:
        res = [citadel(hero, rng) for _ in range(n)]
        wins = [r for r in res if r[0]]
        ends = [sum(1 for r in res if not r[0] and r[1] == f) * 100 // n for f in range(1, 7)]
        print("  %-10s %3.0f    left %.1f    %s" % (R.el_name(hero), len(wins) * 100 / n,
                                                  sum(r[2] for r in wins) / max(1, len(wins)), ends))
    print("\nQUICK TASTE  (% who beat the Lord first time, % who clear the Citadel part first time)")
    for hero in R.ORDER:
        res = [trial(hero, rng) for _ in range(n)]
        print("  %-10s %3.0f   %3.0f" % (R.el_name(hero), sum(r[0] for r in res) * 100 / n, sum(r[1] for r in res) * 100 / n))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 600)
