"""Print the element chart and check it still suits the story for every hero.

    python tools/element_wheel.py

The chart itself lives in game/data/elements.json (the wheel order, the base
pattern and the realism exceptions). Change it there, then re-run this.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import rules as R      # noqa: E402

ORDER = R.ORDER
name = R.el_name

if __name__ == "__main__":
    print("Wheel:", " -> ".join(name(e) for e in ORDER), "-> (back)\n")
    print("%-10s" % "" + "".join("%-10s" % name(d) for d in ORDER))
    for a in ORDER:
        print("%-10s" % name(a) + "".join("%-10s" % ("x%g" % R.mult(a, d)) for d in ORDER))

    print("\nStrong links:")
    for i, a in enumerate(ORDER):
        d = ORDER[(i + 1) % 6]
        print("  %-9s beats %-9s %s" % (name(a), name(d), R.ELEMENTS["links"].get("%s>%s" % (a, d), "(no reason given)")))

    print("\nRealism exceptions:")
    for e in R.ELEMENTS["exceptions"]:
        print("  %-9s -> %-9s x%-5g %s" % (name(e["attacker"]), name(e["defender"]), e["mult"], e["why"]))

    print("\nHow each element fares (averaged over the others):")
    for e in ORDER:
        others = [o for o in ORDER if o != e]
        att = sum(R.mult(e, o) for o in others) / 5
        dfn = sum(1 / R.mult(o, e) for o in others) / 5
        print("  %-9s attack x%.2f   toughness x%.2f" % (name(e), att, dfn))

    print("\nDesign checks per hero:")
    ok = True
    for h in ORDER:
        beater = R.beater_of(h)                    # sweetheart's element / hybrid's 2nd form
        forms = (h, beater)
        obvious = max(ORDER, key=lambda a: R.mult(a, beater))
        obv = min(R.mult(obvious, f) for f in forms)
        best = max(ORDER, key=lambda a: min(R.mult(a, f) for f in forms))
        best_m = min(R.mult(best, f) for f in forms)
        lands = R.land_order(h)
        ok &= obv < 1.0 and best_m <= 1.25 and lands[-1] == beater
        print("  %-9s hybrid %-17s obvious counter %-9s -> %-14s best answer %-9s (%s)  road: %s"
              % (name(h), "+".join(name(f) for f in forms), name(obvious), R.effect_word(obv),
                 name(best), R.effect_word(best_m), " > ".join(name(o) for o in lands)))
    print("\nAll checks pass" if ok else "\nSome checks need a look")
