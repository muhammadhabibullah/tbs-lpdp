#!/usr/bin/env python3
"""Deterministic generator for `aljabar` (algebra) questions.

Covers the four algebra shapes the official test keeps reusing: isolate x in a
linear equation, evaluate a linear combination of a two-variable system, evaluate
a quadratic at a point, and apply a symmetric identity. The answer is COMPUTED
from the construction — the solution `(x, y)` is drawn first and the equations
are built around it — so the key cannot disagree with the stem.

Design rules shared with the other generators:

* Every distractor is a ``(value, reason)`` pair, so each "Salah." explanation
  names the specific slip that produces *that* number. Pairs travel together
  through de-duplication and shuffling and can never be reassigned.
* A distractor that does not render exactly in Indonesian notation (a repeating
  decimal) is dropped and the item redrawn — an option a candidate cannot even
  read is not a distractor.
* Templates are drawn without replacement and grouped by solving method, so one
  package never ships two items solved the same way.

Usage:
    python3 aljabar.py --package 1 --count 3 [--seed 7] [--bank-dir PATH]
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
QTYPE = "aljabar"

_fmt = fmt_number


def _signed(value: int, symbol: str = "") -> str:
    """Render a trailing term of an expression: ``3 -> "+ 3x"``, ``-3 -> "− 3x"``."""
    sign = MINUS if value < 0 else "+"
    magnitude = abs(value)
    if symbol and magnitude == 1:
        return f"{sign} {symbol}"
    return f"{sign} {_fmt(magnitude)}{symbol}"


def _paren(value) -> str:
    """Wrap a negative value in brackets so it can sit inside an expression."""
    return f"({_fmt(value)})" if value < 0 else _fmt(value)


def _coefficient(value: int, symbol: str) -> str:
    """Render a leading coefficient: ``1 -> "x"``, ``-1 -> "−x"``, ``4 -> "4x"``."""
    if value == 1:
        return symbol
    if value == -1:
        return f"{MINUS}{symbol}"
    return f"{_fmt(value)}{symbol}"


def _equation(a: int, b: int, c: int) -> str:
    """``a x + b y = c`` in exam notation."""
    return f"{_coefficient(a, 'x')} {_signed(b, 'y')} = {_fmt(c)}"


# ------------------------------------------------------------------ patterns
# Each returns (text, answer, [(wrong, reason), ...], work, difficulty).

def gen_linear_one_var(rng: random.Random):
    """a·x − b = c — the single most common algebra stem."""
    x = rng.randint(2, 15)
    a = rng.randint(2, 9)
    b = rng.randint(2, 30)
    c = a * x - b
    text = f"Jika {a}x {MINUS} {b} = {_fmt(c)}, nilai x adalah ..."
    work = (
        f"{a}x = {_fmt(c)} + {b} = {_fmt(c + b)}, sehingga "
        f"x = {_fmt(c + b)} : {a} = {_fmt(x)}"
    )
    wrongs = [
        (Fraction(c - b, a),
         f"mengurangkan {b} sekali lagi ketika memindahkan ruas, padahal "
         f"{MINUS}{b} berubah menjadi +{b}"),
        (Fraction(c, a),
         f"membagi {_fmt(c)} dengan {a} tanpa memindahkan {MINUS}{b} lebih dahulu"),
        (Fraction(c + b - a),
         f"mengurangkan koefisien {a} dari {_fmt(c + b)}, padahal koefisien itu "
         f"harus dijadikan pembagi"),
        (Fraction(c + b),
         f"berhenti pada nilai {a}x dan belum membaginya dengan {a}"),
    ]
    return text, Fraction(x), wrongs, work, "easy"


def gen_fraction_equation(rng: random.Random):
    """(x + a) / b = c — the same isolation, one step deeper."""
    b = rng.choice([2, 3, 4, 5, 6])
    a = rng.randint(2, 15)
    x = rng.randrange(3, 24)
    x += (-(x + a)) % b  # push x up until b divides (x + a) exactly
    c = Fraction(x + a, b)
    text = f"Jika (x + {a}) : {b} = {_fmt(c)}, nilai x adalah ..."
    work = (
        f"x + {a} = {_fmt(c)} × {b} = {_fmt(c * b)}, sehingga "
        f"x = {_fmt(c * b)} {MINUS} {a} = {_fmt(x)}"
    )
    wrongs = [
        (c * b + a,
         f"menambahkan {a} setelah mengalikan dengan {b}, padahal {a} harus dikurangkan"),
        (c - a,
         f"mengurangkan {a} tanpa lebih dahulu mengalikan kedua ruas dengan {b}"),
        (b * (c - a),
         f"mengurangkan {a} lebih dahulu, baru mengalikan dengan {b}; urutannya terbalik"),
        (Fraction(c, b) - a,
         f"membagi dengan {b}, padahal kedua ruas harus dikalikan dengan {b}"),
    ]
    return text, Fraction(x), wrongs, work, "medium"


def gen_spldv(rng: random.Random):
    """Two linear equations; the question asks for k(x + y), not for x or y."""
    x, y = rng.randint(-6, 10), rng.randint(-6, 10)
    a1, b1, a2, b2 = 0, 0, 0, 0
    for _ in range(50):
        a1, b1 = rng.randint(1, 5), rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        a2, b2 = rng.randint(1, 5), rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        if a1 * b2 - a2 * b1:  # a proportional pair has no unique solution
            break
    else:
        raise RuntimeError("no non-degenerate coefficient pair drawn")

    c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
    k = rng.choice([2, 3])
    answer = k * (x + y)
    asked = f"{k}x + {k}y"
    text = (
        f"Diketahui {_equation(a1, b1, c1)} dan {_equation(a2, b2, c2)}. "
        f"Nilai dari {asked} adalah ..."
    )
    work = (
        f"Menyelesaikan kedua persamaan diperoleh x = {_fmt(x)} dan y = {_fmt(y)}, "
        f"sehingga {asked} = {k} × ({_paren(x)} + {_paren(y)}) = {_fmt(answer)}"
    )
    wrongs = [
        (Fraction(k * (x - y)),
         f"menghitung {k}x {MINUS} {k}y, yaitu selisihnya, bukan jumlahnya"),
        (Fraction(x + y),
         f"berhenti pada x + y dan lupa mengalikannya dengan {k}"),
        (Fraction(k * x),
         f"hanya menghitung {k}x dan mengabaikan suku {k}y"),
        (Fraction(k * y),
         f"hanya menghitung {k}y dan mengabaikan suku {k}x"),
        # the explanation walks both steps: a bare "lalu dibagi" leaves the
        # reader unable to see where the printed value came from
        (Fraction(k * (c1 + c2), a1 + a2 + b1 + b2) if a1 + a2 + b1 + b2 else None,
         f"menjumlahkan kedua persamaan menjadi {_fmt(c1 + c2)}, membaginya dengan "
         f"jumlah seluruh koefisien ({_fmt(a1 + a2 + b1 + b2)}) sehingga diperoleh "
         f"{_fmt(Fraction(c1 + c2, a1 + a2 + b1 + b2)) if a1 + a2 + b1 + b2 else ''}, "
         f"lalu mengalikannya dengan {k} — seolah-olah koefisien x dan y sudah sama"),
    ]
    return text, Fraction(answer), [w for w in wrongs if w[0] is not None], work, "hard"


def gen_quadratic_substitution(rng: random.Random):
    """Evaluate y = ax² + bx + c at a point, often a negative one."""
    a = rng.randint(2, 5)
    b = rng.choice([-6, -5, -4, -3, -2, 2, 3, 4, 5, 6])
    c = rng.choice([-9, -7, -5, -4, -3, 3, 4, 5, 7, 9])
    k = rng.choice([-4, -3, -2, 2, 3, 4])
    answer = a * k * k + b * k + c
    text = (
        f"Jika y = {a}x² {_signed(b, 'x')} {_signed(c)}, "
        f"nilai y untuk x = {_fmt(k)} adalah ..."
    )
    work = (
        f"y = {a} × ({_fmt(k)})² {_signed(b)} × ({_fmt(k)}) {_signed(c)} = "
        f"{_fmt(a * k * k)} {_signed(b * k)} {_signed(c)} = {_fmt(answer)}"
    )
    wrongs = [
        (Fraction((a * k) ** 2 + b * k + c),
         f"mengkuadratkan {a}x sebagai satu kesatuan, yaitu ({a} × {_paren(k)})², "
         f"padahal yang dikuadratkan hanya x"),
        (Fraction(a * 2 * k + b * k + c),
         f"membaca {a}x² sebagai {a} × 2 × x sehingga pangkat dua berubah menjadi "
         f"perkalian dua"),
        (Fraction(a * k * k - b * k + c),
         f"salah tanda pada suku {_signed(b, 'x')} ketika mensubstitusikan "
         f"x = {_fmt(k)}"),
        (Fraction(a * k * k + b * k - c),
         f"salah tanda pada tetapan {_signed(c)}"),
    ]
    if k < 0:  # only a live mistake when there is a negative to square
        wrongs.append((
            Fraction(-a * k * k + b * k + c),
            f"menganggap ({_fmt(k)})² bernilai negatif, padahal kuadrat bilangan "
            f"negatif selalu positif",
        ))
    return text, Fraction(answer), wrongs, work, "medium"


def gen_identity_sum_product(rng: random.Random):
    """x + y = s, xy = p → x² + y² = s² − 2p."""
    for _ in range(50):
        s = rng.randint(5, 20)
        p = rng.randint(2, 40)
        if s * s - 4 * p >= 0:  # keep x and y real so the premise is satisfiable
            break
    else:
        raise RuntimeError("no real-rooted (s, p) pair drawn")

    answer = s * s - 2 * p
    text = f"Diketahui x + y = {s} dan xy = {p}. Nilai dari x² + y² adalah ..."
    work = (
        f"x² + y² = (x + y)² {MINUS} 2xy = {s}² {MINUS} 2 × {p} = "
        f"{_fmt(s * s)} {MINUS} {_fmt(2 * p)} = {_fmt(answer)}"
    )
    wrongs = [
        (Fraction(s * s),
         f"menghitung (x + y)² = {_fmt(s * s)} dan berhenti di situ, tanpa "
         f"mengurangkan 2xy"),
        (Fraction(s * s - p),
         "mengurangkan xy satu kali, padahal penjabaran (x + y)² memuat 2xy"),
        (Fraction(s * s + 2 * p),
         "menambahkan 2xy, padahal suku itu harus dipindahkan sehingga dikurangkan"),
        (Fraction(s * s - 4 * p),
         f"menghitung (x {MINUS} y)² = (x + y)² {MINUS} 4xy, yang merupakan besaran lain"),
    ]
    return text, Fraction(answer), wrongs, work, "hard"


# Grouped by solving method: the first two are both "isolate x in one linear
# equation" and must not both appear in one package.
PATTERN_GROUPS = [
    [gen_linear_one_var, gen_fraction_equation],
    [gen_spldv],
    [gen_quadratic_substitution],
    [gen_identity_sum_product],
]

PATTERNS = [p for group in PATTERN_GROUPS for p in group]


def build_one(rng: random.Random, package_id: int, number: int, bank_dir: Path,
              pattern) -> Path:
    """Draw from `pattern` until four clean distractors survive, then write it."""
    for _ in range(200):
        text, answer, wrongs, work, difficulty = pattern(rng)
        if not renders_exactly(answer):
            continue

        taken, distractors = {answer}, []
        for value, reason in wrongs:
            value = Fraction(value)
            if value in taken or not renders_exactly(value):
                continue
            taken.add(value)
            distractors.append((value, reason))
        if len(distractors) < 4:
            continue

        rng.shuffle(distractors)
        values = [(answer, None)] + distractors[:4]
        rng.shuffle(values)
        correct_key = "ABCDE"[[v for v, _ in values].index(answer)]

        options, explanations = [], {}
        for key, (value, reason) in zip("ABCDE", values):
            options.append((key, _fmt(value)))
            explanations[key] = (
                f"Benar. {work}." if reason is None
                else f"Salah. Nilai {_fmt(value)} diperoleh dengan {reason}."
            )

        q = make_question(
            package_id=package_id,
            subtest=SUBTEST,
            number=number,
            qtype=QTYPE,
            question_text=text,
            options=options,
            correct_option=correct_key,
            explanations=explanations,
            difficulty=difficulty,
            source="aljabar.py",
        )
        return write_question(q, bank_dir)
    raise RuntimeError(f"{pattern.__name__}: no clean draw after 200 attempts")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=int, required=True)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pool: list = []
    for _ in range(args.count):
        if not pool:  # without replacement, one draw per solving method
            pool = PATTERN_GROUPS[:]
            rng.shuffle(pool)
        number = next_number(args.package, SUBTEST, args.bank_dir)
        path = build_one(rng, args.package, number, args.bank_dir, rng.choice(pool.pop()))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
