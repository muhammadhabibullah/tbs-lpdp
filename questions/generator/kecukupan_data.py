#!/usr/bin/env python3
"""Deterministic generator for `kecukupan_data` (data sufficiency) questions.

Data sufficiency asks whether the information suffices, not what the answer is:
a stem, two numbered statements, and the same five options every time. The key
is therefore a claim about three facts — does (1) alone determine the quantity,
does (2) alone, do they together — and getting it wrong by hand is easy, because
"I cannot see how to solve it" is not the same as "it cannot be solved".

So nothing here is asserted; it is decided:

* Each template states its facts as exact linear equations over `Fraction` and
  the asked-for quantity as one or more linear functionals. The quantity is
  determined by a set of equations iff every functional lies in the row space of
  their coefficient matrix — a rank comparison, computed exactly, with no
  floating point.
* The key falls out of the resulting triple `(s1, s2, s12)`. Templates declare
  which key they are *aiming* for, and a draw whose computed key disagrees is
  discarded — the arithmetic decides, the template only proposes.
* Every "not sufficient" claim is backed by a **witness pair**: two concrete
  assignments that both satisfy the statement yet disagree on the asked-for
  quantity. The witness is found in the null space and rescaled until it obeys
  the template's realism constraint (head counts stay positive integers, a
  triangle still closes), then printed in the explanation. An unsupported
  "tidak cukup" is not an argument.

Three of the templates are geometry items carrying a figure from `figures.py`.
Their figures are schematic and shared by every item of the family, because a
data-sufficiency diagram drawn to scale can be measured, and measuring is not
deciding — see the schematic section of `figures.py` for the reasoning.

Usage:
    python3 kecukupan_data.py --package 1 --count 2 [--seed 7] [--bank-dir PATH]
    python3 kecukupan_data.py --package 1 --count 2 --kind geometry
"""

from __future__ import annotations

import argparse
import random
from fractions import Fraction
from pathlib import Path

from common import (
    BANK_DIR,
    MINUS,
    fmt_number,
    make_question,
    next_number,
    renders_exactly,
    write_question,
)
from figures import ensure_shared_figure

SUBTEST = "kuantitatif"
QTYPE = "kecukupan_data"

_fmt = fmt_number

# The standard Indonesian TPA/TBS option set, in the standard order. It is fixed
# for every item of this type — candidates learn it once and reuse it — so it
# lives here as a constant rather than being re-worded per question.
OPTIONS = [
    ("A", "Pernyataan (1) SAJA cukup untuk menjawab pertanyaan, tetapi pernyataan "
          "(2) SAJA tidak cukup"),
    ("B", "Pernyataan (2) SAJA cukup untuk menjawab pertanyaan, tetapi pernyataan "
          "(1) SAJA tidak cukup"),
    ("C", "DUA pernyataan BERSAMA-SAMA cukup untuk menjawab pertanyaan, tetapi SATU "
          "pernyataan SAJA tidak cukup"),
    ("D", "Pernyataan (1) SAJA cukup untuk menjawab pertanyaan dan pernyataan (2) "
          "SAJA cukup untuk menjawab pertanyaan"),
    ("E", "Pernyataan (1) dan (2) BERSAMA-SAMA tidak cukup untuk menjawab pertanyaan"),
]

PROMPT = ("Putuskan apakah pernyataan (1) dan (2) yang diberikan cukup untuk "
          "menjawab pertanyaan tersebut.")


# -------------------------------------------------------- exact linear algebra

def _rref(rows: list[list[Fraction]], n_cols: int):
    """Reduced row echelon form. Returns (rows, pivot column per row)."""
    rows = [list(r) for r in rows]
    pivots: list[int] = []
    r = 0
    for col in range(n_cols):
        piv = next((i for i in range(r, len(rows)) if rows[i][col]), None)
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        inv = Fraction(1) / rows[r][col]
        rows[r] = [v * inv for v in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col]:
                f = rows[i][col]
                rows[i] = [a - f * b for a, b in zip(rows[i], rows[r])]
        pivots.append(col)
        r += 1
        if r == len(rows):
            break
    return rows[:r], pivots


def _nullspace(coeffs: list[list[Fraction]], n_vars: int) -> list[list[Fraction]]:
    """Basis of {v : A v = 0}."""
    rows, pivots = _rref(coeffs, n_vars)
    basis = []
    for free in (c for c in range(n_vars) if c not in pivots):
        v = [Fraction(0)] * n_vars
        v[free] = Fraction(1)
        for r, pc in enumerate(pivots):
            v[pc] = -rows[r][free]
        basis.append(v)
    return basis


def _dot(a, b) -> Fraction:
    return sum((x * y for x, y in zip(a, b)), Fraction(0))


def _free_direction(equations, targets, n_vars):
    """A direction the equations leave free that moves one of `targets`.

    Returns `None` exactly when the equations pin every functional in `targets`
    down — that is the sufficiency test, and the returned vector is the
    counterexample generator when they do not.

    `targets` is a list because the quantity a stem asks about is not always a
    linear functional of the unknowns. The distance from E to AB in
    `ds_two_right_triangles` is AD·BC/(AD + BC): not linear, but strictly
    increasing in each of AD and BC, so it is determined exactly when both of them
    are — two functionals to pin instead of one. A template using that escape hatch
    must supply a `value_of` that is strictly monotone in the targets over its
    feasible set, or this test stops being the sufficiency test.
    """
    coeffs = [eq[0] for eq in equations]
    for v in _nullspace(coeffs, n_vars):
        if any(_dot(t, v) for t in targets):
            return v
    return None


def _integral(vec: list[Fraction]) -> list[Fraction]:
    """Scale a rational vector to the smallest integer vector in its direction."""
    lcm = 1
    for x in vec:
        d = x.denominator
        lcm = lcm * d // _gcd(lcm, d)
    return [x * lcm for x in vec]


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


# ------------------------------------------------------------------ templates
# A template returns a dict describing one candidate item. `equations` are
# (coefficient-vector, right-hand-side) pairs; `targets` holds the coefficient
# vectors that have to be pinned down for the stem's question to have an answer.
# Optional keys: `value_of` when the asked-for quantity is not simply the first
# target, `feasible` for realism constraints the witness search must respect,
# `renders` for per-unknown formatting, `image` for a shared figure, and
# `insight` for the relation the correct explanation should state.

def _eq(coeffs: list[int], rhs: int):
    return ([Fraction(c) for c in coeffs], Fraction(rhs))


def _plain(v) -> str:
    return _fmt(v)


def _with_unit(unit: str):
    return lambda v: f"{_fmt(v)} {unit}"


def _rupiah(v) -> str:
    return f"Rp{_fmt(v)},00"


def ds_linear_system(rng: random.Random, want: str):
    """Three unknowns, two equations, asking for one of them (sample-book shape).

    Only C and E are reachable here, and deliberately so: with three unknowns a
    single equation can pin z down only by being a bare multiple of z, which
    makes an A/B/D item that answers itself on sight. Those keys come from the
    word templates instead, where one statement can carry a real fact.
    """
    x, y, z = (rng.randint(1, 9) for _ in range(3))
    names = ["x", "y", "z"]

    # (x, y) enter both equations in the same direction, so combining them
    # eliminates both unknowns at once and leaves z alone.
    p, q = rng.choice([(1, 2), (1, 3), (2, 1), (3, 2)])
    m = rng.choice([2, 3])
    a1 = rng.choice([-3, -2, -1, 1, 2, 3])
    a2 = rng.choice([c for c in (-3, -2, -1, 1, 2, 3) if c != m * a1])

    eq1 = _eq([p, q, a1], p * x + q * y + a1 * z)
    eq2 = _eq([m * p, m * q, a2], m * p * x + m * q * y + a2 * z)

    def text(eq):
        parts = []
        for coeff, name in zip(eq[0], names):
            if not coeff:
                continue
            mag = abs(coeff)
            body = name if mag == 1 else f"{_fmt(mag)}{name}"
            if not parts:
                parts.append(f"{MINUS}{body}" if coeff < 0 else body)
            else:
                parts.append(f"{MINUS if coeff < 0 else '+'} {body}")
        return f"{' '.join(parts)} = {_fmt(eq[1])}"

    if want == "C":
        s1, s2 = eq1, eq2
    else:
        # "E": a second *independent* equation whose (x, y) part points elsewhere.
        # Two equations in three unknowns then leave z free — and unlike a visible
        # multiple of the first equation, nothing gives that away on sight.
        p2, q2 = next(
            (c, d) for c, d in rng.sample([(1, 1), (1, 4), (2, 3), (3, 1), (4, 1)],
                                          5)
            if p * d - q * c
        )
        s1 = eq1
        s2 = _eq([p2, q2, a2], p2 * x + q2 * y + a2 * z)

    return {
        "context": "",
        "question": "Berapakah nilai z?",
        "prompt_names": names,
        "render": _plain,
        "render_target": _plain,
        "targets": [[Fraction(0), Fraction(0), Fraction(1)]],
        "target_name": "nilai z",
        "solution": [Fraction(x), Fraction(y), Fraction(z)],
        "base": [],
        "stmt1": (text(s1), [s1]),
        "stmt2": (text(s2), [s2]),
        "positive_integers": False,
        "witness_scales": (1, 2, 3),
        "difficulty": "hard",
    }


def ds_average_mix(rng: random.Random, want: str):
    """Two groups with known means; the stem asks for one group's size.

    Group sizes are redrawn until the combined mean is a round number: a stem
    that prints "rata-rata 3706/23 cm" tells the candidate the answer is an
    artefact of the generator rather than of the situation.
    """
    hi, lo = rng.choice([(165, 155), (170, 158), (80, 68), (78, 66)])
    unit = "cm" if hi > 100 else "kg"
    for _ in range(200):
        n1, n2 = rng.randint(6, 24), rng.randint(6, 24)
        combined = Fraction(hi * n1 + lo * n2, n1 + n2)
        if renders_exactly(combined) and combined.denominator == 1:
            break
    else:
        raise RuntimeError("no group sizes with a whole-number combined mean")

    total = n1 + n2
    quantity = "berat badan" if unit == "kg" else "tinggi badan"
    mean_text = (f"Rata-rata {quantity} seluruh peserta adalah "
                 f"{_fmt(combined)} {unit}.")

    size_eq = _eq([1, 1], total)
    # hi·m + lo·f = combined·(m + f)  ->  (hi − combined)m + (lo − combined)f = 0
    mean_eq = ([Fraction(hi) - combined, Fraction(lo) - combined], Fraction(0))

    if want == "C":
        s1 = (f"Jumlah seluruh peserta adalah {total} orang.", [size_eq])
        s2 = (mean_text, [mean_eq])
    elif want == "A":
        s1 = (f"Banyak peserta pria adalah {n1} orang.", [_eq([1, 0], n1)])
        s2 = (mean_text, [mean_eq])
    else:  # "E" — the mean only fixes the ratio, and so does statement (1)
        g = _gcd(n1, n2)
        s1 = (f"Perbandingan banyak peserta pria dan wanita adalah "
              f"{n1 // g} : {n2 // g}.",
              [([Fraction(n2), Fraction(-n1)], Fraction(0))])
        s2 = (mean_text, [mean_eq])

    return {
        "context": (f"Rata-rata {quantity} peserta pria dalam sebuah pelatihan adalah "
                    f"{hi} {unit}, sedangkan rata-rata {quantity} peserta wanita "
                    f"adalah {lo} {unit}."),
        "question": "Berapakah banyak peserta pria dalam pelatihan tersebut?",
        "prompt_names": ["banyak peserta pria", "banyak peserta wanita"],
        "render": _with_unit("orang"),
        "render_target": _with_unit("orang"),
        "targets": [[Fraction(1), Fraction(0)]],
        "target_name": "banyak peserta pria",
        "solution": [Fraction(n1), Fraction(n2)],
        "base": [],
        "stmt1": s1,
        "stmt2": s2,
        "positive_integers": True,
        "witness_scales": (1, 2, 3),
        "difficulty": "hard" if want == "E" else "medium",
    }


def ds_perimeter(rng: random.Random, want: str):
    """Asks for a perimeter — a linear functional of the sides, not a side.

    This is the shape that punishes the reflex "two unknowns need two equations":
    the sum of the sides is enough, the length alone is not.
    """
    length = rng.randint(8, 25)
    width = rng.randint(4, length - 2)
    sum_eq = _eq([1, 1], length + width)
    diff_eq = _eq([1, -1], length - width)
    length_eq = _eq([1, 0], length)

    if want == "B":
        s1 = (f"Selisih panjang dan lebar taman itu adalah {length - width} m.",
              [diff_eq])
        s2 = (f"Jumlah panjang dan lebar taman itu adalah {length + width} m.",
              [sum_eq])
    elif want == "C":
        s1 = (f"Selisih panjang dan lebar taman itu adalah {length - width} m.",
              [diff_eq])
        s2 = (f"Panjang taman itu adalah {length} m.", [length_eq])
    else:  # "D" — either statement pins the perimeter on its own
        s1 = (f"Jumlah panjang dan lebar taman itu adalah {length + width} m.",
              [sum_eq])
        s2 = (f"Panjang taman itu {length} m dan lebarnya {width} m.",
              [length_eq, _eq([0, 1], width)])

    return {
        "context": "Sebuah taman berbentuk persegi panjang.",
        "question": "Berapakah keliling taman tersebut?",
        "prompt_names": ["panjang", "lebar"],
        "render": _with_unit("m"),
        "render_target": _with_unit("m"),
        "targets": [[Fraction(2), Fraction(2)]],
        "target_name": "keliling taman",
        "solution": [Fraction(length), Fraction(width)],
        "base": [],
        "stmt1": s1,
        "stmt2": s2,
        "positive_integers": True,
        "witness_scales": (1, 2, 3),
        # when both statements plainly settle the perimeter there is nothing to
        # weigh up, so the item is easy however it is dressed
        "difficulty": "easy" if want == "D" else "medium",
    }


def ds_basket_price(rng: random.Random, want: str):
    """Two goods; the stem asks for the price of one of each.

    Two mirrored baskets (3a + 2b and 2a + 3b) never give either price on its
    own, yet their sum divides straight into a + b — the same trap as the
    perimeter, dressed as a shopping bill.
    """
    pen = rng.choice([2_000, 2_500, 3_000, 3_500, 4_000])
    book = rng.choice([6_000, 7_500, 8_000, 9_000, 12_000])
    a1, b1 = rng.choice([(3, 2), (4, 3), (5, 2)])
    mix1 = _eq([a1, b1], a1 * pen + b1 * book)
    mix2 = _eq([b1, a1], b1 * pen + a1 * book)
    pair = _eq([1, 1], pen + book)

    def basket(a, b, eq):
        return (f"Harga {a} pena dan {b} buku tulis adalah {_rupiah(eq[1])}.", [eq])

    if want == "C":
        s1, s2 = basket(a1, b1, mix1), basket(b1, a1, mix2)
    elif want == "A":
        s1 = (f"Harga satu pena dan satu buku tulis adalah {_rupiah(pair[1])}.", [pair])
        s2 = basket(a1, b1, mix1)
    else:  # "E" — the second basket is a scaled copy of the first
        k = rng.choice([2, 3])
        s1 = basket(a1, b1, mix1)
        s2 = basket(a1 * k, b1 * k, ([c * k for c in mix1[0]], mix1[1] * k))

    return {
        "context": "Sebuah toko menjual pena dan buku tulis dengan harga tetap.",
        "question": "Berapakah harga satu pena ditambah satu buku tulis?",
        "prompt_names": ["harga satu pena", "harga satu buku tulis"],
        "render": _rupiah,
        "render_target": _rupiah,
        "targets": [[Fraction(1), Fraction(1)]],
        "target_name": "harga satu pena ditambah satu buku tulis",
        "solution": [Fraction(pen), Fraction(book)],
        "base": [],
        "stmt1": s1,
        "stmt2": s2,
        "positive_integers": True,
        # counterexample prices must land on round rupiah, not on Rp2.998
        "witness_scales": (500, 250, 100, 1_000),
        "difficulty": "medium",
    }


def ds_fleet_total(rng: random.Random, want: str):
    """A difference plus a ratio determines a two-category fleet total.

    This opt-in architecture is kept outside ``WORD_TEMPLATE_GROUPS``.  It is
    available for a later package without changing the legacy template order or
    the output associated with any existing default seed.
    """
    scale = rng.choice([8, 9, 11, 12])
    electric, hybrid = 3 * scale, 2 * scale
    difference = electric - hybrid

    return {
        "context": "Sebuah depo mengoperasikan bus listrik dan bus hibrida.",
        "question": "Berapakah jumlah seluruh bus yang dioperasikan depo tersebut?",
        "prompt_names": ["banyak bus listrik", "banyak bus hibrida"],
        "render": _with_unit("bus"),
        "render_target": _with_unit("bus"),
        "targets": [[Fraction(1), Fraction(1)]],
        "target_name": "jumlah seluruh bus",
        "solution": [Fraction(electric), Fraction(hybrid)],
        "base": [],
        "stmt1": (
            f"Bus listrik berjumlah {difference} lebih banyak daripada bus hibrida.",
            [_eq([1, -1], difference)],
        ),
        "stmt2": (
            "Perbandingan banyak bus listrik dan bus hibrida adalah 3 : 2.",
            [_eq([2, -3], 0)],
        ),
        "positive_integers": True,
        "witness_scales": (1, 2, 3),
        "difficulty": "medium",
    }


EXPLICIT_TEMPLATES = {
    "fleet_total": (ds_fleet_total, ("C",)),
}


# ------------------------------------------------------- geometry with a figure
# Real TBS sets put several data-sufficiency items on a diagram, and they are the
# ones candidates misjudge most: a figure invites you to *look*, and looking is
# not deciding. Each template below pairs with a fixed schematic figure from
# `figures.py` — schematic because a faithful drawing of an angle chase can be
# measured, which would answer the item without any reasoning at all.
#
# The figure is what makes the stems short enough to read: naming the points P, Q,
# R, S, T once in a picture saves a paragraph of prose in every statement.

DEGREES = _plain
CM = _with_unit("cm")


def ds_parallel_angles(rng: random.Random, want: str):
    """Two parallel lines cut by two transversals; the stem asks for an angle.

    Reading the corresponding angles at P and Q and then the triangle QSR gives
    y = x + z − 180. So y needs the *sum* of x and z and nothing more, and the
    template's whole spread of keys comes from how obliquely a statement delivers
    that sum: x alone never does, ∠PTR delivers it in one step, and ∠SQR is x in
    disguise — the same fact wearing a different label.
    """
    # Draw the interior angles instead of the marked ones, so a valid triangle is
    # guaranteed by construction rather than checked after the fact.
    at_p = rng.choice(range(25, 85, 5))
    # y = 90 is excluded: ∠PTR would then be a right angle, and a right angle is the
    # one thing an exam figure always marks — a statement announcing one the picture
    # does not show reads as a mistake in the picture.
    at_r = rng.choice([a for a in range(25, 85, 5)
                       if 50 <= at_p + a <= 155 and at_p + a != 90])
    x, z = 180 - at_p, 180 - at_r
    y = x + z - 180

    x_stmt = (f"Nilai x adalah {_fmt(x)}.", [_eq([1, 0], x)])
    z_stmt = (f"Nilai z adalah {_fmt(z)}.", [_eq([0, 1], z)])
    sum_stmt = (f"Jumlah nilai x dan z adalah {_fmt(x + z)}.", [_eq([1, 1], x + z)])
    # ∠PTR is the apex of triangle PTR, and l ∥ m makes it correspond to y
    apex_stmt = (f"Besar ∠PTR adalah {_fmt(y)}°.", [_eq([1, 1], x + z)])
    # ∠SQR is the interior angle at Q, i.e. 180 − x: statement (1) again, relabelled
    echo_stmt = (f"Besar ∠SQR adalah {_fmt(180 - x)}°.", [_eq([1, 0], x)])

    s1, s2 = {
        "A": (sum_stmt, x_stmt),
        "B": (x_stmt, apex_stmt),
        "C": (x_stmt, z_stmt),
        "D": (sum_stmt, apex_stmt),
        "E": (x_stmt, echo_stmt),
    }[want]

    def feasible(vals):
        a, b = vals
        return (all(v.denominator == 1 and v % 5 == 0 for v in vals)
                and 100 <= a <= 155 and 100 <= b <= 155 and 205 <= a + b <= 310)

    return {
        "context": ("Pada gambar di atas, garis l sejajar dengan garis m, sedangkan "
                    "garis k dan garis n memotong keduanya."),
        "question": "Berapakah nilai y?",
        "prompt_names": ["x", "z"],
        "render": DEGREES,
        "render_target": DEGREES,
        "targets": [[Fraction(1), Fraction(1)]],
        "value_of": lambda vals: vals[0] + vals[1] - 180,
        "target_name": "nilai y",
        "solution": [Fraction(x), Fraction(z)],
        "base": [],
        "stmt1": s1,
        "stmt2": s2,
        "positive_integers": False,
        "feasible": feasible,
        "witness_scales": (5, 10, 15, 20),
        "image": "kd-garis-sejajar.svg",
        "insight": ("Karena l ∥ m, sudut di P dan sudut di Q sehadap, sehingga pada "
                    "segitiga QSR berlaku (180 − x) + (180 − z) + y = 180, yaitu "
                    "y = x + z − 180; yang dibutuhkan hanyalah jumlah x dan z."),
        "difficulty": {"D": "easy", "E": "hard", "C": "medium"}.get(want, "medium"),
    }


def ds_midsegment(rng: random.Random, want: str):
    """Right triangle with a midsegment; the stem asks for the midsegment.

    D is the midpoint of AC and DE ∥ CB, so DE = ½·CB and AE = ½·AB. That splits
    the four lengths into two camps: DE and CB determine each other, AB and AE
    determine each other, and neither camp says anything about the other. Most of
    the work an item like this does is getting the candidate to notice which camp a
    statement landed in — AB is the longest side in the picture and the most
    tempting number on the page, and it is worth nothing here.
    """
    de = rng.choice([3, 4, 5, 6, 7, 8])
    ab = 2 * de + rng.choice([4, 6, 8, 10, 12, 14])   # even, and CB < AB as it must be

    bc_stmt = (f"Panjang BC adalah {_fmt(2 * de)} cm.", [_eq([2, 0], 2 * de)])
    ab_stmt = (f"Panjang AB adalah {_fmt(ab)} cm.", [_eq([0, 1], ab)])
    ae_stmt = (f"Panjang AE adalah {_fmt(ab // 2)} cm.",
               [([Fraction(0), Fraction(1, 2)], Fraction(ab, 2))])
    de_bc_stmt = (f"Jumlah panjang DE dan BC adalah {_fmt(3 * de)} cm.",
                  [_eq([3, 0], 3 * de)])
    de_ae_stmt = (f"Jumlah panjang DE dan AE adalah {_fmt(de + ab // 2)} cm.",
                  [([Fraction(1), Fraction(1, 2)], Fraction(de + ab // 2))])

    s1, s2 = {
        "A": (de_bc_stmt, ab_stmt),
        "B": (ab_stmt, bc_stmt),
        "C": (de_ae_stmt, ab_stmt),
        "D": (bc_stmt, de_bc_stmt),
        "E": (ab_stmt, ae_stmt),
    }[want]

    def feasible(vals):
        d, c = vals
        # CB = 2·DE is a leg and AB the hypotenuse, so 2·DE < AB is not decoration
        return d > 0 and c > 2 * d and all(renders_exactly(v) for v in vals)

    return {
        "context": ("Pada gambar di atas, ABC adalah segitiga siku-siku dengan sudut "
                    "siku-siku di C. Titik D terletak pada AC sehingga AC = 2 × AD, "
                    "sedangkan DE sejajar CB dengan titik E pada AB."),
        "question": "Berapakah panjang DE?",
        "prompt_names": ["DE", "AB"],
        "render": CM,
        "render_target": CM,
        "targets": [[Fraction(1), Fraction(0)]],
        "target_name": "panjang DE",
        "solution": [Fraction(de), Fraction(ab)],
        "base": [],
        "stmt1": s1,
        "stmt2": s2,
        "positive_integers": False,
        "feasible": feasible,
        "witness_scales": (1, 2, 3, Fraction(1, 2)),
        "image": "kd-segitiga-garis-tengah.svg",
        "insight": ("Karena D titik tengah AC dan DE ∥ CB, DE adalah garis tengah "
                    "segitiga ABC, sehingga DE = ½ × CB dan AE = ½ × AB; panjang AB "
                    "sendiri tidak menentukan DE."),
        "difficulty": {"D": "easy", "C": "hard", "E": "hard"}.get(want, "medium"),
    }


def ds_two_right_triangles(rng: random.Random, want: str):
    """Two right triangles on a shared base, diagonals crossing; asks for a height.

    With AD ⊥ AB and BC ⊥ AB, the crossing point of AC and BD sits at a height of
    AD·BC/(AD + BC) above AB — a quantity that does not mention AB at all. So the
    base, which dominates the picture, is a decoy, and the item is decided by
    whether the statements pin both uprights.

    The height is not linear in AD and BC, so the sufficiency test is run on the two
    of them separately: it is strictly increasing in each, hence determined exactly
    when both are (see `_free_direction`).
    """
    pairs = [(p, q) for p in range(3, 21) for q in range(3, 21)
             if renders_exactly(Fraction(p * q, p + q))]
    if want in ("C", "D"):
        pairs = [(p, q) for p, q in pairs if q > p]
    if want == "E":
        pairs = [(p, q) for p, q in pairs if q % p == 0 and q > p]
    p, q = rng.choice(pairs)
    ab = rng.choice([12, 14, 15, 16, 18, 20, 24])

    both_stmt = (f"Panjang AD adalah {_fmt(p)} cm dan panjang BC adalah {_fmt(q)} cm.",
                 [_eq([1, 0, 0], p), _eq([0, 1, 0], q)])
    ab_stmt = (f"Panjang AB adalah {_fmt(ab)} cm.", [_eq([0, 0, 1], ab)])
    sum_stmt = (f"Jumlah panjang AD dan BC adalah {_fmt(p + q)} cm.",
                [_eq([1, 1, 0], p + q)])
    diff_stmt = (f"Selisih panjang BC dan AD adalah {_fmt(q - p)} cm.",
                 [_eq([-1, 1, 0], q - p)])
    sum_diff_stmt = (f"Jumlah panjang AD dan BC adalah {_fmt(p + q)} cm dan selisih "
                     f"panjang BC dan AD adalah {_fmt(q - p)} cm.",
                     [_eq([1, 1, 0], p + q), _eq([-1, 1, 0], q - p)])
    ratio_stmt = (f"Panjang BC adalah {_fmt(q // p)} kali panjang AD.",
                  [_eq([-(q // p), 1, 0], 0)])

    s1, s2 = {
        "A": (both_stmt, ab_stmt),
        "B": (ab_stmt, both_stmt),
        "C": (sum_stmt, diff_stmt),
        "D": (both_stmt, sum_diff_stmt),
        "E": (ab_stmt, ratio_stmt),
    }[want]

    def feasible(vals):
        ad, bc, base = vals
        if not (ad > 0 and bc > 0 and base > 0):
            return False
        return (all(renders_exactly(v) for v in vals)
                and renders_exactly(Fraction(ad * bc, ad + bc)))

    return {
        "context": ("Pada gambar di atas, ABD dan ABC adalah segitiga siku-siku dengan "
                    "AD tegak lurus AB dan BC tegak lurus AB. Titik C dan titik D "
                    "berada pada sisi yang sama terhadap AB, sedangkan AC dan BD "
                    "berpotongan di titik E."),
        "question": "Berapakah jarak titik E ke AB?",
        "prompt_names": ["AD", "BC", "AB"],
        "render": CM,
        "render_target": CM,
        "targets": [[Fraction(1), Fraction(0), Fraction(0)],
                    [Fraction(0), Fraction(1), Fraction(0)]],
        "value_of": lambda vals: Fraction(vals[0] * vals[1], vals[0] + vals[1]),
        "target_name": "jarak titik E ke AB",
        "solution": [Fraction(p), Fraction(q), Fraction(ab)],
        "base": [],
        "stmt1": s1,
        "stmt2": s2,
        "positive_integers": False,
        "feasible": feasible,
        "witness_scales": (1, 2, 3, 4, 5, 6, 8, 9, 10, 12),
        "image": "kd-dua-segitiga-siku.svg",
        "insight": ("Jarak titik E ke AB selalu sama dengan (AD × BC)/(AD + BC), yaitu "
                    "hanya ditentukan oleh AD dan BC; panjang AB tidak "
                    "memengaruhinya sama sekali."),
        "difficulty": {"D": "easy", "E": "hard", "C": "hard"}.get(want, "medium"),
    }


# Grouped by the reasoning they exercise, and paired with the keys each shape can
# realise, so a package can be given a spread of keys instead of five C's.
WORD_TEMPLATE_GROUPS = [
    [(ds_linear_system, ("C", "E"))],
    [(ds_average_mix, ("C", "A", "E"))],
    [(ds_perimeter, ("B", "C", "D"))],
    [(ds_basket_price, ("C", "A", "E"))],
]

GEOMETRY_TEMPLATE_GROUPS = [
    [(ds_parallel_angles, ("A", "B", "C", "D", "E"))],
    [(ds_midsegment, ("A", "B", "C", "D", "E"))],
    [(ds_two_right_triangles, ("A", "B", "C", "D", "E"))],
]

TEMPLATE_GROUPS = WORD_TEMPLATE_GROUPS + GEOMETRY_TEMPLATE_GROUPS

TEMPLATE_KINDS = {
    "any": TEMPLATE_GROUPS,
    "word": WORD_TEMPLATE_GROUPS,
    "geometry": GEOMETRY_TEMPLATE_GROUPS,
}


# ----------------------------------------------------------------- assembling

def _targets(spec) -> list:
    return spec["targets"]


def _value_of(spec, values) -> Fraction:
    """The quantity the stem asks about, at a given assignment.

    Defaults to the first target functional, which is the ordinary case: the stem
    asks for something linear in the unknowns. A template overrides it when the
    asked-for quantity is a monotone function of what the targets pin down.
    """
    fn = spec.get("value_of")
    return fn(values) if fn else _dot(spec["targets"][0], values)


def _realistic(spec, values) -> bool:
    """Whether an assignment is one the template would be willing to print.

    Head counts must be positive whole numbers, prices must land on round rupiah,
    angles must still close a triangle. A counterexample the reader would reject as
    impossible refutes nothing, so it is not allowed to reach the page.
    """
    if spec["positive_integers"] and not all(
        v > 0 and v.denominator == 1 for v in values
    ):
        return False
    extra = spec.get("feasible")
    return extra(values) if extra else True


def _sufficiency(spec, equations):
    """(is_sufficient, free_direction) for a set of equations."""
    v = _free_direction(equations, _targets(spec), len(spec["solution"]))
    return v is None, v


def _witness(spec, direction):
    """Two assignments satisfying the same statements but disagreeing on the target.

    The null-space direction is rescaled until both assignments are realistic for
    the template — head counts and prices must stay positive whole numbers, and
    prices must land on round rupiah, which is why the scale order is the
    template's to choose. A direction that never becomes realistic makes the item
    unusable, so the caller redraws instead of printing a witness nobody would
    accept.

    The final check is on the asked-for quantity rather than on the direction:
    where that quantity is non-linear a particular step along a free direction can
    land back on the same value, and a "counterexample" that agrees with the base
    case proves the opposite of what it is printed to prove.
    """
    base = spec["solution"]
    direction = _integral(direction)
    for scale in spec["witness_scales"]:
        for sign in (1, -1):
            other = [b + sign * scale * d for b, d in zip(base, direction)]
            if not _realistic(spec, other):
                continue
            if _value_of(spec, other) == _value_of(spec, base):
                continue
            return other
    return None


def _assignment_text(spec, values) -> str:
    renders = spec.get("renders") or [spec["render"]] * len(values)
    return ", ".join(
        f"{name} = {render(v)}"
        for name, render, v in zip(spec["prompt_names"], renders, values)
    )


def _cannot_because(spec, index: int, other_values) -> str:
    """'(1) is not enough' spelled out as two assignments that disagree."""
    render = spec["render_target"]
    a = render(_value_of(spec, spec["solution"]))
    b = render(_value_of(spec, other_values))
    return (
        f"pernyataan ({index}) saja tidak cukup, sebab keadaan "
        f"[{_assignment_text(spec, spec['solution'])}] dan "
        f"[{_assignment_text(spec, other_values)}] sama-sama memenuhinya, tetapi "
        f"memberikan {spec['target_name']} sebesar {a} dan {b}"
    )


def _cannot_together(spec, other_values) -> str:
    render = spec["render_target"]
    a = render(_value_of(spec, spec["solution"]))
    b = render(_value_of(spec, other_values))
    return (
        f"kedua pernyataan bersama-sama pun tidak cukup, sebab keadaan "
        f"[{_assignment_text(spec, spec['solution'])}] dan "
        f"[{_assignment_text(spec, other_values)}] memenuhi keduanya, tetapi "
        f"memberikan {spec['target_name']} sebesar {a} dan {b}"
    )


def _is_enough(spec, index: str) -> str:
    value = spec["render_target"](_value_of(spec, spec["solution"]))
    return (f"pernyataan {index} menentukan {spec['target_name']} secara tunggal, "
            f"yaitu {value}")


def _sentence(body: str) -> str:
    """Capitalise the first letter only — `str.capitalize` would lower-case 'Rp'."""
    return body[0].upper() + body[1:] + "."


def build_one(rng: random.Random, package_id: int, number: int, bank_dir: Path,
              template, want: str) -> Path | None:
    """Build one item; returns None when the draw did not realise `want`."""
    spec = template(rng, want)
    base = spec["base"]
    eq1, eq2 = spec["stmt1"][1], spec["stmt2"][1]

    ok1, dir1 = _sufficiency(spec, base + eq1)
    ok2, dir2 = _sufficiency(spec, base + eq2)
    ok12, dir12 = _sufficiency(spec, base + eq1 + eq2)

    if ok1 and ok2:
        key = "D"
    elif ok1:
        key = "A"
    elif ok2:
        key = "B"
    elif ok12:
        key = "C"
    else:
        key = "E"
    if key != want:
        return None  # the arithmetic disagreed with the template's intent

    # every "not sufficient" claim must come with a printable counterexample
    w1 = _witness(spec, dir1) if dir1 is not None else None
    w2 = _witness(spec, dir2) if dir2 is not None else None
    w12 = _witness(spec, dir12) if dir12 is not None else None
    if (dir1 is not None and w1 is None) or (dir2 is not None and w2 is None) \
            or (dir12 is not None and w12 is None):
        return None

    not1 = _cannot_because(spec, 1, w1) if w1 else ""
    not2 = _cannot_because(spec, 2, w2) if w2 else ""
    not12 = _cannot_together(spec, w12) if w12 else ""

    yes1, yes2 = _is_enough(spec, "(1)"), _is_enough(spec, "(2)")
    yes12 = _is_enough(spec, "(1) dan (2) bersama-sama")

    # each option is judged on the claim it actually makes, in its own words
    claims = {
        "A": [(ok1, yes1, not1), (not ok2, not2, yes2)],
        "B": [(ok2, yes2, not2), (not ok1, not1, yes1)],
        "C": [(ok12, yes12, not12), (not ok1, not1, yes1), (not ok2, not2, yes2)],
        "D": [(ok1, yes1, not1), (ok2, yes2, not2)],
        "E": [(not ok12, not12, yes12)],
    }
    # A geometry item's key rests on a relation the picture only hints at, so the
    # correct option states that relation before it states the verdict. The wrong
    # options do not repeat it: each of those has one specific thing to answer for,
    # and the witness pair answers it more concretely than a restated theorem would.
    insight = spec.get("insight")
    explanations = {}
    for opt, conjuncts in claims.items():
        if opt == key:
            verdict = _sentence("; ".join(
                support for holds, support, _ in conjuncts if holds
            ))
            explanations[opt] = f"Benar. {insight} {verdict}" if insight \
                else f"Benar. {verdict}"
        else:
            # name the one conjunct this option gets wrong, not a generic denial
            explanations[opt] = "Salah. " + _sentence(
                next(refute for holds, _, refute in conjuncts if not holds)
            )

    context = f"{spec['context']} " if spec["context"] else ""
    question_text = (
        f"{context}{spec['question']}\n"
        f"(1) {spec['stmt1'][0]}\n"
        f"(2) {spec['stmt2'][0]}\n"
        f"{PROMPT}"
    )

    # Written only now that the draw has survived: an item that fails the key check
    # is discarded, and it should not leave an orphan SVG in the package behind it.
    image = (ensure_shared_figure(spec["image"], package_id, bank_dir)
             if spec.get("image") else None)

    q = make_question(
        package_id=package_id,
        subtest=SUBTEST,
        number=number,
        qtype=QTYPE,
        question_text=question_text,
        options=OPTIONS,
        correct_option=key,
        explanations=explanations,
        difficulty=spec["difficulty"],
        image=image,
        source="kecukupan_data.py",
    )
    return write_question(q, bank_dir)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=int, required=True)
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--kind", choices=sorted(TEMPLATE_KINDS), default="any",
                    help="restrict to the templates that carry a figure "
                         "(geometry) or to those that do not (word)")
    ap.add_argument("--template", choices=sorted(EXPLICIT_TEMPLATES),
                    help="opt-in architecture; excluded from legacy default pools")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    if args.template:
        if args.count != 1 or args.kind == "geometry":
            ap.error("--template requires --count 1 and a non-geometry kind")
        groups = [[EXPLICIT_TEMPLATES[args.template]]]
    else:
        groups = TEMPLATE_KINDS[args.kind]
    pool: list = []
    used_keys: set[str] = set()

    for _ in range(args.count):
        if not pool:  # templates without replacement, one per reasoning shape
            pool = groups[:]
            rng.shuffle(pool)
        template, keys = rng.choice(pool.pop())
        # prefer a key this package has not shown yet, so the answer is not
        # guessable from the pattern of previous items
        fresh = [k for k in keys if k not in used_keys] or list(keys)
        path = None
        for _attempt in range(300):
            want = rng.choice(fresh)
            path = build_one(rng, args.package, next_number(args.package, SUBTEST,
                                                            args.bank_dir),
                             args.bank_dir, template, want)
            if path is not None:
                used_keys.add(want)
                break
        if path is None:
            raise RuntimeError(f"{template.__name__}: no clean draw after 300 attempts")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
