#!/usr/bin/env python3
"""Validate the whole question bank against the schema and the LPDP blueprint.

Checks (per QG-4 in docs/TECHNICAL_REQUIREMENTS.md):
  - every file parses and passes questions/schema.json
  - id/package/subtest/number match the file's path
  - option keys are A..E exactly once, correct_option among them
  - explanations cover all five options
  - referenced images exist in the package's images/ directory
  - unique question numbers per subtest; no gaps in numbering
  - stimulus-based types carry a passage (or, for interpretasi_data, a chart);
    self-contained types don't
  - with --strict: per-subtest counts match the blueprint exactly

Exit code 0 = valid; 1 = errors found. CI-friendly.

Usage:
    python3 validate_bank.py [--strict] [--bank-dir PATH]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

from common import (
    BANK_DIR,
    BLUEPRINT,
    PASSAGE_ALLOWED_TYPES,
    PASSAGE_OR_IMAGE_TYPES,
    PASSAGE_REQUIRED_TYPES,
    TYPES_BY_SUBTEST,
    iter_bank_questions,
    load_schema,
)


def validate(bank_dir: Path, strict: bool) -> int:
    validator = Draft202012Validator(load_schema())
    errors: list[str] = []
    warnings: list[str] = []
    # (package, subtest) -> list of numbers seen
    numbers: dict[tuple[str, str], list[int]] = defaultdict(list)
    count = 0

    for path, q, parse_err in iter_bank_questions(bank_dir):
        rel = path.relative_to(bank_dir)
        count += 1
        if parse_err:
            errors.append(f"{rel}: {parse_err}")
            continue

        n_before = len(errors)
        for e in validator.iter_errors(q):
            loc = "/".join(str(p) for p in e.path) or "(root)"
            errors.append(f"{rel}: schema: {loc}: {e.message}")
        if len(errors) > n_before:
            continue  # don't cascade path/logic checks onto schema-invalid files

        pkg, subtest, fname = rel.parts
        expected_number = int(path.stem)
        if q["package"] != int(pkg):
            errors.append(f"{rel}: package field {q['package']} != directory {pkg}")
        if q["subtest"] != subtest:
            errors.append(f"{rel}: subtest field {q['subtest']!r} != directory {subtest!r}")
        if q["number"] != expected_number:
            errors.append(f"{rel}: number field {q['number']} != filename {expected_number}")
        expected_id = f"{pkg}-{subtest}-{expected_number:03d}"
        if q["id"] != expected_id:
            errors.append(f"{rel}: id {q['id']!r} != expected {expected_id!r}")

        keys = [o["key"] for o in q["options"]]
        if keys != ["A", "B", "C", "D", "E"]:
            errors.append(f"{rel}: option keys must be exactly A..E in order, got {keys}")
        if q["correct_option"] not in keys:
            errors.append(f"{rel}: correct_option {q['correct_option']!r} not among options")
        if q["type"] not in TYPES_BY_SUBTEST.get(subtest, set()):
            errors.append(f"{rel}: type {q['type']!r} not allowed in subtest {subtest!r}")

        qtype = q["type"]
        if qtype in PASSAGE_REQUIRED_TYPES and not q.get("passage"):
            errors.append(f"{rel}: type {qtype!r} must include a passage")
        if qtype in PASSAGE_OR_IMAGE_TYPES and not (q.get("passage") or q.get("image")):
            errors.append(
                f"{rel}: type {qtype!r} must include a data table in `passage` "
                f"or a chart in `image`"
            )
        if qtype not in PASSAGE_ALLOWED_TYPES and q.get("passage"):
            warnings.append(f"{rel}: type {qtype!r} carries a passage but is self-contained")

        if q.get("image"):
            img = bank_dir / pkg / q["image"]
            if not img.is_file():
                errors.append(f"{rel}: referenced image {q['image']!r} not found")

        numbers[(pkg, subtest)].append(expected_number)

    for (pkg, subtest), nums in sorted(numbers.items()):
        dupes = {n for n in nums if nums.count(n) > 1}
        if dupes:
            errors.append(f"package {pkg}/{subtest}: duplicate numbers {sorted(dupes)}")
        expected = BLUEPRINT[subtest][2]
        if len(nums) > expected:
            errors.append(
                f"package {pkg}/{subtest}: {len(nums)} questions exceeds blueprint ({expected})"
            )
        if sorted(set(nums)) != list(range(1, len(set(nums)) + 1)):
            errors.append(f"package {pkg}/{subtest}: numbering has gaps: {sorted(set(nums))}")
        if strict and len(nums) != expected:
            errors.append(
                f"package {pkg}/{subtest}: {len(nums)}/{expected} questions (strict mode)"
            )

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    status = "FAILED" if errors else "OK"
    print(f"\n{status}: {count} question file(s) checked, "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true",
                    help="require complete packages (blueprint counts)")
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    args = ap.parse_args()
    sys.exit(validate(args.bank_dir, args.strict))


if __name__ == "__main__":
    main()
