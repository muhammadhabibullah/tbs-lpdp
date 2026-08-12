---
name: lpdp-question-generation
description: Generate, validate, review, and push LPDP TBS try-out questions. Use whenever creating or editing question bank content in questions/bank, or when asked to "generate a package/subtest", "add questions", or "push questions to Supabase".
---

# LPDP TBS Question Generation

This skill defines the question format and the end-to-end content workflow for the TBS LPDP try-out website. The git question bank is the source of truth; Supabase is a derived copy.

## Blueprint (per package)

One package = one full TBS try-out, 60 questions, 90 minutes:

| Subtest key | Name | Questions | Duration | Type mix (guideline) |
|-------------|------|-----------|----------|----------------------|
| `verbal` | Penalaran Verbal | 23 | 30 min | 4 `sinonim`, 4 `antonim`, 5 `analogi`, 3 `silogisme`, 2 `kalimat_efektif`, 5 `reading` (1–2 passages) |
| `kuantitatif` | Penalaran Kuantitatif | 25 | 40 min | 5 `aritmetika`, 3 `aljabar`, 4 `deret_angka`, 1 `deret_huruf`, 4 `perbandingan_kuantitatif`, 2 `kecukupan_data`, 4 `soal_cerita`, 2 `geometri` |
| `pemecahan_masalah` | Pemecahan Masalah | 12 | 20 min | 4 `logika_analitis`, 2 `penalaran_kasus`, 2 `interpretasi_data`, 2 `peluang_kombinatorik`, 1 `analisis_teks`, 1 `soal_cerita` |

Difficulty mix per subtest, **from package 4 onwards**: ~15% `easy`, ~45% `medium`, ~40% `hard`. Packages 1–3 were built to an easier ~30/50/20 and are not to be rewritten; every *new* package aims at the harder mix, because the real test is harder than those first three. Scoring is +5/0, so no trick "no correct answer" items — exactly one correct option, always.

Where the extra difficulty comes from — pick the harder variant, never a murkier one. An item is harder because it takes more correct steps, not because it is vaguer:

- **More inference per item.** Prefer stems that hide the rule behind two things at once (an operation cycle *and* a climbing operand), reasoning that needs a case split, or a table whose claim needs two rows combined rather than one read off.
- **Less evidence, one checkable anchor.** The `--interior` stem is the model: fewer visible terms, but a printed value further along that a correct rule must land on. Difficulty from *withheld* evidence is fair; difficulty from ambiguity is not.
- **Negative and non-integer intermediates.** Sequences that dip negative, ratios that are fractions, percentages of percentages — arithmetic that punishes sloppiness without needing a calculator.
- **Distractors that are the near-miss.** The strongest option set is one where each wrong answer is the result of a specific, nameable slip (right rule applied one step too far, operand not carried forward, two operations merged into one). If a distractor is wrong for no describable reason, it is wasted.
- **Never** by trick wording, hidden assumptions, unstated units, or answers that hinge on a reading of the Indonesian rather than the mathematics.

The mix is a guideline; `validate_bank.py` enforces the per-subtest **totals**, not the split. Package 1 predates this mix and does not match it. Packages 1–6 use five `deret_angka`; **package 7 onward replaces one with `deret_huruf`**. Across the remaining four number sequences, include at least one two-blank item, one anchored `--interior` item, and the opt-in `fixed_four_operation_cycle` architecture. For package 7 specifically, make that fixed cycle the two-blank item, then use one `--leading`, one `--interior`, and one `--template three_interleaved` item; later packages must rotate architectures again. Of the two `kecukupan_data` items, use at least one geometry item and, from package 7 onward, prefer the predicate script for the other. Which types a subtest may carry *is* enforced from `TYPES_BY_SUBTEST` in `questions/generator/common.py` — `soal_cerita` and `peluang_kombinatorik` are deliberately legal in two subtests each.

## Directory layout

```
questions/bank/<package_id>/
├── package.json                  # {"id": 1, "title": "...", "description": "..."}
├── images/                       # optional; referenced as "images/<file>"
└── <subtest_key>/
    └── <NNN>.json                # 001.json … zero-padded, = question number
```

The question's stable ID is derived from its path: `<package_id>-<subtest_key>-<NNN>`. Never rename files after a package has been pushed to Supabase.

## Question JSON format

Authoritative schema: `questions/schema.json` (validate against it, don't trust memory). Shape:

```json
{
  "id": "1-verbal-001",
  "package": 1,
  "subtest": "verbal",
  "number": 1,
  "type": "sinonim",
  "question_text": "SEREBRUM = ...",
  "image": null,
  "passage": null,
  "options": [
    {"key": "A", "text": "Otak kecil"},
    {"key": "B", "text": "Otak besar"},
    {"key": "C", "text": "Sumsum tulang"},
    {"key": "D", "text": "Saraf pusat"},
    {"key": "E", "text": "Batang otak"}
  ],
  "correct_option": "B",
  "explanations": {
    "A": "Otak kecil adalah serebelum, bukan serebrum.",
    "B": "Benar. Serebrum adalah istilah anatomi untuk otak besar.",
    "C": "Sumsum tulang tidak berkaitan dengan istilah serebrum.",
    "D": "Saraf pusat mencakup otak dan sumsum, lebih luas dari serebrum.",
    "E": "Batang otak adalah struktur berbeda yang menghubungkan otak dan sumsum."
  },
  "difficulty": "easy",
  "source": "codex-generated",
  "verified": false
}
```

Notes: `image` is a path relative to the package dir (`"images/geo-001.png"`) or `null`; `passage` carries the shared stimulus (see below); `verified` flips to `true` only after question_reviewer PASSes it.

`passage` is rendered above the stem with `white-space: pre-wrap`, so line breaks survive but column alignment by spaces does not (the font is proportional). Rules by type:

| Type | `passage` |
|------|-----------|
| `reading`, `analisis_teks` | **required** — the shared text; repeat the identical string in every question of the set |
| `interpretasi_data` | **required unless `image` is set** — a pipe-delimited table, header row first |
| everything else | must be `null` (the validator warns otherwise) |

## Figures

Every SVG in the bank is generated by `questions/generator/figures.py` and none is edited by hand — `figures.py --check` fails CI if a file on disk differs from what the builder produces. There are two kinds, and the difference matters:

| Kind | Used by | Scaled? | Where it lives |
|------|---------|---------|----------------|
| **Measured** | hand-authored `geometri` items | yes — the drawing follows the stem's numbers | one entry per question in `FIGURES`, keyed by question id |
| **Schematic** | script-generated `kecukupan_data` geometry items | no — one fixed configuration per family, shared by every item of it | `SHARED_FIGURES`, keyed by filename; written by the generator via `ensure_shared_figure` |

A measured figure may label only what the stem already gives: the trapezoid's height and the sector's arc length are the work being asked for, and putting them in the picture answers the question.

A data-sufficiency figure goes further and labels **no** value at all. Its numbers arrive in the two statements, and the quantity the stem asks about is exactly what a candidate could recover from a faithful drawing with a protractor — so those figures name points and mark which lines are parallel and which angles are right, nothing more, and each carries the caption *Gambar tidak digambar menurut skala*. That is also what makes one file safe to share across every item of a family: it holds none of their numbers.

To add a figure: write (or reuse) a builder returning a `Drawing`, register it, and run `python3 questions/generator/figures.py --link`. A schematic builder takes no arguments — the moment one needs a parameter, the figure has started depending on the item, and the item's answer has started leaking into the picture.

Table convention for `interpretasi_data` — `|` separators, never space padding:

```
Tingkat Pendidikan | Jumlah Perawat
Vokasi (D3)        | 24
Sarjana (S1)       | 41
Ners               | 18
Spesialis          | 3
```

## The question types

The bank recognises nineteen types. Nine have especially strict format contracts because candidates recognise them on sight; `deret_huruf` is the newest, added after the tutorial-screenshot coverage audit.

- **`silogisme`** (verbal, also legal in `pemecahan_masalah`) — premises then `Simpulan yang tepat adalah ...`. The key must follow *necessarily*; the strongest distractors are conclusions that are merely probable, that reverse the implication, or that over-generalise from "tidak semua"/"sebagian". Include some items whose correct answer is a hedge (`... belum tentu ...`), as in real sets.
- **`kalimat_efektif`** (verbal) — a flawed sentence, then five rewrites. Exactly one must be correct under standard *kalimat efektif* rules (no redundant words, clear subject and predicate, consistent conjunction, PUEBI spelling). Every distractor must break a **nameable** rule, and the explanation must name it. Do not write items where two rewrites are both defensible — this is the easiest type to get wrong.
- **`deret_angka`** (kuantitatif) — number sequences. **Script-generated**, and the screening matters as much as the rule: every candidate is tested against rival readings (arithmetic, geometric, second difference, two/three interleaved tracks, alternating, Fibonacci) and thrown away if any of them fits the printed terms but continues differently. Four stem shapes are supported: a one-blank tail, a two-blank tail, `--leading` (the first term is missing, with three later observations per interleaved track so two equal intervals anchor it), and `--interior` (four terms, two blanks, then a printed anchor, e.g. `−9, −10, −8, −24, ..., ..., −138`). Rules span the whole list the official sets use: `+`, `−`, `×`, `:`, Fibonacci sums, second-difference climbs, and two/three-track *loncat angka*. Two operation-cycle architectures are distinct: `cycling_ops` repeats three operators while its operand keeps climbing, whereas opt-in `fixed_four_operation_cycle` repeats `×m, −k, :m, +k` with fixed operands, as in the screenshot architecture. Division is exact by construction, and a draw is rejected when its subtraction transition is also readable as exact integer division. A repeated answer is normally rejected, but the fixed four-cycle may legitimately return to an earlier printed value because its inverse operations make that repetition evidence of the rule.
- **`deret_huruf`** (kuantitatif) — alphabet-position sequences, with A=1 through Z=26. **Script-generated.** Supported families match the screenshot set: increasing jumps (`+1,+2,+3,...`), two opposite interleaved tracks, two interleaved tracks whose jumps increase, a four-step jump cycle, a constant `+5` sequence that wraps after Z, and the anchored descending-square positions `Y, P, I, ..., A`. It supports one or two tail blanks. Every tail item is screened against constant/second differences, interleaved tracks, three/four-step cycles, and modular steps; the interior square item is accepted only when exactly one A–Z candidate preserves its second difference. Do not mix letters and numbers in one item until a separate screened template exists.
- **`aljabar`** (kuantitatif) — linear equations, two-variable systems, evaluating expressions, symmetric identities. **Script-generated.**
- **`kecukupan_data`** (kuantitatif) — a question, two numbered statements, and the fixed five options (see `OPTIONS` in `kecukupan_data.py`; never re-word them). The key is a claim about three separate facts — (1) alone, (2) alone, both — so it is decided by computation, never by eye. **Script-generated.** `kecukupan_data.py` handles exact-quantity questions with rational linear algebra and includes geometry figures. `kecukupan_data_predikat.py` handles the screenshot's yes/no inequality architecture: it symbolically reduces the fraction comparison, checks every sufficiency key against a positive-integer model search, and prints concrete counterexamples for every insufficient statement. Never route a predicate item through the exact-quantity engine. Real sets lean on geometry and predicate variants because both punish deciding by appearance rather than proof.
- **`peluang_kombinatorik`** (kuantitatif and pemecahan_masalah) — probability and counting. Probabilities print as reduced fractions (`12/95`), never decimals. **Script-generated.**
- **`interpretasi_data`** (pemecahan_masalah) — a table or chart, then a question whose options are claims about it. Every option must be decidable from the data alone; the classic key is a superlative ("paling sedikit"), and the classic distractor is a plausible claim the table simply does not cover — which must be labelled as such in its explanation.
- **`analisis_teks`** (pemecahan_masalah) — a short argumentative text (an editorial, a report), then a question about its main problem, the writer's stance, or an implied conclusion. Distractors should be statements that appear in the text but are supporting detail rather than the main point.

## Workflow

1. **Generate** — run the `question_generator` agent. Computable types MUST come from the deterministic scripts (they write valid files directly and print what they created):
   ```bash
   python3 questions/generator/deret_angka.py --package 1 --count 3              # next term
   python3 questions/generator/deret_angka.py --package 1 --count 1 --blanks 2   # next two terms
   python3 questions/generator/deret_angka.py --package 1 --count 1 --interior   # hardest: 4 terms, 2 blanks, anchor
   python3 questions/generator/deret_angka.py --package 1 --count 1 --leading    # missing first term
   python3 questions/generator/deret_angka.py --package 1 --count 1 --template fixed_four_operation_cycle --blanks 2
   python3 questions/generator/deret_angka.py --package 1 --count 1 --template three_interleaved
   python3 questions/generator/deret_huruf.py --package 1 --count 1              # one letter
   python3 questions/generator/deret_huruf.py --package 1 --count 1 --blanks 2   # next two letters
   python3 questions/generator/deret_huruf.py --package 1 --count 1 --interior   # Y, P, I, ..., A family
   python3 questions/generator/aritmetika.py --package 1 --count 5 --type aritmetika
   python3 questions/generator/aritmetika.py --package 1 --count 4 --type perbandingan_kuantitatif
   python3 questions/generator/aljabar.py --package 1 --count 3
   python3 questions/generator/kecukupan_data.py --package 1 --count 2
   python3 questions/generator/kecukupan_data.py --package 1 --count 1 --kind geometry   # with a figure
   python3 questions/generator/kecukupan_data_predikat.py --package 1 --count 1          # yes/no inequality
   python3 questions/generator/peluang_kombinatorik.py --package 1 --count 2 --subtest pemecahan_masalah
   ```
   Every script takes `--seed` for reproducible output and `--bank-dir` to write somewhere other than `questions/bank` (use a scratch dir when experimenting — the scripts refuse to overwrite an existing file).

   `kecukupan_data.py --kind geometry` writes the shared SVG into the package's `images/` directory itself and points the question's `image` field at it; there is no separate step, and re-running it rewrites the identical bytes. `--kind word` restricts to the templates that need no figure. Aim for at least one geometry item per package — the official test always has some.

   Verbal, `soal_cerita`, `geometri`, `interpretasi_data`, `analisis_teks` and the pemecahan_masalah logic types are written by the agent. Anything with a number in it — `geometri` answers, the totals in an `interpretasi_data` table — still gets checked with a quick Python calculation via Bash before it is saved.
2. **Validate** — `python3 questions/generator/validate_bank.py` must exit 0 (schema, counts vs blueprint, unique numbers, key ∈ options, all 5 explanations, images exist).
3. **Review** — run the read-only `question_reviewer` agent (blind re-solve). Route every FAIL back to `question_generator`, regenerate it, and re-validate. After a question PASSes, have `question_generator` set `"verified": true`, then validate once more.
4. **Push** — developer-run, needs `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in env:
   ```bash
   python3 questions/generator/push_to_supabase.py --package 1
   ```
   Idempotent upsert; safe to re-run after edits. Never expose the service-role key to the frontend or commit it.

## Style rules for authored content

- Formal Bahasa Indonesia, matching official PUSMENDIK CBT phrasing; no slang, no first person.
- Stems end with `...` for completion-style items (sinonim shows the stimulus word with `=`, antonim with `><`, e.g. `INSINUASI = ...` or `PROMINEN >< ...`).
- Distractors encode believable mistakes (off-by-one in sequences, near-synonyms, reversed analogy order) — never random noise.
- Reading passages: 120–200 words, neutral topics (science, education, environment); questions answerable from the passage alone. `analisis_teks` texts are shorter (80–140 words) and must actually argue something.
- **Vary the item architecture across packages, not just the wording.** A candidate who has sat an earlier package must not be able to shortcut a later one by pattern. Two habits caught in review of package 2: reusing the same reading stem set in the same order (`Gagasan utama ...` → `Berdasarkan bacaan, ... karena ...` → `Simpulan ... paragraf ketiga ...`) with the same key letters and the same "... bukan pada X" closing device, and using a literal reversal of the stimulus pair as a distractor in almost every `analogi` item. Before writing a new package, read the same subtest in the previous one and deliberately pick different stem types (makna kata dalam konteks, tujuan penulis, pernyataan yang tidak sesuai) and different distractor devices. Cap any one distractor device at roughly two items per subtest.
- Numbers follow Indonesian notation: `1.215`, `19,5`, `Rp4.500,00`, and the typographic minus `−` (see `fmt_number` in `common.py`). Probabilities stay as reduced fractions, and so do the options of an arithmetic item whose working is in fractions — the order-of-operations format `a − b × c + [(d − e) : f]` (`gen_fraction_order_of_ops`) exists to test precedence and the `:` operator, and an option list of decimals invites a calculator instead. Its five options also sit in a tight band, as real ones do; a value an order of magnitude off the others is struck out on sight and stops being a distractor.
- No real living public figures, no politically or religiously charged content, nothing culturally insensitive. Data in an `interpretasi_data` table is invented for the item; never present it as real statistics about a real institution.
