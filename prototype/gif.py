"""Minimal animated-GIF writer (standard library only).

Frames are given as palette indices for a sub-rectangle of the screen, so
only the part that changed needs encoding. Colour tables are 256 entries.
"""
import struct


def lzw_encode(data, min_size=8):
    """GIF-flavoured LZW (variable code width, max 12 bits)."""
    clear = 1 << min_size
    eoi = clear + 1
    init_bits = min_size + 1
    n_bits = init_bits
    maxcode = (1 << n_bits) - 1
    free = clear + 2
    table = {}
    out = bytearray()
    buf = 0
    nb = 0

    def emit(code, buf, nb):
        buf |= code << nb
        nb += n_bits
        while nb >= 8:
            out.append(buf & 0xFF)
            buf >>= 8
            nb -= 8
        return buf, nb

    buf, nb = emit(clear, buf, nb)
    it = iter(data)
    try:
        ent = next(it)
    except StopIteration:
        ent = None
    if ent is not None:
        for c in it:
            key = (ent << 8) | c
            v = table.get(key)
            if v is not None:
                ent = v
                continue
            buf, nb = emit(ent, buf, nb)
            if free > maxcode:
                n_bits += 1
                maxcode = 4096 if n_bits == 12 else (1 << n_bits) - 1
            ent = c
            if free < 4096:
                table[key] = free
                free += 1
            else:
                buf, nb = emit(clear, buf, nb)
                table.clear()
                free = clear + 2
                n_bits = init_bits
                maxcode = (1 << n_bits) - 1
        buf, nb = emit(ent, buf, nb)
        if free > maxcode and n_bits < 12:
            n_bits += 1
            maxcode = 4096 if n_bits == 12 else (1 << n_bits) - 1
    buf, nb = emit(eoi, buf, nb)
    if nb > 0:
        out.append(buf & 0xFF)
    return bytes(out)


def _blocks(data):
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        out.append(len(chunk))
        out += chunk
    out.append(0)
    return bytes(out)


def write_gif(path, width, height, palette, frames, loop=0):
    """palette: 256 (r, g, b) tuples.
    frames: list of (x, y, w, h, indices_bytes, delay_centiseconds)."""
    pal = list(palette) + [(0, 0, 0)] * (256 - len(palette))
    with open(path, "wb") as f:
        f.write(b"GIF89a")
        f.write(struct.pack("<HHBBB", width, height, 0xF7, 0, 0))
        f.write(bytes(v for c in pal[:256] for v in c))
        # loop forever
        f.write(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01" + struct.pack("<H", loop) + b"\x00")
        for (x, y, w, h, idx, delay) in frames:
            # graphic control: disposal 1 (keep), no transparency
            f.write(b"\x21\xF9\x04" + bytes([0x04]) + struct.pack("<H", delay) + b"\x00\x00")
            f.write(b"\x2C" + struct.pack("<HHHHB", x, y, w, h, 0))
            f.write(bytes([8]))
            f.write(_blocks(lzw_encode(idx, 8)))
        f.write(b"\x3B")


def median_cut(counts, n=256):
    """Reduce a {colour: count} histogram to n colours."""
    boxes = [list(counts.items())]
    while len(boxes) < n:
        # split the box with the widest channel range (weighted by size)
        best, best_score, best_ch = None, -1, 0
        for i, box in enumerate(boxes):
            if len(box) < 2:
                continue
            for ch in range(3):
                vals = [c[ch] for c, _ in box]
                score = (max(vals) - min(vals)) * len(box) ** 0.5
                if score > best_score:
                    best, best_score, best_ch = i, score, ch
        if best is None:
            break
        box = sorted(boxes.pop(best), key=lambda cc: cc[0][best_ch])
        total = sum(k for _, k in box)
        acc, cut = 0, 1
        for j, (_, k) in enumerate(box):
            acc += k
            if acc >= total / 2:
                cut = max(1, min(len(box) - 1, j + 1))
                break
        boxes += [box[:cut], box[cut:]]
    palette = []
    for box in boxes:
        total = sum(k for _, k in box)
        palette.append(tuple(int(round(sum(c[ch] * k for c, k in box) / total)) for ch in range(3)))
    return palette
