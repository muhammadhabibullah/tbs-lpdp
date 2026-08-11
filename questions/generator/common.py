"""Shared helpers for LPDP TBS question generator/validator/push scripts.

The git question bank (questions/bank) is the source of truth; see
.claude/skills/lpdp-question-generation/SKILL.md for the format contract.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BANK_DIR = REPO_ROOT / "questions" / "bank"
SCHEMA_PATH = REPO_ROOT / "questions" / "schema.json"

SUBTESTS = ("verbal", "kuantitatif", "pemecahan_masalah")

# key -> (display name, position, question_count, duration_seconds, passing_grade)
BLUEPRINT = {
    "verbal": ("Penalaran Verbal", 1, 23, 30 * 60, 70),
    "kuantitatif": ("Penalaran Kuantitatif", 2, 25, 40 * 60, 75),
    "pemecahan_masalah": ("Pemecahan Masalah", 3, 12, 20 * 60, 35),
}

# A type may legitimately appear in more than one subtest: a probability item is
# quantitative reasoning in `kuantitatif` and applied problem solving in
# `pemecahan_masalah`, and the official test uses it in both places.
TYPES_BY_SUBTEST = {
    "verbal": {
        "sinonim",
        "antonim",
        "analogi",
        "silogisme",
        "kalimat_efektif",
        "reading",
    },
    "kuantitatif": {
        "aritmetika",
        "aljabar",
        "deret_angka",
        "perbandingan_kuantitatif",
        "kecukupan_data",
        "peluang_kombinatorik",
        "soal_cerita",
        "geometri",
    },
    "pemecahan_masalah": {
        "logika_analitis",
        "penalaran_kasus",
        "silogisme",
        "interpretasi_data",
        "analisis_teks",
        "soal_cerita",
        "peluang_kombinatorik",
    },
}

# Types whose stem cannot be answered without the shared stimulus in `passage`.
PASSAGE_REQUIRED_TYPES = {"reading", "analisis_teks"}

# Types that need a stimulus but may carry it either as text in `passage`
# (a pipe-delimited table) or as a chart in `image`.
PASSAGE_OR_IMAGE_TYPES = {"interpretasi_data"}

# Everything else is self-contained; a stray passage there is an authoring slip.
PASSAGE_ALLOWED_TYPES = PASSAGE_REQUIRED_TYPES | PASSAGE_OR_IMAGE_TYPES

OPTION_KEYS = ("A", "B", "C", "D", "E")
DIFFICULTY_WEIGHTS = {"easy": 1, "medium": 2, "hard": 3}


MINUS = "−"  # typographic minus, matches the one used in question stems


def package_difficulty(difficulty_counts: dict[str, int]) -> tuple[str, Fraction]:
    """Return the deterministic v3.1 package band and its exact index.

    Easy is below 1.90, Medium is 1.90–2.19, and Hard starts at 2.20.
    Integer cross-multiplication keeps boundary decisions deterministic.
    """
    total = sum(difficulty_counts.get(key, 0) for key in DIFFICULTY_WEIGHTS)
    if total <= 0:
        raise ValueError("cannot calculate package difficulty without questions")
    weighted = sum(
        difficulty_counts.get(key, 0) * weight
        for key, weight in DIFFICULTY_WEIGHTS.items()
    )
    if 10 * weighted < 19 * total:
        label = "easy"
    elif 10 * weighted < 22 * total:
        label = "medium"
    else:
        label = "hard"
    return label, Fraction(weighted, total)


def fmt_number(x) -> str:
    """Format a number the way an Indonesian exam paper would.

    Comma as decimal separator, dot as thousands separator, typographic minus:
    ``1215 -> "1.215"``, ``-19.2 -> "−19,2"``. Values whose denominator does not
    divide 100 keep exact fraction notation (``"2/3"``) instead of being
    silently rounded into a repeating decimal.
    """
    f = Fraction(x).limit_denominator(10_000)
    sign = MINUS if f < 0 else ""
    f = abs(f)
    if f.denominator == 1:
        return sign + f"{f.numerator:,}".replace(",", ".")
    if 100 % f.denominator:
        return f"{sign}{f.numerator}/{f.denominator}"
    cents = f.numerator * (100 // f.denominator)
    whole, frac = divmod(cents, 100)
    digits = f"{frac:02d}".rstrip("0")
    return f"{sign}{whole:,}".replace(",", ".") + f",{digits}"


def renders_exactly(value) -> bool:
    """True when the value prints as a whole number or a terminating decimal.

    `fmt_number` falls back to fraction notation otherwise, which reads as a typo
    when it turns up in an option list or inside a stem.
    """
    f = Fraction(value)
    return f.denominator == 1 or 100 % f.denominator == 0


def load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def subtest_dir(package_id: int, subtest: str, bank_dir: Path = BANK_DIR) -> Path:
    return bank_dir / str(package_id) / subtest


def next_number(package_id: int, subtest: str, bank_dir: Path = BANK_DIR) -> int:
    """Next free question number (1-based) in a subtest directory."""
    d = subtest_dir(package_id, subtest, bank_dir)
    if not d.is_dir():
        return 1
    numbers = [
        int(p.stem) for p in d.glob("[0-9][0-9][0-9].json") if p.stem.isdigit()
    ]
    return max(numbers, default=0) + 1


def question_id(package_id: int, subtest: str, number: int) -> str:
    return f"{package_id}-{subtest}-{number:03d}"


def write_question(q: dict, bank_dir: Path = BANK_DIR) -> Path:
    """Write a question dict to its canonical bank path and return the path."""
    d = subtest_dir(q["package"], q["subtest"], bank_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{q['number']:03d}.json"
    if path.exists():
        raise FileExistsError(f"{path} already exists; refusing to overwrite")
    with path.open("w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def make_question(
    *,
    package_id: int,
    subtest: str,
    number: int,
    qtype: str,
    question_text: str,
    options: list[tuple[str, str]],
    correct_option: str,
    explanations: dict[str, str],
    difficulty: str,
    image: str | None = None,
    passage: str | None = None,
    source: str = "script-generated",
) -> dict:
    """Assemble a question dict in schema order with basic sanity checks."""
    keys = [k for k, _ in options]
    if keys != list(OPTION_KEYS):
        raise ValueError(f"options must be exactly A..E in order, got {keys}")
    if correct_option not in OPTION_KEYS:
        raise ValueError(f"bad correct_option {correct_option!r}")
    if set(explanations) != set(OPTION_KEYS):
        raise ValueError("explanations must cover exactly A..E")
    if qtype not in TYPES_BY_SUBTEST[subtest]:
        raise ValueError(f"type {qtype!r} not allowed in subtest {subtest!r}")
    return {
        "id": question_id(package_id, subtest, number),
        "package": package_id,
        "subtest": subtest,
        "number": number,
        "type": qtype,
        "question_text": question_text,
        "image": image,
        "passage": passage,
        "options": [{"key": k, "text": t} for k, t in options],
        "correct_option": correct_option,
        "explanations": explanations,
        "difficulty": difficulty,
        "source": source,
        "verified": False,
    }


def iter_bank_questions(bank_dir: Path = BANK_DIR):
    """Yield (path, parsed-json-or-None, error-or-None) for every bank question file."""
    for path in sorted(bank_dir.glob("*/*/[0-9][0-9][0-9].json")):
        try:
            with path.open(encoding="utf-8") as f:
                yield path, json.load(f), None
        except json.JSONDecodeError as e:
            yield path, None, f"invalid JSON: {e}"
