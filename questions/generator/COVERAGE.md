# Question-type coverage audit (tutorial screenshots)

Audit date: 2026-08-12. Scope: packages 1–6 and the ten tutorial screenshots supplied for package-7 planning.

## Existing bank

- The schema previously recognised 18 types. Every completed package has 60 questions; packages 2–6 share the current 23/25/12 type mix.
- Packages 1–6 contain 31 `deret_angka` items and no letter-sequence item. Packages 2–6 each devote five quantitative slots to number sequences.
- Existing `deret_angka.py` already covers geometric/Fibonacci rules, increasing or doubling differences, two interleaved tracks, alternating operations, a climbing-operand three-operation cycle, one/two tail blanks, and two anchored interior blanks.
- Existing `kecukupan_data.py` proves exact quantities by rational linear algebra. It cannot model a yes/no inequality predicate without confusing “the quantity is known” with “the truth value is known.”

## Screenshot-to-generator mapping

| Tutorial architecture | Before audit | Delivered support |
|---|---|---|
| Fibonacci, fixed differences/ratios, powers and combined operations | Covered | Retained in `deret_angka.py` |
| Two interleaved number tracks | Covered only as a tail question | Added `--leading`; it prints three later observations per track so the missing predecessor is anchored by two intervals |
| Three interleaved number tracks | Missing | Added `--template three_interleaved` and a rival-rule screen |
| Fixed `×m, −k, :m, +k` cycle | Missing | Added `--template fixed_four_operation_cycle`; exact division is constructed, subtraction/division double readings are rejected, and a legitimate repeated answer is allowed |
| One or two requested letters | Missing type | Added schema type `deret_huruf` and `deret_huruf.py --blanks 1\|2` |
| Increasing letter jumps | Missing | Added `increasing_steps` |
| Opposite/interleaved letter tracks | Missing | Added `opposite_interleaved` and `accelerating_interleaved` |
| Repeating letter-jump cycle | Missing | Added `four_step_cycle` |
| EJOTY-style +5 alphabet wrap | Missing | Added `five_step_modulo` |
| Anchored square-position letters (`Y, P, I, ..., A`) | Missing | Added `deret_huruf.py --interior` with unique-candidate screening |
| Fraction-comparison data sufficiency | Exact-quantity engine was unsuitable | Added `kecukupan_data_predikat.py`, with symbolic equivalence, all A–E sufficiency architectures, and printed counterexample witnesses |

The screenshots are architecture references, not answer-key sources. Cropped or underdetermined examples are not copied into the bank. New scripts redraw values, compute their own keys, reject rival continuations, and explain each generated distractor.

## Package 7 recipe

The quantitative total remains 25. Replace one of the former five number-sequence slots with `deret_huruf`:

```bash
python3 questions/generator/deret_angka.py --package 7 --count 1 --template fixed_four_operation_cycle --blanks 2 --seed SEED
python3 questions/generator/deret_angka.py --package 7 --count 1 --leading --seed SEED
python3 questions/generator/deret_angka.py --package 7 --count 1 --interior --seed SEED
python3 questions/generator/deret_angka.py --package 7 --count 1 --template three_interleaved --seed SEED
python3 questions/generator/deret_huruf.py --package 7 --count 1 --seed SEED
python3 questions/generator/kecukupan_data.py --package 7 --count 1 --kind geometry --seed SEED
python3 questions/generator/kecukupan_data_predikat.py --package 7 --count 1 --seed SEED
```

Use distinct recorded seeds. Generation order determines the next free quantitative question number, so the package generator must reserve the intended slots before running these commands. Finish with the question-reviewer workflow and `python3 questions/generator/validate_bank.py`.
