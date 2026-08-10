#!/usr/bin/env python3
"""Deterministic generator for `deret_angka` (number sequence) questions.

The answer key is COMPUTED from the sequence rule, so it is correct by
construction. Two properties are enforced beyond that:

* **Explanations describe their own option.** Every distractor is produced as a
  ``(value, reason)`` pair and the pair travels together through de-duplication
  and shuffling, so an option can never inherit a neighbour's justification.
* **The sequence has one reading.** Each candidate is screened against a battery
  of rival rules (arithmetic, geometric, constant second difference, interleaved
  arithmetic/geometric, alternating differences, Fibonacci-like). If any rival
  fits every printed term but predicts a different continuation, the candidate is
  discarded and redrawn — an ambiguous stem has no defensible key.

Distractors are also barred from equalling a term already printed in the stem;
such an option is dead on sight and wastes one of the five slots.

`--blanks 2` produces the "..., ..." variant the official sets use, where each
option is a *pair* of numbers. That stem prints one more term of evidence once
the 7th term is granted, so the 8th term is screened against the rival rules a
second time; its distractors split evenly between pairs whose 7th term is right
and 8th wrong, and pairs that are already wrong at the 7th.

`--interior` produces the hardest shape — four terms, two blanks, then a further
term printed as an anchor (``−9, −10, −8, −24, ..., ..., −138``). The rule has to
be inferred from less evidence, and the anchor is there to be checked against
rather than continued, which is what separates a near-miss rule from the right
one. It gets its own screening: a rival reading only makes the item ambiguous if
it fits the four printed terms *and* lands on the anchor by different middles.

Usage:
    python3 deret_angka.py --package 1 --count 5 [--blanks 2 | --interior]
                           [--seed 42] [--bank-dir PATH]
"""

from __future__ import annotations

import argparse
import random
from fractions import Fraction
from pathlib import Path

from common import BANK_DIR, MINUS, fmt_number, make_question, next_number, write_question

SUBTEST = "kuantitatif"
QTYPE = "deret_angka"

_fmt = fmt_number


# ------------------------------------------------------- rival-rule screening

def _rule_arithmetic(t):
    d = {b - a for a, b in zip(t, t[1:])}
    return t[-1] + d.pop() if len(d) == 1 else None


def _rule_geometric(t):
    if any(x == 0 for x in t[:-1]):
        return None
    ratios = {Fraction(b, a) for a, b in zip(t, t[1:])}
    if len(ratios) != 1:
        return None
    nxt = t[-1] * ratios.pop()
    return int(nxt) if nxt.denominator == 1 else None


def _rule_second_difference(t):
    d = [b - a for a, b in zip(t, t[1:])]
    if len(d) < 2:
        return None
    dd = {y - x for x, y in zip(d, d[1:])}
    return t[-1] + d[-1] + dd.pop() if len(dd) == 1 else None


def _rule_interleaved_arithmetic(t):
    a, b = t[0::2], t[1::2]
    if len(a) < 2 or len(b) < 2:
        return None
    da = {y - x for x, y in zip(a, a[1:])}
    db = {y - x for x, y in zip(b, b[1:])}
    if len(da) != 1 or len(db) != 1:
        return None
    # an even-length stem ends on the second sequence, so the next term is the
    # first sequence's turn, and vice versa
    return a[-1] + da.pop() if len(t) % 2 == 0 else b[-1] + db.pop()


def _rule_interleaved_geometric(t):
    a, b = t[0::2], t[1::2]
    if len(a) < 2 or len(b) < 2 or any(x == 0 for x in t):
        return None
    ra = {Fraction(y, x) for x, y in zip(a, a[1:])}
    rb = {Fraction(y, x) for x, y in zip(b, b[1:])}
    if len(ra) != 1 or len(rb) != 1:
        return None
    nxt = a[-1] * ra.pop() if len(t) % 2 == 0 else b[-1] * rb.pop()
    return int(nxt) if nxt.denominator == 1 else None


def _rule_alternating_differences(t):
    """Differences alternate between two constants (+a, +b, +a, +b, ...)."""
    d = [y - x for x, y in zip(t, t[1:])]
    if len(d) < 4:
        return None
    odd, even = {d[i] for i in range(0, len(d), 2)}, {d[i] for i in range(1, len(d), 2)}
    if len(odd) != 1 or len(even) != 1 or odd == even:
        return None
    return t[-1] + (odd if len(d) % 2 == 0 else even).pop()


def _rule_fibonacci(t):
    if len(t) < 4 or any(t[i] != t[i - 1] + t[i - 2] for i in range(2, len(t))):
        return None
    return t[-1] + t[-2]


def _weak_interleaved_second_difference(t):
    """Each half read as its own constant-second-difference sequence.

    With a six-term stem each half holds only three points, so this rule is
    *always* satisfiable and confirms nothing — it cannot veto a candidate. It
    is still a reading a test-taker may reach, so its prediction must not be
    allowed to land on one of the distractors.
    """
    a, b = t[0::2], t[1::2]
    if len(a) < 3 or len(b) < 3:
        return None
    half = a if len(t) % 2 == 0 else b
    d = [y - x for x, y in zip(half, half[1:])]
    return half[-1] + d[-1] + (d[-1] - d[-2])


def _weak_interleaved_mixed(t):
    """One half arithmetic, the other geometric (or vice versa)."""
    a, b = t[0::2], t[1::2]
    if len(a) < 3 or len(b) < 3 or any(x == 0 for x in t):
        return None
    half = a if len(t) % 2 == 0 else b
    ratios = {Fraction(y, x) for x, y in zip(half, half[1:])}
    if len(ratios) != 1:
        return None
    nxt = half[-1] * ratios.pop()
    return int(nxt) if nxt.denominator == 1 else None


WEAK_RULES = (_weak_interleaved_second_difference, _weak_interleaved_mixed)


def weak_predictions(terms: list[int]) -> set[int]:
    """Continuations reachable by under-determined readings of the stem.

    These never veto a sequence — a three-point fit confirms nothing — but a
    distractor sitting on one of them would reward the wrong reading, so they
    are excluded from the option set.
    """
    return {p for rule in WEAK_RULES if (p := rule(terms)) is not None}


RIVAL_RULES = (
    _rule_arithmetic,
    _rule_geometric,
    _rule_second_difference,
    _rule_interleaved_arithmetic,
    _rule_interleaved_geometric,
    _rule_alternating_differences,
    _rule_fibonacci,
)


def is_unambiguous(terms: list[int], answer: int) -> bool:
    """True when no rival rule fitting every printed term predicts anything else."""
    for rule in RIVAL_RULES:
        predicted = rule(terms)
        if predicted is not None and predicted != answer:
            return False
    return True


# --------------------------------------------------------------- the patterns
# Each returns (terms, answer, [(wrong_value, reason), ...], explanation, difficulty).
# Reasons are written to be true of *that specific value*.

def gen_geometric(rng: random.Random):
    start = rng.choice([2, 3, 4, 5, 6])
    ratio = rng.choice([2, 3, -2, -3])
    terms = [start * ratio**i for i in range(5)]
    answer = terms[-1] * ratio
    answer2 = answer * ratio
    wrongs = [
        (2 * terms[-1] - terms[-2],
         f"menambahkan selisih dua suku terakhir ({_fmt(terms[-1] - terms[-2])}) "
         f"alih-alih mengalikan dengan rasio {_fmt(ratio)}"),
        (answer * ratio,
         "mengalikan dengan rasio dua kali sehingga melompat satu suku terlalu jauh"),
        (terms[-1] * (ratio + 1),
         f"menggunakan rasio {_fmt(ratio + 1)}, padahal rasio deret ini {_fmt(ratio)}"),
        # a sign slip is only a believable mistake when there is a sign to slip on
        ((-answer, "menerapkan besar rasio dengan tanda yang keliru") if ratio < 0
         else (terms[-1] + (terms[1] - terms[0]),
               f"menambahkan selisih dua suku pertama ({_fmt(terms[1] - terms[0])}) "
               "seolah-olah deret ini deret aritmetika")),
    ]
    shown = f"({_fmt(ratio)})" if ratio < 0 else _fmt(ratio)
    expl = (
        f"Setiap suku diperoleh dengan mengalikan suku sebelumnya dengan {_fmt(ratio)}: "
        f"{_fmt(terms[-1])} × {shown} = {_fmt(answer)}."
    )
    return terms, answer, answer2, wrongs, expl, "easy" if ratio > 0 else "medium"


def gen_two_interleaved(rng: random.Random):
    a0, ad = rng.randint(2, 20), rng.choice([3, 4, 5, 6, 7])
    b0, bd = rng.randint(35, 70), rng.choice([-3, -4, -5, -6, -8])
    terms = []
    for i in range(3):
        terms += [a0 + i * ad, b0 + i * bd]
    answer = a0 + 3 * ad  # the 7th term belongs to the first sequence
    answer2 = b0 + 3 * bd  # ... and the 8th belongs to the second
    wrongs = [
        (b0 + 3 * bd,
         "melanjutkan deret kedua, padahal suku ketujuh adalah giliran deret pertama"),
        (terms[-1] + ad,
         f"menambahkan beda deret pertama ({_fmt(ad)}) pada suku terakhir, "
         "padahal suku terakhir milik deret kedua"),
        (a0 + 2 * ad + bd,
         "menerapkan beda deret kedua pada suku terakhir deret pertama"),
        (answer + ad,
         "melanjutkan deret pertama dua langkah sekaligus"),
    ]
    expl = (
        f"Deret ini terdiri atas dua deret berselang-seling. Suku ganjil "
        f"({_fmt(a0)}, {_fmt(a0 + ad)}, {_fmt(a0 + 2 * ad)}) naik tetap {_fmt(ad)}, "
        f"sedangkan suku genap ({_fmt(b0)}, {_fmt(b0 + bd)}, {_fmt(b0 + 2 * bd)}) "
        f"berubah tetap {_fmt(bd)}. Suku ketujuh melanjutkan deret pertama: "
        f"{_fmt(a0 + 2 * ad)} + {_fmt(ad)} = {_fmt(answer)}."
    )
    return terms, answer, answer2, wrongs, expl, "medium"


def gen_increasing_diff(rng: random.Random):
    start = rng.randint(2, 15)
    d0 = rng.randint(2, 6)
    step = rng.choice([2, 3, 4])
    terms, cur, d = [start], start, d0
    for _ in range(5):
        cur += d
        terms.append(cur)
        d += step
    answer = cur + d
    answer2 = answer + d + step
    wrongs = [
        (cur + d - step,
         f"mengulang selisih terakhir ({_fmt(d - step)}) dan menganggap selisih itu tetap"),
        (cur + d + step,
         "menambah selisih dua tingkat sekaligus"),
        (cur + d0,
         f"memakai selisih pertama ({_fmt(d0)}) untuk langkah terakhir"),
        (terms[-2] + d,
         "menerapkan selisih berikutnya pada suku kelima, bukan pada suku keenam"),
    ]
    expl = (
        f"Selisih antarsuku bertambah tetap {_fmt(step)}: {_fmt(d0)}, {_fmt(d0 + step)}, "
        f"{_fmt(d0 + 2 * step)}, dan seterusnya. Selisih berikutnya adalah {_fmt(d)}, "
        f"sehingga suku berikutnya {_fmt(cur)} + {_fmt(d)} = {_fmt(answer)}."
    )
    return terms, answer, answer2, wrongs, expl, "medium"


def gen_alternating_ops(rng: random.Random):
    """×m → +a → ×m → +a ...

    Five operations are applied, so the printed stem stops just after a
    multiplication and the term being asked for is an *addition* step.
    """
    start = rng.randint(2, 8)
    mul = rng.choice([2, 3])
    add = rng.choice([3, 4, 5, 6])
    terms, cur = [start], start
    for i in range(5):
        cur = cur * mul if i % 2 == 0 else cur + add
        terms.append(cur)
    answer = terms[-1] + add  # the sixth operation is an addition
    answer2 = answer * mul   # ... and the seventh is a multiplication again
    wrongs = [
        (terms[-1] * mul,
         f"menerapkan perkalian dengan {_fmt(mul)} padahal giliran berikutnya adalah "
         f"penjumlahan dengan {_fmt(add)}"),
        (terms[-1] * mul + add,
         "menerapkan kedua operasi sekaligus dalam satu langkah"),
        (terms[-1] + (terms[-1] - terms[-2]),
         f"menganggap deret memiliki selisih tetap sebesar selisih dua suku terakhir "
         f"({_fmt(terms[-1] - terms[-2])})"),
        (answer * mul,
         "melanjutkan dua langkah sekaligus, yaitu menambah lalu mengalikan"),
    ]
    expl = (
        f"Operasi berselang-seling: kalikan {_fmt(mul)}, lalu tambah {_fmt(add)}, "
        f"lalu kalikan {_fmt(mul)} lagi, dan seterusnya "
        f"({_fmt(terms[0])} × {_fmt(mul)} = {_fmt(terms[1])}; "
        f"{_fmt(terms[1])} + {_fmt(add)} = {_fmt(terms[2])}). "
        f"Suku terakhir diperoleh melalui perkalian, sehingga langkah berikutnya adalah "
        f"penjumlahan: {_fmt(terms[-1])} + {_fmt(add)} = {_fmt(answer)}."
    )
    return terms, answer, answer2, wrongs, expl, "hard"


OP_LABEL = {"add": "tambah", "sub": "kurangi", "mul": "kali", "div": "bagi"}
OP_SYMBOL = {"add": "+", "sub": MINUS, "mul": "×", "div": ":"}


def _apply(op: str, value: int, n: int) -> int:
    """One step of an operation cycle. Division is only ever called where the
    construction has already guaranteed it comes out whole."""
    if op == "add":
        return value + n
    if op == "sub":
        return value - n
    if op == "mul":
        return value * n
    assert value % n == 0, "inexact division reached _apply"
    return value // n


def _unapply(op: str, value: int, n: int) -> int:
    """Inverse of `_apply`, for building a divide-cycle backwards from its end."""
    return {"add": value - n, "sub": value + n, "div": value * n}[op]


def _try(op: str, value: int, n: int):
    """`_apply` for distractors: None when a division would leave a remainder."""
    if op == "div" and (n == 0 or value % n != 0):
        return None
    return _apply(op, value, n)


def gen_cycling_ops(rng: random.Random):
    """Operations repeat in a three-step cycle while the operand climbs by one.

    `−9, −10, −8, −24, …` is −1, +2, ×3, then −4, +5, ×6: the reader has to see
    two things at once — that the operations run in a cycle, and that the number
    they are applied with keeps counting up straight through the repeat. This is
    the shape the official sets use for their hardest sequence item.

    Each cycle carries two additive steps and one multiplicative one. A ×-cycle
    is built forwards; a ÷-cycle is built **backwards** from a small final term,
    because every division going forwards is a multiplication going back — so
    the sequence divides exactly at every step by construction rather than by
    luck.
    """
    first, second = rng.sample(["sub", "add"], 2)
    third = rng.choice(["mul", "mul", "div"])
    ops = (first, second, third)
    k = rng.choice([1, 2])
    operands = [k + i for i in range(7)]  # 7 steps → 8 terms

    if third == "mul":
        terms = [rng.choice([-1, -1, 1]) * rng.randint(4, 15)]
        for i, n in enumerate(operands):
            terms.append(_apply(ops[i % 3], terms[-1], n))
    else:
        terms = [rng.choice([-1, -1, 1]) * rng.randint(2, 9)]  # the 7th term
        for i in range(5, -1, -1):
            terms.insert(0, _unapply(ops[i % 3], terms[0], operands[i]))
        terms.append(_apply(ops[0], terms[-1], operands[6]))

    answer, answer2 = terms[6], terms[7]
    shown = terms[:6]
    step_op, step_n, before = ops[2], operands[5], terms[5]

    wrongs = []
    for value, reason in (
        (_try(ops[1], before, step_n),
         f"menerapkan operasi {OP_LABEL[ops[1]]} {_fmt(step_n)}, padahal langkah ketiga "
         f"dalam setiap siklus adalah {OP_LABEL[step_op]}"),
        (_try(step_op, before, step_n - 1),
         f"memakai bilangan {_fmt(step_n - 1)} lagi, padahal bilangan operasinya naik "
         f"satu setiap langkah sehingga giliran ini memakai {_fmt(step_n)}"),
        (_try(ops[0], _try(step_op, before, step_n) or 0, step_n),
         f"menerapkan dua operasi sekaligus dalam satu langkah "
         f"({OP_LABEL[step_op]} {_fmt(step_n)} lalu {OP_LABEL[ops[0]]} {_fmt(step_n)})"),
        (_try(step_op, before, operands[2]),
         f"mengulang bilangan {_fmt(operands[2])} dari siklus pertama alih-alih "
         f"melanjutkan hitungan ke {_fmt(step_n)}"),
    ):
        if value is not None:
            wrongs.append((value, reason))

    # The two hidden terms of the interior-blank stem, and the ways a reader
    # arrives at the wrong pair. Each is a real misreading of *this* rule.
    t5, t6 = terms[4], terms[5]
    restart5 = _try(ops[0], terms[3], operands[0])
    swap5 = _try(ops[1], terms[3], operands[3])
    keep5 = _try(ops[0], terms[3], operands[3])
    interior_wrongs = []
    for pair_values, reason in (
        ((restart5, restart5 is not None and _try(ops[1], restart5, operands[1])),
         f"mengulang bilangan operasi dari awal ({_fmt(operands[0])}, {_fmt(operands[1])}) "
         f"ketika siklus berulang, padahal bilangan itu terus naik ke "
         f"{_fmt(operands[3])} dan {_fmt(operands[4])}"),
        ((swap5, swap5 is not None and _try(ops[0], swap5, operands[4])),
         f"menukar urutan kedua operasi dalam siklus ({OP_LABEL[ops[1]]} dulu, baru "
         f"{OP_LABEL[ops[0]]})"),
        ((t5, keep5 is not None and _try(ops[1], t5, operands[3])),
         f"menghitung suku kelima dengan benar, tetapi memakai bilangan "
         f"{_fmt(operands[3])} lagi untuk suku keenam alih-alih menaikkannya menjadi "
         f"{_fmt(operands[4])}"),
    ):
        a, b = pair_values
        if a is not None and b is not None and b is not False:
            interior_wrongs.append(((a, b), reason))

    cycle = ", ".join(
        f"{OP_SYMBOL[ops[i % 3]]}{_fmt(operands[i])}" for i in range(6)
    )
    expl = (
        f"Operasinya berulang dalam siklus tiga langkah — {OP_LABEL[ops[0]]}, "
        f"{OP_LABEL[ops[1]]}, lalu {OP_LABEL[ops[2]]} — sementara bilangan operasinya naik "
        f"satu setiap langkah dan tidak ikut diulang: {cycle}. "
        f"Langkah keenam adalah {OP_LABEL[step_op]} {_fmt(step_n)}, sehingga "
        f"{_fmt(before)} {OP_SYMBOL[step_op]} {_fmt(step_n)} = {_fmt(answer)}."
    )
    return shown, answer, answer2, wrongs, expl, "hard", interior_wrongs


def gen_fibonacci_like(rng: random.Random):
    a, b = rng.randint(1, 6), rng.randint(2, 9)
    terms = [a, b]
    for _ in range(4):
        terms.append(terms[-1] + terms[-2])
    answer = terms[-1] + terms[-2]
    answer2 = answer + terms[-1]
    # NB: Fibonacci identities collapse many "obvious" distractors onto each
    # other (t6+t5+t4 == 2·t6, and t6+t4 == 2·t6−t5), so these four are chosen
    # to stay distinct for every draw.
    wrongs = [
        (terms[-1] + terms[-3],
         "menjumlahkan suku terakhir dengan suku keempat, bukan dengan suku kelima"),
        (terms[-1] * 2,
         "menggandakan suku terakhir alih-alih menjumlahkannya dengan suku sebelumnya"),
        # NB: t6 + t5 − t4 reduces to 2·t6 − ... which coincides exactly with the
        # interleaved second-difference misreading of a Fibonacci stem, so it is
        # excluded by weak_predictions() and cannot be used here.
        (terms[-1] + terms[1],
         "menjumlahkan suku terakhir dengan suku kedua, bukan dengan suku kelima"),
        (answer + terms[-1],
         "melanjutkan deret dua langkah sehingga memperoleh suku kedelapan"),
    ]
    expl = (
        f"Setiap suku merupakan jumlah dua suku sebelumnya "
        f"({_fmt(terms[0])} + {_fmt(terms[1])} = {_fmt(terms[2])}; "
        f"{_fmt(terms[1])} + {_fmt(terms[2])} = {_fmt(terms[3])}). "
        f"Suku berikutnya adalah {_fmt(terms[-2])} + {_fmt(terms[-1])} = {_fmt(answer)}."
    )
    return terms, answer, answer2, wrongs, expl, "hard"


def gen_squares_offset(rng: random.Random):
    c = rng.choice([-3, -2, -1, 1, 2, 3, 4, 5])
    terms = [n * n + c for n in range(1, 7)]
    answer = 49 + c
    answer2 = 64 + c
    wrongs = [
        (terms[-1] + (terms[-1] - terms[-2]),
         f"menganggap selisih tetap sebesar {_fmt(terms[-1] - terms[-2])}, "
         "padahal selisihnya bertambah dua setiap langkah"),
        (terms[-1] + 12,
         "menambahkan 2 × 6 = 12 dan lupa bahwa selisih berikutnya adalah 2 × 6 + 1 = 13"),
        (49,
         f"menghitung 7² tetapi lupa menambahkan tetapan {_fmt(c)}"),
        (64 + c,
         "melompat ke suku kedelapan (8² + tetapan), bukan suku ketujuh"),
    ]
    expl = (
        f"Suku ke-n adalah n² {'+' if c > 0 else '−'} {_fmt(abs(c))} "
        f"(1² {'+' if c > 0 else '−'} {_fmt(abs(c))} = {_fmt(terms[0])}, "
        f"2² {'+' if c > 0 else '−'} {_fmt(abs(c))} = {_fmt(terms[1])}, dan seterusnya). "
        f"Suku ketujuh adalah 7² {'+' if c > 0 else '−'} {_fmt(abs(c))} = {_fmt(answer)}."
    )
    return terms, answer, answer2, wrongs, expl, "medium"


def gen_doubling_diff(rng: random.Random):
    """Differences double each step — a geometric pattern in the differences."""
    start = rng.randint(2, 12)
    d = rng.choice([2, 3, 4, 5])
    terms, cur, step = [start], start, d
    for _ in range(5):
        cur += step
        terms.append(cur)
        step *= 2
    answer = cur + step
    answer2 = answer + step * 2
    last_diff = step // 2
    wrongs = [
        (cur + last_diff,
         f"mengulang selisih terakhir ({_fmt(last_diff)}) alih-alih menggandakannya"),
        (cur + last_diff * 3,
         "mengalikan selisih terakhir dengan 3, bukan dengan 2"),
        (cur * 2,
         "menggandakan suku terakhir, padahal yang berlipat dua adalah selisihnya"),
        (answer + step * 2,
         "melanjutkan deret dua langkah sekaligus"),
    ]
    expl = (
        f"Selisih antarsuku berlipat dua setiap langkah: {_fmt(d)}, {_fmt(2 * d)}, "
        f"{_fmt(4 * d)}, dan seterusnya. Selisih berikutnya adalah {_fmt(step)}, "
        f"sehingga suku berikutnya {_fmt(cur)} + {_fmt(step)} = {_fmt(answer)}."
    )
    return terms, answer, answer2, wrongs, expl, "medium"


# Grouped so that one package never draws two sequences solved the same way:
# `gen_squares_offset` (n² + c) is just a constant-second-difference sequence
# with step 2, so it shares a group with `gen_increasing_diff`.
PATTERN_GROUPS = [
    [gen_geometric],
    [gen_two_interleaved],
    [gen_increasing_diff, gen_squares_offset],
    [gen_alternating_ops],
    [gen_fibonacci_like],
    [gen_doubling_diff],
    [gen_cycling_ops],
]

PATTERNS = [p for group in PATTERN_GROUPS for p in group]

# The families worth putting behind the anchored stem (--interior). Each is a
# rule a reader can still pin down from four terms: an operation cycle, a
# Fibonacci sum, a second-difference climb, two interleaved sequences, or
# differences that double. `gen_geometric` and `gen_squares_offset` are left out
# — four terms of either is a giveaway, and the anchor adds nothing.
INTERIOR_GROUPS = [
    [gen_cycling_ops],
    [gen_fibonacci_like],
    [gen_increasing_diff],
    [gen_two_interleaved],
    [gen_doubling_diff],
]


def _single_blank(terms, answer, answer2, wrongs, expl_correct):
    """Option set for the one-blank stem: five numbers, one of them the 7th term."""
    # drop values that are dead on sight (already printed) or that reward an
    # under-determined reading
    taken, distractors = {answer, *terms, *weak_predictions(terms)}, []
    for value, reason in wrongs:
        if value in taken:
            continue
        taken.add(value)
        distractors.append((_fmt(value), f"Nilai {_fmt(value)} diperoleh dengan {reason}."))
    stem = (", ".join(_fmt(t) for t in terms)
            + ", ... Bilangan yang tepat untuk melanjutkan deret tersebut adalah ...")
    return stem, _fmt(answer), distractors, expl_correct


def _double_blank(terms, answer, answer2, wrongs, expl_correct):
    """Option set for the two-blank stem, as in `6, 3, 18, 9, 54, 27, 162, ..., ...`.

    A pair is wrong as soon as either component is, so the distractors split into
    two honest families: the 7th term is right but the 8th continues it by the
    wrong rule, or the 7th term is already wrong (and the reason for it carries
    over unchanged from the one-blank mistakes).
    """
    def pair(a, b):
        return f"{_fmt(a)}, {_fmt(b)}"

    correct = pair(answer, answer2)
    repeat_diff = answer + (answer - terms[-1])
    overshoot = answer2 + (answer2 - answer)

    candidates = [
        (pair(answer, repeat_diff),
         f"Suku ketujuh sudah tepat, tetapi suku kedelapan {_fmt(repeat_diff)} "
         f"diperoleh dengan mengulangkan selisih suku ketujuh dan keenam "
         f"({_fmt(answer - terms[-1])}), seolah-olah selisih deret ini tetap."),
        # NB: this value is NOT the ninth term (the pattern's next difference is
        # generally larger), so the reason must describe the arithmetic that
        # produces it rather than claim a position in the sequence
        (pair(answer, overshoot),
         f"Suku ketujuh sudah tepat, tetapi bilangan kedua {_fmt(overshoot)} "
         f"diperoleh dengan menambahkan selisih {_fmt(answer2 - answer)} pada suku "
         f"kedelapan {_fmt(answer2)}, yaitu mengulangi selisih suku ketujuh ke "
         f"kedelapan alih-alih berhenti pada suku kedelapan."),
    ]
    # the 7th term already fails, so the reason for it settles the pair
    seconds = [answer2, answer2 + (answer2 - answer), answer2 - (answer2 - answer)]
    for i, (value, reason) in enumerate(wrongs):
        if value in terms or value in weak_predictions(terms) or value == answer:
            continue
        candidates.append((
            pair(value, seconds[i % len(seconds)]),
            f"Suku ketujuh {_fmt(value)} diperoleh dengan {reason}, sehingga "
            f"pasangan ini keliru sejak bilangan pertamanya.",
        ))

    seen, distractors = {correct}, []
    for text, reason in candidates:
        if text in seen:
            continue
        seen.add(text)
        distractors.append((text, reason))
    stem = (", ".join(_fmt(t) for t in terms)
            + ", ..., ... Dua bilangan yang tepat untuk melanjutkan deret tersebut "
              "adalah ...")
    explanation = (f"{expl_correct} Dengan pola yang sama, suku kedelapan adalah "
                   f"{_fmt(answer2)}.")
    return stem, correct, distractors, explanation


def interior_unambiguous(terms: list[int], answer: int) -> bool:
    """Screening for the anchored stem, whose printed evidence is different.

    Only four consecutive terms are visible, so more rival rules fit them than
    fit a six-term stem — but a rival only makes the item ambiguous if, run
    three steps on, it *also* lands on the printed anchor while passing through
    different hidden terms. That is the whole job the anchor does.
    """
    for rule in RIVAL_RULES:
        seq = terms[:4]
        for _ in range(3):
            nxt = rule(seq)
            if nxt is None:
                break
            seq = seq + [nxt]
        else:
            if seq[-1] == answer and (seq[4], seq[5]) != (terms[4], terms[5]):
                return False
    return True


def _interior_blanks(terms, answer, extra_wrongs, expl_correct):
    """Option set for `−9, −10, −8, −24, ..., ..., −138`.

    Four terms, two blanks, then one more term printed as an anchor. Harder than
    the tail stems in the way the official sets are hard: the rule has to be
    inferred from less evidence, and the anchor is there to be *checked against*
    rather than continued — a reader who never uses it cannot tell a near-miss
    rule from the right one.
    """
    def pair(a, b):
        return f"{_fmt(a)}, {_fmt(b)}"

    shown, t5, t6 = terms[:4], terms[4], terms[5]
    correct = pair(t5, t6)

    candidates = [(pair(a, b), reason) for (a, b), reason in extra_wrongs]

    # Generic misreadings, true of any sequence and used to fill the option set
    # when the pattern supplies fewer than four of its own.
    d = shown[3] - shown[2]
    candidates.append((
        pair(shown[3] + d, shown[3] + 2 * d),
        f"menganggap selisih deret tetap sebesar selisih dua suku tercetak terakhir "
        f"({_fmt(d)}), yang tidak membawa deret sampai ke suku terakhir",
    ))
    candidates.append((
        pair(t6, answer),
        "menggeser jawaban satu suku, sehingga titik-titik diisi dengan suku keenam dan "
        "suku ketujuh — padahal suku ketujuh sudah tercetak",
    ))
    candidates.append((
        pair(t6, t5),
        "menemukan kedua bilangan dengan benar tetapi menuliskannya terbalik",
    ))
    # the two classic misreadings: a second-difference climb, and two
    # interleaved sequences — both fit the four printed terms and both miss
    d1, dd = shown[2] - shown[1], (shown[3] - shown[2]) - (shown[2] - shown[1])
    candidates.append((
        pair(shown[3] + d + dd, shown[3] + 2 * d + 3 * dd),
        f"membaca deret ini sebagai pola tingkat dua, yaitu selisih yang bertambah "
        f"tetap {_fmt(dd)} setiap langkah",
    ))
    candidates.append((
        pair(shown[2] + (shown[2] - shown[0]), shown[3] + (shown[3] - shown[1])),
        "membaca deret ini sebagai dua deret berselang-seling, masing-masing dilanjutkan "
        "dari suku sejenisnya",
    ))
    if shown[2] != 0 and Fraction(shown[3], shown[2]).denominator == 1:
        r = shown[3] // shown[2]
        candidates.append((
            pair(shown[3] * r, shown[3] * r * r),
            f"menganggap deret ini dikalikan tetap dengan {_fmt(r)}, rasio dua suku "
            f"tercetak terakhir",
        ))

    seen, distractors = {correct}, []
    for text, reason in candidates:
        if text in seen:
            continue
        seen.add(text)
        distractors.append((text, f"Pasangan ini diperoleh dengan {reason}."))

    stem = (", ".join(_fmt(t) for t in shown)
            + f", ..., ..., {_fmt(answer)} Dua bilangan yang tepat untuk mengisi "
              "titik-titik tersebut berturut-turut adalah ...")
    explanation = (
        f"{expl_correct} Dua bilangan yang hilang adalah {_fmt(t5)} dan {_fmt(t6)}; "
        f"suku terakhir yang tercetak ({_fmt(answer)}) mengonfirmasi pola tersebut."
    )
    return stem, correct, distractors, explanation


def build_one(rng: random.Random, package_id: int, number: int, bank_dir: Path,
              pattern, blanks: int = 1, interior: bool = False) -> Path:
    """Draw from `pattern` until a clean, unambiguous item comes out, then write it."""
    for _ in range(200):
        drawn = pattern(rng)
        terms, answer, answer2, wrongs, expl_correct, difficulty = drawn[:6]
        # a pattern may add its own interior-blank misreadings as a 7th element
        interior_wrongs = drawn[6] if len(drawn) > 6 else []

        if interior:
            if not interior_unambiguous(terms, answer):
                continue
            # two identical hidden terms would make the swapped-order distractor
            # the same pair as the key
            if terms[4] == terms[5]:
                continue
            stem, correct_text, distractors, explanation = _interior_blanks(
                terms, answer, interior_wrongs, expl_correct
            )
            difficulty = "hard"
        else:
            if not is_unambiguous(terms, answer):
                continue
            if answer in terms:
                continue  # an answer already printed in the stem reads as a misprint
            # a two-blank stem prints one more term of evidence, so the 8th term must
            # survive the same screening once the 7th is taken as given
            if blanks == 2 and not is_unambiguous(terms + [answer], answer2):
                continue
            layout = _single_blank if blanks == 1 else _double_blank
            stem, correct_text, distractors, explanation = layout(
                terms, answer, answer2, wrongs, expl_correct
            )
            if blanks == 2:
                difficulty = "hard"
        if len(distractors) < 4:
            continue

        values = [(correct_text, None)] + distractors[:4]
        rng.shuffle(values)
        correct_key = "ABCDE"[[t for t, _ in values].index(correct_text)]

        options, explanations = [], {}
        for key, (text, reason) in zip("ABCDE", values):
            options.append((key, text))
            explanations[key] = (f"Benar. {explanation}" if reason is None
                                 else f"Salah. {reason}")

        q = make_question(
            package_id=package_id,
            subtest=SUBTEST,
            number=number,
            qtype=QTYPE,
            question_text=stem,
            options=options,
            correct_option=correct_key,
            explanations=explanations,
            difficulty=difficulty,
            source="deret_angka.py",
        )
        return write_question(q, bank_dir)
    raise RuntimeError(f"{pattern.__name__}: no clean draw after 200 attempts")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=int, required=True)
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--blanks", type=int, choices=[1, 2], default=1,
                    help="1 = ask for the next term; 2 = ask for the next two")
    ap.add_argument("--interior", action="store_true",
                    help="hardest stem: four terms, two blanks, then one more term "
                         "printed as an anchor to check the rule against")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    groups = INTERIOR_GROUPS if args.interior else PATTERN_GROUPS
    pool: list = []
    for _ in range(args.count):
        if not pool:  # without replacement, and one draw per solving method
            pool = groups[:]
            rng.shuffle(pool)
        number = next_number(args.package, SUBTEST, args.bank_dir)
        path = build_one(rng, args.package, number, args.bank_dir,
                         rng.choice(pool.pop()), args.blanks, args.interior)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
