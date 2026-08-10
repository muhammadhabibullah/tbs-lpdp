#!/usr/bin/env python3
"""Deterministic generator for `peluang_kombinatorik` (probability and counting).

This type is why the deterministic generators exist. Two of the sample items
collected from public LPDP tip sites are keyed wrongly — a "one red and one blue
out of 6 red, 4 blue, 10 green" item keyed 2/15 when the answer is 24/C(20,2) =
12/95, and a "split four sweets between two friends" item keyed 12 when the
answer is C(4,2) = 6. Both are the kind of slip nobody catches by re-reading;
they are caught by computing. Every key here comes from `math.comb` / `factorial`
applied to the same construction that produced the stem.

Two further rules, shared with the other generators:

* Distractors are ``(value, reason)`` pairs. Each one is a *named* mistake —
  counting ordered pairs when the draw is simultaneous, using n² as the sample
  space, adding two choices that should be multiplied — so the "Salah."
  explanation says what the candidate did, not merely that they are wrong.
* Probabilities print as reduced fractions, never as decimals: `fmt_number`
  would render 1/4 as "0,25", which is not how an exam paper writes a
  probability.

The type is allowed in both `kuantitatif` and `pemecahan_masalah`; pass
`--subtest` to choose where the items land.

Usage:
    python3 peluang_kombinatorik.py --package 1 --count 2 \
        [--subtest pemecahan_masalah] [--seed 7] [--bank-dir PATH]
"""

from __future__ import annotations

import argparse
import random
from fractions import Fraction
from math import comb, factorial, perm
from pathlib import Path

from common import BANK_DIR, MINUS, fmt_number, make_question, next_number, write_question

QTYPE = "peluang_kombinatorik"

_fmt = fmt_number


def _frac(value) -> str:
    """Render a probability the way an exam paper does: a reduced fraction."""
    f = Fraction(value)
    return _fmt(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def _reduce_step(num: int, den: int) -> str:
    """Show the reduction only when there is one: '24/190 = 12/95', else '5/36'."""
    raw, reduced = f"{num}/{den}", _frac(Fraction(num, den))
    return raw if raw == reduced else f"{raw} = {reduced}"


# ------------------------------------------------------------------ patterns
# Each returns (text, answer, [(wrong, reason), ...], work, difficulty, render).

def gen_two_colour_draw(rng: random.Random):
    """Two marbles drawn at once; asks for one of each of two named colours."""
    red, blue, green = rng.randint(4, 8), rng.randint(3, 6), rng.randint(5, 12)
    total = red + blue + green
    ways = comb(total, 2)
    answer = Fraction(red * blue, ways)
    text = (
        f"Sebuah kantong berisi {red} kelereng merah, {blue} kelereng biru, dan "
        f"{green} kelereng hijau. Apabila diambil dua kelereng sekaligus secara "
        f"acak, peluang terambil satu kelereng merah dan satu kelereng biru "
        f"adalah ..."
    )
    work = (
        f"Banyak cara mengambil 2 kelereng dari {total} kelereng adalah "
        f"C({total}, 2) = {ways}. Banyak cara memilih satu merah dan satu biru "
        f"adalah {red} × {blue} = {red * blue}. Peluangnya "
        f"{_reduce_step(red * blue, ways)}"
    )
    wrongs = [
        (Fraction(2 * red * blue, ways),
         "menghitung pasangan merah-biru dan biru-merah sebagai dua hasil berbeda, "
         "padahal kedua kelereng diambil sekaligus sehingga urutannya tidak dibedakan"),
        (Fraction(red * blue, total * total),
         f"memakai {total}² sebagai banyak hasil yang mungkin, yaitu pengambilan "
         f"dua kali dengan pengembalian dan memperhatikan urutan"),
        (Fraction(red + blue, total),
         "menghitung peluang terambil satu kelereng berwarna merah atau biru pada "
         "satu kali pengambilan"),
        (Fraction(comb(red, 2) + comb(blue, 2), ways),
         "menghitung peluang kedua kelereng sama-sama merah atau sama-sama biru, "
         "bukan satu merah dan satu biru"),
        (Fraction(red * blue, comb(red + blue, 2)),
         f"mengabaikan {green} kelereng hijau ketika menghitung banyak cara "
         f"pengambilan"),
    ]
    return text, answer, wrongs, work, "hard", _frac


def gen_at_least_one(rng: random.Random):
    """The complement trap: 'at least one' is not 'exactly one'."""
    red = rng.randint(3, 6)
    other = rng.randint(5, 9)
    total = red + other
    ways = comb(total, 2)
    answer = 1 - Fraction(comb(other, 2), ways)
    text = (
        f"Sebuah kotak berisi {red} bola merah dan {other} bola putih. Apabila "
        f"diambil dua bola sekaligus secara acak, peluang terambil sekurang-kurangnya "
        f"satu bola merah adalah ..."
    )
    work = (
        f"Peluang tidak ada bola merah yang terambil adalah C({other}, 2) : "
        f"C({total}, 2) = {_reduce_step(comb(other, 2), ways)}. Peluang "
        f"sekurang-kurangnya satu bola merah adalah komplemennya, yaitu "
        f"1 {MINUS} {_frac(Fraction(comb(other, 2), ways))} = {_frac(answer)}"
    )
    wrongs = [
        (Fraction(comb(other, 2), ways),
         "menghitung peluang tidak ada bola merah yang terambil, yaitu justru "
         "komplemen dari yang ditanyakan"),
        (Fraction(red * other, ways),
         "menghitung peluang tepat satu bola merah dan mengabaikan kemungkinan "
         "kedua bola berwarna merah"),
        (Fraction(comb(red, 2), ways),
         "menghitung peluang kedua bola berwarna merah, padahal yang diminta "
         "sekurang-kurangnya satu"),
        (2 * Fraction(red, total),
         "menjumlahkan peluang merah pada pengambilan pertama dan kedua, sehingga "
         "kejadian kedua bola merah terhitung dua kali"),
        (Fraction(red, total),
         "menghitung peluang untuk satu kali pengambilan saja"),
    ]
    return text, answer, wrongs, work, "hard", _frac


def gen_committee(rng: random.Random):
    """A committee with a composition constraint — counted, not guessed."""
    men, women = rng.randint(5, 8), rng.randint(4, 7)
    size = rng.randint(3, 4)
    j = rng.randint(1, size - 1)  # exactly j women
    answer = comb(women, j) * comb(men, size - j)
    text = (
        f"Sebuah panitia beranggotakan {size} orang akan dibentuk dari {men} calon "
        f"laki-laki dan {women} calon perempuan. Apabila panitia harus memuat tepat "
        f"{j} orang perempuan, banyak susunan panitia yang mungkin adalah ..."
    )
    work = (
        f"Memilih {j} perempuan dari {women} calon dapat dilakukan dengan "
        f"C({women}, {j}) = {comb(women, j)} cara, dan memilih {size - j} laki-laki "
        f"dari {men} calon dengan C({men}, {size - j}) = {comb(men, size - j)} cara. "
        f"Keduanya dipilih bersamaan, sehingga banyak susunan adalah "
        f"{comb(women, j)} × {comb(men, size - j)} = {answer}"
    )
    wrongs = [
        (comb(men + women, size),
         f"menghitung seluruh cara memilih {size} orang dari {men + women} calon "
         f"tanpa memperhatikan syarat banyak perempuan"),
        (comb(women, j) + comb(men, size - j),
         "menjumlahkan kedua pilihan, padahal keduanya dilakukan bersamaan sehingga "
         "banyak caranya dikalikan"),
        (perm(women, j) * comb(men, size - j),
         "memperhatikan urutan ketika memilih anggota perempuan, padahal susunan "
         "panitia tidak membedakan urutan"),
        (comb(women, size - j) * comb(men, j),
         f"menukar syaratnya menjadi {size - j} perempuan dan {j} laki-laki"),
    ]
    return text, Fraction(answer), wrongs, work, "medium", _fmt


def gen_arrangement_together(rng: random.Random):
    """n people in a row with two of them adjacent — the 'glue them' trick."""
    n = rng.randint(5, 7)
    answer = 2 * factorial(n - 1)
    text = (
        f"Sebanyak {n} orang peserta akan duduk berjajar pada {n} kursi. Apabila "
        f"dua orang di antaranya harus selalu duduk berdampingan, banyak susunan "
        f"tempat duduk yang mungkin adalah ..."
    )
    work = (
        f"Kedua orang yang harus berdampingan dipandang sebagai satu blok, sehingga "
        f"tersisa {n - 1} objek yang dapat disusun dalam {n - 1}! = "
        f"{factorial(n - 1)} cara. Di dalam blok, kedua orang itu dapat bertukar "
        f"tempat dalam 2 cara, sehingga seluruhnya 2 × {factorial(n - 1)} = {answer}"
    )
    wrongs = [
        (factorial(n),
         f"menghitung seluruh susunan {n} orang tanpa syarat kedua orang itu "
         f"berdampingan"),
        (factorial(n - 1),
         "memandang kedua orang itu sebagai satu blok tetapi lupa bahwa di dalam "
         "blok keduanya masih dapat bertukar tempat"),
        (2 * factorial(n),
         f"mengalikan seluruh susunan {n} orang dengan 2, padahal penggabungan "
         f"menjadi satu blok lebih dahulu mengurangi banyak objek menjadi {n - 1}"),
        (factorial(n) - 2 * factorial(n - 1),
         "menghitung banyak susunan ketika kedua orang itu justru tidak berdampingan"),
    ]
    return text, Fraction(answer), wrongs, work, "medium", _fmt


def gen_split_equally(rng: random.Random):
    """Split 2k distinct items between two named friends, k each."""
    k = rng.randint(2, 4)
    total = 2 * k
    answer = comb(total, k)
    text = (
        f"Rani memiliki {total} jenis permen yang berbeda dan akan membagikan "
        f"seluruhnya kepada dua orang temannya. Apabila setiap teman harus menerima "
        f"{k} permen, banyak cara pembagian yang mungkin adalah ..."
    )
    work = (
        f"Cukup memilih {k} permen untuk teman pertama; sisanya otomatis menjadi "
        f"bagian teman kedua. Banyak caranya adalah C({total}, {k}) = {answer}"
    )
    wrongs = [
        (perm(total, k),
         f"memperhatikan urutan ketika memilih {k} permen untuk teman pertama, "
         f"padahal permen yang diterima tidak berurutan"),
        (comb(total, k) // 2,
         "membagi hasilnya dengan 2 seolah-olah kedua teman tidak dibedakan, "
         "padahal keduanya orang yang berbeda"),
        (factorial(total),
         f"menghitung seluruh urutan {total} permen, bukan pembagiannya menjadi "
         f"dua kelompok"),
        (2 ** total,
         "menganggap setiap permen bebas diberikan kepada salah satu dari dua "
         f"teman, tanpa syarat masing-masing menerima {k} permen"),
    ]
    return text, Fraction(answer), wrongs, work, "medium", _fmt


def gen_dice_sum(rng: random.Random):
    """Two dice — the sample space is 36 ordered pairs, not 21 unordered ones."""
    s = rng.choice([5, 6, 7, 8, 9, 10])
    pairs = [(a, b) for a in range(1, 7) for b in range(1, 7) if a + b == s]
    count = len(pairs)
    distinct = len({frozenset((a, b)) for a, b in pairs})
    at_most = sum(1 for a in range(1, 7) for b in range(1, 7) if a + b <= s)
    answer = Fraction(count, 36)
    text = (
        f"Dua buah dadu setimbang dilempar bersama-sama satu kali. Peluang jumlah "
        f"mata dadu yang muncul sama dengan {s} adalah ..."
    )
    work = (
        f"Ruang sampelnya memuat 6 × 6 = 36 pasangan terurut. Pasangan yang "
        f"berjumlah {s} ada {count}, sehingga peluangnya {_reduce_step(count, 36)}"
    )
    wrongs = [
        (Fraction(count, 21),
         "memakai 21 sebagai banyak hasil yang mungkin, yaitu banyak pasangan mata "
         "dadu tanpa memperhatikan urutan"),
        (Fraction(count, 12),
         "memakai 12 sebagai banyak hasil yang mungkin, yaitu jumlah kedua sisi "
         "dadu, bukan banyak pasangan yang mungkin"),
        (Fraction(distinct, 36),
         f"hanya menghitung {distinct} pasangan nilai yang berbeda dan mengabaikan "
         f"bahwa pasangan seperti (1, 2) dan (2, 1) merupakan dua hasil berbeda"),
        (Fraction(1, 6),
         "menganggap setiap kemungkinan jumlah mata dadu berpeluang sama seperti "
         "satu sisi dadu, padahal jumlah 7 jauh lebih sering muncul daripada 2"),
        (Fraction(at_most, 36),
         f"menghitung peluang jumlah mata dadu paling banyak {s}, bukan tepat {s}"),
    ]
    return text, answer, wrongs, work, "medium", _frac


def gen_even_three_digit(rng: random.Random):
    """Three-digit even numbers from five nonzero digits, without repetition."""
    digits = rng.choice([
        (1, 2, 3, 4, 5),
        (2, 3, 4, 5, 7),
        (1, 3, 4, 6, 7),
        (1, 2, 5, 6, 7),
    ])
    evens = sum(d % 2 == 0 for d in digits)
    n = len(digits)
    answer = evens * (n - 1) * (n - 2)
    digit_text = ", ".join(str(d) for d in digits)
    text = (
        f"Dari digit {digit_text} akan dibentuk bilangan genap tiga digit tanpa "
        "pengulangan digit. Banyak bilangan yang dapat dibentuk adalah ..."
    )
    work = (
        f"Digit satuan harus genap, sehingga tersedia {evens} pilihan. Setelah satuan "
        f"dipilih, digit ratusan memiliki {n - 1} pilihan dan digit puluhan "
        f"{n - 2} pilihan. Jadi banyak bilangan adalah {evens} × {n - 1} × "
        f"{n - 2} = {answer}"
    )
    wrongs = [
        (perm(n, 3),
         f"menghitung seluruh P({n}, 3) susunan tiga digit tanpa mensyaratkan digit "
         "satuannya genap"),
        ((n - 1) * (n - 2),
         f"memilih digit satuan genap seolah-olah hanya ada satu pilihan, lalu hanya "
         f"menghitung {n - 1} × {n - 2}"),
        (n * (n - 1) * evens,
         "memberi pilihan digit ratusan sebelum menyisihkan digit genap yang dipakai "
         "sebagai satuan, sehingga beberapa susunan mengulang digit"),
        (2 * answer,
         "mengalikan hasil dengan 2 untuk pertukaran digit ratusan dan puluhan, "
         "padahal kedua urutan itu sudah dihitung terpisah dalam aturan perkalian"),
        (evens ** 3,
         "mengharuskan ketiga digit semuanya genap dan sekaligus membolehkan "
         "pengulangan, padahal hanya digit satuan yang wajib genap"),
    ]
    return text, Fraction(answer), wrongs, work, "medium", _fmt


def gen_nonadjacent_days(rng: random.Random):
    """Choose two nonconsecutive days from a consecutive run of days."""
    n = rng.randint(6, 9)
    all_pairs = comb(n, 2)
    adjacent = n - 1
    answer = all_pairs - adjacent
    text = (
        f"Dari {n} hari berturut-turut, sebuah tim harus memilih tepat dua hari untuk "
        "melakukan pemeriksaan. Kedua hari yang dipilih tidak boleh berurutan. Banyak "
        "pasangan hari yang dapat dipilih adalah ..."
    )
    work = (
        f"Seluruh pasangan dua hari berjumlah C({n}, 2) = {all_pairs}. Pasangan hari "
        f"yang berurutan ada {adjacent}, sehingga pasangan yang tidak berurutan "
        f"berjumlah {all_pairs} − {adjacent} = {answer}"
    )
    wrongs = [
        (all_pairs,
         f"menghitung seluruh C({n}, 2) pasangan tanpa mengeluarkan pasangan hari "
         "yang berurutan"),
        (adjacent,
         f"menghitung {adjacent} pasangan hari yang justru berurutan"),
        (n * (n - 1),
         "menghitung pilihan hari pertama dan kedua dengan memperhatikan urutan serta "
         "mengabaikan larangan hari berurutan"),
        (2 * answer,
         "menghitung setiap pasangan hari tidak berurutan dua kali, yaitu berdasarkan "
         "urutan hari pertama dan hari kedua"),
        (comb(n - 2, 2),
         f"hanya memilih dari {n - 2} hari bagian tengah dan membuang kedua hari ujung, "
         "padahal hari ujung tetap boleh dipilih"),
    ]
    return text, Fraction(answer), wrongs, work, "medium", _fmt


def gen_circular_nonadjacent(rng: random.Random):
    """Circular permutations in which two named people may not sit together."""
    n = rng.choice([6, 7])
    total = factorial(n - 1)
    adjacent = 2 * factorial(n - 2)
    answer = total - adjacent
    text = (
        f"Sebanyak {n} orang, termasuk Nara dan Riko, akan duduk mengelilingi sebuah "
        "meja bundar. Susunan yang hanya berbeda karena diputar dianggap sama. Jika "
        "Nara dan Riko tidak boleh duduk berdampingan, banyak susunan tempat duduk "
        "yang mungkin adalah ..."
    )
    work = (
        f"Seluruh susunan melingkar berjumlah ({n} − 1)! = {total}. Jika Nara dan "
        f"Riko berdampingan, keduanya dipandang sebagai satu blok yang dapat bertukar "
        f"urutan, sehingga ada 2 × ({n} − 2)! = {adjacent} susunan. Jadi banyak "
        f"susunan yang tidak berdampingan adalah {total} − {adjacent} = {answer}"
    )
    wrongs = [
        (total,
         "menghitung seluruh susunan melingkar tanpa mengeluarkan susunan ketika "
         "Nara dan Riko berdampingan"),
        (adjacent,
         "menghitung susunan ketika Nara dan Riko justru berdampingan"),
        (factorial(n) - 2 * factorial(n - 1),
         "memakai susunan berjajar n! dan 2(n − 1)!, sehingga susunan yang hanya "
         "berbeda karena rotasi terhitung berulang"),
        (factorial(n - 2),
         "menggabungkan Nara dan Riko sebagai satu blok tetapi melupakan dua urutan "
         "di dalam blok, lalu menjawab banyak susunan berdampingan"),
        (total - factorial(n - 2),
         "mengurangi susunan berdampingan hanya untuk satu urutan Nara–Riko dan "
         "melupakan urutan Riko–Nara"),
    ]
    return text, Fraction(answer), wrongs, work, "medium", _fmt


def gen_lattice_checkpoint(rng: random.Random):
    """Shortest monotone paths constrained to pass through one checkpoint."""
    east, north, check_east, check_north = rng.choice([
        (5, 4, 2, 1),
        (6, 4, 2, 2),
        (5, 5, 1, 3),
    ])
    first_steps = check_east + check_north
    second_east, second_north = east - check_east, north - check_north
    second_steps = second_east + second_north
    first_ways = comb(first_steps, check_north)
    second_ways = comb(second_steps, second_north)
    answer = first_ways * second_ways
    total = comb(east + north, north)
    text = (
        f"Pada kisi koordinat, sebuah robot bergerak dari (0, 0) ke ({east}, {north}). "
        "Setiap langkah hanya boleh satu satuan ke kanan atau satu satuan ke atas. "
        f"Jika robot wajib melalui titik ({check_east}, {check_north}), banyak lintasan "
        "terpendek yang mungkin adalah ..."
    )
    work = (
        f"Dari (0, 0) ke ({check_east}, {check_north}) diperlukan {first_steps} langkah "
        f"dengan {check_north} langkah ke atas, sehingga ada C({first_steps}, "
        f"{check_north}) = {first_ways} lintasan. Dari titik itu ke ({east}, {north}) "
        f"diperlukan {second_steps} langkah dengan {second_north} langkah ke atas, "
        f"sehingga ada C({second_steps}, {second_north}) = {second_ways} lintasan. "
        f"Kedua bagian ditempuh berurutan, jadi banyak lintasannya {first_ways} × "
        f"{second_ways} = {answer}"
    )
    wrongs = [
        (total,
         f"menghitung seluruh C({east + north}, {north}) lintasan terpendek tanpa "
         "mensyaratkan lintasan melalui titik pemeriksaan"),
        (first_ways + second_ways,
         "menjumlahkan pilihan lintasan sebelum dan sesudah titik pemeriksaan, "
         "padahal satu pilihan dari tiap bagian harus dipasangkan"),
        (2 ** (east + north),
         "memberi dua pilihan arah pada setiap langkah tanpa mempertahankan tepat "
         f"{east} langkah ke kanan dan {north} langkah ke atas"),
        (first_ways,
         "hanya menghitung lintasan dari titik awal ke titik pemeriksaan dan "
         "mengabaikan perjalanan sesudahnya"),
        (second_ways,
         "hanya menghitung lintasan dari titik pemeriksaan ke tujuan dan "
         "mengabaikan perjalanan sebelumnya"),
    ]
    return text, Fraction(answer), wrongs, work, "medium", _fmt


# Grouped by the idea being tested, so one package never draws two items that
# come down to the same manoeuvre.
PATTERN_GROUPS = [
    [gen_two_colour_draw, gen_at_least_one],
    [gen_committee, gen_split_equally],
    [gen_arrangement_together],
    [gen_dice_sum],
]

PATTERNS = [p for group in PATTERN_GROUPS for p in group]

# Explicit-only templates extend the generator without changing the default pool
# or its order. Existing package seed commands therefore remain byte-for-byte
# reproducible, while a package can deliberately request a new reasoning shape.
EXPLICIT_TEMPLATES = {
    "circular_nonadjacent": gen_circular_nonadjacent,
    "even_three_digit": gen_even_three_digit,
    "lattice_checkpoint": gen_lattice_checkpoint,
    "nonadjacent_days": gen_nonadjacent_days,
}


def build_one(rng: random.Random, package_id: int, subtest: str, number: int,
              bank_dir: Path, pattern) -> Path:
    for _ in range(200):
        text, answer, wrongs, work, difficulty, render = pattern(rng)

        taken, distractors = {Fraction(answer)}, []
        for value, reason in wrongs:
            value = Fraction(value)
            if value in taken or value < 0:
                continue
            taken.add(value)
            distractors.append((value, reason))
        if len(distractors) < 4:
            continue

        rng.shuffle(distractors)
        values = [(Fraction(answer), None)] + distractors[:4]
        rng.shuffle(values)
        correct_key = "ABCDE"[[v for v, _ in values].index(Fraction(answer))]

        options, explanations = [], {}
        for key, (value, reason) in zip("ABCDE", values):
            options.append((key, render(value)))
            explanations[key] = (
                f"Benar. {work}." if reason is None
                else f"Salah. Nilai {render(value)} diperoleh dengan {reason}."
            )

        q = make_question(
            package_id=package_id,
            subtest=subtest,
            number=number,
            qtype=QTYPE,
            question_text=text,
            options=options,
            correct_option=correct_key,
            explanations=explanations,
            difficulty=difficulty,
            source="peluang_kombinatorik.py",
        )
        return write_question(q, bank_dir)
    raise RuntimeError(f"{pattern.__name__}: no clean draw after 200 attempts")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=int, required=True)
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--subtest", choices=["kuantitatif", "pemecahan_masalah"],
                    default="kuantitatif")
    ap.add_argument("--template", choices=sorted(EXPLICIT_TEMPLATES),
                    help="generate one explicit template without changing the default pool")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pool: list = []
    for _ in range(args.count):
        if args.template:
            pattern = EXPLICIT_TEMPLATES[args.template]
        else:
            if not pool:  # without replacement, one draw per idea
                pool = PATTERN_GROUPS[:]
                rng.shuffle(pool)
            pattern = rng.choice(pool.pop())
        number = next_number(args.package, args.subtest, args.bank_dir)
        path = build_one(rng, args.package, args.subtest, number, args.bank_dir,
                         pattern)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
