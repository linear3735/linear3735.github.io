"""Tiny SVG helper so every diagram in this post shares one look.

Palette is lifted from the blog's own theme (assets/css/site.css) so the
figures sit on the page rather than on top of it.
"""

INK = "#252b33"
MUTED = "#737c88"
BLUE = "#3568a3"
LINE = "#e7eaf0"
PAPER = "#ffffff"
CANVAS = "#f3f5f7"

FILL_BLUE = "#e8eff7"   # blue-tinted node
FILL_WARM = "#fdf0e3"   # highlight / "this one matters"
FILL_TEAL = "#e4f1ee"   # secondary
FILL_GREY = "#eef1f5"   # inert

# text colours that match the tinted fills above (the fills are too light to
# read as text)
WARM_TXT = "#b5762a"
TEAL_TXT = "#2f7d6d"

FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
        "'Hiragino Sans GB','Microsoft YaHei',sans-serif")
MONO = "SFMono-Regular,Consolas,'Liberation Mono',monospace"


def _preserve_indent(t):
    r"""Turn leading ASCII spaces into no-break spaces.

    Sketching code in a diagram means sketching indentation, and SVG drops it:
    leading whitespace in a text node is collapsed away, so `    cur = ...`
    renders flush left and a loop body looks like a flat list of statements.
    `xml:space="preserve"` does NOT fix this (verified with sips/WebKit) — only
    a non-collapsible space character survives.  U+00A0 is the one that renders
    at the same advance width as a normal space, so the code still lines up.
    """
    stripped = t.lstrip(" ")
    if stripped == t:
        return t
    return "\u00a0" * (len(t) - len(stripped)) + stripped


def _esc(t):
    """XML-escape text content.  `&` must be replaced first."""
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts = []

    # ---------- primitives ----------
    def raw(self, s):
        self.parts.append(s)
        return self

    def rect(self, x, y, w, h, fill=PAPER, stroke=INK, sw=1.4, rx=6, dash=None, op=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' opacity="{op}"' if op else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{o}/>')
        return self

    def circle(self, cx, cy, r, fill=PAPER, stroke=INK, sw=1.4):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="{sw}"/>')
        return self

    def text(self, x, y, t, size=14, fill=INK, anchor="middle", weight="400",
             font=None, style=None):
        # No font-family by default: the SVG is inlined next to the post body,
        # so text inherits body's font stack (site.css).  Hardcoding a family
        # here would fight the page style.  Pass `font=` to override.
        if t == "":
            return self          # never emit an empty <text> node
        f = f' font-family="{font}"' if font else ""
        s = f' font-style="{style}"' if style else ""
        # Escape by default.  Diagram labels routinely carry things like
        # `i < n`, `a && b`, `preSum[i] > 0`; a bare `<` or `&` makes the file
        # invalid XML, and sips then fails with a bare exit 13 and no message,
        # which is a genuinely confusing failure.  Escaping here is worth more
        # than the convenience of hand-writing markup — callers who really need
        # inline markup (e.g. <tspan>) can use .raw_text().
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{f}{s}>'
            f'{_esc(_preserve_indent(t))}</text>')
        return self

    def raw_text(self, x, y, markup, size=14, fill=INK, anchor="middle",
                 weight="400", font=None, style=None):
        """Like text(), but content is emitted verbatim — no escaping.

        Only for deliberate inline markup such as <tspan>.
        """
        if markup == "":
            return self
        f = f' font-family="{font}"' if font else ""
        s = f' font-style="{style}"' if style else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{f}{s}>'
            f'{markup}</text>')
        return self

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.4, dash=None, cap="round"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                          f'stroke="{stroke}" stroke-width="{sw}" '
                          f'stroke-linecap="{cap}"{d}/>')
        return self

    def arrow(self, x1, y1, x2, y2, stroke=BLUE, sw=1.8, dash=None, head=8.0):
        """Line with a solid triangular head at (x2, y2)."""
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{bx:.2f}" y2="{by:.2f}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}/>')
        p = 4.6  # half-width of the head
        pts = (f"{x2:.2f},{y2:.2f} "
               f"{bx - p * math.sin(ang):.2f},{by + p * math.cos(ang):.2f} "
               f"{bx + p * math.sin(ang):.2f},{by - p * math.cos(ang):.2f}")
        self.parts.append(f'<polygon points="{pts}" fill="{stroke}"/>')
        return self

    # ---------- composite ----------
    def box(self, x, y, w, h, label, sub=None, fill=PAPER, stroke=INK, size=14,
            sub_size=11, sw=1.4):
        """A node with an optional subscript line."""
        self.rect(x, y, w, h, fill=fill, stroke=stroke, sw=sw)
        if sub:
            self.text(x + w / 2, y + h / 2 - 3, label, size=size)
            self.text(x + w / 2, y + h / 2 + 14, sub, size=sub_size, fill=MUTED)
        else:
            self.text(x + w / 2, y + h / 2 + size * 0.36, label, size=size)
        return self

    def cell(self, x, y, w, h, label, fill=PAPER, stroke=INK, size=14, sub=None):
        """An array cell: sharp corners, sits flush against its neighbours."""
        self.rect(x, y, w, h, fill=fill, stroke=stroke, rx=0, sw=1.4)
        if sub:
            self.text(x + w / 2, y + h / 2 - 2, label, size=size)
            self.text(x + w / 2, y + h / 2 + 14, sub, size=10, fill=MUTED)
        else:
            self.text(x + w / 2, y + h / 2 + size * 0.36, label, size=size)
        return self

    def panel(self, x, y, w, h, fill=CANVAS, stroke=LINE, rx=10):
        self.rect(x, y, w, h, fill=fill, stroke=stroke, rx=rx, sw=1.2)
        return self

    def label(self, x, y, t, size=12, fill=MUTED, anchor="start", weight="400"):
        self.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
        return self

    def save(self, path):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'role="img">')
        body = "\n".join("  " + p for p in self.parts)
        open(path, "w", encoding="utf-8").write(
            f'{head}\n  <rect width="{self.w}" height="{self.h}" fill="{PAPER}"/>\n'
            f'{body}\n</svg>\n')
        print(f"  wrote {path}")


# --------------------------------------------------------------------------
# Geometric self-check. Eyeballing renders does not scale, so every text run
# and arrow gets a hitbox and we assert they do not collide, do not escape
# the canvas, and do not spill out of the panel they were meant to sit in.
# --------------------------------------------------------------------------

def _adv(ch, size):
    """Rough advance width. CJK/fullwidth glyphs are ~1em, Latin ~0.55em."""
    o = ord(ch)
    wide = (0x1100 <= o <= 0x115F or 0x2E80 <= o <= 0xA4CF or
            0xAC00 <= o <= 0xD7A3 or 0xF900 <= o <= 0xFAFF or
            0xFE30 <= o <= 0xFE6F or 0xFF00 <= o <= 0xFF60 or
            0xFFE0 <= o <= 0xFFE6)
    return size * (1.0 if wide else 0.55)


class Check:
    """Collects hitboxes while a diagram is being built, then validates."""

    def __init__(self, svg):
        self.svg = svg
        self.texts = []      # (name, x0, y0, x1, y1)
        self.arrows = []     # (name, x0, y0, x1, y1)
        self.panels = []     # (name, x0, y0, x1, y1)

    def text(self, name, x, y, t, size=14, anchor="middle"):
        w = sum(_adv(c, size) for c in t)
        if anchor == "middle":
            x0 = x - w / 2
        elif anchor == "end":
            x0 = x - w
        else:
            x0 = x
        # y is the baseline
        self.texts.append((name, x0, y - size * 0.80, x0 + w, y + size * 0.24))
        return self

    def arrow(self, name, x1, y1, x2, y2):
        self.arrows.append((name, min(x1, x2), min(y1, y2),
                            max(x1, x2), max(y1, y2)))
        return self

    def panel(self, name, x, y, w, h):
        self.panels.append((name, x, y, x + w, y + h))
        return self

    @staticmethod
    def _ov(a, b, pad=0.0):
        return (a[1] < b[3] - pad and b[1] < a[3] - pad and
                a[2] < b[4] - pad and b[2] < a[4] - pad)

    def run(self, label):
        bad = []
        # 1. text vs text
        for i in range(len(self.texts)):
            for j in range(i + 1, len(self.texts)):
                a, b = self.texts[i], self.texts[j]
                if self._ov(a, b, pad=0.5):
                    bad.append(f"text/text overlap: {a[0]!r} <-> {b[0]!r}")
        # 2. text vs arrow (arrows are thin; use a 3px pad)
        for a in self.texts:
            for r in self.arrows:
                if self._ov(a, r, pad=3.0):
                    bad.append(f"text/arrow overlap: {a[0]!r} <-> {r[0]!r}")
        # 3. everything must stay on the canvas
        W, H = self.svg.w, self.svg.h
        for a in self.texts:
            # Hitboxes are (name, left, top, right, bottom) and y grows
            # downward.  This line used to read `a[3] < 0 or a[4] > H`: the
            # right edge was tested against 0 (so text running off the LEFT
            # edge was missed whenever it started at x >= 0) and the bottom
            # edge against H (so text hanging off the BOTTOM was missed), while
            # the top was tested against H (false positives near the bottom).
            if a[1] < 0 or a[3] > W or a[2] < 0 or a[4] > H:
                bad.append(f"text off-canvas: {a[0]!r} "
                           f"({a[1]:.0f},{a[2]:.0f})-({a[3]:.0f},{a[4]:.0f}) "
                           f"canvas {W}x{H}")
        for r in self.arrows:
            if r[1] < 0 or r[3] > W or r[2] < 0 or r[4] > H:
                bad.append(f"arrow off-canvas: {r[0]!r}")
        # 4. text meant to be inside a panel must stay inside it
        for p in self.panels:
            for a in self.texts:
                # Hitbox is (name, left, top, right, bottom): centre is the
                # midpoint of left..right and of top..bottom.  This read
                # `(a[1]+a[2])/2, (a[3]+a[4])/2` — mixing an x with a y — so
                # the "is this label inside that panel" test was nonsense and
                # the spill check below fired on the wrong labels.
                cx, cy = (a[1] + a[3]) / 2, (a[2] + a[4]) / 2
                if p[1] <= cx <= p[3] and p[2] <= cy <= p[4]:      # centred inside
                    if a[1] < p[1] + 2 or a[3] > p[3] - 2:
                        bad.append(f"text spills out of {p[0]!r}: {a[0]!r} "
                                   f"x {a[1]:.0f}..{a[3]:.0f} vs panel "
                                   f"{p[1]:.0f}..{p[3]:.0f}")
        if bad:
            print(f"  !! {label}: {len(bad)} layout problem(s)")
            for b in bad:
                print(f"       - {b}")
        else:
            print(f"  ok {label}: {len(self.texts)} texts, "
                  f"{len(self.arrows)} arrows, no collisions")
        return len(bad)
