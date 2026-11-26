"""Print what this terminal says about itself (size, character cell size,
Sixel support). Useful when the game picks the wrong picture mode.

    python tools/termcheck.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.engine import sixel, term      # noqa: E402

term.prepare_stdout()
cols, rows = term.term_size()
cell_w, cell_h, supported, measured = sixel.query_terminal(cols, rows)
print("window: %d x %d characters" % (cols, rows))
print("character cell: %d x %d pixels (%s)" % (cell_w, cell_h, "measured" if measured else "a guess: the terminal didn't say"))
print("Sixel support: %s" % {True: "yes", False: "no (the terminal answered, without Sixel)",
                            None: "unknown (the terminal didn't answer)"}[supported])
print("TERM_PROGRAM=%s  WT_SESSION=%s" % (os.environ.get("TERM_PROGRAM", ""), "set" if os.environ.get("WT_SESSION") else ""))
