#!/usr/bin/env python3
"""Generate yes/no predicate variants of ``kecukupan_data``.

The main ``kecukupan_data.py`` engine handles questions that ask for one exact
quantity and proves sufficiency with exact linear algebra.  This companion
handles the distinct screenshot architecture: whether an inequality is true.
For positive ``a, b, c, d`` it uses the exact equivalence

    a/b < (a+c)/(b+d)  iff  ad < bc  iff  a/b < c/d.

Each statement architecture is checked over a deterministic positive-integer
domain.  Sufficiency claims also carry a symbolic proof from the equivalence;
insufficiency claims print two concrete assignments with opposite yes/no
answers.  The finite search supplies counterexamples and guards the templates,
while the symbolic implication is what proves a sufficient statement.

Usage:
    python3 kecukupan_data_predikat.py --package 7 --count 1 --seed 42
    python3 kecukupan_data_predikat.py --package 7 --template ratio_vs_sum
"""

from __future__ import annotations

import argparse
import itertools
import random
from pathlib import Path
from typing import Callable

from common import BANK_DIR, make_question, next_number, write_question
from kecukupan_data import OPTIONS, PROMPT

SUBTEST = "kuantitatif"
QTYPE = "kecukupan_data"

State = tuple[int, int, int, int]
Constraint = Callable[[State], bool]
DOMAIN = tuple(itertools.product(range(1, 10), repeat=4))


def _predicate(state: State) -> bool:
    a, b, c, d = state
    return a * (b + d) < b * (a + c)


def _ratio_order(state: State) -> bool:
    a, b, c, d = state
    return a * d < b * c


def _sum_order(state: State) -> bool:
    a, b, c, d = state
    return a + c < b + d


def _a_equals_c(state: State) -> bool:
    a, _, c, _ = state
    return a == c


def _b_less_d(state: State) -> bool:
    _, b, _, d = state
    return b < d


def _b_greater_d(state: State) -> bool:
    _, b, _, d = state
    return b > d


def _b_equals_d(state: State) -> bool:
    _, b, _, d = state
    return b == d


def _a_less_c(state: State) -> bool:
    a, _, c, _ = state
    return a < c


def _all(*constraints: Constraint) -> Constraint:
    return lambda state: all(constraint(state) for constraint in constraints)


COMMON_PROOF = ("Karena semua peubah positif, a/b < (a+c)/(b+d) ekuivalen "
                "dengan ad < bc, yang juga ekuivalen dengan a/b < c/d.")


def _templates() -> dict[str, dict]:
    return {
        "ratio_vs_sum": {
            "statements": (
                ("a/b < c/d.", _ratio_order),
                ("a + c < b + d.", _sum_order),
            ),
            "proofs": {"1": f"{COMMON_PROOF} Pernyataan (1) memastikan jawabannya Ya."},
            "difficulty": "hard",
        },
        "sum_vs_equal_denominator": {
            "statements": (
                ("a + c < b + d.", _sum_order),
                ("a < c dan b = d.", _all(_a_less_c, _b_equals_d)),
            ),
            "proofs": {
                "2": (f"{COMMON_PROOF} Jika a<c dan b=d, maka ad<cd=bc; "
                      "jadi pernyataan (2) memastikan jawabannya Ya.")
            },
            "difficulty": "medium",
        },
        "combined_only": {
            "statements": (
                ("a = c.", _a_equals_c),
                ("b < d.", _b_less_d),
            ),
            "proofs": {
                "12": (f"{COMMON_PROOF} Jika a=c dan b<d, maka ad=cd>bc; "
                       "jadi pertidaksamaan yang ditanyakan pasti salah (jawabannya Tidak).")
            },
            "difficulty": "hard",
        },
        "each_sufficient": {
            "statements": (
                ("a/b < c/d.", _ratio_order),
                ("a = c dan b > d.", _all(_a_equals_c, _b_greater_d)),
            ),
            "proofs": {
                "1": f"{COMMON_PROOF} Pernyataan (1) memastikan jawabannya Ya.",
                "2": (f"{COMMON_PROOF} Jika a=c dan b>d, maka ad=cd<bc; "
                      "jadi pernyataan (2) juga memastikan jawabannya Ya."),
                "12": f"{COMMON_PROOF} Masing-masing pernyataan sendiri sudah memastikan jawaban Ya.",
            },
            "difficulty": "medium",
        },
        "still_insufficient": {
            "statements": (
                ("a < c.", _a_less_c),
                ("b < d.", _b_less_d),
            ),
            "proofs": {},
            "difficulty": "hard",
        },
    }


TEMPLATES = _templates()


def _states(constraints: tuple[Constraint, ...]) -> list[State]:
    return [state for state in DOMAIN if all(test(state) for test in constraints)]


def _decision(constraints: tuple[Constraint, ...]) -> tuple[bool, bool | None, tuple[State, State] | None]:
    states = _states(constraints)
    if not states:
        raise RuntimeError("template statements have no positive-integer model")
    by_result = {result: next((state for state in states if _predicate(state) == result), None)
                 for result in (False, True)}
    if by_result[False] is not None and by_result[True] is not None:
        return False, None, (by_result[False], by_result[True])
    result = by_result[True] is not None
    return True, result, None


def _assignment(state: State) -> str:
    return ", ".join(f"{name}={value}" for name, value in zip("abcd", state))


def _not_enough(label: str, witness: tuple[State, State]) -> str:
    no_state, yes_state = witness
    return (f"pernyataan {label} tidak cukup: [{_assignment(no_state)}] dan "
            f"[{_assignment(yes_state)}] sama-sama memenuhinya, tetapi jawaban "
            "pertanyaan masing-masing Tidak dan Ya")


def _enough(label: str, result: bool, proof: str) -> str:
    return (f"pernyataan {label} cukup dan menetapkan jawaban "
            f"{'Ya' if result else 'Tidak'}. {proof}")


def _sentence(text: str) -> str:
    return text[0].upper() + text[1:].rstrip(".") + "."


def build_one(rng: random.Random, package_id: int, number: int, bank_dir: Path,
              template_name: str) -> Path:
    spec = TEMPLATES[template_name]
    (text1, statement1), (text2, statement2) = spec["statements"]
    ok1, result1, witness1 = _decision((statement1,))
    ok2, result2, witness2 = _decision((statement2,))
    ok12, result12, witness12 = _decision((statement1, statement2))

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

    proofs = dict(spec["proofs"])
    if ok12 and "12" not in proofs:
        if ok1:
            proofs["12"] = "Pernyataan (1) sudah cukup, sehingga menambahkan pernyataan (2) tidak mengubah kepastian jawaban."
        elif ok2:
            proofs["12"] = "Pernyataan (2) sudah cukup, sehingga menambahkan pernyataan (1) tidak mengubah kepastian jawaban."
    if (ok1 and "1" not in proofs) or (ok2 and "2" not in proofs) or (ok12 and "12" not in proofs):
        raise RuntimeError(f"{template_name}: enumerated sufficiency lacks a symbolic proof")

    yes1 = _enough("(1)", bool(result1), proofs["1"]) if ok1 else ""
    yes2 = _enough("(2)", bool(result2), proofs["2"]) if ok2 else ""
    yes12 = _enough("(1) dan (2) bersama-sama", bool(result12), proofs["12"]) if ok12 else ""
    no1 = _not_enough("(1)", witness1) if witness1 else ""
    no2 = _not_enough("(2)", witness2) if witness2 else ""
    no12 = _not_enough("(1) dan (2) bersama-sama", witness12) if witness12 else ""

    claims = {
        "A": [(ok1, yes1, no1), (not ok2, no2, yes2)],
        "B": [(ok2, yes2, no2), (not ok1, no1, yes1)],
        "C": [(ok12, yes12, no12), (not ok1, no1, yes1), (not ok2, no2, yes2)],
        "D": [(ok1, yes1, no1), (ok2, yes2, no2)],
        "E": [(not ok12, no12, yes12)],
    }
    explanations = {}
    for option, conjuncts in claims.items():
        if option == key:
            support = "; ".join(text.rstrip(".") for holds, text, _ in conjuncts if holds)
            explanations[option] = f"Benar. {_sentence(support)}"
        else:
            refutation = next(text for holds, _, text in conjuncts if not holds)
            explanations[option] = f"Salah. {_sentence(refutation)}"

    question_text = (
        "a, b, c, dan d adalah bilangan positif. Apakah a/b < (a+c)/(b+d)?\n"
        f"(1) {text1}\n"
        f"(2) {text2}\n"
        f"{PROMPT}"
    )
    question = make_question(
        package_id=package_id,
        subtest=SUBTEST,
        number=number,
        qtype=QTYPE,
        question_text=question_text,
        options=OPTIONS,
        correct_option=key,
        explanations=explanations,
        difficulty=spec["difficulty"],
        source="kecukupan_data_predikat.py",
    )
    return write_question(question, bank_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=int, required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--template", choices=sorted(TEMPLATES))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = parser.parse_args()
    if args.template and args.count != 1:
        parser.error("--template requires --count 1")

    rng = random.Random(args.seed)
    names = [args.template] if args.template else list(TEMPLATES)
    if not args.template:
        rng.shuffle(names)
    if args.count > len(names):
        parser.error(f"--count cannot exceed {len(names)} without repeating an architecture")

    for template_name in names[:args.count]:
        number = next_number(args.package, SUBTEST, args.bank_dir)
        path = build_one(rng, args.package, number, args.bank_dir, template_name)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
