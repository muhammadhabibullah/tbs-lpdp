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

from common import BANK_DIR, iter_bank_questions

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


def rhombus(*, d1_u: float, d2_u: float, unit: str,
            target_w: float = 300, target_h: float = 170) -> Drawing:
    """Rhombus from its two diagonals, drawn dashed and labelled.

    The side length — and with it the perimeter — is what Pythagoras on the
    half-diagonals is for, so no side is ever dimensioned."""
    scale = min(target_w / d1_u, target_h / d2_u)
    w, h = d1_u * scale, d2_u * scale
    cx, cy = PAD + w / 2, PAD + h / 2
    L, R = (cx - w / 2, cy), (cx + w / 2, cy)
    T, B = (cx, cy - h / 2), (cx, cy + h / 2)

    parts = [
        _polygon([L, T, R, B], FILL),
        f'<line x1="{_f(L[0])}" y1="{_f(L[1])}" x2="{_f(R[0])}" y2="{_f(R[1])}" '
        f'stroke="{INK_SOFT}" stroke-width="1.5" stroke-dasharray="5 4"/>',
        f'<line x1="{_f(T[0])}" y1="{_f(T[1])}" x2="{_f(B[0])}" y2="{_f(B[1])}" '
        f'stroke="{INK_SOFT}" stroke-width="1.5" stroke-dasharray="5 4"/>',
        _text(cx + w / 4, cy + CAP + 6, f"{_num(d1_u)} {unit}"),
        _text(cx + 8, cy - h / 4 + CAP / 2, f"{_num(d2_u)} {unit}", anchor="start"),
    ]
    return Drawing(
        width=R[0] + PAD,
        height=B[1] + PAD,
        parts=parts,
        note=(f"belah ketupat dengan diagonal {_num(d1_u)} dan {_num(d2_u)} {unit}; "
              f"skala {_f(scale)} px per {unit}. Panjang sisi TIDAK dilabeli."),
    )


def cone(*, radius_u: float, height_u: float, unit: str,
         target_h: float = 190, target_w: float = 200) -> Drawing:
    """Cone with its base ellipse, dashed axis, and dimensioned height.

    The slant height is what Pythagoras is for, so it is never drawn as a
    labelled edge — only the radius and the vertical height are dimensioned."""
    scale = min(target_h / height_u, target_w / (2 * radius_u))
    rx = radius_u * scale
    ry = rx * ELLIPSE_RATIO
    body_h = height_u * scale

    cx = PAD + rx
    apex_y = PAD + 6.0
    base_cy = apex_y + body_h
    dim_x = cx + rx + 34
    # The radius label goes below the base with a leader, mirroring how the
    # cylinder labels its radius above the lid: anywhere inside the ellipse it
    # would land on the curve for some r/h ratio.
    leader_x = cx + rx / 2

    parts = [
        # body: apex, down the left slant, along the front (lower) arc, back up
        f'<path d="M {_f(cx)} {_f(apex_y)} L {_f(cx - rx)} {_f(base_cy)} '
        f'A {_f(rx)} {_f(ry)} 0 0 0 {_f(cx + rx)} {_f(base_cy)} Z" '
        f'fill="{FILL}" stroke="{STROKE}" stroke-width="2"/>',
        # hidden back half of the base rim
        f'<path d="M {_f(cx - rx)} {_f(base_cy)} A {_f(rx)} {_f(ry)} 0 0 1 '
        f'{_f(cx + rx)} {_f(base_cy)}" fill="none" stroke="{HIDDEN}" '
        f'stroke-width="1.5" stroke-dasharray="5 4"/>',
        # axis (the height) and the radius it stands on
        f'<line x1="{_f(cx)}" y1="{_f(apex_y)}" x2="{_f(cx)}" y2="{_f(base_cy)}" '
        f'stroke="{INK_SOFT}" stroke-width="1.5" stroke-dasharray="5 4"/>',
        f'<line class="tick" x1="{_f(cx)}" y1="{_f(base_cy)}" x2="{_f(cx + rx)}" '
        f'y2="{_f(base_cy)}" stroke="{INK}"/>',
        f'<circle cx="{_f(cx)}" cy="{_f(base_cy)}" r="2.5" fill="{INK}"/>',
        f'<line class="tick" x1="{_f(leader_x)}" y1="{_f(base_cy + 2)}" '
        f'x2="{_f(leader_x)}" y2="{_f(base_cy + ry + 8)}"/>',
        _text(leader_x, base_cy + ry + 22, f"{_num(radius_u)} {unit}"),
        *_dim_v(apex_y, base_cy, dim_x, f"{_num(height_u)} {unit}", left=False),
    ]
    return Drawing(
        width=dim_x + 34,
        height=base_cy + ry + 22 + PAD - 8,
        parts=parts,
        note=(f"kerucut jari-jari {_num(radius_u)} {unit}, tinggi {_num(height_u)} {unit}; "
              f"skala {_f(scale)} px per {unit}. Garis pelukis TIDAK dilabeli."),
    )


def parallelogram(*, base_u: float, side_u: float, height_u: float, unit: str,
                  target_w: float = 300, target_h: float = 170) -> Drawing:
    """Parallelogram from its base, slant side and height.

    All three are stated by the stem, so all three are labelled — the height as
    a dashed segment with the right angle at its foot. The area the item asks
    for appears nowhere in the drawing."""
    if side_u <= height_u:
        raise ValueError(f"side {side_u} cannot reach height {height_u}")
    offset_u = math.sqrt(side_u ** 2 - height_u ** 2)

    scale = min(target_w / (base_u + offset_u), target_h / height_u)
    left, top = 66.0, PAD
    base_y = top + height_u * scale
    bl = (left, base_y)
    br = (left + base_u * scale, base_y)
    tl = (left + offset_u * scale, top)
    tr = (tl[0] + base_u * scale, top)
    centre = ((bl[0] + tr[0]) / 2, (top + base_y) / 2)

    foot = (tl[0], base_y)
    sq = 12.0
    parts = [
        _polygon([bl, br, tr, tl], FILL),
        # the height, dashed from the top-left vertex straight down to the base
        f'<line x1="{_f(tl[0])}" y1="{_f(tl[1])}" x2="{_f(foot[0])}" y2="{_f(foot[1])}" '
        f'stroke="{INK_SOFT}" stroke-width="1.5" stroke-dasharray="5 4"/>',
        # its right angle, opening into the interior on the left of the foot
        f'<polyline points="{_f(foot[0] - sq)},{_f(base_y)} {_f(foot[0] - sq)},{_f(base_y - sq)} '
        f'{_f(foot[0])},{_f(base_y - sq)}" fill="none" stroke="{INK}" stroke-width="1.4"/>',
        _text(foot[0] + 7, (top + base_y) / 2 + CAP / 2,
              f"{_num(height_u)} {unit}", anchor="start"),
        *_dim_h(bl[0], br[0], base_y + GAP + TICK, f"{_num(base_u)} {unit}"),
        _label_beside(br, tr, centre, f"{_num(side_u)} {unit}"),
    ]
    return Drawing(
        width=tr[0] + 62,
        height=base_y + GAP + TICK + CAP + 6 + PAD - 8,
        parts=parts,
        note=(f"jajargenjang: alas {_num(base_u)} {unit}, sisi miring {_num(side_u)} "
              f"{unit}, tinggi {_num(height_u)} {unit}; skala {_f(scale)} px per {unit}. "
              f"Ketiganya diberikan di soal; luas yang ditanya TIDAK tercantum."),
    )


def annular_track(*, outer_diameter_u: float, track_width_u: float, unit: str,
                  target_d: float = 250) -> Drawing:
    """An annular track from its outer diameter and radial width.

    Both dimensions are stated in the stem. The inner radius and the annulus area
    are deliberately absent because deriving them is the work of the item.
    """
    outer_r_u = outer_diameter_u / 2
    inner_r_u = outer_r_u - track_width_u
    if inner_r_u <= 0:
        raise ValueError("track width must be smaller than the outer radius")

    scale = target_d / outer_diameter_u
    outer_r, inner_r = outer_r_u * scale, inner_r_u * scale
    cx, cy = PAD + outer_r, PAD + outer_r
    diameter_label = f"{str(_num(outer_diameter_u)).replace('.', ',')} {unit}"
    width_label = f"{str(_num(track_width_u)).replace('.', ',')} {unit}"

    parts = [
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(outer_r)}" '
        f'fill="{FILL}" stroke="{STROKE}" stroke-width="2"/>',
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(inner_r)}" '
        f'fill="white" stroke="{STROKE}" stroke-width="2"/>',
        # A radial dimension for the stated track width.
        *_dim_h(cx + inner_r, cx + outer_r, cy, width_label, below=False),
        # The full outside diameter sits below the shape so it cannot be mistaken
        # for the inner opening's diameter.
        *_dim_h(cx - outer_r, cx + outer_r, cy + outer_r + GAP + TICK,
                diameter_label),
    ]
    return Drawing(
        width=cx + outer_r + PAD,
        height=cy + outer_r + GAP + TICK + CAP + 6 + PAD - 8,
        parts=parts,
        note=(f"lintasan cincin: diameter luar {_num(outer_diameter_u)} {unit}, lebar "
              f"radial {_num(track_width_u)} {unit}; skala {_f(scale)} px per {unit}. "
              "Jari-jari dalam dan luas lintasan TIDAK dilabeli."),
    )


def right_triangle_parallel_cut(*, base_u: float, height_u: float,
                                end_segment_u: float, unit: str,
                                target_w: float = 290, target_h: float = 210) -> Drawing:
    """Right triangle with a segment through the base parallel to its height.

    The large legs and the short terminal base segment are given. The parallel
    segment's length follows by similarity and is never printed in the figure.
    """
    if not 0 < end_segment_u < base_u:
        raise ValueError("end segment must lie strictly inside the triangle base")

    scale = min(target_w / base_u, target_h / height_u)
    w, h = base_u * scale, height_u * scale
    left, top = 66.0, PAD
    base_y = top + h
    A, B, C = (left, base_y), (left + w, base_y), (left, top)
    D = (B[0] - end_segment_u * scale, base_y)
    cut_height_u = height_u * end_segment_u / base_u
    E = (D[0], base_y - cut_height_u * scale)

    marker_y1 = top + h * 0.44
    marker_y2 = (D[1] + E[1]) / 2
    parts = [
        _polygon([A, C, E, D], FILL),
        _polygon([D, E, B], FILL_TOP),
        # Right angle at A.
        f'<polyline points="{_f(A[0])},{_f(A[1] - 12)} '
        f'{_f(A[0] + 12)},{_f(A[1] - 12)} {_f(A[0] + 12)},{_f(A[1])}" '
        f'fill="none" stroke="{INK}" stroke-width="1.4"/>',
        # Matching parallel marks on AC and DE.
        f'<line x1="{_f(A[0] - 5)}" y1="{_f(marker_y1 + 5)}" '
        f'x2="{_f(A[0] + 5)}" y2="{_f(marker_y1 - 5)}" '
        f'stroke="{INK}" stroke-width="1.5"/>',
        f'<line x1="{_f(D[0] - 5)}" y1="{_f(marker_y2 + 5)}" '
        f'x2="{_f(D[0] + 5)}" y2="{_f(marker_y2 - 5)}" '
        f'stroke="{INK}" stroke-width="1.5"/>',
        *_dim_h(A[0], B[0], base_y + GAP + TICK,
                f"{_num(base_u)} {unit}"),
        *_dim_v(C[1], A[1], A[0] - GAP - TICK,
                f"{_num(height_u)} {unit}"),
        _text((D[0] + B[0]) / 2, base_y - 8,
              f"{_num(end_segment_u)} {unit}"),
        _text(A[0] - 13, A[1] + 2, "A", anchor="end"),
        _text(B[0] + 11, B[1] + 2, "B", anchor="start"),
        _text(C[0] - 10, C[1] + 2, "C", anchor="end"),
        _text(D[0], D[1] + 20, "D"),
        _text(E[0] + 10, E[1] - 6, "E", anchor="start"),
    ]
    return Drawing(
        width=B[0] + 46,
        height=base_y + GAP + TICK + CAP + 6 + PAD - 8,
        parts=parts,
        note=(f"segitiga siku-siku ABC: AB {_num(base_u)} {unit}, AC "
              f"{_num(height_u)} {unit}, DB {_num(end_segment_u)} {unit}, DE sejajar "
              f"AC; skala {_f(scale)} px per {unit}. DE dan luas ACED TIDAK dilabeli."),
    )


def triangular_prism(*, leg_front_u: float, leg_depth_u: float, height_u: float,
                     unit: str, target_w: float = 160, target_h: float = 190) -> Drawing:
    """Upright prism on a right-triangle base, in oblique projection.

    The front bottom edge and the receding edge are the triangle's legs; its
    hypotenuse is what Pythagoras is for, so that edge is never labelled."""
    scale = min(target_w / leg_front_u, target_h / height_u)
    w, h = leg_front_u * scale, height_u * scale
    depth = leg_depth_u * scale * DEPTH_FACTOR
    dx = depth * math.cos(math.radians(DEPTH_ANGLE))
    dy = -depth * math.sin(math.radians(DEPTH_ANGLE))

    left = 60.0
    top = PAD - dy          # room for the back vertex above the front face
    x0, y0 = left, top
    x1, y1 = left + w, top + h
    A, B = (x0, y1), (x1, y1)          # front bottom edge — the first leg
    At, Bt = (x0, y0), (x1, y0)
    Cb = (x0 + dx, y1 + dy)            # back vertex, along the second leg
    Ct = (x0 + dx, y0 + dy)
    top_centre = ((At[0] + Bt[0] + Ct[0]) / 3, (At[1] + Bt[1] + Ct[1]) / 3)

    # The base triangle's right angle, drawn skewed on the visible top face.
    n = math.hypot(dx, dy)
    u1, u2 = (1.0, 0.0), (dx / n, dy / n)
    sq = 11.0
    sq_pts = " ".join(
        f"{_f(At[0] + vx * sq)},{_f(At[1] + vy * sq)}"
        for vx, vy in (u1, (u1[0] + u2[0], u1[1] + u2[1]), u2))

    parts = [
        _polygon([B, Cb, Ct, Bt], FILL_SIDE),      # the hypotenuse face
        _polygon([At, Bt, Ct], FILL_TOP),          # top triangle
        f'<rect x="{_f(x0)}" y="{_f(y0)}" width="{_f(w)}" height="{_f(h)}" '
        f'fill="{FILL}" stroke="{STROKE}" stroke-width="2"/>',
        f'<line x1="{_f(A[0])}" y1="{_f(A[1])}" x2="{_f(Cb[0])}" y2="{_f(Cb[1])}" '
        f'stroke="{HIDDEN}" stroke-width="1.5" stroke-dasharray="5 4"/>',
        f'<polyline points="{sq_pts}" fill="none" stroke="{INK}" stroke-width="1.4"/>',
        *_dim_h(x0, x1, y1 + GAP + TICK, f"{_num(leg_front_u)} {unit}"),
        *_dim_v(y0, y1, x0 - GAP - TICK, f"{_num(height_u)} {unit}"),
        _label_beside(At, Ct, top_centre, f"{_num(leg_depth_u)} {unit}", offset=14),
    ]
    return Drawing(
        width=x1 + 40,
        height=y1 + GAP + TICK + CAP + 6 + PAD - 8,
        parts=parts,
        note=(f"prisma tegak, alas segitiga siku-siku {_num(leg_front_u)} x "
              f"{_num(leg_depth_u)} {unit}, tinggi {_num(height_u)} {unit}, proyeksi "
              f"miring {_f(DEPTH_ANGLE)}°; skala {_f(scale)} px per {unit}. "
              f"Sisi miring alas TIDAK dilabeli."),
    )


def kite(*, d_vertical_u: float, d_horizontal_u: float, unit: str,
         target_w: float = 250, target_h: float = 210) -> Drawing:
    """Kite from its perpendicular diagonals.

    Both diagonals are stated in the stem and therefore labelled. Their product
    and the resulting area are never printed in the picture.
    """
    scale = min(target_w / d_horizontal_u, target_h / d_vertical_u)
    w, h = d_horizontal_u * scale, d_vertical_u * scale
    cx, cy = PAD + w / 2, PAD + h * 0.43
    left, right = (cx - w / 2, cy), (cx + w / 2, cy)
    top, bottom = (cx, cy - h * 0.43), (cx, cy + h * 0.57)

    parts = [
        _polygon([top, right, bottom, left], FILL),
        f'<line x1="{_f(top[0])}" y1="{_f(top[1])}" x2="{_f(bottom[0])}" '
        f'y2="{_f(bottom[1])}" stroke="{INK_SOFT}" stroke-width="1.5" '
        f'stroke-dasharray="5 4"/>',
        f'<line x1="{_f(left[0])}" y1="{_f(left[1])}" x2="{_f(right[0])}" '
        f'y2="{_f(right[1])}" stroke="{INK_SOFT}" stroke-width="1.5" '
        f'stroke-dasharray="5 4"/>',
        _text(cx + 9, top[1] + h * 0.24, f"{_num(d_vertical_u)} {unit}",
              anchor="start"),
        _text(cx + w * 0.25, cy - 9, f"{_num(d_horizontal_u)} {unit}"),
    ]
    return Drawing(
        width=right[0] + PAD,
        height=bottom[1] + PAD,
        parts=parts,
        note=(f"layang-layang dengan diagonal {_num(d_vertical_u)} dan "
              f"{_num(d_horizontal_u)} {unit}; skala {_f(scale)} px per {unit}. "
              "Luas TIDAK dilabeli."),
    )


def square_pyramid(*, base_u: float, height_u: float, unit: str,
                   target_base: float = 170, target_h: float = 180) -> Drawing:
    """Right square pyramid in oblique projection.

    The base side and perpendicular height are given by the stem. The slant
    height is derived to answer the item, so it is intentionally absent.
    """
    scale = min(target_base / base_u, target_h / height_u)
    side = base_u * scale
    depth = side * DEPTH_FACTOR
    dx = depth * math.cos(math.radians(DEPTH_ANGLE))
    dy = depth * math.sin(math.radians(DEPTH_ANGLE))

    left = 58.0
    base_top = PAD + height_u * scale + 16
    back_left = (left + dx, base_top)
    back_right = (left + side + dx, base_top)
    front_left = (left, base_top + dy)
    front_right = (left + side, base_top + dy)
    centre = ((back_left[0] + front_right[0]) / 2,
              (back_left[1] + front_right[1]) / 2)
    apex = (centre[0], centre[1] - height_u * scale)
    inside = centre

    parts = [
        _polygon([apex, front_right, front_left], FILL),
        _polygon([apex, back_right, front_right], FILL_SIDE),
        f'<line x1="{_f(apex[0])}" y1="{_f(apex[1])}" x2="{_f(back_left[0])}" '
        f'y2="{_f(back_left[1])}" stroke="{HIDDEN}" stroke-width="1.5" '
        f'stroke-dasharray="5 4"/>',
        f'<line x1="{_f(back_left[0])}" y1="{_f(back_left[1])}" '
        f'x2="{_f(back_right[0])}" y2="{_f(back_right[1])}" stroke="{HIDDEN}" '
        f'stroke-width="1.5" stroke-dasharray="5 4"/>',
        f'<line x1="{_f(back_left[0])}" y1="{_f(back_left[1])}" '
        f'x2="{_f(front_left[0])}" y2="{_f(front_left[1])}" stroke="{HIDDEN}" '
        f'stroke-width="1.5" stroke-dasharray="5 4"/>',
        f'<line x1="{_f(apex[0])}" y1="{_f(apex[1])}" x2="{_f(centre[0])}" '
        f'y2="{_f(centre[1])}" stroke="{INK_SOFT}" stroke-width="1.5" '
        f'stroke-dasharray="5 4"/>',
        _text(apex[0] + 9, (apex[1] + centre[1]) / 2 + CAP / 2,
              f"{_num(height_u)} {unit}", anchor="start"),
        _label_beside(front_left, front_right, inside, f"{_num(base_u)} {unit}"),
    ]
    return Drawing(
        width=back_right[0] + 48,
        height=front_right[1] + 38,
        parts=parts,
        note=(f"limas segiempat tegak: sisi alas {_num(base_u)} {unit}, tinggi "
              f"{_num(height_u)} {unit}; skala {_f(scale)} px per {unit}. "
              "Tinggi sisi tegak TIDAK dilabeli."),
    )


def _num(v: float) -> str:
    """Format a quantity for a label: 20 not 20.0, 7.5 stays 7.5."""
    return str(int(v)) if float(v).is_integer() else _f(v)


# ----------------------------------------------- schematic (unscaled) figures --
# Everything above is a *measured* drawing: it scales with the numbers its stem
# states, and those numbers are given to the candidate anyway.
#
# A `kecukupan_data` figure cannot work that way. Its numbers arrive in the two
# statements, and the quantity the stem asks about is precisely what a candidate
# could read off a faithful drawing with a protractor or a ruler — measuring it
# would replace the reasoning the item exists to test. These figures are therefore
# schematic: one fixed generic configuration per family, showing which lines are
# parallel and which angles are right, labelled with names (P, Q, x°) and never
# with values. Every item of a family shares one file, which is safe exactly
# because the file contains none of the item's numbers, and each carries the note
# an exam prints under such a diagram: it is not drawn to scale.
#
# One consequence worth stating: a builder here takes no arguments. If a builder
# ever needs one, the figure has started depending on the item, and the item's
# answer has started leaking into the picture.

SCHEMATIC_NOTE = "Gambar tidak digambar menurut skala."

NOTE_GAP = 26   # bottom of the drawing -> baseline of that note


def _unit(v: tuple[float, float]) -> tuple[float, float]:
    n = math.hypot(*v) or 1.0
    return (v[0] / n, v[1] / n)


def _walk(p: tuple[float, float], d: tuple[float, float], t: float):
    return (p[0] + d[0] * t, p[1] + d[1] * t)


def _mid(p: tuple[float, float], q: tuple[float, float]):
    return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)


def _meet(p, d, q, e) -> tuple[float, float]:
    """Where the lines p + t·d and q + s·e cross."""
    det = d[0] * e[1] - d[1] * e[0]
    if abs(det) < 1e-9:
        raise ValueError("those lines are parallel and do not meet")
    s = ((q[0] - p[0]) * d[1] - (q[1] - p[1]) * d[0]) / det
    return _walk(q, e, s)


class _Frame:
    """Maps a builder's own coordinates (y up, arbitrary units) onto the canvas.

    Builders think in the geometry's terms and hand the frame every point they
    intend to draw; the frame works out the extent and the offsets. Decorations
    sized in pixels (angle arcs, right-angle squares, label offsets) stay in
    pixels — they are screen furniture and must not grow with the figure.
    """

    def __init__(self, points, *, scale: float, left: float, top: float):
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        self.scale, self.left, self.top = scale, left, top
        self._minx, self._maxy = min(xs), max(ys)
        self.width = (max(xs) - min(xs)) * scale
        self.height = (max(ys) - min(ys)) * scale

    def __call__(self, p) -> tuple[float, float]:
        return (self.left + (p[0] - self._minx) * self.scale,
                self.top + (self._maxy - p[1]) * self.scale)

    @property
    def bottom(self) -> float:
        return self.top + self.height


def _seg(fr: _Frame, p, q, *, width: float = 2.0, colour: str = STROKE,
         dash: str | None = None) -> str:
    (x1, y1), (x2, y2) = fr(p), fr(q)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
            f'stroke="{colour}" stroke-width="{_f(width)}" stroke-linecap="round"{extra}/>')


def _node(fr: _Frame, p, name: str, offset: tuple[float, float]) -> list[str]:
    """A named point: a dot plus its capital, offset in pixels (y up, as drawn)."""
    x, y = fr(p)
    dx, dy = offset
    return [
        f'<circle cx="{_f(x)}" cy="{_f(y)}" r="3.2" fill="{INK}"/>',
        _text(x + dx, y - dy + CAP / 2, name, cls="pt"),
    ]


def _line_tag(fr: _Frame, p, name: str, offset: tuple[float, float]) -> str:
    x, y = fr(p)
    return _text(x + offset[0], y - offset[1] + CAP / 2, name, cls="ln")


def _angle_mark(fr: _Frame, centre, d1, d2, label: str, *,
                radius: float = 27.0, gap: float = 15.0) -> list[str]:
    """Mark the sector swept counter-clockwise from direction `d1` to `d2`.

    Counter-clockwise as the reader sees it, which is why the SVG sweep flag is 0:
    the canvas y axis points down, so screen-anticlockwise is the negative
    direction in SVG's own frame.
    """
    cx, cy = fr(centre)
    a1, a2 = math.atan2(d1[1], d1[0]), math.atan2(d2[1], d2[0])
    span = (a2 - a1) % (2 * math.pi)

    def at(angle: float, r: float) -> tuple[float, float]:
        return (cx + r * math.cos(angle), cy - r * math.sin(angle))

    (sx, sy), (ex, ey) = at(a1, radius), at(a2, radius)
    lx, ly = at(a1 + span / 2, radius + gap)
    return [
        f'<path d="M {_f(sx)} {_f(sy)} A {_f(radius)} {_f(radius)} 0 '
        f'{1 if span > math.pi else 0} 0 {_f(ex)} {_f(ey)}" fill="none" '
        f'stroke="{INK}" stroke-width="1.3"/>',
        _text(lx, ly + CAP / 2, label),
    ]


def _right_angle(fr: _Frame, corner, d1, d2, *, size: float = 13.0) -> str:
    """The little square that says 90°, drawn inside the corner it belongs to."""
    cx, cy = fr(corner)
    u1, u2 = _unit(d1), _unit(d2)

    def at(v) -> str:
        return f"{_f(cx + v[0] * size)},{_f(cy - v[1] * size)}"

    pts = " ".join([at(u1), at((u1[0] + u2[0], u1[1] + u2[1])), at(u2)])
    return (f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="1.4"/>')


def _chevron(fr: _Frame, p, d, *, size: float = 10.0) -> str:
    """A single arrowhead — the mark that says "this side is parallel to that one"."""
    x, y = fr(p)
    u = _unit(d)
    ang = math.atan2(u[1], u[0])
    wings = []
    for turn in (math.radians(148), math.radians(-148)):
        wx = x + size * math.cos(ang + turn)
        wy = y - size * math.sin(ang + turn)
        wings.append(f"{_f(wx)},{_f(wy)}")
    return (f'<polyline points="{wings[0]} {_f(x)},{_f(y)} {wings[1]}" fill="none" '
            f'stroke="{STROKE}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')


def _schematic(fr: _Frame, parts: list[str], *, right: float, note: str,
               below: float = 0.0) -> Drawing:
    """Close off a schematic figure: add the not-to-scale caption and size the canvas.

    `below` is the room needed by labels that hang under the lowest drawn point —
    a figure whose base sits on the frame's bottom edge (A, B on a horizontal side)
    labels those points below it, and the caption has to clear them.
    """
    width = fr.left + fr.width + right
    baseline = fr.bottom + below + NOTE_GAP
    parts = parts + [_text(width / 2, baseline, SCHEMATIC_NOTE, cls="note")]
    return Drawing(
        width=width, height=baseline + 12, parts=parts, note=note,
        # Only these figures name points and lines, so the rules live here rather
        # than in `render`: adding them globally would rewrite every measured
        # figure in the bank with CSS it does not use, and `--check` would call
        # five untouched files stale.
        extra_style=[
            f".pt {{ font-size: 15px; font-weight: 700; fill: {INK}; }}",
            f".ln {{ font-size: 14px; font-style: italic; fill: {INK_SOFT}; }}",
        ],
    )


def parallel_lines_transversals() -> Drawing:
    """Two parallel lines cut by two transversals — the angle-chase configuration.

    Line k is horizontal. Lines l and m are parallel and meet k at P and Q; line n
    falls to the right and meets m at S, k at R and l at T. Reading the corresponding
    angles at P and Q and then the triangle QSR gives y = x + z − 180, which is the
    whole item, so x, y and z are drawn at whatever this fixed configuration happens
    to produce and never at the values a statement supplies.
    """
    P, Q, R = (80.0, 0.0), (230.0, 0.0), (560.0, 0.0)
    dk = (1.0, 0.0)
    dl = _unit((1.0, 1.4))      # l and m share it — that is what makes them parallel
    dn = _unit((-1.0, 1.15))    # n, pointing up and to the left from R
    S, T = _meet(Q, dl, R, dn), _meet(P, dl, R, dn)

    k_ends = ((10.0, 0.0), (650.0, 0.0))
    l_ends = (_walk(P, dl, -110), _walk(P, dl, 430))
    m_ends = (_walk(Q, dl, -110), _walk(Q, dl, 300))
    n_ends = (_walk(R, dn, -110), _walk(R, dn, 445))
    fr = _Frame([*k_ends, *l_ends, *m_ends, *n_ends], scale=0.62, left=34, top=32)

    parts = [
        _seg(fr, *k_ends),
        _seg(fr, *l_ends),
        _seg(fr, *m_ends),
        _seg(fr, *n_ends),
        _chevron(fr, _walk(P, dl, 125), dl),
        _chevron(fr, _walk(Q, dl, 125), dl),
        *_angle_mark(fr, P, dl, (-1.0, 0.0), "x°"),
        *_angle_mark(fr, R, dk, dn, "z°"),
        *_angle_mark(fr, S, dl, dn, "y°", radius=24, gap=14),
        *_node(fr, P, "P", (-15, -15)),
        *_node(fr, Q, "Q", (-15, -15)),
        *_node(fr, R, "R", (15, -15)),
        *_node(fr, S, "S", (17, -9)),
        *_node(fr, T, "T", (0, 19)),
        _line_tag(fr, k_ends[1], "k", (11, 12)),
        _line_tag(fr, l_ends[1], "l", (10, 7)),
        _line_tag(fr, m_ends[1], "m", (12, 5)),
        _line_tag(fr, n_ends[1], "n", (-13, 7)),
    ]
    return _schematic(fr, parts, right=36, note=(
        "skematis: garis l ∥ m dipotong garis k dan garis n; sudut x, y, z hanya "
        "diberi nama, TIDAK diberi nilai, dan gambar sengaja tidak berskala."))


def right_triangle_midsegment() -> Drawing:
    """Right triangle ABC (right angle at C) with D on AC and DE ∥ CB.

    D sits at the midpoint of AC because the stem says AC = 2·AD; that E then
    bisects AB and DE is half of CB is the inference under test, so no segment is
    dimensioned and the reader is told the drawing is not to scale.
    """
    A, B = (30.0, 0.0), (400.0, 0.0)
    # C anywhere on the circle with diameter AB gives a right angle at C
    # (Thales); 66° is simply an angle at which no side looks special.
    centre, radius = _mid(A, B), (B[0] - A[0]) / 2
    C = (centre[0] + radius * math.cos(math.radians(66.0)),
         radius * math.sin(math.radians(66.0)))
    D, E = _mid(A, C), _mid(A, B)
    along = _unit((B[0] - C[0], B[1] - C[1]))   # DE ∥ CB, so one direction serves both

    fr = _Frame([A, B, C], scale=0.86, left=40, top=34)
    parts = [
        _seg(fr, A, B),
        _seg(fr, B, C),
        _seg(fr, C, A),
        _seg(fr, D, E),
        _chevron(fr, _mid(D, E), along),
        _chevron(fr, _mid(C, B), along),
        _right_angle(fr, C, (A[0] - C[0], A[1] - C[1]), (B[0] - C[0], B[1] - C[1])),
        *_node(fr, A, "A", (-17, -13)),
        *_node(fr, B, "B", (17, -13)),
        *_node(fr, C, "C", (11, 16)),
        *_node(fr, D, "D", (-17, 9)),
        *_node(fr, E, "E", (0, -19)),
    ]
    return _schematic(fr, parts, right=40, below=24, note=(
        "skematis: segitiga siku-siku ABC dengan siku-siku di C, D titik tengah AC, "
        "dan DE ∥ CB; tidak ada ukuran yang dilabeli."))


def two_right_triangles() -> Drawing:
    """Right triangles ABD and ABC on a common base, with their diagonals crossing.

    AD ⊥ AB and BC ⊥ AB on the same side of AB; AC and BD cross at E, and the dashed
    EF is the distance from E to AB. That distance equals AD·BC/(AD + BC) and does
    not involve AB at all — the trap the item is built on — so AB is drawn as an
    ordinary side with nothing to draw the eye to it.
    """
    A, B = (30.0, 0.0), (390.0, 0.0)
    D, C = (30.0, 150.0), (390.0, 235.0)
    E = _meet(A, (C[0] - A[0], C[1] - A[1]), B, (D[0] - B[0], D[1] - B[1]))
    F = (E[0], 0.0)

    fr = _Frame([A, B, C, D], scale=0.86, left=40, top=32)
    parts = [
        _seg(fr, A, B),
        _seg(fr, A, D),
        _seg(fr, B, C),
        _seg(fr, A, C),
        _seg(fr, B, D),
        _seg(fr, E, F, width=1.6, colour=HIDDEN, dash="5 4"),
        _right_angle(fr, A, (1.0, 0.0), (0.0, 1.0)),
        _right_angle(fr, B, (-1.0, 0.0), (0.0, 1.0)),
        _right_angle(fr, F, (1.0, 0.0), (0.0, 1.0), size=10),
        *_node(fr, A, "A", (-17, -13)),
        *_node(fr, B, "B", (17, -13)),
        *_node(fr, C, "C", (15, 11)),
        *_node(fr, D, "D", (-15, 11)),
        *_node(fr, E, "E", (0, 18)),
        *_node(fr, F, "F", (2, -19)),
    ]
    return _schematic(fr, parts, right=40, below=24, note=(
        "skematis: segitiga siku-siku ABD dan ABC pada alas AB, AC dan BD "
        "berpotongan di E, EF ⊥ AB; tidak ada ukuran yang dilabeli."))


# Figures shared by every generated item of a family. Keyed by filename because
# that is what a question's `image` field holds, and one file serves many questions.
SHARED_FIGURES: dict[str, Callable[[], Drawing]] = {
    "kd-garis-sejajar.svg": parallel_lines_transversals,
    "kd-segitiga-garis-tengah.svg": right_triangle_midsegment,
    "kd-dua-segitiga-siku.svg": two_right_triangles,
}


def shared_image_field(filename: str) -> str:
    return f"images/{filename}"


def ensure_shared_figure(filename: str, package_id: int,
                         bank_dir: Path = BANK_DIR) -> str:
    """Put a shared figure in the package's images/ dir and return its `image` value.

    Idempotent, and idempotent byte for byte: the builder takes no arguments, so a
    second generator writing the same figure into the same package rewrites the
    identical file rather than racing the first one.
    """
    if filename not in SHARED_FIGURES:
        raise KeyError(f"{filename!r} is not a shared figure")
    path = bank_dir / str(package_id) / "images" / filename
    svg = render(SHARED_FIGURES[filename](), question_id=f"paket {package_id}")
    if not path.is_file() or path.read_text(encoding="utf-8") != svg:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding="utf-8")
    return shared_image_field(filename)


def _shared_usage(bank_dir: Path, only: str | None) -> dict[tuple[int, str], list[str]]:
    """(package, shared filename) -> the question ids pointing at it."""
    usage: dict[tuple[int, str], list[str]] = {}
    for _path, q, err in iter_bank_questions(bank_dir):
        if err or not q or not q.get("image"):
            continue
        if only and q.get("id") != only:
            continue
        name = q["image"].split("/")[-1]
        if name in SHARED_FIGURES:
            usage.setdefault((q["package"], name), []).append(q["id"])
    return usage


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
    Figure("3-kuantitatif-024", "belah-ketupat.svg", lambda: rhombus(
        d1_u=24, d2_u=10, unit="cm")),
    Figure("3-kuantitatif-025", "kerucut.svg", lambda: cone(
        radius_u=7, height_u=24, unit="cm")),
    Figure("4-kuantitatif-024", "jajargenjang.svg", lambda: parallelogram(
        base_u=25, side_u=17, height_u=15, unit="cm")),
    Figure("4-kuantitatif-025", "prisma-segitiga.svg", lambda: triangular_prism(
        leg_front_u=12, leg_depth_u=9, height_u=20, unit="cm")),
    Figure("5-kuantitatif-024", "layang-layang.svg", lambda: kite(
        d_vertical_u=18, d_horizontal_u=12, unit="cm")),
    Figure("5-kuantitatif-025", "limas-segiempat.svg", lambda: square_pyramid(
        base_u=10, height_u=12, unit="cm")),
    Figure("6-kuantitatif-024", "lintasan-cincin.svg", lambda: annular_track(
        outer_diameter_u=28, track_width_u=3.5, unit="m")),
    Figure("6-kuantitatif-025", "segitiga-potongan-sejajar.svg",
           lambda: right_triangle_parallel_cut(
               base_u=24, height_u=18, end_segment_u=8, unit="cm")),
    Figure("7-kuantitatif-024", "tabung.svg", lambda: cylinder(
        radius_u=14, height_u=15, unit="cm")),
    Figure("7-kuantitatif-025", "belah-ketupat.svg", lambda: rhombus(
        d1_u=16, d2_u=12, unit="cm")),
    Figure("8-kuantitatif-024", "balok.svg", lambda: cuboid(
        length_u=16, width_u=9, height_u=7, unit="cm")),
    Figure("8-kuantitatif-025", "prisma-segitiga.svg", lambda: triangular_prism(
        leg_front_u=8, leg_depth_u=15, height_u=10, unit="cm")),
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
        if not figures and not _shared_usage(args.bank_dir, args.only):
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

    # Shared schematic figures are not in FIGURES — a generator wrote them, and
    # which packages hold them depends on what was generated. Find them by asking
    # the bank which questions point at one, so `--check` still covers every SVG
    # in the bank rather than only the hand-registered ones.
    for (pkg, name), ids in sorted(_shared_usage(args.bank_dir, args.only).items()):
        svg = render(SHARED_FIGURES[name](), question_id=f"paket {pkg}")
        path = args.bank_dir / str(pkg) / "images" / name
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        label = f"{path.relative_to(args.bank_dir.parent.parent)} ({len(ids)} soal)"
        if args.check:
            if current != svg:
                stale.append(f"{pkg}/{name}")
            continue
        if current == svg:
            print(f"ok      {label}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding="utf-8")
        print(f"wrote   {label}")

    for p in problems:
        print(f"WARN    {p}", file=sys.stderr)
    if args.check and stale:
        print(f"stale figures: {', '.join(stale)} — run `python3 figures.py`",
              file=sys.stderr)
    if stale or problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
