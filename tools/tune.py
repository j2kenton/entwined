"""Search for Lord and Citadel levels that give the intended difficulty curve.

    python tools/tune.py

Prints suggested numbers for game/data/tuning.json. It changes nothing itself.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import rules as R, sim      # noqa: E402

T = R.TUNING
TARGETS = [0.92, 0.84, 0.74, 0.62, 0.50]     # chance of beating each Lord alone, first to last
CITADEL_TARGET = 0.75


def lord_rate(i, level, n, rng):
    T["lords"]["levels"][i] = level
    tot = 0
    for hero in R.ORDER:
        order = R.land_order(hero)
        tot += sum(sim.team_fight(sim.hero_team(hero, i), sim.lord_team(order[i], i), rng) for _ in range(n)) / n
    return tot / 6


def citadel_rate(n, rng):
    return sum(sim.citadel(hero, rng)[0] for hero in R.ORDER for _ in range(n)) / (6 * n)


if __name__ == "__main__":
    rng = random.Random(11)
    for i in range(5):
        rates = {lv: lord_rate(i, lv, 120, rng) for lv in range(4, 21)}
        best = min(rates, key=lambda lv: abs(rates[lv] - TARGETS[i]))
        T["lords"]["levels"][i] = best
        print("Lord %d: level %2d gives %.0f%% (target %.0f%%)" % (i + 1, best, rates[best] * 100, TARGETS[i] * 100))
    print('"lords": {"levels": %s, ...}' % T["lords"]["levels"])
    c = T["citadel"]
    results = []
    for nem in range(13, 20):
        for extra in (2, 4, 6):
            c.update(nemesis_level=nem, sixth_level=nem + 1, final_level=nem + 1, hybrid_level=nem + extra)
            results.append((abs(citadel_rate(60, rng) - CITADEL_TARGET), nem, extra))
    results.sort()
    for miss, nem, extra in results[:4]:
        c.update(nemesis_level=nem, sixth_level=nem + 1, final_level=nem + 1, hybrid_level=nem + extra)
        print("Citadel: nemesis %d, sixth %d, final %d, hybrid %d -> clears %.0f%%"
              % (nem, nem + 1, nem + 1, nem + extra, citadel_rate(200, rng) * 100))
