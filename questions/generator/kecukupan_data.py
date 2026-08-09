#!/usr/bin/env python3
"""Deterministic generator for `kecukupan_data` (data sufficiency) questions.

Data sufficiency asks whether the information suffices, not what the answer is:
a stem, two numbered statements, and the same five options every time. The key
is therefore a claim about three facts — does (1) alone determine the quantity,
does (2) alone, do they together — and getting it wrong by hand is easy, because
"I cannot see how to solve it" is not the same as "it cannot be solved".

So nothing here is asserted; it is decided:

* Each template states its facts as exact linear equations over `Fraction` and
  the asked-for quantity as a linear functional `t`. The quantity is determined
  by a set of equations iff `t` lies in the row space of their coefficient
  matrix — a rank comparison, computed exactly, with no floating point.
* The key falls out of the resulting triple `(s1, s2, s12)`. Templates declare
  which key they are *aiming* for, and a draw whose computed key disagrees is
  discarded — the arithmetic decides, the template only proposes.
* Every "not sufficient" claim is backed by a **witness pair**: two concrete
  assignments that both satisfy the statement yet disagree on the asked-for
  quantity. The witness is found in the null space and rescaled until it obeys
  the template's realism constraint (head counts stay positive integers), then
  printed in the explanation. An unsupported "tidak cukup" is not an argument.

Usage:
    python3 kecukupan_data.py --package 1 --count 2 [--seed 7] [--bank-dir PATH]
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


def _free_direction(equations, target, n_vars):
    """A direction the equations leave free that changes the asked-for quantity.

    Returns `None` exactly when the equations pin the quantity down — that is the
    sufficiency test, and the returned vector is the counterexample generator
    when they do not.
    """
    coeffs = [eq[0] for eq in equations]
    for v in _nullspace(coeffs, n_vars):
        if _dot(target, v):
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
# (coefficient-vector, right-hand-side) pairs; `target` is the coefficient
# vector of the quantity the stem asks about.

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
        "target": [Fraction(0), Fraction(0), Fraction(1)],
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
        "target": [Fraction(1), Fraction(0)],
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
        "target": [Fraction(2), Fraction(2)],
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
        "target": [Fraction(1), Fraction(1)],
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


# Grouped by the reasoning they exercise, and paired with the keys each shape can
# realise, so a package can be given a spread of keys instead of five C's.
TEMPLATE_GROUPS = [
    [(ds_linear_system, ("C", "E"))],
    [(ds_average_mix, ("C", "A", "E"))],
    [(ds_perimeter, ("B", "C", "D"))],
    [(ds_basket_price, ("C", "A", "E"))],
]


# ----------------------------------------------------------------- assembling

def _sufficiency(spec, equations):
    """(is_sufficient, free_direction) for a set of equations."""
    v = _free_direction(equations, spec["target"], len(spec["solution"]))
    return v is None, v


def _witness(spec, direction):
    """Two assignments satisfying the same statements but disagreeing on the target.

    The null-space direction is rescaled until both assignments are realistic for
    the template — head counts and prices must stay positive whole numbers, and
    prices must land on round rupiah, which is why the scale order is the
    template's to choose. A direction that never becomes realistic makes the item
    unusable, so the caller redraws instead of printing a witness nobody would
    accept.
    """
    base = spec["solution"]
    direction = _integral(direction)
    for scale in spec["witness_scales"]:
        for sign in (1, -1):
            other = [b + sign * scale * d for b, d in zip(base, direction)]
            if spec["positive_integers"] and not all(
                v > 0 and v.denominator == 1 for v in other
            ):
                continue
            if _dot(spec["target"], other) == _dot(spec["target"], base):
                continue
            return other
    return None


def _assignment_text(spec, values) -> str:
    render = spec["render"]
    return ", ".join(
        f"{name} = {render(v)}" for name, v in zip(spec["prompt_names"], values)
    )


def _cannot_because(spec, index: int, other_values) -> str:
    """'(1) is not enough' spelled out as two assignments that disagree."""
    render = spec["render_target"]
    a = render(_dot(spec["target"], spec["solution"]))
    b = render(_dot(spec["target"], other_values))
    return (
        f"pernyataan ({index}) saja tidak cukup, sebab keadaan "
        f"[{_assignment_text(spec, spec['solution'])}] dan "
        f"[{_assignment_text(spec, other_values)}] sama-sama memenuhinya, tetapi "
        f"memberikan {spec['target_name']} sebesar {a} dan {b}"
    )


def _cannot_together(spec, other_values) -> str:
    render = spec["render_target"]
    a = render(_dot(spec["target"], spec["solution"]))
    b = render(_dot(spec["target"], other_values))
    return (
        f"kedua pernyataan bersama-sama pun tidak cukup, sebab keadaan "
        f"[{_assignment_text(spec, spec['solution'])}] dan "
        f"[{_assignment_text(spec, other_values)}] memenuhi keduanya, tetapi "
        f"memberikan {spec['target_name']} sebesar {a} dan {b}"
    )


def _is_enough(spec, index: str) -> str:
    value = spec["render_target"](_dot(spec["target"], spec["solution"]))
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
    explanations = {}
    for opt, conjuncts in claims.items():
        if opt == key:
            explanations[opt] = "Benar. " + _sentence("; ".join(
                support for holds, support, _ in conjuncts if holds
            ))
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
        source="kecukupan_data.py",
    )
    return write_question(q, bank_dir)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=int, required=True)
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pool: list = []
    used_keys: set[str] = set()

    for _ in range(args.count):
        if not pool:  # templates without replacement, one per reasoning shape
            pool = TEMPLATE_GROUPS[:]
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
