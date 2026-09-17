#!/usr/bin/env python3
"""
Structural-change coverage wheel
================================

A radial map of which dimensions of structural change each PhD chapter covers.

    framework ring   one flat, light colour per category; every dimension is
                     a segment of the same single ring, all on one level
    chapter rings    one per chapter, a faint track carrying a dot at every
                     dimension that chapter covers
    the gap          the wheel stops on the right, where the chapter names sit

Three layouts, differing in how the ring is labelled
----------------------------------------------------
    d  names set as genuinely curved text following the ring
    e  names on leader lines, set horizontally in two columns
    f  names set radially inside a thicker ring

Usage
-----
    python structural_coverage.py --design f            # static -> PNG/SVG/PDF
    python structural_coverage.py --design f --animate  # animated SVG (web)
    python structural_coverage.py --all                 # render all three
    python structural_coverage.py --columns             # print column order
    python structural_coverage.py --csv data.csv        # matrix from a CSV
    python structural_coverage.py --exclude 5 --out structural_coverage_no5
                                                        # drop chapter 5
"""

from __future__ import annotations

import argparse
import colorsys
import csv
import math
import re
import textwrap
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.ft2font import FT2Font
from matplotlib.patches import Rectangle, Wedge

# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

# (category, colour, dimensions). A category with no dimensions listed takes a
# single segment named after itself. Every category sits at the same level and
# is one flat colour: no shading within a category.
CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("Demand", "#E3C68A", ["Level", "Composition"]),
    ("Employment", "#93B3C8", ["Level", "Wage", "Condition", "Skills"]),
    ("Distribution", "#F0A99D", []),
    ("Sectoral composition", "#98C7AC", []),
    ("Industrial organisation", "#C7A6B7", [
        "Market concentration", "Trade", "Business model", "Geography", "IO structure"]),
    ("Technical change", "#B7ACD8", ["Productivity", "R&D", "Investment"]),
    ("Institutions", "#A8BCC5", []),
]

CHAPTERS: list[str] = [
    "1. Systematic mapping",
    "2. Quality over Quantity",
    "3. Enabling investment",
    "4. Periphery impact",
    "5. Skill reallocation",
]

# 'X' = covered, spaces ignored. Column order (run --columns to reprint):
#
#   Demand    Employment      Di  Se  Industrial organisation  Tech chg  In
#   Lvl Cmp   Lvl Wg Cnd Skl  --  --  Mkt Trd Bus Geo IOst     Prd RD Inv  --
#
COVERAGE: dict[str, str] = {
    "1. Systematic mapping":    "XX  XXXX  X  X  .XXX.  XX.  .",
    "2. Quality over Quantity": "XX  XX..  X  X  ..X..  X..  .",
    "3. Enabling investment":   "XX  X...  X  X  .....  X.X  .",
    "4. Periphery impact":      "XX  XX..  X  X  .X.XX  X..  .",
    "5. Skill reallocation":    "XX  XX.X  X  X  ...XX  X..  .",
}

# CIRED blue, flat across every project: 6.9:1 on white, and the same for a
# white numeral on the chip. Projects are told apart by number and radius.
CIRED_BLUE = "#05646D"
CHAPTER_COLORS: list[str] = [CIRED_BLUE] * 5

# The site loads Fira Sans, and it is installed here too, so the SVG
# renders the same face in a browser as matplotlib laid out.
FONT_FAMILY = "Fira Sans"
matplotlib.rcParams.update({"font.family": FONT_FAMILY, "svg.fonttype": "none"})

DOT_SIZE = 68
TRACK_LW = 1.1
TRACK_ALPHA = 0.55
INK = "#33383c"


# ---------------------------------------------------------------------------
# LAYOUTS
# ---------------------------------------------------------------------------

LAYOUTS: dict[str, dict] = {
    # curved names following the ring
    "d": dict(
        gap=58.0, labels="curved", names_in_gap=False,
        r_ring=(0.97, 1.10), r_label=1.155, line_step=0.082,
        r_cat_arc=1.50, r_cat_label=1.575,
        r_ch_out=0.85, r_ch_step=0.113, x_tail=1.70,
        xlim=(-1.80, 2.72), ylim=(-1.80, 1.80),
        sub_fs=7.2, cat_fs=11.5, wrap=13,
    ),
    # leader lines out to horizontal names; chapter names sit inside the gap
    "e": dict(
        gap=62.0, labels="leader", names_in_gap=True,
        r_ring=(0.95, 1.07), r_stub_in=1.30, r_stub=1.42, x_col=2.05,
        r_cat_label=1.175,
        r_ch_out=0.86, r_ch_step=0.118, x_tail=1.02,
        xlim=(-3.05, 2.95), ylim=(-1.72, 1.72),
        sub_fs=8.0, cat_fs=10.5, wrap=0,
    ),
    # radial names inside a thicker ring
    "f": dict(
        # A smaller gap buys angular room and a thicker ring buys radial room;
        # together they are what let the type be set large enough to survive
        # the SVG being scaled down into a web column.
        gap=48.0, labels="radial-in", names_in_gap=False,
        r_ring=(0.84, 1.52), r_cat_arc=1.60, r_cat_label=1.695,
        r_ch_out=0.72, r_ch_step=0.102, x_tail=1.54,
        xlim=(-1.92, 2.92), ylim=(-1.92, 1.92),
        sub_fs=13.0, cat_fs=16.0, wrap=12, label_flip=True,
    ),
}


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _rgb_to_hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c * 255))) for c in rgb)


def darken(base: str, f: float = 0.55) -> str:
    r, g, b = _hex_to_rgb(base)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return _rgb_to_hex(colorsys.hls_to_rgb(h, max(0.0, l * f), min(1.0, s * 1.15)))


# ---------------------------------------------------------------------------
# Text metrics and curved text
# ---------------------------------------------------------------------------

_FONT_CACHE: dict[float, FT2Font] = {}


def _font(fs: float) -> FT2Font:
    if fs not in _FONT_CACHE:
        f = FT2Font(findfont(FontProperties(family=FONT_FAMILY, size=fs)))
        _FONT_CACHE[fs] = f
    f = _FONT_CACHE[fs]
    f.set_size(fs, 72)
    return f


def text_width_pt(s: str, fs: float) -> float:
    f = _font(fs)
    f.set_text(s, 0)
    return f.get_width_height()[0] / 64.0


def char_widths_pt(s: str, fs: float) -> list[float]:
    return [text_width_pt(c, fs) for c in s]


def curved_text(ax, r, theta_c, lines, fs, color, ppu, weight="normal", zorder=5):
    """Set text along an arc, one glyph at a time.

    matplotlib has no curved text, so each character is placed at its own angle
    and rotated to the local tangent. Multi-line labels stack on concentric
    arcs. Text on the lower half is flipped so it never reads upside down.
    """
    if isinstance(lines, str):
        lines = [lines]
    flip = 180.0 < (theta_c % 360.0) < 360.0
    step = 1.12 * fs / ppu  # line spacing in data units
    # Radius grows outward, but "up" for flipped text points inward, so the
    # first line takes the outermost arc only when the text is not flipped.
    order = lines if flip else list(reversed(lines))

    for li, line in enumerate(order):
        rr = r + li * step
        widths = char_widths_pt(line, fs)
        total_ang = math.degrees((sum(widths) / ppu) / rr)
        sgn = 1.0 if flip else -1.0
        start = theta_c - sgn * total_ang / 2.0
        acc = 0.0
        for ch, w in zip(line, widths):
            aw = math.degrees((w / ppu) / rr)
            a = start + sgn * (acc + aw / 2.0)
            x, y = polar(rr, a)
            ax.text(x, y, ch, rotation=(a + 90.0) if flip else (a - 90.0),
                    rotation_mode="anchor", ha="center", va="center",
                    fontsize=fs, color=color, fontweight=weight, zorder=zorder)
            acc += aw


def fit_lines(s: str, fs: float, arc_units: float, ppu: float) -> list[str]:
    """Wrap a label onto as many curved lines as it needs to fit its arc.

    Keeps one font size for every category name; only the number of lines
    changes, so nothing is set smaller than its neighbours.
    """
    budget = arc_units * ppu * 0.94
    words = s.split()
    for n in range(1, len(words) + 1):
        width = max(1, math.ceil(len(s) / n))
        lines = textwrap.wrap(s, width=width, break_long_words=False)
        if all(text_width_pt(l, fs) <= budget for l in lines):
            return lines
    return [s]


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


# A category with no dimensions of its own still has to carry its name on the
# outer arc at the same size as the others, so give it more angular width than
# a single dimension would get. Everything else is one unit per dimension.
SOLO_WIDTH = 1.5


def build_slots(gap: float) -> list[dict]:
    slots: list[dict] = []
    weights: list[float] = []
    for ci, (cat, colour, subs) in enumerate(CATEGORIES):
        names = subs if subs else [cat]
        for name in names:
            slots.append({"category": cat, "category_index": ci, "label": name,
                          "is_own_label": not subs, "colour": colour,
                          "index": len(slots)})
            weights.append(SOLO_WIDTH if not subs else 1.0)

    span = 360.0 - 2.0 * gap
    unit = span / sum(weights)
    a = gap
    for s, w in zip(slots, weights):
        s["theta0"] = a
        s["theta1"] = a + w * unit
        s["theta"] = 0.5 * (s["theta0"] + s["theta1"])
        a = s["theta1"]
    return slots


DATA_XLSX = Path(__file__).with_name("structural_coverage.xlsx")


def _rows_from_xlsx(path: Path) -> list[list[str]]:
    import openpyxl

    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    return [["" if c is None else str(c).strip() for c in row]
            for row in ws.iter_rows(values_only=True)]


def _match_chapters(rows: list[list[str]], n: int) -> dict[str, list[bool]]:
    """Match sheet rows to CHAPTERS on their leading number, so the figure can
    use short names while the sheet keeps the full ones."""
    by_num = {}
    for r in rows:
        m = re.match(r"\s*(\d+)", r[0])
        if not m:
            continue
        cells = (r[1 : n + 1] + [""] * n)[:n]
        by_num[int(m.group(1))] = [c.strip() not in {"", "0"} for c in cells]

    out = {}
    for ch in CHAPTERS:
        m = re.match(r"\s*(\d+)", ch)
        k = int(m.group(1)) if m else None
        if k not in by_num:
            raise SystemExit(f"No row in the data for chapter {ch!r}")
        out[ch] = by_num[k]
    return out


def parse_coverage(slots, csv_path: Path | None) -> dict[str, list[bool]]:
    n = len(slots)
    if csv_path is None and DATA_XLSX.exists():
        return _match_chapters(_rows_from_xlsx(DATA_XLSX), n)
    if csv_path is not None and csv_path.suffix.lower() == ".xlsx":
        return _match_chapters(_rows_from_xlsx(csv_path), n)
    if csv_path is not None:
        rows = [r for r in csv.reader(csv_path.open(newline="", encoding="utf-8"))
                if r and any(c.strip() for c in r)]
        body = [r for r in rows if r[0].strip() not in {"", "Category", "Subcategory"}]
        return {r[0].strip(): [c.strip() not in {"", "0"} for c in (r[1 : n + 1] + [""] * n)[:n]]
                for r in body}
    out = {}
    for chapter in CHAPTERS:
        row = COVERAGE[chapter].replace(" ", "")
        if len(row) != n:
            raise SystemExit(f"COVERAGE[{chapter!r}] has {len(row)} marks, need {n}")
        out[chapter] = [c.upper() == "X" for c in row]
    return out


def polar(r, deg):
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def arc_points(r, t0, t1, n=400):
    a = np.radians(np.linspace(t0, t1, n))
    return r * np.cos(a), r * np.sin(a)


def wrap_lines(text: str, width: int) -> list[str]:
    if not width or len(text) <= width:
        return [text]
    return textwrap.wrap(text, width=width, break_long_words=False)


def declutter(ys: list[float], min_gap: float) -> list[float]:
    """Push labels apart, preserving order, keeping the block centred."""
    out = sorted(range(len(ys)), key=lambda i: ys[i], reverse=True)
    vals = [ys[i] for i in out]
    for k in range(1, len(vals)):
        if vals[k - 1] - vals[k] < min_gap:
            vals[k] = vals[k - 1] - min_gap
    shift = (sum(ys) - sum(vals)) / max(1, len(vals))
    res = [0.0] * len(ys)
    for k, i in enumerate(out):
        res[i] = vals[k] + shift
    return res


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def draw_ring(ax, slots, L, ppu) -> None:
    r0, r1 = L["r_ring"]
    for s in slots:
        ax.add_patch(Wedge((0, 0), r1, s["theta0"], s["theta1"], width=r1 - r0,
                           facecolor=s["colour"], edgecolor="white",
                           linewidth=0.9, zorder=3))

    if L["labels"] == "curved":
        for s in slots:
            if s["is_own_label"]:
                continue  # named on the outer arc with every other category
            curved_text(ax, L["r_label"], s["theta"], wrap_lines(s["label"], L["wrap"]),
                        L["sub_fs"], INK, ppu)
    elif L["labels"] == "radial-in":
        for s in slots:
            if s["is_own_label"]:
                continue  # named on the outer arc with every other category
            # label_flip=False: every label reads outward from the centre, so
            # they all sit the same way round in their wedge - but radial text
            # cannot do that around a circle without inverting on the left.
            # label_flip=True keeps every label upright instead.
            # Radial, centred in the wedge, and turned the same way everywhere.
            # Radial text has to reverse somewhere; applying the turn to every
            # label puts that reversal in the gap, where there is nothing to
            # see, so no two labels on the ring disagree.
            rot = s["theta"] + 180.0
            x, y = polar(0.5 * (r0 + r1), s["theta"])
            ax.text(x, y, "\n".join(wrap_lines(s["label"], L["wrap"])), rotation=rot,
                    rotation_mode="anchor", ha="center", va="center",
                    fontsize=L["sub_fs"], color=INK, linespacing=1.15, zorder=5)
    else:  # leader lines out to horizontal text
        right = [s for s in slots if not (90 < s["theta"] % 360 < 270)]
        left = [s for s in slots if 90 < s["theta"] % 360 < 270]
        gap_y = 1.30 * L["sub_fs"] / ppu
        for group, side in ((right, 1), (left, -1)):
            group = [s for s in group if not s["is_own_label"]]
            group = sorted(group, key=lambda s: polar(L["r_stub"], s["theta"])[1])
            ys = declutter([polar(L["r_stub"], s["theta"])[1] for s in group], gap_y)
            for s, y in zip(group, ys):
                ex, ey = polar(L["r_stub_in"], s["theta"])
                sx, sy = polar(L["r_stub"], s["theta"])
                x_col = side * L["x_col"]
                ax.plot([ex, sx, x_col], [ey, sy, y], color="#b9c0c5", lw=0.7,
                        solid_capstyle="round", zorder=2)
                ax.text(x_col + side * 0.04, y, s["label"], ha="left" if side > 0 else "right",
                        va="center", fontsize=L["sub_fs"], color=INK, zorder=5)

    # category names
    for ci, (cat, colour, _subs) in enumerate(CATEGORIES):
        members = [s for s in slots if s["category_index"] == ci]
        t0, t1 = members[0]["theta0"], members[-1]["theta1"]
        mid = 0.5 * (t0 + t1)
        dark = darken(colour)

        if L["labels"] == "leader":
            # thick arc hugging the ring, with the name curved just outside it
            bx, by = arc_points(r1 + 0.035, t0 + 0.6, t1 - 0.6)
            ax.plot(bx, by, color=dark, lw=3.0, solid_capstyle="butt", zorder=4)
            arc_units = math.radians(t1 - t0) * L["r_cat_label"]
            fs = fit_fs(cat, L["cat_fs"], arc_units, ppu)
            curved_text(ax, L["r_cat_label"], mid, [cat], fs, dark, ppu, weight="bold")
            continue

        bx, by = arc_points(L["r_cat_arc"], t0 + 1.0, t1 - 1.0)
        ax.plot(bx, by, color=dark, lw=1.6, solid_capstyle="round", zorder=4)
        arc_units = math.radians(t1 - t0) * L["r_cat_label"]
        lines = fit_lines(cat, L["cat_fs"], arc_units, ppu)
        curved_text(ax, L["r_cat_label"], mid, lines, L["cat_fs"], dark, ppu, weight="bold")


def truncate_path(xs, ys, frac):
    """The first `frac` of a polyline, by arc length."""
    if frac <= 0:
        return [], []
    pts = np.column_stack([xs, ys])
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    target = cum[-1] * min(1.0, frac)
    k = int(np.searchsorted(cum, target))
    if k >= len(pts):
        return list(xs), list(ys)
    t = (target - cum[k - 1]) / max(1e-9, seg[k - 1]) if k else 0.0
    p = pts[k - 1] + t * (pts[k] - pts[k - 1]) if k else pts[0]
    out = np.vstack([pts[:k], p])
    return list(out[:, 0]), list(out[:, 1])


def draw_chapter(ax, i, chapter, covered, slots, L, ppu, y_label) -> dict:
    r = L["r_ch_out"] - i * L["r_ch_step"]
    color = CHAPTER_COLORS[i % len(CHAPTER_COLORS)]
    t0, t1 = L["gap"], 360.0 - L["gap"]

    (track,) = ax.plot(*arc_points(r, t0, t1), color=color, lw=TRACK_LW,
                       alpha=TRACK_ALPHA, solid_capstyle="round", zorder=2)

    # a dot takes the colour of the dimension it sits under, not the chapter's
    pts, cols, fracs = [], [], []
    for sl, c in zip(slots, covered):
        if c:
            pts.append(polar(r, sl["theta"]))
            cols.append(sl["colour"])
            fracs.append((sl["theta"] - t0) / (t1 - t0))
    dots = ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=DOT_SIZE,
                      color=cols, linewidths=0, zorder=6)

    # leave the arc along its tangent, break once, then run straight to the
    # label: the tangent at the exit points along decreasing angle
    # Run along the tangent until it reaches this chapter's label row, break
    # once, then go level to the label. The tangent length therefore differs
    # per chapter, which is what keeps both segments straight.
    ex, ey = polar(r, t0)
    a = math.radians(t0)
    t = (ey - y_label) / math.cos(a)
    tx = [ex, ex + t * math.sin(a), L["x_tail"]]
    ty = [ey, y_label, y_label]
    (tail,) = ax.plot(tx, ty, color=color, lw=TRACK_LW, alpha=TRACK_ALPHA,
                      solid_capstyle="round", solid_joinstyle="round", zorder=4)

    m = re.match(r"\s*(\d+)\s*[.)]?\s*(.*)", chapter)
    number, title = (m.group(1), m.group(2)) if m else ("", chapter)

    # a true square, not a text bbox that follows the glyph's width
    fs_num = 13.5
    side = 1.62 * fs_num / ppu
    x0 = L["x_tail"] + 0.055
    numbox = ax.add_patch(Rectangle((x0, y_label - side / 2), side, side,
                                    facecolor=color, edgecolor="none", zorder=6))
    num = ax.text(x0 + side / 2, y_label, number, ha="center", va="center",
                  fontsize=fs_num, color="white", fontweight="bold", zorder=7)
    label = ax.text(x0 + side + 0.06, y_label, title, ha="left", va="center",
                    fontsize=14.5, color=color, fontweight="bold", zorder=6)
    return {"track": track, "dots": dots, "tail": tail, "label": label,
            "num": num, "numbox": numbox, "r": r, "t0": t0, "t1": t1,
            "tx": tx, "ty": ty, "pts": pts, "fracs": fracs}


def make_axes(L):
    x0, x1 = L["xlim"]
    y0, y1 = L["ylim"]
    w = 13.0
    fig, ax = plt.subplots(figsize=(w, w * (y1 - y0) / (x1 - x0)))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    ppu = w * 72.0 / (x1 - x0)  # points per data unit
    return fig, ax, ppu


def build(slots, coverage, L, gid: bool = False):
    fig, ax, ppu = make_axes(L)
    draw_ring(ax, slots, L, ppu)
    # evenly spaced label rows, centred on where the tails naturally leave
    n = len(CHAPTERS)
    row = L.get("label_gap_pt", 27.0) / ppu
    ends = [polar(L["r_ch_out"] - i * L["r_ch_step"], L["gap"])[1] for i in range(n)]
    top = ends[0] - L.get("label_drop", 0.10)
    ys = [top - i * row for i in range(n)]

    items = []
    for i, chapter in enumerate(CHAPTERS):
        it = draw_chapter(ax, i, chapter, coverage[chapter], slots, L, ppu, ys[i])
        if gid:
            for part in ("track", "dots", "tail", "label", "num", "numbox"):
                it[part].set_gid(f"sc-ch{i}-{part}")
        items.append(it)
    return fig, ax, items


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------


def animated_figure(slots, coverage, L, hold=18, per_chapter=46, fade=14):
    fig, _ax, items = build(slots, coverage, L)
    for it in items:
        it["all_offsets"] = np.array(it["pts"]) if it["pts"] else np.empty((0, 2))
    total = hold + len(items) * per_chapter + fade

    def update(frame):
        changed = []
        for i, it in enumerate(items):
            t = float(np.clip((frame - (hold + i * per_chapter)) / per_chapter, 0, 1))
            p = 1 - (1 - t) ** 3
            tp = float(np.clip(p / 0.55, 0, 1))
            dp = float(np.clip((p - 0.30) / 0.55, 0, 1))
            lp = float(np.clip((p - 0.70) / 0.30, 0, 1))
            if tp <= 0:
                it["track"].set_data([], [])
            else:
                it["track"].set_data(*arc_points(it["r"], it["t0"],
                                                 it["t0"] + (it["t1"] - it["t0"]) * tp))
            it["track"].set_alpha(TRACK_ALPHA * min(1.0, tp * 2))
            k = int(round(dp * len(it["all_offsets"])))
            it["dots"].set_offsets(it["all_offsets"][:k] if k else np.empty((0, 2)))
            it["tail"].set_data(*truncate_path(it["tx"], it["ty"], lp))
            it["label"].set_alpha(lp)
            it["num"].set_alpha(lp)
            it["numbox"].set_alpha(lp)
            changed += [it["track"], it["dots"], it["tail"],
                        it["label"], it["num"], it["numbox"]]
        return changed

    return fig, FuncAnimation(fig, update, frames=total, interval=1000 / 30, blit=False)


SVG_KEYFRAMES = ("\n@keyframes sc-draw { to { stroke-dashoffset: 0; } }"
                 "\n@keyframes sc-fade { to { opacity: 1; } }\n")


def animated_svg(slots, coverage, L, path: Path, per_chapter=0.75, lead=0.25) -> None:
    fig, _ax, items = build(slots, coverage, L, gid=True)
    fig.savefig(path, format="svg", facecolor="white",
                bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    svg = path.read_text(encoding="utf-8")

    # matplotlib writes an XML declaration and a DOCTYPE. Neither is legal
    # inside an HTML document, and a browser renders them as visible text when
    # the file is inlined, so keep the markup from <svg onwards.
    svg = svg[svg.index("<svg"):]

    # Give every dot its own delay, set from how far round the arc it sits, so
    # the dots land one by one as the track sweeps past them rather than the
    # whole set fading in together.
    for i, it in enumerate(items):
        a = svg.find(f'<g id="sc-ch{i}-dots">')
        if a < 0:
            continue
        b = svg.find('<g id="sc-ch', a + 1)
        b = len(svg) if b < 0 else b
        block, k, t0 = svg[a:b], 0, lead + i * per_chapter

        def stamp(m, _t0=t0, _it=it):
            nonlocal k
            d = _t0 + 0.08 + 0.85 * (_it["fracs"][k] if k < len(_it["fracs"]) else 1.0)
            k += 1
            return (m.group(1) + m.group(2)
                    + f";opacity:0;animation:sc-fade .3s ease-out {d:.2f}s forwards"
                    + m.group(3))

        svg = svg[:a] + re.sub(r'(<use[^>]*style=")([^"]*)("\s*/>)', stamp, block) + svg[b:]

    for i in range(len(CHAPTERS)):
        for part in ("track", "tail"):
            svg = re.sub(rf'(<g id="sc-ch{i}-{part}">\s*<path )',
                         lambda m: m.group(1) + 'pathLength="1" ', svg, count=1)
    rules = []
    for i in range(len(CHAPTERS)):
        t = lead + i * per_chapter
        rules.append(
            f"#sc-ch{i}-track path {{ stroke-dasharray: 1; stroke-dashoffset: 1;"
            f" animation: sc-draw .85s cubic-bezier(.25,.8,.35,1) {t:.2f}s forwards; }}\n"
            f"#sc-ch{i}-tail path {{ stroke-dasharray: 1; stroke-dashoffset: 1;"
            f" animation: sc-draw .5s ease-out {t + 0.46:.2f}s forwards; }}\n"
            f"#sc-ch{i}-label, #sc-ch{i}-num, #sc-ch{i}-numbox {{ opacity: 0;"
            f" animation: sc-fade .45s ease-out {t + 0.62:.2f}s forwards; }}")
    style = ("<style>" + SVG_KEYFRAMES + "\n".join(rules)
             # .sc-wait holds everything at its start state; the dots are <use>
        # children, so they have to be named too or they animate regardless.
        # !important is needed: each dot carries its animation in an inline
        # style attribute, and the shorthand there resets play-state to
        # running at inline specificity, which would outrank this rule.
        + "\n.sc-wait [id^='sc-ch'], .sc-wait [id^='sc-ch'] path,"
          " .sc-wait [id^='sc-ch'] use { animation-play-state: paused !important; }"
        # .sc-reset clears the animations outright, so the page can restart
        # them by toggling it across a reflow.
        + "\n.sc-reset [id^='sc-ch'], .sc-reset [id^='sc-ch'] path,"
          " .sc-reset [id^='sc-ch'] use { animation: none !important; }"
             + "\n@media (prefers-reduced-motion: reduce) {"
               "\n  [id^='sc-ch'], [id^='sc-ch'] path, [id^='sc-ch'] use { animation: none !important;"
               " opacity: 1 !important; stroke-dashoffset: 0 !important; }\n}\n</style>")
    svg = re.sub(r"(<svg[^>]*>)", lambda m: m.group(1) + "\n" + style, svg, count=1)

    def _resize(m):
        tag = re.sub(r'\s(width|height)="[^"]*"', "", m.group(1))
        return tag[:-1] + ' style="width:100%;height:auto">'

    svg = re.sub(r"(<svg[^>]*>)", _resize, svg, count=1)
    path.write_text(svg, encoding="utf-8")


# ---------------------------------------------------------------------------


def render(design, csv_path, out: Path, animate, fmt, dpi, fps, anim_dpi) -> None:
    L = LAYOUTS[design]
    slots = build_slots(L["gap"])
    coverage = parse_coverage(slots, csv_path)
    if animate:
        if fmt == "svg":
            p = out.with_suffix(".svg")
            animated_svg(slots, coverage, L, p)
            print(f"wrote {p}  ({p.stat().st_size / 1e3:.0f} KB, vector)")
            return
        fig, anim = animated_figure(slots, coverage, L)
        p = out.with_suffix("." + fmt)
        if fmt == "gif":
            anim.save(p, writer=PillowWriter(fps=fps), dpi=anim_dpi)
        else:
            anim.save(p, fps=fps, dpi=anim_dpi,
                      extra_args=["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                                  "-pix_fmt", "yuv420p", "-crf", "20"])
        print(f"wrote {p}  ({p.stat().st_size / 1e6:.1f} MB)")
        plt.close("all")
        return
    fig, _ax, _items = build(slots, coverage, L)
    for ext in ("png", "svg", "pdf"):
        p = out.with_suffix("." + ext)
        fig.savefig(p, dpi=dpi, facecolor="white",
                    bbox_inches="tight", pad_inches=0.04)
        print(f"wrote {p}")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", default="f", choices=sorted(LAYOUTS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--animate", action="store_true")
    ap.add_argument("--format", default="svg", choices=["svg", "mp4", "gif"])
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--columns", action="store_true")
    ap.add_argument("--exclude", type=int, nargs="+", default=[], metavar="N",
                    help="leave out the chapters with these leading numbers")
    ap.add_argument("--out", type=Path, default=Path("structural_coverage"))
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--anim-dpi", type=int, default=110)
    args = ap.parse_args()

    if args.columns:
        for i, s in enumerate(build_slots(LAYOUTS[args.design]["gap"]), 1):
            print(f"  {i:>2}. {s['category']:<26} {'-' if s['is_own_label'] else s['label']}")
        return

    if args.exclude:
        drop = {str(n) for n in args.exclude}
        CHAPTERS[:] = [c for c in CHAPTERS if c.split(".")[0].strip() not in drop]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    designs = sorted(LAYOUTS) if args.all else [args.design]
    for d in designs:
        out = args.out if len(designs) == 1 else args.out.with_name(f"{args.out.name}_{d}")
        print(f"--- design {d} ---")
        render(d, args.csv, out, args.animate, args.format, args.dpi, args.fps, args.anim_dpi)


if __name__ == "__main__":
    main()
