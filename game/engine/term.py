"""Terminal helpers: keyboard, window size, screen setup."""
import os
import sys


def term_size(default=(100, 40)):
    try:
        return tuple(os.get_terminal_size())
    except OSError:
        return default           # not a terminal: assume it fits


def enter_screen(out):
    out.write("\x1b[?1049h\x1b[?25l\x1b[0m\x1b[2J")   # alternate screen, hide cursor
    out.flush()


def leave_screen(out):
    out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
    out.flush()


def prepare_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if os.name == "nt":
        os.system("")            # turn on ANSI handling in older consoles


class Keys:
    """Non-blocking key reader for Windows (msvcrt) and Mac/Linux (termios).
    poll() returns names: up, down, left, right, enter, quit, bigger, smaller."""

    PLAIN = {"\r": "enter", "\n": "enter", " ": "enter", "\x1b": "quit",
             "w": "up", "s": "down", "a": "left", "d": "right",
             "W": "up", "S": "down", "A": "left", "D": "right",
             "+": "bigger", "=": "bigger", "-": "smaller", "_": "smaller"}

    def __init__(self):
        self.win = os.name == "nt"
        if not self.win:
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)

    def close(self):
        if not self.win:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    def poll(self):
        keys = []
        if self.win:
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    keys.append({"H": "up", "P": "down", "K": "left", "M": "right"}.get(msvcrt.getwch()))
                else:
                    keys.append(self.PLAIN.get(ch))
        else:
            import select
            while select.select([sys.stdin], [], [], 0)[0]:
                data = os.read(self.fd, 64).decode(errors="ignore")
                for seq, name in (("\x1b[A", "up"), ("\x1b[B", "down"),
                                  ("\x1b[D", "left"), ("\x1b[C", "right")):
                    while seq in data:
                        keys.append(name)
                        data = data.replace(seq, "", 1)
                keys += [self.PLAIN.get(ch) for ch in data]
        return [k for k in keys if k]


def size_message(cols, rows, need):
    """A short, centred 'make the window bigger' screen that fits any size."""
    lines = [
        ("\x1b[1;38;2;255;200;90m", "The window is too small"),
        ("", ""),
        ("\x1b[38;2;230;230;235m", "Needs at least %d x %d characters." % need),
        ("\x1b[38;2;230;230;235m", "Yours is %d x %d." % (cols, rows)),
        ("", ""),
        ("\x1b[38;2;170;200;255m", "Make the window bigger,"),
        ("\x1b[38;2;170;200;255m", "press F11 for full screen,"),
        ("\x1b[38;2;170;200;255m", "or zoom out with Ctrl and minus (-)."),
        ("", ""),
        ("\x1b[38;2;150;150;160m", "It starts as soon as it fits.  Esc quits."),
    ]
    top = max(0, (rows - len(lines)) // 2)
    out = ["\n" * top]
    for style, text in lines:
        text = text[:max(0, cols - 1)]
        pad = max(0, (cols - len(text)) // 2)
        out.append(" " * pad + style + text + "\x1b[0m\n")
    return "".join(out).rstrip("\n")
