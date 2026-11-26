"""Entwined concept art.

    python show.py            # print all three images in the terminal
    python show.py hero       # just one (hero / creature / citadel)
    python show.py --png      # also save PNGs into images/
    python show.py --hd       # high-resolution version (needs ~200 columns)
"""
import os
import sys

from scenes import SCENES

if os.name == "nt":
    os.system("")  # turn on ANSI colour handling in older Windows consoles


def main(argv):
    save = "--png" in argv
    scale = 2 if "--hd" in argv else 1
    names = [a for a in argv if not a.startswith("--")] or list(SCENES)
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, "images")
    for name in names:
        cv = SCENES[name](scale)
        cv.print()
        print()
        if save:
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, name + ("_hd" if scale > 1 else "") + ".png")
            cv.save_png(path)
            print("saved", path)


if __name__ == "__main__":
    main(sys.argv[1:])
