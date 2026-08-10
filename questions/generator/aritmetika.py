#!/usr/bin/env python3
"""Deterministic generator for `aritmetika` and `perbandingan_kuantitatif`
questions. Answer keys are computed, never guessed.

Design rules enforced here:

* Every distractor is produced as a ``(value, reason)`` pair, so each "Salah."
  explanation names the specific mistake that yields *that* option. A generic
  "this does not match the calculation" is not an explanation.
* Templates are drawn without replacement, so one package never ships the same
  computation twice with different numbers.
* Operands are constrained to values that render exactly in Indonesian notation
  (denominator dividing 100) — no repeating decimals, no fraction that silently
  reduces to a whole number. A pattern whose working belongs in fractions rather
  than decimals overrides that test by returning its own (see
  `gen_fraction_order_of_ops`, where 23/18 is the right kind of answer).
* `perbandingan_kuantitatif` includes an indeterminate case, so option D is a
  live answer rather than a permanently wrong one, and its fifth option is a
  substantive claim that has to be computed to be rejected.

Usage:
    python3 aritmetika.py --package 1 --count 6 --type aritmetika [--seed 7]
    python3 aritmetika.py --package 1 --count 5 --type perbandingan_kuantitatif
"""

from __future__ import annotations

import argparse
import math
import random
from fractions import Fraction
from pathlib import Path

from common import (
    BANK_DIR,
    MINUS,
    fmt_number,
    make_question,
    next_number,
    write_question,
)

SUBTEST = "kuantitatif"

_fmt = fmt_number


def _rupiah(value) -> str:
    return f"Rp{fmt_number(value)},00"


def _sentence_case(work: str) -> str:
    """Capitalise a worked step, leaving single-letter maths symbols alone.

    Upper-casing blindly rewrites `a : b = 5 : 4` into `A : b = 5 : 4`, which
    renames the variable (and collides with the option keys).
    """
    head = work.split(" ", 1)[0]
    if len(head) > 1 and head[0].isalpha():
        return work[0].upper() + work[1:]
    return work


# ---------------------------------------------------------------- aritmetika
# Each pattern returns (text, answer, [(wrong, reason), ...], work, difficulty, fmt),
# optionally followed by a predicate deciding which values print acceptably.

def gen_percent(rng: random.Random):
    base = rng.choice([120, 150, 200, 240, 300, 360, 400, 480, 500, 600, 750, 800])
    pct = rng.choice([5, 10, 12, 15, 20, 25, 30, 40, 60, 75])
    answer = Fraction(pct * base, 100)
    text = f"{pct}% dari {_fmt(base)} adalah ..."
    work = f"{pct}% × {_fmt(base)} = ({pct}/100) × {_fmt(base)} = {_fmt(answer)}"
    wrongs = [
        (answer * 10, "menggeser koma desimal satu tempat ke kanan"),
        (answer / 10, "menggeser koma desimal satu tempat ke kiri"),
        (Fraction(base - pct), f"mengurangkan {pct} dari {_fmt(base)} alih-alih "
                               "menghitung persentasenya"),
        (Fraction(base) - answer, f"menghitung sisanya, yaitu bagian {100 - pct}%"),
    ]
    return text, answer, wrongs, work, "easy", _fmt


def gen_percent_of_remainder(rng: random.Random):
    """Two chained percentages — the second applies to the survivors of the first."""
    total = rng.choice([400, 500, 600, 800, 1_200, 1_500, 2_000])
    p = rng.choice([20, 25, 40, 50, 60, 75])
    # p + q == 100 makes the "added the percentages" distractor equal the total
    # printed in the stem, i.e. "all applicants passed" — self-refuting on sight
    q = rng.choice([v for v in (20, 25, 40, 50, 60) if v + p != 100])
    first = Fraction(total * p, 100)
    answer = first * Fraction(q, 100)
    text = (
        f"Dari {_fmt(total)} pelamar sebuah program beasiswa, {p}% dinyatakan lulus "
        f"seleksi administrasi. Dari pelamar yang lulus seleksi administrasi tersebut, "
        f"{q}% dinyatakan lulus seleksi wawancara. Berapa banyak pelamar yang lulus "
        f"kedua tahap seleksi itu?"
    )
    work = (
        f"lulus administrasi = {p}% × {_fmt(total)} = {_fmt(first)}; lulus wawancara = "
        f"{q}% × {_fmt(first)} = {_fmt(answer)}"
    )
    wrongs = [
        (Fraction(total * q, 100),
         f"menerapkan {q}% pada seluruh pelamar, bukan pada pelamar yang lulus "
         "seleksi administrasi"),
        (first, "berhenti pada tahap pertama dan tidak menerapkan seleksi kedua"),
        (Fraction(total * (p + q), 100),
         f"menjumlahkan kedua persentase menjadi {p + q}% lalu menerapkannya sekaligus"),
        # NB: `first − total·q/100` goes negative whenever q > p, i.e. a negative
        # number of applicants — dead on sight. Count the eliminated instead.
        (first - answer,
         "menghitung pelamar yang gugur pada seleksi wawancara, bukan yang lulus"),
    ]
    return text, answer, wrongs, work, "medium", _fmt


def gen_rate_proportion(rng: random.Random):
    """Unit rate, then scale it — two steps, not one lookup."""
    per_unit = rng.choice([12, 15, 18, 20, 24, 25])
    minutes = rng.choice([4, 5, 6, 8])
    sheets = per_unit * minutes
    target = rng.choice([m for m in (10, 12, 15, 18, 20, 24, 30) if m != minutes])
    answer = Fraction(per_unit * target)
    text = (
        f"Sebuah mesin fotokopi menghasilkan {_fmt(sheets)} lembar salinan dalam "
        f"{minutes} menit. Apabila kecepatannya tetap, berapa lembar salinan yang "
        f"dihasilkan mesin itu dalam {target} menit?"
    )
    work = (
        f"kecepatan mesin = {_fmt(sheets)} ÷ {minutes} = {_fmt(per_unit)} lembar per menit; "
        f"dalam {target} menit dihasilkan {_fmt(per_unit)} × {target} = {_fmt(answer)} lembar"
    )
    wrongs = [
        (Fraction(sheets * minutes, target),
         f"membalik perbandingan menjadi {_fmt(sheets)} × {minutes} ÷ {target}"),
        (Fraction(sheets * target),
         f"mengalikan {_fmt(sheets)} dengan {target} tanpa membaginya dengan {minutes} "
         "lebih dahulu"),
        (Fraction(sheets + (target - minutes)),
         f"menambahkan selisih waktu ({target} − {minutes}) pada banyaknya salinan"),
        (Fraction(per_unit * (target - minutes)),
         f"menghitung salinan untuk selisih waktunya saja, yaitu {target} − {minutes} menit"),
    ]
    return text, answer, wrongs, work, "medium", _fmt


def _as_fraction(f: Fraction) -> str:
    """Render exactly as a fraction — a decimal would hide the step being tested."""
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def gen_fraction_ops(rng: random.Random):
    # coprime denominators, so finding the common denominator is a real step
    # rather than one denominator dividing the other
    den_a, den_b = rng.choice([(2, 5), (5, 2), (4, 5), (5, 4), (2, 3), (3, 2),
                               (3, 4), (4, 3), (3, 5), (5, 3)])
    a = Fraction(rng.randint(1, den_a - 1), den_a)
    b = Fraction(rng.randint(1, den_b - 1), den_b)
    k = rng.choice([m for m in (10, 12, 15, 20, 30, 60) if m % (den_a * den_b) == 0]
                   or [den_a * den_b])
    answer = (a + b) * k
    a_s, b_s = _as_fraction(a), _as_fraction(b)
    text = f"Hasil dari ({a_s} + {b_s}) × {k} adalah ..."
    work = (f"({a_s} + {b_s}) × {k} = {_as_fraction(a + b)} × {k} = {_fmt(answer)}")
    wrongs = [
        (a + b * k, f"mengalikan hanya pecahan kedua dengan {k} sehingga sifat "
                    "distributif tidak diterapkan"),
        (a * k + b, f"mengalikan hanya pecahan pertama dengan {k}, lalu menambahkan "
                    f"{b_s} yang belum dikalikan"),
        ((a + b) + k, f"menambahkan {k} alih-alih mengalikannya"),
        (a * b * k, "mengalikan kedua pecahan, bukan menjumlahkannya lebih dahulu"),
    ]
    return text, answer, wrongs, work, "medium", _fmt


def _fraction_text(value) -> str:
    """A fraction the way an exam paper prints it: 23/18, 1, −5/6.

    Deliberately not `fmt_number`: an order-of-operations item is about precedence,
    and printing 1,28 in the option list would let a candidate reach for a
    calculator instead of the rule being tested.
    """
    f = Fraction(value)
    sign = MINUS if f < 0 else ""
    f = abs(f)
    return sign + (str(f.numerator) if f.denominator == 1
                   else f"{f.numerator}/{f.denominator}")


def _fraction_ok(value) -> bool:
    """Whether an option prints as a fraction anyone would write down."""
    return Fraction(value).denominator <= 60


def gen_fraction_order_of_ops(rng: random.Random):
    """a − b × c + [(d − e) : f] — precedence, a bracket, and dividing by a fraction.

    Four operations, and the arithmetic on each one is easy; what the item tests is
    the order they are done in and whether `:` by a unit fraction is recognised as
    multiplication by its reciprocal. Every distractor is one specific rule dropped
    and then carried through consistently, so the option a candidate lands on names
    the rule they lost: left-to-right instead of precedence, `:` read as ×, the
    bracket ignored, the bracket subtracted, the bracket's own sign flipped.
    """
    parts = [Fraction(1, 2), Fraction(1, 3), Fraction(2, 3), Fraction(3, 4),
             Fraction(1, 4), Fraction(2, 5), Fraction(3, 5), Fraction(5, 6)]
    a = rng.choice(parts)
    b, c = rng.choice(parts), rng.choice(parts)
    d, e = sorted(rng.sample(parts, 2), reverse=True)     # d > e keeps the bracket positive
    # A divisor equal to one of the operands it sits beside turns the "ignored the
    # bracket" explanation into "yang dibagi 1/3 hanya 1/3", which reads as a typo.
    f = Fraction(1, rng.choice([k for k in (3, 4, 5, 6, 8)
                                if Fraction(1, k) not in (d, e)]))

    product, bracket = b * c, (d - e) / f
    answer = a - product + bracket
    if answer in (0, a):
        # a result that lands back on 0 or on the first operand looks like the item
        # was built to cancel, and invites guessing instead of computing
        return gen_fraction_order_of_ops(rng)
    fr = _fraction_text
    text = (f"Hasil dari {fr(a)} − {fr(b)} × {fr(c)} + [({fr(d)} − {fr(e)}) : {fr(f)}] "
            f"adalah ...")
    work = (
        f"{fr(b)} × {fr(c)} = {fr(product)}; ({fr(d)} − {fr(e)}) : {fr(f)} = "
        f"{fr(d - e)} × {fr(1 / f)} = {fr(bracket)}; "
        f"{fr(a)} − {fr(product)} + {fr(bracket)} = {fr(answer)}"
    )
    wrongs = [
        ((a - b) * c + bracket,
         f"mengerjakan operasi dari kiri ke kanan, yaitu ({fr(a)} − {fr(b)}) × {fr(c)}, "
         "sehingga perkalian tidak didahulukan"),
        (a - product + (d - e) * f,
         f"mengalikan isi kurung dengan {fr(f)} alih-alih membaginya"),
        (a - product + d - e / f,
         f"mengabaikan tanda kurung sehingga yang dibagi {fr(f)} hanya {fr(e)}"),
        (a - product - bracket,
         "mengurangkan hasil dalam kurung siku, bukan menambahkannya"),
        (a - product + (d + e) / f,
         f"menjumlahkan {fr(d)} dan {fr(e)} di dalam kurung, bukan mengurangkannya"),
    ]
    # Real option lists for this format sit in a tight band — 5/18, 9/10, 1, 10/9,
    # 23/18 — and one value an order of magnitude off is struck out on sight
    # without any arithmetic, which costs the item a distractor.
    wrongs = [(v, why) for v, why in wrongs if abs(v - answer) <= 3]
    return text, answer, wrongs, work, "hard", fr, _fraction_ok


def gen_mixed_ops(rng: random.Random):
    a, b, c, d = (rng.randint(4, 30) for _ in range(4))
    answer = Fraction(a * b - c * d)
    text = f"Nilai dari {a} × {b} − {c} × {d} adalah ..."
    work = f"{a} × {b} − {c} × {d} = {_fmt(a * b)} − {_fmt(c * d)} = {_fmt(answer)}"
    # Distractors stay within the same order of magnitude as the answer:
    # reintroducing a factor (e.g. (a×b − c) × d) yields values tens of times
    # larger, which a candidate discards on sight without doing the sum.
    wrongs = [
        (-answer, "membalik urutan pengurangan sehingga tandanya tertukar"),
        (Fraction(a * d - c * b),
         f"menukar faktor kedua pada masing-masing perkalian, yaitu {a} × {d} − {c} × {b}"),
        (Fraction(a * b + c * d),
         "menjumlahkan kedua hasil kali, bukan mengurangkannya"),
        (Fraction(a * b - (c + d)),
         f"mengurangkan jumlah {c} dan {d}, bukan hasil kalinya"),
    ]
    return text, answer, wrongs, work, "medium", _fmt


def gen_percent_change(rng: random.Random):
    price = rng.choice([200_000, 400_000, 500_000, 600_000, 800_000, 1_200_000])
    up, down = rng.sample([10, 20, 25, 40, 50], 2)
    after_up = Fraction(price * (100 + up), 100)
    answer = after_up * Fraction(100 - down, 100)
    text = (
        f"Harga sebuah barang {_rupiah(price)} dinaikkan {up}%, kemudian harga baru "
        f"itu diturunkan {down}%. Berapakah harga barang setelah kedua perubahan tersebut?"
    )
    work = (
        f"harga setelah kenaikan = {_rupiah(price)} × {100 + up}/100 = {_rupiah(after_up)}; "
        f"harga setelah penurunan = {_rupiah(after_up)} × {100 - down}/100 = {_rupiah(answer)}"
    )
    wrongs = [
        (Fraction(price * (100 + up - down), 100),
         f"menjumlahkan langsung kedua persentase menjadi {up}% − {down}% dan "
         "menerapkannya pada harga awal"),
        (after_up, "berhenti setelah kenaikan dan tidak menerapkan penurunan"),
        (Fraction(price * (100 - down), 100),
         f"hanya menerapkan penurunan {down}% pada harga awal"),
        (Fraction(price),
         "menganggap kenaikan dan penurunan dengan persentase saling meniadakan"),
    ]
    return text, answer, wrongs, work, "medium", _rupiah


def gen_average(rng: random.Random):
    n = 4
    mean = rng.choice([12, 15, 18, 20, 24, 25])
    delta = rng.choice([1, 2, 3, 5])
    extra = mean + (n + 1) * delta
    total = n * mean
    answer = Fraction(mean + delta)
    text = (
        f"Rata-rata {n} bilangan adalah {mean}. Apabila bilangan {extra} ditambahkan "
        f"ke dalam kelompok tersebut, berapakah rata-rata {n + 1} bilangan itu?"
    )
    work = (
        f"jumlah semula = {n} × {mean} = {_fmt(total)}; jumlah baru = {_fmt(total)} + "
        f"{extra} = {_fmt(total + extra)}; rata-rata baru = {_fmt(total + extra)} ÷ "
        f"{n + 1} = {_fmt(answer)}"
    )
    wrongs = [
        (Fraction(mean + extra, 2),
         "merata-ratakan rata-rata lama dengan bilangan baru seolah-olah keduanya "
         "berbobot sama"),
        (Fraction(total + extra, n),
         f"membagi jumlah baru dengan {n}, yaitu banyaknya bilangan semula"),
        (Fraction(mean),
         "menganggap rata-rata tidak berubah oleh penambahan satu bilangan"),
        (Fraction(total, n + 1),
         f"membagi jumlah semula dengan {n + 1} tanpa menambahkan bilangan baru"),
    ]
    return text, answer, wrongs, work, "medium", _fmt


def gen_ratio(rng: random.Random):
    n1, n2 = rng.choice([(2, 5), (3, 5), (4, 5), (3, 4), (5, 4), (5, 2), (7, 10), (3, 10)])
    m = rng.choice([6, 8, 9, 12, 15, 18])
    a_val, answer = n1 * m, Fraction(n2 * m)
    text = (
        f"Diketahui a : b = {n1} : {n2}. Apabila a = {_fmt(a_val)}, "
        f"berapakah nilai b?"
    )
    work = (
        f"a : b = {n1} : {n2}, sehingga b = a × {n2}/{n1} = {_fmt(a_val)} × "
        f"{n2}/{n1} = {_fmt(answer)}"
    )
    wrongs = [
        (Fraction(a_val * n1, n2),
         f"membalik perbandingan sehingga menghitung {_fmt(a_val)} × {n1}/{n2}"),
        (Fraction(a_val * n2),
         f"mengalikan dengan {n2} tanpa membaginya dengan {n1}"),
        (Fraction((n1 + n2) * m),
         "menghitung jumlah a dan b, bukan nilai b saja"),
        (Fraction(m),
         f"berhenti pada faktor pengali perbandingan ({_fmt(a_val)} ÷ {n1}) "
         "dan tidak mengalikannya kembali"),
        (Fraction(a_val + (n2 - n1)),
         f"menambahkan selisih suku perbandingan ({n2} − {n1}) pada nilai a"),
    ]
    return text, answer, wrongs, work, "easy", _fmt


def gen_power_root(rng: random.Random):
    a = rng.choice([2, 3, 4, 5])
    # when root == 2a the "a³ read as a×3" distractor lands exactly on the base
    # already printed in the stem, which reads like a typo rather than an error
    sq = rng.choice([s for s in (64, 81, 100, 121, 144, 169, 196, 225)
                     if math.isqrt(s) != 2 * a])
    root = math.isqrt(sq)
    answer = Fraction(a**3 - root)
    text = f"Nilai dari {a}³ − √{sq} adalah ..."
    work = f"{a}³ = {_fmt(a**3)} dan √{sq} = {root}, sehingga {_fmt(a**3)} − {root} = {_fmt(answer)}"
    # both operands come from standard tables, so this never earns "hard"
    difficulty = "medium"
    wrongs = [
        (Fraction(a * 3 - root), f"menghitung {a}³ sebagai {a} × 3 = {_fmt(a * 3)}"),
        (Fraction(a**2 - root), f"menghitung pangkat tiga sebagai pangkat dua ({a}² = {_fmt(a**2)})"),
        (Fraction(a**3 + root), "menjumlahkan kedua nilai alih-alih mengurangkannya"),
        (Fraction(a**3) - Fraction(sq, 2),
         f"menghitung akar kuadrat sebagai setengah dari {sq}"),
    ]
    return text, answer, wrongs, work, difficulty, _fmt


# Single-step items are recall, not reasoning: at a 96-second-per-item budget an
# LPDP candidate answers them instantly, so at least half of each draw comes from
# the multi-step pool.
ARITMETIKA_MULTISTEP = [
    gen_percent_change,
    gen_average,
    gen_percent_of_remainder,
    gen_rate_proportion,
    gen_fraction_order_of_ops,
]

ARITMETIKA_SINGLE_STEP = [
    gen_percent,
    gen_fraction_ops,
    gen_mixed_ops,
    gen_ratio,
    gen_power_root,
]

ARITMETIKA_PATTERNS = ARITMETIKA_MULTISTEP + ARITMETIKA_SINGLE_STEP


def aritmetika_pool(rng: random.Random, count: int) -> list:
    """`count` distinct templates, at least half of them multi-step."""
    want_multi = min(len(ARITMETIKA_MULTISTEP), (count + 1) // 2)
    pool = (rng.sample(ARITMETIKA_MULTISTEP, want_multi)
            + rng.sample(ARITMETIKA_SINGLE_STEP,
                         min(len(ARITMETIKA_SINGLE_STEP), count - want_multi)))
    while len(pool) < count:  # only for counts beyond the template supply
        pool += rng.sample(ARITMETIKA_PATTERNS, min(count - len(pool), len(ARITMETIKA_PATTERNS)))
    rng.shuffle(pool)
    return pool


def _decimal_ok(value) -> bool:
    """Whether a value prints as a terminating decimal in Indonesian notation."""
    return 100 % Fraction(value).denominator == 0


def build_aritmetika(rng: random.Random, package_id: int, number: int, bank_dir: Path,
                     pattern) -> Path:
    for _ in range(200):
        # The last element is optional: a pattern that keeps its working in
        # fractions says so by supplying its own admissibility test, because the
        # default one — "must print as a terminating decimal" — would throw away
        # 23/18, which is exactly the kind of answer such an item is meant to have.
        drawn = pattern(rng)
        text, answer, wrongs, work, difficulty, fmt = drawn[:6]
        acceptable = drawn[6] if len(drawn) > 6 else _decimal_ok
        answer = Fraction(answer)
        scale_limit = 15 * max(abs(answer), 1)

        taken, distractors = {answer}, []
        for value, reason in wrongs:
            value = Fraction(value)
            if (value in taken                      # duplicate option
                    or not acceptable(value)        # would not print cleanly
                    or abs(value) > scale_limit):   # discardable on magnitude alone
                continue
            taken.add(value)
            distractors.append((value, reason))
        if len(distractors) < 4 or not acceptable(answer):
            continue

        values = [(answer, None)] + distractors[:4]
        rng.shuffle(values)
        correct_key = "ABCDE"[[v for v, _ in values].index(answer)]

        options, explanations = [], {}
        for key, (value, reason) in zip("ABCDE", values):
            options.append((key, fmt(value)))
            explanations[key] = (
                f"Benar. {_sentence_case(work)}." if reason is None
                else f"Salah. Nilai {fmt(value)} diperoleh dengan {reason}."
            )

        q = make_question(
            package_id=package_id,
            subtest=SUBTEST,
            number=number,
            qtype="aritmetika",
            question_text=text,
            options=options,
            correct_option=correct_key,
            explanations=explanations,
            difficulty=difficulty,
            source="aritmetika.py",
        )
        return write_question(q, bank_dir)
    raise RuntimeError(f"{pattern.__name__}: no clean draw after 200 attempts")


# ------------------------------------------------- perbandingan_kuantitatif
# Each kind returns (p_desc, q_desc, P, Q, difficulty). P/Q are None when the
# relation genuinely cannot be determined; the kind then supplies witnesses.

_USED_COEFFICIENTS: set[tuple[int, int]] = set()
_USED_CLAIMS: set[str] = set()  # fifth-option templates already spent in this package


def pk_percent_vs_fraction(rng: random.Random):
    base = rng.choice([80, 120, 160, 200, 240, 300])
    pct = rng.choice([20, 25, 40, 50, 60, 75])
    den = rng.choice([2, 4, 5, 8])
    num = rng.randint(1, den - 1)
    return (f"P = {pct}% dari {base}", f"Q = {num}/{den} dari {base}",
            Fraction(pct * base, 100), Fraction(num * base, den), "easy", "")


SUPERSCRIPT = {2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶"}


def pk_power(rng: random.Random):
    a, b = rng.sample([2, 3, 4, 5], 2)
    return (f"P = {a}{SUPERSCRIPT[b]}", f"Q = {b}{SUPERSCRIPT[a]}",
            Fraction(a**b), Fraction(b**a), "medium", "")


def pk_linear(rng: random.Random):
    x = rng.randint(2, 9)
    for _ in range(200):
        m1, m2 = rng.randint(2, 6), rng.randint(2, 6)
        # equal coefficients make P − Q constant, so the given x does no work
        if m1 != m2 and (m1, m2) not in _USED_COEFFICIENTS:
            break
    _USED_COEFFICIENTS.add((m1, m2))
    c1, c2 = rng.randint(-6, 10), rng.randint(-6, 10)

    def side(m, c):
        return f"{m}x − {abs(c)}" if c < 0 else (f"{m}x + {c}" if c else f"{m}x")

    return (f"Diketahui x = {x}.\nP = {side(m1, c1)}", f"Q = {side(m2, c2)}",
            Fraction(m1 * x + c1), Fraction(m2 * x + c2), "medium", "")


def pk_area(rng: random.Random):
    s = rng.choice([6, 8, 9, 10, 12])
    p = rng.choice([4, 6, 8, 12, 16, 18])
    q = rng.choice([4, 6, 8, 9, 12, 16])
    return (f"P = luas persegi yang panjang sisinya {s} cm",
            f"Q = luas persegi panjang berukuran {p} cm × {q} cm",
            Fraction(s * s), Fraction(p * q), "medium", " cm²")


def pk_indeterminate(rng: random.Random):
    for _ in range(200):
        m1 = rng.choice([2, 3, 4])
        m2 = rng.choice([m for m in (3, 4, 5, 6) if m > m1])  # Q must overtake P
        if (m1, m2) not in _USED_COEFFICIENTS:
            break
    _USED_COEFFICIENTS.add((m1, m2))
    c = rng.choice([6, 8, 10, 12])
    return (f"Diketahui x adalah bilangan bulat positif.\nP = {m1}x + {c}",
            f"Q = {m2}x", None, None, "hard", (m1, c, m2))


def _false_claim(rng: random.Random, p_val: Fraction, q_val: Fraction, unit: str):
    """A substantive fifth option that is false but has to be computed to reject.

    A *true* claim here would give the item two correct answers, so every
    candidate is evaluated and only false ones are eligible; the template is
    varied so the fifth option cannot be dismissed on sight across a package.
    """
    gap, total = abs(p_val - q_val), p_val + q_val
    hi, lo = max(p_val, q_val), min(p_val, q_val)
    margin = rng.choice([5, 10, 20])
    candidates = [
        ("gap",
         f"Selisih antara P dan Q lebih besar daripada {_fmt(gap + margin)}{unit}",
         f"selisihnya {_fmt(gap)}{unit}, tidak lebih besar daripada "
         f"{_fmt(gap + margin)}{unit}"),
    ]
    # a threshold that undershoots the sum by more than half (or goes negative)
    # is rejected on sight instead of by computing, so keep it plausible
    if total > 0 and margin * 2 <= total:
        candidates.append((
            "total",
            f"Jumlah P dan Q kurang daripada {_fmt(total - margin)}{unit}",
            f"jumlahnya {_fmt(total)}{unit}, tidak kurang daripada {_fmt(total - margin)}{unit}",
        ))
    if lo and hi < 2 * lo:  # only offer this when it is genuinely false
        bigger, smaller = ("P", "Q") if p_val > q_val else ("Q", "P")
        candidates.append((
            "double",
            f"{bigger} bernilai lebih dari dua kali {smaller}",
            f"dua kali {smaller} adalah {_fmt(2 * lo)}{unit}, sedangkan {bigger} hanya "
            f"{_fmt(hi)}{unit}",
        ))
    # name the value that actually fails: "at least one of them" understates the
    # common case where neither is odd, and reads as hedging
    odd = [name for name, v in (("P", p_val), ("Q", q_val))
           if v.denominator == 1 and v.numerator % 2]
    if len(odd) < 2:
        if not odd:
            why = "keduanya bukan bilangan ganjil"
        else:
            why = f"{'Q' if odd[0] == 'P' else 'P'} bukan bilangan ganjil"
        candidates.append((
            "parity",
            "P dan Q keduanya merupakan bilangan ganjil",
            why,
        ))
    fresh = [c for c in candidates if c[0] not in _USED_CLAIMS] or candidates
    name, text, why = rng.choice(fresh)
    _USED_CLAIMS.add(name)
    return text, why


PK_KINDS = [pk_percent_vs_fraction, pk_power, pk_linear, pk_area, pk_indeterminate]


def build_perbandingan(rng: random.Random, package_id: int, number: int, bank_dir: Path,
                       kind) -> Path:
    p_desc, q_desc, p_val, q_val, difficulty, extra_info = kind(rng)

    base_options = [
        ("A", "P lebih besar daripada Q"),
        ("B", "Q lebih besar daripada P"),
        ("C", "P sama dengan Q"),
        ("D", "Hubungan P dan Q tidak dapat ditentukan dari informasi yang diberikan"),
    ]

    if p_val is None:  # indeterminate case — D is the key
        m1, c, m2 = extra_info
        small, big = 1, c + 1  # witnesses on either side of the crossing point
        p_small, q_small = m1 * small + c, m2 * small
        p_big, q_big = m1 * big + c, m2 * big
        if not (p_small > q_small and p_big < q_big):
            raise RuntimeError("indeterminate kind failed to straddle the crossing point")
        correct_key = "D"
        extra = ("Nilai P dan Q tidak dapat dihitung untuk nilai x mana pun",
                 "Salah. Begitu sebuah nilai x dipilih, P dan Q langsung dapat dihitung; "
                 "yang tidak dapat ditentukan adalah hubungan keduanya secara umum.")
        witness = (
            f"untuk x = {small} diperoleh P = {_fmt(p_small)} dan Q = {_fmt(q_small)} "
            f"sehingga P > Q, sedangkan untuk x = {big} diperoleh P = {_fmt(p_big)} "
            f"dan Q = {_fmt(q_big)} sehingga Q > P"
        )
        explanations = {
            "A": f"Salah. P tidak selalu lebih besar: {witness}.",
            "B": f"Salah. Q tidak selalu lebih besar: {witness}.",
            "C": f"Salah. Kedua besaran tidak selalu sama: {witness}.",
            "D": f"Benar. Hubungan P dan Q bergantung pada nilai x — {witness} — sehingga "
                 "tidak ada satu hubungan yang berlaku untuk seluruh bilangan bulat positif.",
            "E": extra[1],
        }
    else:
        unit = extra_info
        correct_key = "A" if p_val > q_val else ("B" if p_val < q_val else "C")
        work = f"P = {_fmt(p_val)}{unit} dan Q = {_fmt(q_val)}{unit}"
        verdict = {"A": "sehingga P > Q", "B": "sehingga Q > P", "C": "sehingga P = Q"}[correct_key]
        claim_text, claim_why = _false_claim(rng, p_val, q_val, unit)
        extra = (claim_text, f"Salah. {work}, {claim_why}.")

        # each wrong relation is refuted by the comparison it actually gets wrong,
        # never by a shared filler sentence
        refutation = {
            "A": f"nilai P tidak melebihi nilai Q ({_fmt(p_val)}{unit} "
                 f"tidak lebih besar daripada {_fmt(q_val)}{unit})",
            "B": f"nilai Q tidak melebihi nilai P ({_fmt(q_val)}{unit} "
                 f"tidak lebih besar daripada {_fmt(p_val)}{unit})",
            "C": f"kedua nilai tidak sama ({_fmt(p_val)}{unit} ≠ {_fmt(q_val)}{unit})",
        }
        explanations = {
            k: (f"Benar. {work}, {verdict}." if k == correct_key
                else f"Salah. {work}, {verdict}; {refutation[k]}.")
            for k in ("A", "B", "C")
        }
        explanations["D"] = (
            f"Salah. Kedua besaran dapat dihitung pasti dari informasi yang diberikan "
            f"({work}), sehingga hubungannya dapat ditentukan."
        )
        explanations["E"] = extra[1]

    q = make_question(
        package_id=package_id,
        subtest=SUBTEST,
        number=number,
        qtype="perbandingan_kuantitatif",
        question_text=(
            f"Perhatikan dua besaran berikut.\n{p_desc}\n{q_desc}\n"
            "Manakah pernyataan yang benar mengenai hubungan P dan Q?"
        ),
        options=base_options + [("E", extra[0])],
        correct_option=correct_key,
        explanations=explanations,
        difficulty=difficulty,
        source="aritmetika.py",
    )
    return write_question(q, bank_dir)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=int, required=True)
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--type", choices=["aritmetika", "perbandingan_kuantitatif"],
                    default="aritmetika")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    _USED_COEFFICIENTS.clear()
    _USED_CLAIMS.clear()

    if args.type == "aritmetika":
        pool, build = aritmetika_pool(rng, args.count), build_aritmetika
    else:
        pool, build = PK_KINDS[:], build_perbandingan
        rng.shuffle(pool)

    for _ in range(args.count):
        if not pool:  # only when the count exceeds the template supply
            pool = (aritmetika_pool(rng, args.count) if args.type == "aritmetika"
                    else PK_KINDS[:])
            rng.shuffle(pool)
        number = next_number(args.package, SUBTEST, args.bank_dir)
        path = build(rng, args.package, number, args.bank_dir, pool.pop())
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
