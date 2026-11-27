"""Sound: music and effects, made by the game itself.

Nothing is downloaded and nothing needs installing. The tunes and effects are
written below as notes; the first time the game runs they are turned into
sound files in a folder named `.entwined/sound` in your home folder.

Playing them uses what Windows has built in (it can play looping music and
an effect at the same time). On other systems the game is silent for now.

    sound.start()            make the files if needed, get ready to play
    sound.music("road")      loop a theme (None for silence)
    sound.fx("hit")          play an effect over it
    sound.cycle()            volume: normal, quiet, off
    sound.close()
"""
import array
import hashlib
import math
import os
import random
import sys
import wave

RATE = 22050
HOME = os.path.join(os.path.expanduser("~"), ".entwined", "sound")
_STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


# =========================================================================
# The tunes. A track is (voice, loudness, notes); a note is NAME:BEATS,
# "-" is a rest, "x" a tick of noise, "k" a low thump.
# =========================================================================
def _rep(bar, n):
    return " ".join([bar] * n)


THEMES = {
    # wistful: where the journey waits to begin
    "title": dict(bpm=96, tracks=[
        ("lead", 0.50, "E5:2 A5:2 A5:2 G5:1 F5:1 G5:2 E5:1 C5:1 D5:3 -:1 "
                       "E5:2 A5:1 B5:1 C6:2 A5:2 B5:2 G5:1 B5:1 A5:4"),
        ("pluck", 0.30, " ".join(_rep(bar, 2) for bar in (
            "A3:.5 C4:.5 E4:.5 C4:.5", "F3:.5 A3:.5 C4:.5 A3:.5", "C4:.5 E4:.5 G4:.5 E4:.5", "G3:.5 B3:.5 D4:.5 B3:.5",
            "A3:.5 C4:.5 E4:.5 C4:.5", "F3:.5 A3:.5 C4:.5 A3:.5", "G3:.5 B3:.5 D4:.5 B3:.5", "A3:.5 C4:.5 E4:.5 C4:.5"))),
        ("bass", 0.55, "A2:4 F2:4 C3:4 G2:4 A2:4 F2:4 G2:4 A2:4"),
    ]),
    # a walking tune for the open road
    "road": dict(bpm=120, tracks=[
        ("lead", 0.50, "E5:1 G5:1 C6:1 G5:1 E5:1 G5:.5 A5:.5 G5:2 F5:1 A5:1 C6:1 A5:1 G5:1 B5:.5 A5:.5 G5:2 "
                       "E5:1 G5:1 C6:1.5 B5:.5 A5:1 C6:.5 B5:.5 A5:1 E5:1 F5:1 A5:1 G5:1 B5:1 C6:3 -:1"),
        ("bass", 0.60, "C3:1 G3:1 C3:1 G3:1 C3:1 G3:1 C3:1 G3:1 F2:1 C3:1 F2:1 C3:1 G2:1 D3:1 G2:1 D3:1 "
                       "C3:1 G3:1 C3:1 G3:1 A2:1 E3:1 A2:1 E3:1 F2:1 C3:1 G2:1 D3:1 C3:1 G2:1 C3:2"),
        ("hat", 0.16, _rep("-:.5 x:.5", 32)),
    ]),
    # quick and driving
    "battle": dict(bpm=152, tracks=[
        ("lead", 0.46, "A4:.5 C5:.5 E5:.5 A5:.5 E5:.5 C5:.5 A4:.5 C5:.5 B4:.5 D5:.5 E5:.5 G5:.5 E5:1 -:.5 E5:.5 "
                       "F5:.5 E5:.5 C5:.5 A4:.5 F4:.5 A4:.5 C5:.5 F5:.5 G5:.5 F5:.5 D5:.5 B4:.5 G4:.5 B4:.5 D5:1 "
                       "A5:1 E5:.5 A5:.5 C6:1 B5:.5 A5:.5 G5:.5 E5:.5 G5:.5 A5:.5 E5:2 "
                       "F5:.5 A5:.5 C6:.5 A5:.5 F5:.5 A5:.5 C6:1 B5:1 G#5:1 E5:1 G#5:.5 B5:.5"),
        ("drive", 0.50, " ".join(_rep(n + ":.5", 8) for n in ("A2", "A2", "F2", "G2", "A2", "A2", "F2", "E2"))),
        ("hat", 0.14, _rep("x:.5", 64)),
        ("kick", 0.60, _rep("k:1 -:1", 16)),
    ]),
    # slow and wary: the climb
    "citadel": dict(bpm=84, tracks=[
        ("soft", 0.50, "D5:2 F5:1 A5:1 Bb5:3 A5:1 G5:2 Bb5:1 D6:1 C#6:3 -:1 "
                       "D6:1.5 C6:.5 Bb5:1 A5:1 Bb5:2 F5:2 G5:1 Bb5:1 A5:1 E5:1 D5:4"),
        ("pluck", 0.22, " ".join(_rep(bar, 2) for bar in (
            "D4:.5 F4:.5 A4:.5 F4:.5", "Bb3:.5 D4:.5 F4:.5 D4:.5", "G3:.5 Bb3:.5 D4:.5 Bb3:.5", "A3:.5 C#4:.5 E4:.5 C#4:.5",
            "D4:.5 F4:.5 A4:.5 F4:.5", "Bb3:.5 D4:.5 F4:.5 D4:.5", "G3:.5 Bb3:.5 A3:.5 C#4:.5", "D4:.5 F4:.5 A4:.5 F4:.5"))),
        ("bass", 0.62, "D3:4 Bb2:4 G2:4 A2:4 D3:4 Bb2:4 G2:2 A2:2 D3:4"),
    ]),
    # a waltz, for the last picture
    "wedding": dict(bpm=108, tracks=[
        ("soft", 0.52, "C5:1 F5:1 A5:1 C6:2 A5:1 Bb5:1 D6:1 Bb5:1 A5:2 F5:1 G5:1 C6:1 Bb5:1 A5:2 F5:1 D5:1 G5:1 E5:1 F5:3 "
                       "A5:1 C6:1 F6:1 E6:2 C6:1 D6:1 Bb5:1 D6:1 C6:2 A5:1 Bb5:1 G5:1 E5:1 F5:1 A5:1 C6:1 Bb5:1 G5:1 E5:1 F5:3"),
        ("pluck", 0.30, _rep("F3:1 A3:1 C4:1 F3:1 A3:1 C4:1 Bb2:1 D3:1 F3:1 F3:1 A3:1 C4:1 "
                             "C3:1 E3:1 G3:1 F3:1 A3:1 C4:1 Bb2:1 C3:1 E3:1 F3:1 A3:1 C4:1", 2)),
    ]),
}

# Effects, written the same way at ten beats a second.
FX = {
    "move": [("lead", 0.30, "A5:.3")],
    "select": [("lead", 0.34, "E5:.5 B5:.8")],
    "deny": [("drive", 0.36, "F3:1 D3:1.4")],
    "next": [("soft", 0.26, "C5:.3")],
    "send": [("lead", 0.30, "G4:.4 C5:.4 G5:.6")],
    "hit": [("noise", 0.50, "x:1"), ("kick", 0.55, "k:1.2")],
    "crit": [("noise", 0.60, "x:1.6"), ("kick", 0.62, "k:1 k:1"), ("lead", 0.26, "A5:.4 E6:.8")],
    "miss": [("air", 0.26, "x:1.6")],
    "guard": [("soft", 0.40, "E4:.5 E4:.7"), ("noise", 0.16, "x:.4")],
    "heal": [("soft", 0.40, "C5:.6 E5:.6 G5:.6 C6:1.4")],
    "boost": [("lead", 0.30, "C4:.4 E4:.4 G4:.4 C5:.4 E5:.4 G5:1")],
    "cloud": [("air", 0.30, "x:3")],
    "faint": [("lead", 0.34, "G4:.9 E4:.9 C4:.9 A3:1.6")],
    "level": [("lead", 0.36, "C5:.7 E5:.7 G5:.7 C6:.7 G5:.7 C6:2.2"), ("bass", 0.4, "C3:1.4 G3:1.4 C3:2.9")],
    "lure": [("soft", 0.36, "E5:.8 G5:1.2")],
    "join": [("lead", 0.34, "C5:.6 E5:.6 G5:.6 C6:.6 E6:2.4"), ("soft", 0.3, "-:1.2 G4:1.2 C5:2.4")],
    "refuse": [("lead", 0.30, "E4:1 C4:1.6")],
    "fanfare": [("lead", 0.38, "G4:1 C5:1 E5:1 G5:1 C6:4"), ("bass", 0.45, "C3:2 G2:2 C3:4")],
    "clear": [("lead", 0.34, "C5:.6 G5:.6 C6:1.8")],
    "lose": [("soft", 0.42, "C4:2 B3:2 Bb3:2 A3:4")],
    "rest": [("soft", 0.36, "E5:1.5 C5:1.5 D5:1.5 G4:3")],
    "coin": [("lead", 0.30, "B5:.5 E6:1.2")],
    "pickup": [("lead", 0.30, "E5:.5 A5:.9")],
}
FX_BPM = 600

# how each voice sounds: (wave, pulse width, how fast it dies away, pitch slide, how much of the note sounds)
VOICES = {
    "lead": ("square", 0.25, 2.0, 0.0, 0.9),
    "soft": ("tri", 0.5, 1.2, 0.0, 0.95),
    "pluck": ("square", 0.125, 7.0, 0.0, 0.9),
    "bass": ("tri", 0.5, 0.6, 0.0, 0.92),
    "drive": ("saw", 0.5, 5.0, 0.0, 0.8),
    "hat": ("noise", 0.5, 60.0, 0.0, 0.3),
    "noise": ("noise", 0.5, 30.0, 0.0, 1.0),
    "air": ("noise", 0.5, 9.0, 0.0, 1.0),
    "kick": ("tri", 0.5, 22.0, -0.75, 1.0),
}


# =========================================================================
# Turning notes into sound
# =========================================================================
def _freq(name):
    n = _STEP[name[0]]
    i = 1
    if name[i] == "#":
        n, i = n + 1, i + 1
    elif name[i] == "b":
        n, i = n - 1, i + 1
    return 440.0 * 2 ** ((n - 9 + (int(name[i:]) - 4) * 12) / 12.0)


def _note(buf, start, seconds, hz, voice, loud, rng):
    shape, width, fade, slide, gate = VOICES[voice]
    n = min(int(seconds * gate * RATE), len(buf) - start)
    if n <= 0:
        return
    edge = max(1, int(0.004 * RATE))
    tail = max(1, int(0.02 * RATE))
    phase, held, hold = 0.0, 0.0, 0
    step0 = hz / RATE
    for i in range(n):
        env = math.exp(-fade * i / RATE)
        if i < edge:
            env *= i / edge
        if n - i < tail:
            env *= (n - i) / tail
        if shape == "noise":
            if hold <= 0:
                held, hold = rng.uniform(-1, 1), (1 if voice != "air" else 3)
            hold -= 1
            s = held
        else:
            phase += step0 * (1 + slide * i / n)
            x = phase % 1.0
            if shape == "square":
                s = 1.0 if x < width else -1.0
            elif shape == "tri":
                s = 4 * abs(x - 0.5) - 1
            else:
                s = 2 * x - 1
        buf[start + i] += s * loud * env


def render(tracks, bpm):
    """Notes in, a list of samples (-1..1) out."""
    beat = 60.0 / bpm
    length = 0.0
    parsed = []
    for voice, loud, notes in tracks:
        t, items = 0.0, []
        for token in notes.split():
            name, _, beats = token.partition(":")
            b = float(beats) if beats else 1.0
            items.append((t, b, name))
            t += b
        parsed.append((voice, loud, items))
        length = max(length, t)
    buf = [0.0] * (int(length * beat * RATE) + 1)
    rng = random.Random(7)
    for voice, loud, items in parsed:
        for t, b, name in items:
            if name == "-":
                continue
            hz = 3000.0 if name == "x" else 110.0 if name == "k" else _freq(name)
            _note(buf, int(t * beat * RATE), b * beat, hz, voice, loud, rng)
    peak = max(0.001, max(abs(v) for v in buf))
    k = min(1.0, 0.85 / peak)
    return [v * k for v in buf]


def _write(path, samples):
    data = array.array("h", (int(max(-1.0, min(1.0, v)) * 32000) for v in samples))
    if sys.byteorder == "big":
        data.byteswap()
    tmp = path + ".tmp"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    os.replace(tmp, path)


def folder():
    """Where this version of the sounds lives (it changes whenever the tunes above change)."""
    mark = hashlib.sha1(repr((THEMES, FX, VOICES, FX_BPM, RATE)).encode()).hexdigest()[:10]
    return os.path.join(HOME, mark)


def missing():
    d = folder()
    return [n for n in list(THEMES) + list(FX) if not os.path.exists(os.path.join(d, n + ".wav"))]


def prepare(tell=None):
    """Make any sound files that aren't there yet. `tell(name)` is called before each one."""
    d = folder()
    os.makedirs(d, exist_ok=True)
    for name in missing():
        if tell:
            tell(name)
        if name in THEMES:
            samples = render(THEMES[name]["tracks"], THEMES[name]["bpm"])
        else:
            samples = render(FX[name], FX_BPM)
        _write(os.path.join(d, name + ".wav"), samples)
    return d


# =========================================================================
# Playing (Windows)
# =========================================================================
LEVELS = [("normal", 1.0), ("quiet", 0.45), ("off", 0.0)]
MUSIC_SHARE = 0.5              # music sits under the effects


class _State:
    on = False                 # can and should we play?
    send = None
    opened = set()
    now = None                 # the theme that is playing
    level = 0


_S = _State()


def _mci(text):
    buf = ctypes_buffer()
    return _S.send(text, buf, 63, None)


def ctypes_buffer():
    import ctypes
    return ctypes.create_unicode_buffer(64)


def _volume(alias, share):
    _mci("setaudio %s volume to %d" % (alias, int(1000 * LEVELS[_S.level][1] * share)))


def _open(name):
    if name not in _S.opened:
        if _mci('open "%s" type mpegvideo alias s_%s' % (os.path.join(folder(), name + ".wav"), name)) != 0:
            return False
        _S.opened.add(name)
        _volume("s_" + name, MUSIC_SHARE if name in THEMES else 1.0)
    return True


def start(level=0, tell=None):
    """Get ready to play. Returns True if there will be sound."""
    if _S.on:
        return True
    if os.name != "nt":
        return False
    try:
        import ctypes
        prepare(tell)
        _S.send = ctypes.windll.winmm.mciSendStringW
        _S.level = level
        _S.on = True
    except Exception:                       # no sound is never a reason not to play the game
        _S.on = False
    return _S.on


def music(name):
    """Loop a theme under everything else (None for silence)."""
    if not _S.on or name == _S.now:
        if not _S.on:
            _S.now = name
        return
    if _S.now:
        _mci("stop s_%s" % _S.now)
    _S.now = name
    if name and _open(name):
        _mci("play s_%s from 0 repeat" % name)


def current():
    return _S.now


def battle():
    """A fight is coming: start its music now, remembering what to go back to afterwards.
    (The Citadel keeps its own theme through its fights.) Returns the theme to go back to."""
    if _S.now not in ("battle", "citadel"):
        _S.before = _S.now
        music("battle")
    return _S.now if _S.now == "citadel" else getattr(_S, "before", None)


def fx(name):
    """Play an effect once, over the music."""
    if _S.on and LEVELS[_S.level][1] > 0 and _open(name):
        _mci("play s_%s from 0" % name)


def cycle():
    """Normal, quiet, off, and round again. Returns the new setting's name."""
    _S.level = (_S.level + 1) % len(LEVELS)
    if _S.on:
        for name in _S.opened:
            _volume("s_" + name, MUSIC_SHARE if name in THEMES else 1.0)
    return LEVELS[_S.level][0]


def close():
    if _S.on:
        for name in list(_S.opened):
            _mci("close s_%s" % name)
    _S.opened = set()
    _S.on = False
    _S.now = None
