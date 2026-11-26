"""Putting a frame on screen: the picture plus the text box under it.

Two ways to draw the picture:
  sixel   HD art (scale 2) as real pixels, sized to the window
  blocks  retro art (scale 1) as coloured half-block characters
"""
from . import sixel

BOX_ROWS = 7          # text box height in terminal rows (5 lines of text)
BOX_COLS = 100
PIC_W, PIC_H = 100, 60    # the picture, in logical pixels


class Display:
    def __init__(self, mode, out, cell_w=10, cell_h=20, measured=False, scale=None):
        self.mode = mode                  # "sixel", "blocks" or "null" (tests)
        self.out = out
        self.S = scale or (2 if mode == "sixel" else 1)
        self.cell_w, self.cell_h, self.measured = cell_w, cell_h, measured
        self.need = (BOX_COLS, 10 + BOX_ROWS) if mode == "sixel" else (BOX_COLS, PIC_H // 2 + BOX_ROWS)
        self.adjust = 0                   # player's +/- tweak to the picture size
        self.enc = sixel.SixelEncoder()
        self.reset()

    def reset(self):
        """Forget what's on screen, so the next frame redraws everything."""
        self.last_layout = None
        self.last_img = None
        self.last_box = None

    def present(self, cv, box_lines, cols, rows):
        if self.mode == "null":
            return
        out = []
        if self.mode == "sixel":
            room_w = cols * self.cell_w
            room_h = (rows - BOX_ROWS) * self.cell_h
            k = max(1, min(room_w // cv.w, room_h // cv.h) + self.adjust)
            pic_cols = -(-cv.w * k // self.cell_w)
            pic_rows = -(-cv.h * k // self.cell_h)
            left = max(0, (cols - pic_cols) // 2)
            if self.measured:             # box right under the picture, block centred
                top = max(0, (rows - pic_rows - BOX_ROWS) // 2)
                box_top = min(rows - BOX_ROWS, top + pic_rows)
            else:                         # cell size is a guess: keep them apart
                top, box_top = 0, rows - BOX_ROWS
            layout = (k, left, top, box_top, cols, rows)
            if layout != self.last_layout:
                out.append("\x1b[0m\x1b[2J")
                self.last_layout, self.last_img, self.last_box = layout, None, None
            img = self.enc.encode(cv.px, k)
            if img != self.last_img:
                out.append("\x1b[%d;%dH" % (top + 1, left + 1))
                out.append(img)
                self.last_img = img
        else:
            layout = (cols, rows)
            if layout != self.last_layout:
                out.append("\x1b[0m\x1b[2J")
                self.last_layout, self.last_img, self.last_box = layout, None, None
            left = max(0, (cols - cv.w) // 2)
            lines = cv.to_ansi()
            top = max(0, (rows - len(lines) - BOX_ROWS) // 2)
            box_top = top + len(lines)
            if lines != self.last_img:
                prev = self.last_img or []
                for i, line in enumerate(lines):
                    if i >= len(prev) or prev[i] != line:
                        out.append("\x1b[%d;%dH%s" % (top + 1 + i, left + 1, line))
                self.last_img = lines
        if box_lines != self.last_box:
            box_left = max(0, (cols - BOX_COLS) // 2)
            for i, line in enumerate(box_lines):
                out.append("\x1b[%d;%dH%s" % (box_top + 1 + i, box_left + 1, line))
            self.last_box = list(box_lines)
        if out:
            self.out.write("".join(out))
            self.out.flush()
