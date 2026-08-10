#!/usr/bin/env python3
"""Deterministic generator for the bank's geometry figures (SVG).

A `geometri` item stated only in prose makes every candidate draw the same
picture from scratch before the actual reasoning can start. The official CBT
shows the figure, so the bank should too.

Nothing here is hand-placed. Every figure is derived from the same numbers the
stem states: the trapezoid's height decides where its top edge goes, the
sector's canvas follows from its central angle. So re-running this file
reproduces the bank's images byte for byte (`--check` proves it), and a
question whose numbers are corrected gets a figure that follows.

One rule is enforced by construction: **a figure may label only what the stem
gives.** Derived quantities are computed here because the drawing needs them,
but they are never emitted as text — the trapezoid's height and the sector's
arc length are precisely the work being asked for, and putting them in the
picture would answer the question. Note the asymmetry that makes this safe:
`_dim_*` helpers take a label from the caller, and no builder passes a value
it computed itself.

Adding a figure: write (or reuse) a builder that returns a `Drawing`, append a
`Figure` entry to FIGURES, then run `python3 figures.py --link`.

Usage:
    python3 figures.py                       # (re)generate every figure
    python3 figures.py --check               # exit 1 if any file on disk is stale
    python3 figures.py --only 1-kuantitatif-025
    python3 figures.py --link                # also point each question's `image` at its file
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from common import BANK_DIR

# ------------------------------------------------------------------ palette --
# Taken from web/src/styles.css so a figure never looks pasted in from elsewhere.
INK = "#3f4650"
INK_SOFT = "#6b7280"
HIDDEN = "#9aa1ac"
STROKE = "#1a5fb4"
FILL = "#d6e4fa"
FILL_TOP = "#eaf0fb"
FILL_SIDE = "#c9dcf7"
FILL_GRASS = "#eaf4ec"

FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif'

TICK = 6        # half-length of a dimension line's end tick
GAP = 10        # shape edge -> its dimension line
CAP = 10        # approximate cap height of the label font, for clearances
PAD = 24        # canvas padding

# Perspective constants. Fixed, not tuned per figure, so every solid in the bank
# is drawn the same way.
ELLIPSE_RATIO = 0.43    # ry/rx of a circle seen at an angle
DEPTH_FACTOR = 0.5      # oblique (cabinet) projection foreshortening
DEPTH_ANGLE = 45.0


# ------------------------------------------------------------------ drawing --

@dataclass
class Drawing:
    """A finished figure: canvas size, body elements, and a provenance note."""
    width: float
    height: float
    parts: list[str]
    note: str = ""
    extra_style: list[str] = field(default_factory=list)


def _f(v: float) -> str:
    """2-dp fixed formatting with trailing zeros stripped — stable output."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text(x: float, y: float, s: str, *, cls: str = "dim", anchor: str = "middle") -> str:
    return (f'<text class="{cls}" x="{_f(x)}" y="{_f(y)}" '
            f'text-anchor="{anchor}">{_esc(s)}</text>')


def _dim_h(x1: float, x2: float, y: float, label: str, *, below: bool = True) -> list[str]:
    """Horizontal dimension line with end ticks, labelled below (or above)."""
    return [
        f'<line class="tick" x1="{_f(x1)}" y1="{_f(y)}" x2="{_f(x2)}" y2="{_f(y)}"/>',
        f'<line class="tick" x1="{_f(x1)}" y1="{_f(y - TICK)}" x2="{_f(x1)}" y2="{_f(y + TICK)}"/>',
        f'<line class="tick" x1="{_f(x2)}" y1="{_f(y - TICK)}" x2="{_f(x2)}" y2="{_f(y + TICK)}"/>',
        _text((x1 + x2) / 2, y + TICK + CAP + 6 if below else y - TICK - 8, label),
    ]


def _dim_v(y1: float, y2: float, x: float, label: str, *, left: bool = True) -> list[str]:
    """Vertical dimension line; the label reads bottom-to-top, as is conventional."""
    tx = x - TICK - 4 if left else x + TICK + 18
    cy = (y1 + y2) / 2
    return [
        f'<line class="tick" x1="{_f(x)}" y1="{_f(y1)}" x2="{_f(x)}" y2="{_f(y2)}"/>',
        f'<line class="tick" x1="{_f(x - TICK)}" y1="{_f(y1)}" x2="{_f(x + TICK)}" y2="{_f(y1)}"/>',
        f'<line class="tick" x1="{_f(x - TICK)}" y1="{_f(y2)}" x2="{_f(x + TICK)}" y2="{_f(y2)}"/>',
        (f'<text class="dim" x="{_f(tx)}" y="{_f(cy)}" text-anchor="middle" '
         f'transform="rotate(-90 {_f(tx)} {_f(cy)})">{_esc(label)}</text>'),
    ]


def _label_beside(p1: tuple[float, float], p2: tuple[float, float],
                  inside: tuple[float, float], label: str, *, offset: float = 18) -> str:
    """Label a segment on the side facing away from `inside` (a point in the
    shape's interior). Used for slanted edges, where no fixed rule works."""
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length
    if nx * (mx - inside[0]) + ny * (my - inside[1]) < 0:   # points inward — flip
        nx, ny = -nx, -ny
    x, y = mx + nx * offset, my + ny * offset + CAP / 2
    anchor = "end" if nx < -0.3 else "start" if nx > 0.3 else "middle"
    return _text(x, y, label, anchor=anchor)


def _polygon(points: list[tuple[float, float]], fill: str) -> str:
    pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{STROKE}" stroke-width="2"/>'


def render(drawing: Drawing, *, question_id: str) -> str:
    """Wrap a Drawing in an SVG document. Styles are inlined: an <img> tag
    cannot reach a stylesheet, and these files are served from Storage."""
    style = [
        f"text {{ font-family: {FONT}; }}",
        f".dim {{ font-size: 14px; font-weight: 600; fill: {INK}; }}",
        f".note {{ font-size: 13px; fill: {INK_SOFT}; }}",
        f".tick {{ stroke: {INK_SOFT}; stroke-width: 1; }}",
        *drawing.extra_style,
    ]
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(drawing.width)}" '
            f'height="{_f(drawing.height)}" '
            f'viewBox="0 0 {_f(drawing.width)} {_f(drawing.height)}">')
    body = "\n".join(f"  {p}" for p in drawing.parts)
    note = "\n".join(f"       {line}" for line in drawing.note.strip().splitlines())
    return "\n".join([
        head,
        f"  <!-- {question_id} — generated by questions/generator/figures.py; do not edit by hand.",
        f"{note} -->",
        "  <style>",
        *(f"    {s}" for s in style),
        "  </style>",
        "",
        body,
        "</svg>",
        "",
    ])


# ------------------------------------------------------------------ builders --

def rect_with_inner_square(*, width_u: float, height_u: float, inner_u: float,
                           unit: str, outer_label: str, inner_label: str,
                           target_w: float = 320, target_h: float = 220) -> Drawing:
    """Rectangle with a smaller square inside it (garden + pond, plot + shed)."""
    # Whichever side binds sets the scale, so a long thin plot does not produce
    # a figure the layout has to shrink back down (see `cylinder` for the same).
    scale = min(target_w / width_u, target_h / height_u)
    w, h, s = width_u * scale, height_u * scale, inner_u * scale
    left, top = 62.0, 34.0
    right, bottom = left + w, top + h

    # Placement is a fixed rule, not an eyeballed offset: right of centre,
    # vertically centred. Where it sits cannot change the answer (area is
    # position-independent), but it must not touch an edge and imply otherwise.
    ix, iy = left + 0.68 * w - s / 2, top + 0.50 * h - s / 2
    if not (left < ix and ix + s < right and top < iy and iy + s < bottom):
        raise ValueError(f"inner square {inner_u} does not fit in {width_u}x{height_u}")

    parts = [
        f'<rect x="{_f(left)}" y="{_f(top)}" width="{_f(w)}" height="{_f(h)}" '
        f'fill="{FILL_GRASS}" stroke="{STROKE}" stroke-width="2"/>',
        f'<rect x="{_f(ix)}" y="{_f(iy)}" width="{_f(s)}" height="{_f(s)}" '
        f'fill="{FILL}" stroke="{STROKE}" stroke-width="2"/>',
        _text(left + 0.17 * w, top + 0.17 * h, outer_label, cls="note"),
        _text(ix + s / 2, iy + s / 2 + 5, inner_label, cls="note"),
        *_dim_h(left, right, bottom + GAP + TICK, f"{_num(width_u)} {unit}"),
        *_dim_v(top, bottom, left - GAP - TICK, f"{_num(height_u)} {unit}"),
    ]
    # The inner dimension goes wherever the figure actually has room.
    if iy - top >= GAP + 2 * TICK + CAP + 6:
        parts += _dim_h(ix, ix + s, iy - GAP, f"{_num(inner_u)} {unit}", below=False)
    else:
        parts += _dim_h(ix, ix + s, iy + s + GAP, f"{_num(inner_u)} {unit}")

    return Drawing(
        width=right + PAD,
        height=bottom + GAP + TICK + CAP + 6 + PAD - 8,
        parts=parts,
        note=(f"persegi panjang {_num(width_u)} x {_num(height_u)} {unit} dengan persegi "
              f"sisi {_num(inner_u)} {unit} di dalamnya; skala {_f(scale)} px per {unit}."),
    )


def cylinder(*, radius_u: float, height_u: float, unit: str,
             target_h: float = 160, target_w: float = 200) -> Drawing:
    """Closed cylinder seen from slightly above."""
    # A squat, wide cylinder must not scale by its height alone — that is how a
    # 12x9 drum ends up 500 px across. Whichever dimension binds wins.
    scale = min(target_h / height_u, target_w / (2 * radius_u))
    rx = radius_u * scale
    ry = rx * ELLIPSE_RATIO
    body_h = height_u * scale

    label_y = 16.0
    top_cy = max(label_y + 32, ry + 24)
    bottom_cy = top_cy + body_h
    cx = PAD + rx
    dim_x = cx + rx + 34

    # The radius label sits above the lid with a leader: anywhere inside the
    # ellipse it would land on the curve for some r/h ratio.
    leader_x = cx + rx / 2

    parts = [
        f'<path d="M {_f(cx - rx)} {_f(top_cy)} L {_f(cx - rx)} {_f(bottom_cy)} '
        f'A {_f(rx)} {_f(ry)} 0 0 0 {_f(cx + rx)} {_f(bottom_cy)} '
        f'L {_f(cx + rx)} {_f(top_cy)} Z" '
        f'fill="{FILL}" stroke="{STROKE}" stroke-width="2"/>',
        f'<ellipse cx="{_f(cx)}" cy="{_f(top_cy)}" rx="{_f(rx)}" ry="{_f(ry)}" '
        f'fill="{FILL_TOP}" stroke="{STROKE}" stroke-width="2"/>',
        f'<line class="tick" x1="{_f(cx)}" y1="{_f(top_cy)}" x2="{_f(cx + rx)}" '
        f'y2="{_f(top_cy)}" stroke="{INK}"/>',
        f'<circle cx="{_f(cx)}" cy="{_f(top_cy)}" r="2.5" fill="{INK}"/>',
        f'<line class="tick" x1="{_f(leader_x)}" y1="{_f(label_y + 6)}" '
        f'x2="{_f(leader_x)}" y2="{_f(top_cy - 2)}"/>',
        _text(leader_x, label_y, f"{_num(radius_u)} {unit}"),
        *_dim_v(top_cy, bottom_cy, dim_x, f"{_num(height_u)} {unit}", left=False),
    ]
    return Drawing(
        width=dim_x + 34,
        height=bottom_cy + ry + PAD,
        parts=parts,
        note=(f"tabung jari-jari {_num(radius_u)} {unit}, tinggi {_num(height_u)} {unit}; "
              f"skala {_f(scale)} px per {unit}."),
    )


def isosceles_trapezoid(*, long_u: float, short_u: float, leg_u: float, unit: str,
                        target_w: float = 288, target_h: float = 200) -> Drawing:
    """Isosceles trapezoid from its two parallel sides and its leg.

    The height is computed (the drawing cannot exist without it) and never
    labelled — deriving it via Pythagoras is the question."""
    offset_u = (long_u - short_u) / 2
    if leg_u <= abs(offset_u):
        raise ValueError(f"leg {leg_u} too short to span offset {offset_u}")
    height_u = math.sqrt(leg_u ** 2 - offset_u ** 2)

    scale = min(target_w / long_u, target_h / height_u)
    # Top margin has to clear the dimension line that goes *above* the shape,
    # plus that line's label: gap + tick + label gap + cap height + breathing room.
    left = 66.0
    base_y = (GAP + TICK + 8 + CAP + 4) + height_u * scale
    bl = (left, base_y)
    br = (left + long_u * scale, base_y)
    tl = (left + offset_u * scale, base_y - height_u * scale)
    tr = (left + (offset_u + short_u) * scale, base_y - height_u * scale)
    centre = ((bl[0] + br[0]) / 2, (base_y + tl[1]) / 2)

    parts = [_polygon([bl, br, tr, tl], FILL)]
    # Equal-leg ticks: the stem says "sama kaki", the figure should show it.
    for p1, p2 in ((bl, tl), (br, tr)):
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length * 5, dx / length * 5
        parts.append(f'<line x1="{_f(mx - nx)}" y1="{_f(my - ny)}" x2="{_f(mx + nx)}" '
                     f'y2="{_f(my + ny)}" stroke="{STROKE}" stroke-width="2"/>')

    parts += _dim_h(bl[0], br[0], base_y + GAP + TICK, f"{_num(long_u)} {unit}")
    parts += _dim_h(tl[0], tr[0], tl[1] - GAP, f"{_num(short_u)} {unit}", below=False)
    parts.append(_label_beside(bl, tl, centre, f"{_num(leg_u)} {unit}"))
    parts.append(_label_beside(br, tr, centre, f"{_num(leg_u)} {unit}"))

    return Drawing(
        width=br[0] + 66,
        height=base_y + GAP + TICK + CAP + 6 + PAD - 8,
        parts=parts,
        note=(f"trapesium sama kaki: sisi sejajar {_num(long_u)} dan {_num(short_u)} {unit}, "
              f"kaki {_num(leg_u)} {unit}; skala {_f(scale)} px per {unit}. "
              f"Tinggi dipakai untuk menggambar, TIDAK dilabeli."),
    )


def cuboid(*, length_u: float, width_u: float, height_u: float, unit: str,
           target_w: float = 195) -> Drawing:
    """Cuboid in oblique projection, hidden edges dashed."""
    scale = target_w / length_u
    w, h = length_u * scale, height_u * scale
    depth = width_u * scale * DEPTH_FACTOR
    dx = depth * math.cos(math.radians(DEPTH_ANGLE))
    dy = -depth * math.sin(math.radians(DEPTH_ANGLE))

    left = 60.0
    top = PAD - dy          # room for the back face above the front one
    x0, y0 = left, top
    x1, y1 = left + w, top + h
    back = lambda p: (p[0] + dx, p[1] + dy)   # noqa: E731
    fbl, fbr, ftr, ftl = (x0, y1), (x1, y1), (x1, y0), (x0, y0)
    centre = ((x0 + x1) / 2 + dx / 2, (y0 + y1) / 2 + dy / 2)

    parts = [
        _polygon([ftl, back(ftl), back(ftr), ftr], FILL_TOP),
        _polygon([ftr, back(ftr), back(fbr), fbr], FILL_SIDE),
        f'<rect x="{_f(x0)}" y="{_f(y0)}" width="{_f(w)}" height="{_f(h)}" '
        f'fill="{FILL}" stroke="{STROKE}" stroke-width="2"/>',
        f'<g stroke="{HIDDEN}" stroke-width="1.5" stroke-dasharray="5 4" fill="none">',
    ]
    hidden = back(fbl)
    for target in (back(ftl), back(fbr), fbl):
        parts.append(f'  <line x1="{_f(hidden[0])}" y1="{_f(hidden[1])}" '
                     f'x2="{_f(target[0])}" y2="{_f(target[1])}"/>')
    parts.append("</g>")

    parts += _dim_h(x0, x1, y1 + GAP + TICK, f"{_num(length_u)} {unit}")
    parts += _dim_v(y0, y1, x0 - GAP - TICK, f"{_num(height_u)} {unit}")
    parts.append(_label_beside(fbr, back(fbr), centre, f"{_num(width_u)} {unit}", offset=14))

    return Drawing(
        width=back(fbr)[0] + 56,
        height=y1 + GAP + TICK + CAP + 6 + PAD - 8,
        parts=parts,
        note=(f"balok {_num(length_u)} x {_num(width_u)} x {_num(height_u)} {unit}, "
              f"proyeksi miring {_f(DEPTH_ANGLE)}°; skala {_f(scale)} px per {unit}."),
    )


def circular_sector(*, angle_deg: float, radius_u: float, unit: str,
                    label: str | None = None, target_r: float = 150) -> Drawing:
    """Circular sector. The whole outline is stroked: for a fencing question the
    boundary *is* the subject. The arc length is never labelled."""
    if not 0 < angle_deg < 360:
        raise ValueError(f"central angle {angle_deg} out of range")
    r = target_r
    scale = target_r / radius_u

    def at(deg: float, rad: float = r) -> tuple[float, float]:
        return rad * math.cos(math.radians(deg)), -rad * math.sin(math.radians(deg))

    # Canvas from the sector's real extent, so any angle is framed correctly.
    pts = [(0.0, 0.0), at(0), at(angle_deg)]
    pts += [at(k) for k in (90, 180, 270) if 0 < k < angle_deg]
    minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
    miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
    pad_l, pad_t = 56.0, 30.0
    cx, cy = pad_l - minx, pad_t - miny

    p0 = (cx + at(0)[0], cy + at(0)[1])
    p1 = (cx + at(angle_deg)[0], cy + at(angle_deg)[1])
    large = 1 if angle_deg > 180 else 0
    inside = (cx + at(angle_deg / 2, r * 0.4)[0], cy + at(angle_deg / 2, r * 0.4)[1])

    arc_r = min(34.0, r * 0.25)
    a0 = (cx + at(0, arc_r)[0], cy + at(0, arc_r)[1])
    a1 = (cx + at(angle_deg, arc_r)[0], cy + at(angle_deg, arc_r)[1])
    ang_label = (cx + at(angle_deg / 2, arc_r + 22)[0],
                 cy + at(angle_deg / 2, arc_r + 22)[1] + CAP / 2)

    parts = [
        f'<path d="M {_f(cx)} {_f(cy)} L {_f(p0[0])} {_f(p0[1])} '
        f'A {_f(r)} {_f(r)} 0 {large} 0 {_f(p1[0])} {_f(p1[1])} Z" '
        f'fill="{FILL}" stroke="{STROKE}" stroke-width="2.5" stroke-linejoin="round"/>',
        f'<path d="M {_f(a0[0])} {_f(a0[1])} A {_f(arc_r)} {_f(arc_r)} 0 {large} 0 '
        f'{_f(a1[0])} {_f(a1[1])}" fill="none" stroke="{INK}" stroke-width="1.2"/>',
        _text(ang_label[0], ang_label[1], f"{_num(angle_deg)}°"),
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="3" fill="{INK}"/>',
        _label_beside((cx, cy), p0, inside, f"{_num(radius_u)} {unit}"),
        _label_beside((cx, cy), p1, inside, f"{_num(radius_u)} {unit}"),
    ]
    if label:
        centroid = (cx + at(angle_deg / 2, r * 0.62)[0], cy + at(angle_deg / 2, r * 0.62)[1])
        parts.append(_text(centroid[0], centroid[1], label, cls="note"))

    return Drawing(
        width=maxx - minx + pad_l + PAD,
        height=maxy - miny + pad_t + 40,
        parts=parts,
        note=(f"juring sudut pusat {_num(angle_deg)}°, jari-jari {_num(radius_u)} {unit}; "
              f"skala {_f(scale)} px per {unit}. Panjang busur TIDAK dilabeli."),
    )


def _num(v: float) -> str:
    """Format a quantity for a label: 20 not 20.0, 7.5 stays 7.5."""
    return str(int(v)) if float(v).is_integer() else _f(v)


# ------------------------------------------------------------------ registry --

@dataclass(frozen=True)
class Figure:
    question_id: str
    filename: str
    build: Callable[[], Drawing]

    @property
    def package(self) -> int:
        return int(self.question_id.split("-")[0])

    def image_field(self) -> str:
        return f"images/{self.filename}"

    def image_path(self, bank_dir: Path) -> Path:
        return bank_dir / str(self.package) / "images" / self.filename

    def question_path(self, bank_dir: Path) -> Path:
        pkg, subtest, number = self.question_id.split("-")
        return bank_dir / pkg / subtest / f"{number}.json"


FIGURES: list[Figure] = [
    Figure("1-kuantitatif-023", "taman-kolam.svg", lambda: rect_with_inner_square(
        width_u=20, height_u=12, inner_u=6, unit="m",
        outer_label="rumput", inner_label="kolam")),
    Figure("1-kuantitatif-024", "tabung.svg", lambda: cylinder(
        radius_u=7, height_u=20, unit="cm")),
    Figure("1-kuantitatif-025", "trapesium.svg", lambda: isosceles_trapezoid(
        long_u=32, short_u=20, leg_u=10, unit="cm")),
    Figure("2-kuantitatif-024", "balok.svg", lambda: cuboid(
        length_u=15, width_u=8, height_u=6, unit="cm")),
    Figure("2-kuantitatif-025", "juring.svg", lambda: circular_sector(
        angle_deg=60, radius_u=21, unit="m", label="taman")),
]


# ---------------------------------------------------------------------- main --

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    ap.add_argument("--only", help="regenerate a single question id")
    ap.add_argument("--check", action="store_true",
                    help="do not write; exit 1 if any file on disk differs")
    ap.add_argument("--link", action="store_true",
                    help="also set each question's `image` field to its figure")
    args = ap.parse_args()

    figures = FIGURES
    if args.only:
        figures = [f for f in FIGURES if f.question_id == args.only]
        if not figures:
            sys.exit(f"no figure registered for {args.only}")

    stale, problems = [], []
    for fig in figures:
        svg = render(fig.build(), question_id=fig.question_id)
        path = fig.image_path(args.bank_dir)

        # A figure nobody points at is dead weight; a question pointing at the
        # wrong file is worse. Check both, always.
        qpath = fig.question_path(args.bank_dir)
        if not qpath.is_file():
            problems.append(f"{fig.question_id}: no question file at {qpath}")
        else:
            q = json.loads(qpath.read_text(encoding="utf-8"))
            if q.get("image") != fig.image_field():
                if args.link and not args.check:
                    q["image"] = fig.image_field()
                    qpath.write_text(
                        json.dumps(q, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
                    print(f"linked  {qpath.relative_to(args.bank_dir.parent.parent)}")
                else:
                    problems.append(
                        f"{fig.question_id}: `image` is {q.get('image')!r}, "
                        f"expected {fig.image_field()!r} (run with --link)")

        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if args.check:
            if current != svg:
                stale.append(fig.question_id)
            continue
        if current == svg:
            print(f"ok      {path.relative_to(args.bank_dir.parent.parent)}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding="utf-8")
        print(f"wrote   {path.relative_to(args.bank_dir.parent.parent)}")

    for p in problems:
        print(f"WARN    {p}", file=sys.stderr)
    if args.check and stale:
        print(f"stale figures: {', '.join(stale)} — run `python3 figures.py`",
              file=sys.stderr)
    if stale or problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
