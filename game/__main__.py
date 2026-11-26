"""Entwined: play it with

    python -m game              (from the repo root; or use play.bat / play.sh)

Options:
    --sixel          force HD pictures drawn with real pixels (Sixel)
    --blocks         force retro pictures drawn with coloured text blocks
    --hero NAME      skip the opening and start as this hero (e.g. marisol or wave)
    --from citadel   (with --hero) skip the five Lords and start at the Citadel
    --from top       (with --hero) skip straight to the final floor
"""
import sys

from . import rules as R
from .engine import sixel, term
from .engine.display import Display
from .engine.ui import UI, Quit
from .story import Game, Member, Stage


def find_hero(word):
    word = word.lower()
    for el, h in R.HEROES.items():
        if word in (el, h["name"].lower()):
            return el
    raise SystemExit("Unknown hero %r. Choose from: %s" % (
        word, ", ".join(h["name"].lower() for h in R.HEROES.values())))


def option(argv, name):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
        raise SystemExit("%s needs a value" % name)
    return None


def make_display(argv):
    if "--blocks" in argv:
        return Display("blocks", sys.stdout)
    cols, rows = term.term_size()
    cell_w, cell_h, supported, measured = sixel.query_terminal(cols, rows)
    if "--sixel" in argv or supported:
        return Display("sixel", sys.stdout, cell_w, cell_h, measured)
    return Display("blocks", sys.stdout)


def play_once(ui, hero, start):
    g = Game(ui)
    if not hero:
        g.run()
        return
    g.start(hero)
    if start in ("citadel", "top"):
        for el in g.order:                      # everyone has already joined
            g.level += 1
            g.party.append(Member(el, 1.0))
        for m in g.party:
            m.mon.set_power(R.level_power(g.level), keep_ratio=False)
        g.citadel(first_floor=5 if start == "top" else 0)
    else:
        g.play("hero_intro", stage=Stage(ui, hero))
        g.journey()
        g.citadel()
    g.outro()
    g.end()


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return
    hero = option(argv, "--hero")
    hero = find_hero(hero) if hero else None
    start = option(argv, "--from")
    if start not in (None, "citadel", "top"):
        raise SystemExit("--from takes 'citadel' or 'top'")
    if start and not hero:
        raise SystemExit("--from needs --hero as well")
    term.prepare_stdout()
    display = make_display(argv)
    keys = term.Keys()
    term.enter_screen(sys.stdout)
    try:
        while True:
            play_once(UI(display, keys), hero, start)
            display.reset()
    except (Quit, KeyboardInterrupt):
        pass
    finally:
        keys.close()
        term.leave_screen(sys.stdout)
    print("Thanks for playing Entwined!")


if __name__ == "__main__":
    main(sys.argv[1:])
