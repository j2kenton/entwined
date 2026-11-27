"""Entwined: play it with

    python -m game              (from the repo root; or use play.bat / play.sh)

Options:
    --sixel            force HD pictures drawn with real pixels (Sixel)
    --blocks           force retro pictures drawn with coloured text blocks
    --trial            go straight to the quick taste (about ten minutes)
    --quiet            no music or sound effects (in the game, V turns the sound down, then off)
    --test             tester's dials: press T at any time to raise or lower levels,
                       health, healing touches and coins, for one trainer, for
                       everyone, or for the creature facing you

For trying out later parts without playing up to them (your saved journey
is left alone):
    --hero NAME --from LAND      start in a land: home, 1, 2, 3, 4 or 5
    --hero NAME --from citadel   start at the foot of the Citadel
    --hero NAME --from top       start at the Citadel's final floor
"""
import os
import sys

from . import rules as R
from . import state as S
from .engine import sixel, sound, term
from .engine.display import Display
from .engine.ui import UI, Quit
from .story import STORY, Game

T = R.TUNING


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


def preview_state(hero, where):
    """A journey already some way along, with the party it would have by then."""
    stage = {"home": 0, "citadel": 6, "top": 6}.get(where)
    if stage is None:
        if where not in ("1", "2", "3", "4", "5"):
            raise SystemExit("--from takes home, 1-5, citadel or top")
        stage = int(where)
    st = S.State(hero)
    joined = min(stage, 6) - 1                      # Lords already won over
    c = T["citadel"]
    if stage >= 6:                                  # a party that has trained for the Citadel
        st.party[0].team = R.make_team(hero, c["nemesis_level"], 5)
    elif stage > 0:
        st.party[0].team = R.make_team(hero, T["expected"]["levels"][stage - 1] - 1, T["expected"]["team"][stage - 1])
    for k in range(max(0, joined)):
        el = st.order[k]
        if stage >= 6:
            team = R.make_team(el, c["nemesis_level"] - 1, 4)
        else:
            team = R.make_team(el, T["expected"]["levels"][stage - 1] - 2, min(3, k + 2))
        st.party.append(S.Member(el, team))
    st.stage = st.reached = stage
    st.bag = {"remedy": 3, "tonic": 2, "charm": 2, "elixir": 1}
    st.coins = 40 + 20 * stage
    if where == "top":
        st.floor = 5
        st.climbing = True
    return st


def play(ui, argv):
    g = Game(ui)
    if "--test" in argv:
        ui.tester = g.tester_options
    hero = option(argv, "--hero")
    where = option(argv, "--from")
    if where and not hero:
        raise SystemExit("--from needs --hero as well")
    if where:
        g.no_save = True
        g.play_journey(S.Journal(), preview_state(find_hero(hero), where))
    elif "--trial" in argv:
        g.play_trial(find_hero(hero) if hero else g.choose_hero())
    else:
        g.run()


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return
    hero = option(argv, "--hero")                   # check the options before taking over the screen
    if hero:
        find_hero(hero)
    where = option(argv, "--from")
    if where:
        preview_state(find_hero(hero or "wave"), where)
    term.prepare_stdout()
    if "--quiet" not in argv:
        if os.name == "nt" and sound.missing():
            print("Getting the music ready (first time only, a few seconds)...", flush=True)
        sound.start()
    display = make_display(argv)
    keys = term.Keys()
    term.enter_screen(sys.stdout)
    try:
        ui = UI(display, keys)
        q = STORY["quit"]
        ui.confirm_quit = (q["ask"], q["saved"], q["stay"], q["leave"])
        while True:
            play(ui, argv)
            display.reset()
            if "--trial" in argv or option(argv, "--from"):
                argv = [a for a in argv if a not in ("--trial",)]
                argv = [a for i, a in enumerate(argv) if a != "--from" and (i == 0 or argv[i - 1] != "--from")]
    except (Quit, KeyboardInterrupt):
        pass
    finally:
        sound.close()
        keys.close()
        term.leave_screen(sys.stdout)
    print("Thanks for playing Entwined!")


if __name__ == "__main__":
    main(sys.argv[1:])
