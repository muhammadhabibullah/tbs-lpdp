#!/usr/bin/env python3
"""Deterministic generator for ``deret_huruf`` (letter-sequence) questions.

Letters are converted to positions A=1 through Z=26, the continuation is
computed from the selected rule, and every distractor records the exact
misreading that produces it.  Tail questions support one or two missing terms;
``--interior`` produces the anchored square-position shape ``Y, P, I, ..., A``.

Every tail draw is screened against rival readings: constant and accelerating
steps, two interleaved tracks, repeating three/four-step cycles, and modular
constant steps.  A draw is rejected if another supported rule fits every
printed letter but predicts a different continuation.

Usage:
    python3 deret_huruf.py --package 7 --count 1 [--blanks 1|2]
    python3 deret_huruf.py --package 7 --count 1 --interior
    python3 deret_huruf.py --package 7 --count 1 --template four_step_cycle
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from common import BANK_DIR, make_question, next_number, write_question

SUBTEST = "kuantitatif"
QTYPE = "deret_huruf"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _letter(position: int) -> str:
    if not 1 <= position <= 26:
        raise ValueError(f"alphabet position out of range: {position}")
    return ALPHABET[position - 1]


def _constant_step(terms: list[int]) -> int | None:
    differences = {b - a for a, b in zip(terms, terms[1:])}
    if len(differences) != 1:
        return None
    answer = terms[-1] + differences.pop()
    return answer if 1 <= answer <= 26 else None


def _constant_second_difference(terms: list[int]) -> int | None:
    differences = [b - a for a, b in zip(terms, terms[1:])]
    if len(differences) < 2:
        return None
    second = {b - a for a, b in zip(differences, differences[1:])}
    if len(second) != 1:
        return None
    answer = terms[-1] + differences[-1] + second.pop()
    return answer if 1 <= answer <= 26 else None


def _track_prediction(track: list[int]) -> int | None:
    # Two points always define a line and therefore do not establish a rival
    # interleaved rule.  Require three observations on the track.
    if len(track) < 3:
        return None
    differences = [b - a for a, b in zip(track, track[1:])]
    if len(set(differences)) == 1:
        answer = track[-1] + differences[-1]
    elif len(differences) >= 2 and len({b - a for a, b in zip(differences, differences[1:])}) == 1:
        answer = track[-1] + 2 * differences[-1] - differences[-2]
    else:
        return None
    return answer if 1 <= answer <= 26 else None


def _interleaved(terms: list[int]) -> int | None:
    track = terms[0::2] if len(terms) % 2 == 0 else terms[1::2]
    return _track_prediction(track)


def _cycle(terms: list[int], period: int) -> int | None:
    differences = [b - a for a, b in zip(terms, terms[1:])]
    if len(differences) < period * 2:
        return None
    if any(differences[i] != differences[i % period] for i in range(len(differences))):
        return None
    answer = terms[-1] + differences[len(differences) % period]
    return answer if 1 <= answer <= 26 else None


def _modular_constant(terms: list[int]) -> int | None:
    steps = {(b - a) % 26 for a, b in zip(terms, terms[1:])}
    if len(steps) != 1:
        return None
    step = steps.pop()
    return (terms[-1] - 1 + step) % 26 + 1


RIVAL_RULES = (
    _constant_step,
    _constant_second_difference,
    _interleaved,
    lambda terms: _cycle(terms, 3),
    lambda terms: _cycle(terms, 4),
    _modular_constant,
)


def _unambiguous(terms: list[int], answer: int) -> bool:
    return all((prediction := rule(terms)) is None or prediction == answer
               for rule in RIVAL_RULES)


def gen_increasing_steps(rng: random.Random) -> dict:
    start = rng.randint(1, 4)
    terms = [start]
    for step in (1, 2, 3, 4):
        terms.append(terms[-1] + step)
    answer, answer2 = terms[-1] + 5, terms[-1] + 5 + 6
    return {
        "terms": terms,
        "answers": (answer, answer2),
        "wrongs": [
            (terms[-1] + 4, "mengulang lompatan terakhir +4, padahal lompatannya naik menjadi +5"),
            (terms[-1] + 6, "menaikkan lompatan dua tingkat sekaligus dari +4 menjadi +6"),
            (answer - 2, "menghitung lompatan berikutnya sebagai +3, bukan +5"),
            (answer2, "melanjutkan dua langkah sekaligus dan memilih suku setelah jawaban"),
        ],
        "explanation": ("Posisi huruf bertambah dengan lompatan berurutan +1, +2, +3, "
                        f"+4, sehingga lompatan berikutnya +5 dan menghasilkan {_letter(answer)}. "
                        f"Sesudah itu lompatan +6 menghasilkan {_letter(answer2)}."),
        "difficulty": "medium",
    }


def gen_opposite_interleaved(rng: random.Random) -> dict:
    low, high = rng.randint(1, 5), rng.randint(22, 26)
    step = rng.choice([2, 3])
    terms = []
    for index in range(3):
        terms.extend((low + index * step, high - index * step))
    answer, answer2 = low + 3 * step, high - 3 * step
    return {
        "terms": terms,
        "answers": (answer, answer2),
        "wrongs": [
            (answer2, "melanjutkan jalur huruf genap, padahal giliran berikutnya jalur ganjil"),
            (terms[-2] + step + 1, f"menaikkan jalur ganjil sebesar {step + 1}, bukan {step}"),
            (answer - 1, "melanjutkan jalur menaik tetapi bergeser satu posisi alfabet"),
            (answer + step, "melompati satu suku pada jalur huruf ganjil"),
        ],
        "explanation": (f"Huruf pada posisi ganjil naik {step} tempat, sedangkan huruf pada "
                        f"posisi genap turun {step} tempat. Dua huruf berikutnya adalah "
                        f"{_letter(answer)} dan {_letter(answer2)}."),
        "difficulty": "medium",
    }


def gen_accelerating_interleaved(rng: random.Random) -> dict:
    low, high = rng.randint(1, 3), rng.randint(24, 26)
    up = [low]
    down = [high]
    for step in (1, 2, 3, 4):
        up.append(up[-1] + step)
        down.append(down[-1] - step)
    terms = [up[0], down[0], up[1], down[1], up[2], down[2], up[3]]
    answer, answer2 = down[3], up[4]
    return {
        "terms": terms,
        "answers": (answer, answer2),
        "wrongs": [
            (down[2] - 2, "mengulang penurunan −2, padahal lompatan jalur menurun menjadi −3"),
            (down[2] - 4, "menaikkan besar lompatan dua tingkat sekaligus menjadi −4"),
            (up[4], "melanjutkan jalur menaik lebih dahulu, padahal giliran berikutnya jalur menurun"),
            (answer - 2, "membaca penurunan berikutnya sebagai −5, bukan −3"),
        ],
        "explanation": ("Dua jalur berselang-seling bergerak berlawanan. Jalur ganjil naik "
                        "+1, +2, +3, +4, sedangkan jalur genap turun −1, −2, −3, −4. "
                        f"Dua huruf berikutnya adalah {_letter(answer)} dan {_letter(answer2)}."),
        "difficulty": "hard",
    }


def gen_four_step_cycle(rng: random.Random) -> dict:
    # The tutorial shape X,W,U,V,T,S,Q,R,P,O follows −1,−2,+1,−2.
    start = rng.randint(23, 26)
    steps = (-1, -2, 1, -2)
    terms = [start]
    for index in range(9):
        terms.append(terms[-1] + steps[index % 4])
    answer = terms[-1] + steps[9 % 4]
    answer2 = answer + steps[10 % 4]
    return {
        "terms": terms,
        "answers": (answer, answer2),
        "wrongs": [
            (terms[-1] - 1, "mengulang lompatan −1, padahal giliran berikutnya adalah −2"),
            (terms[-1] + 1, "menerapkan lompatan +1 terlalu awal dalam siklus"),
            (answer - 2, "membaca lompatan berikutnya sebagai −4, bukan −2"),
            (answer - 1, "membaca lompatan berikutnya sebagai −3, bukan −2"),
            (answer - 3, "membaca lompatan berikutnya sebagai −5, bukan −2"),
            (answer - 4, "menerapkan dua lompatan −2 sekaligus"),
        ],
        "explanation": ("Perubahan posisi huruf mengulang siklus −1, −2, +1, −2. "
                        f"Dua langkah setelah {_letter(terms[-1])} menghasilkan "
                        f"{_letter(answer)} lalu {_letter(answer2)}."),
        "difficulty": "hard",
    }


def gen_five_step_modulo(rng: random.Random) -> dict:
    start = rng.randint(3, 6)
    terms = [((start - 1 + 5 * index) % 26) + 1 for index in range(5)]
    answer = ((terms[-1] - 1 + 5) % 26) + 1
    answer2 = ((answer - 1 + 5) % 26) + 1
    return {
        "terms": terms,
        "answers": (answer, answer2),
        "wrongs": [
            (26, "berhenti di Z dan tidak melanjutkan hitungan kembali dari A"),
            (((terms[-1] - 1 + 4) % 26) + 1, "menggunakan lompatan +4, bukan +5"),
            (((terms[-1] - 1 + 6) % 26) + 1, "menggunakan lompatan +6, bukan +5"),
            (answer2, "melakukan dua lompatan +5 sekaligus"),
            (((terms[-1] - 1 + 3) % 26) + 1, "menggunakan lompatan +3, bukan +5"),
            (((terms[-1] - 1 + 7) % 26) + 1, "menggunakan lompatan +7, bukan +5"),
        ],
        "explanation": ("Setiap huruf maju lima posisi alfabet; setelah Z hitungan kembali "
                        f"ke A. Dua huruf berikutnya adalah {_letter(answer)} dan "
                        f"{_letter(answer2)}."),
        "difficulty": "easy",
    }


PATTERN_GROUPS = [
    [gen_increasing_steps],
    [gen_opposite_interleaved, gen_accelerating_interleaved],
    [gen_four_step_cycle],
    [gen_five_step_modulo],
]

EXPLICIT_PATTERNS = {
    "accelerating_interleaved": gen_accelerating_interleaved,
    "five_step_modulo": gen_five_step_modulo,
    "four_step_cycle": gen_four_step_cycle,
    "increasing_steps": gen_increasing_steps,
    "opposite_interleaved": gen_opposite_interleaved,
}


def _tail_layout(spec: dict, blanks: int):
    terms = spec["terms"]
    answer, answer2 = spec["answers"]
    if not _unambiguous(terms, answer):
        return None
    if blanks == 2 and not _unambiguous(terms + [answer], answer2):
        return None

    if blanks == 1:
        correct = _letter(answer)
        candidates = [(_letter(value), reason) for value, reason in spec["wrongs"]
                      if 1 <= value <= 26 and value != answer and value not in terms]
        stem = (", ".join(_letter(value) for value in terms)
                + ", ... Huruf yang tepat untuk melanjutkan deret tersebut adalah ...")
        explanation = spec["explanation"].split(" Dua huruf berikutnya")[0]
        explanation = explanation.split(" Dua langkah setelah")[0]
        explanation = explanation.split(" Sesudah itu")[0].rstrip(".")
        explanation += f". Jadi, huruf berikutnya adalah {_letter(answer)}."
    else:
        correct = f"{_letter(answer)} dan {_letter(answer2)}"
        pair_candidates = [
            ((answer2, answer), "menukar urutan kedua suku yang sebenarnya"),
            ((answer, answer2 + 1), "mempertahankan suku pertama yang benar tetapi memajukan suku kedua satu posisi"),
            ((answer - 1, answer2), "memundurkan suku pertama satu posisi walaupun suku kedua sudah benar"),
            ((answer + 1, answer2 - 1), "memajukan suku pertama dan memundurkan suku kedua masing-masing satu posisi"),
            ((answer2, answer2 + 1), "memakai suku kedua yang benar sebagai suku pertama, lalu bergerak satu posisi alfabet"),
        ]
        candidates = []
        for (a, b), reason in pair_candidates:
            if not (1 <= a <= 26 and 1 <= b <= 26) or (a, b) == (answer, answer2):
                continue
            text = f"{_letter(a)} dan {_letter(b)}"
            candidates.append((text, f"pasangan {text} diperoleh karena {reason}"))
        stem = (", ".join(_letter(value) for value in terms)
                + ", ..., ... Dua huruf yang tepat untuk melanjutkan deret tersebut adalah ...")
        explanation = spec["explanation"]

    seen, clean = {correct}, []
    for text, reason in candidates:
        if text not in seen:
            seen.add(text)
            clean.append((text, reason))
    return (stem, correct, clean, explanation) if len(clean) >= 4 else None


def _interior_layout():
    # Descending square positions: 5², 4², 3², 2², 1².
    shown = [25, 16, 9, None, 1]
    answer = 4
    candidates = [
        (_letter(6), "mengurangi posisi I sebesar 3, padahal pola kuadrat memerlukan langkah I(9) − 5 = D(4)"),
        (_letter(5), "mengurangi posisi I sebanyak 4 tetapi tidak memakai posisi 2²"),
        (_letter(3), "menggunakan 2² − 1 dan bergeser satu posisi dari D"),
        (_letter(2), "langsung memilih posisi 2, bukan kuadratnya 2²"),
    ]
    # Rival candidate search: only D should complete a constant-second-
    # difference sequence across all five printed/anchored positions.
    valid = []
    for candidate in range(1, 27):
        seq = [candidate if value is None else value for value in shown]
        differences = [b - a for a, b in zip(seq, seq[1:])]
        if len({b - a for a, b in zip(differences, differences[1:])}) == 1:
            valid.append(candidate)
    if valid != [answer]:
        raise RuntimeError(f"interior square pattern is not unique: {valid}")
    stem = "Y, P, I, ..., A Huruf yang tepat untuk mengisi titik-titik tersebut adalah ..."
    explanation = ("Posisi huruf mengikuti kuadrat menurun: Y=25=5², P=16=4², "
                   "I=9=3², D=4=2², dan A=1=1². Jadi huruf yang hilang adalah D.")
    return stem, _letter(answer), candidates, explanation


def build_one(rng: random.Random, package_id: int, number: int, bank_dir: Path,
              pattern=None, blanks: int = 1, interior: bool = False) -> Path:
    for _ in range(200):
        spec = None if interior else pattern(rng)
        layout = _interior_layout() if interior else _tail_layout(spec, blanks)
        if layout is None:
            continue
        stem, correct, distractors, explanation = layout
        values = [(correct, None)] + distractors[:4]
        rng.shuffle(values)
        correct_key = "ABCDE"[[text for text, _ in values].index(correct)]
        options = []
        explanations = {}
        for key, (text, reason) in zip("ABCDE", values):
            options.append((key, text))
            explanations[key] = (f"Benar. {explanation}" if reason is None
                                 else f"Salah. {reason[0].upper() + reason[1:]}.")
        question = make_question(
            package_id=package_id,
            subtest=SUBTEST,
            number=number,
            qtype=QTYPE,
            question_text=stem,
            options=options,
            correct_option=correct_key,
            explanations=explanations,
            difficulty="hard" if interior else spec["difficulty"],
            source="deret_huruf.py",
        )
        return write_question(question, bank_dir)
    raise RuntimeError("no clean letter-sequence draw after 200 attempts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=int, required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--blanks", type=int, choices=[1, 2], default=1)
    parser.add_argument("--interior", action="store_true")
    parser.add_argument("--template", choices=sorted(EXPLICIT_PATTERNS))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = parser.parse_args()

    if args.interior and (args.count != 1 or args.template or args.blanks != 1):
        parser.error("--interior requires --count 1, --blanks 1, and no --template")
    if args.template and args.count != 1:
        parser.error("--template requires --count 1")

    rng = random.Random(args.seed)
    if args.interior:
        patterns = [None]
    elif args.template:
        patterns = [EXPLICIT_PATTERNS[args.template]]
    else:
        pool = PATTERN_GROUPS[:]
        rng.shuffle(pool)
        patterns = []
        for _ in range(args.count):
            if not pool:
                pool = PATTERN_GROUPS[:]
                rng.shuffle(pool)
            patterns.append(rng.choice(pool.pop()))

    for pattern in patterns:
        number = next_number(args.package, SUBTEST, args.bank_dir)
        path = build_one(rng, args.package, number, args.bank_dir, pattern,
                         args.blanks, args.interior)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
