"""Show how hard the Citadel would be at different levels, for parties of
different strengths, to help choose the numbers in game/data/tuning.json.

    python tools/tune.py

It changes nothing itself. (For the five Masters, see `python -m game.sim`.)
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import rules as R, sim      # noqa: E402

T = R.TUNING


if __name__ == "__main__":
    rng = random.Random(11)
    # The Citadel's levels are fixed, so the question is how well-trained a party has to be.
    c = T["citadel"]
    print()
    print("Citadel: chance of clearing it in one climb. Rows: the level of its floors")
    print("(the one more and your nemesis a level higher, the hybrid two higher).")
    print("Columns: your best creature's level, for parties of 3, 4 and 5 creatures each.")
    for nem in range(14, 19):
        c.update(nemesis_level=nem, sixth_level=nem + 1, final_level=nem + 1, hybrid_level=nem + 2)
        cells = []
        for size in (3, 4, 5):
            cells.append("  ".join("L%d %3.0f%%" % (lv, sim.citadel_rate(25, rng, lv, size) * 100)
                                   for lv in (nem - 2, nem, nem + 2) if lv <= T["level_cap"]))
        print("  floors at %d:   %s" % (nem, "   |   ".join(cells)))
