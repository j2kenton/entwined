"""The element chart: the wheel order, the base pattern, and realism exceptions.
Prints the full chart and checks the design still works for every hero.

    python tools/element_wheel.py

Change ORDER or EXCEPTIONS here, re-run, and see what it does to the game.
"""

ORDER = ["Wave", "Flame", "Root", "Breeze", "Soil", "Lightning"]

# each element strongly beats the next one round the wheel
STRONG_LINKS = {
    ("Wave", "Flame"): "water puts out fire",
    ("Flame", "Root"): "fire burns plants",
    ("Root", "Breeze"): "a breeze only spreads seeds and helps plants grow; roots hold firm",
    ("Breeze", "Soil"): "wind blows soil away",
    ("Soil", "Lightning"): "the ground earths lightning",
    ("Lightning", "Wave"): "water conducts the shock",
}

# your variant, by steps round the wheel (attacker -> defender)
PATTERN = {1: 2.0, 2: 0.8, 3: 1.0, 4: 1.25, 5: 0.5}
SAME = 0.8          # alike things resist each other

# where reality disagrees with the pattern, reality wins
EXCEPTIONS = {
    ("Flame", "Soil"): (0.8, "soil smothers flame"),
    ("Soil", "Flame"): (1.25, "...so soil hits flame a little harder"),
    ("Flame", "Lightning"): (1.0, "no real relationship"),
    ("Soil", "Soil"): (1.0, "rock on rock is fine"),
    ("Breeze", "Breeze"): (1.0, "wind can't really resist wind"),
    ("Lightning", "Lightning"): (0.5, "storms swallow lightning"),
}


def mult(a, d):
    if (a, d) in EXCEPTIONS:
        return EXCEPTIONS[(a, d)][0]
    if a == d:
        return SAME
    return PATTERN[(ORDER.index(d) - ORDER.index(a)) % 6]


def word(m):
    return {2.0: "strong", 1.25: "slightly strong", 1.0: "even",
            0.8: "slightly weak", 0.5: "weak"}[m]


if __name__ == "__main__":
    print("Wheel:", " -> ".join(ORDER), "-> (back)\n")
    print("%-10s" % "" + "".join("%-10s" % d for d in ORDER))
    for a in ORDER:
        print("%-10s" % a + "".join("%-10s" % ("x%g" % mult(a, d)) for d in ORDER))

    print("\nHow each element fares (attack / defence, averaged over the others):")
    for e in ORDER:
        others = [o for o in ORDER if o != e]
        att = sum(mult(e, o) for o in others) / 5
        dfn = sum(1 / mult(o, e) for o in others) / 5
        print("  %-9s attack x%.2f   toughness x%.2f" % (e, att, dfn))

    print("\nDesign checks per hero:")
    ok = True
    for h in ORDER:
        beater = ORDER[(ORDER.index(h) - 1) % 6]   # sweetheart's element / hybrid's 2nd form
        forms = (h, beater)
        obvious = max(ORDER, key=lambda a: mult(a, beater))
        obv = min(mult(obvious, f) for f in forms)
        best = max(ORDER, key=lambda a: min(mult(a, f) for f in forms))
        best_m = min(mult(best, f) for f in forms)
        lands = sorted((o for o in ORDER if o != h), key=lambda o: -(mult(h, o) / mult(o, h)))
        twist = obv < 1.0 and best_m <= 1.25
        hardest_ok = lands[-1] == beater
        ok &= twist and hardest_ok
        print("  %-9s hybrid %-17s obvious counter %-9s -> %-14s best answer %-9s (%s)  lands: %s"
              % (h, "+".join(forms), obvious, word(obv), best, word(best_m), " > ".join(lands)))
    print("\nAll checks pass" if ok else "\nSome checks need a look")
