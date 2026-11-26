"""Balance check: simulate the whole campaign for every hero.

    python -m game.sim            (from the repo root)

Prints, per hero: the win rate of each Lord fight (solo, and with the best
ally stepping in), and how often a sensible party clears the Citadel.
"""
import random
import sys

from . import rules as R

T = R.TUNING
CITADEL_LEVEL = T["start_level"] + 5


def duel(p, e, rng, p_careful=True, max_turns=60):
    """Fight until one side faints. Returns True if p wins."""
    p.clear_status()
    turns = 0
    while p.alive and e.alive and turns < max_turns:
        turns += 1
        pm = R.choose_ai(p, e, rng, careful=p_careful)
        em = R.choose_ai(e, p, rng)
        for user, mv, target in R.turn_order(p, pm, e, em):
            if user.alive and target.alive:
                R.use_move(user, target, mv, rng)
        p.guard = e.guard = False
    return p.alive and not e.alive


def journey(hero, n, rng):
    order = R.land_order(hero)
    solo, with_ally = [], []
    for i, lord_el in enumerate(order):
        w_solo = w_ally = 0
        for _ in range(n):
            me = R.make_mon(hero, power=R.level_power(T["start_level"] + i))
            lord = R.make_mon(lord_el, power=T["lord_power"][i])
            if duel(me, lord, rng):
                w_solo += 1
                w_ally += 1
            elif i > 0:
                ally_el = max(order[:i], key=lambda a: R.mult(a, lord_el) / R.mult(lord_el, a))
                ally = R.make_mon(ally_el, power=R.level_power(T["start_level"] + i))
                lord = R.make_mon(lord_el, power=T["lord_power"][i])
                w_ally += duel(ally, lord, rng)
        solo.append(w_solo / n)
        with_ally.append(w_ally / n)
    return order, solo, with_ally


def pick(party, hero, foe, smart=True, reserve_hero=True):
    """Choose who to send in against `foe`."""
    alive = [m for m in party.values() if m.alive]
    if reserve_hero and len(alive) > 1:
        alive = [m for m in alive if m is not party[hero]] or alive
    if not alive:
        return None

    def score(m):
        el = foe.element
        if foe.forms and smart:
            el = foe.best_form(m.element)
        return R.matchup_score(m, el) * (0.35 + 0.65 * m.ratio)
    return max(alive, key=score)


def fight_through(active, foe, party, hero, rng, smart, allow_swap=True):
    """Fight `foe`, sending in replacements as creatures faint. True if foe falls."""
    while True:
        if foe.forms:
            foe.element = foe.best_form(active.element)
        if duel(active, foe, rng):
            return True
        if not foe.alive:
            return True
        if not allow_swap:
            return False
        active = pick(party, hero, foe, smart, reserve_hero=False)
        if active is None:
            return False


def citadel(hero, rng, smart=True):
    """Returns (cleared, floor_reached, creatures_left)."""
    order = R.land_order(hero)
    power = R.level_power(CITADEL_LEVEL)
    party = {el: R.make_mon(el, power=power) for el in [hero] + order}
    for k, ally_el in enumerate(order):
        first = R.make_mon(ally_el, "shadow", T["citadel_first_power"])
        active = party[ally_el] if party[ally_el].alive else pick(party, hero, first, smart)
        if active is None or not fight_through(active, first, party, hero, rng, smart):
            return False, k + 1, 0
        sixth = R.make_mon(R.beater_of(ally_el), "shadow", T["citadel_sixth_power"])
        active = pick(party, hero, sixth, smart)
        if active is None or not fight_through(active, sixth, party, hero, rng, smart):
            return False, k + 1, 0
    me = party[hero]
    if not me.alive:
        return False, 6, 0
    first = R.make_mon(hero, "shadow", T["nemesis_first_power"])
    if not fight_through(me, first, party, hero, rng, smart, allow_swap=False):
        return False, 6, 0
    hybrid = R.make_hybrid(hero, T["hybrid_power"])
    active = pick(party, hero, hybrid, smart, reserve_hero=False)
    if not fight_through(active, hybrid, party, hero, rng, smart):
        return False, 6, 0
    return True, 7, sum(m.alive for m in party.values())


def main(n=1500):
    rng = random.Random(7)
    print("LORD FIGHTS  (careful player; solo win % / win % with the best ally stepping in after a loss)")
    for hero in R.ORDER:
        order, solo, ally = journey(hero, n, rng)
        cells = ["%-9s %3.0f/%3.0f" % (R.el_name(o), s * 100, a * 100) for o, s, a in zip(order, solo, ally)]
        print("  %-10s %s" % (R.el_name(hero), "   ".join(cells)))
    print("\nCITADEL  (clear %: smart picks / naive picks vs the hybrid;  creatures left;  where runs end)")
    for hero in R.ORDER:
        res = [citadel(hero, rng, True) for _ in range(n)]
        naive = [citadel(hero, rng, False) for _ in range(n)]
        clear = sum(r[0] for r in res) / n
        left = sum(r[2] for r in res if r[0]) / max(1, sum(r[0] for r in res))
        ends = [sum(1 for r in res if not r[0] and r[1] == f) * 100 // n for f in range(1, 7)]
        print("  %-10s %3.0f / %3.0f    left %.1f    lost on floor 1-5, top: %s"
              % (R.el_name(hero), clear * 100, sum(r[0] for r in naive) * 100 / n, left, ends))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1500)
