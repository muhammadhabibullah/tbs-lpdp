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
| `kuantitatif` | Penalaran Kuantitatif | 25 | 40 min | 5 `aritmetika`, 3 `aljabar`, 5 `deret_angka` (1–2 of them two-blank), 4 `perbandingan_kuantitatif`, 2 `kecukupan_data`, 4 `soal_cerita`, 2 `geometri` |
| `pemecahan_masalah` | Pemecahan Masalah | 12 | 20 min | 4 `logika_analitis`, 2 `penalaran_kasus`, 2 `interpretasi_data`, 2 `peluang_kombinatorik`, 1 `analisis_teks`, 1 `soal_cerita` |

Difficulty mix per subtest: ~30% `easy`, ~50% `medium`, ~20% `hard`. Scoring is +5/0, so no trick "no correct answer" items — exactly one correct option, always.

The mix is a guideline; `validate_bank.py` enforces the per-subtest **totals**, not the split. Package 1 predates this mix and does not match it. Which types a subtest may carry *is* enforced, from `TYPES_BY_SUBTEST` in `questions/generator/common.py` — `soal_cerita` and `peluang_kombinatorik` are deliberately legal in two subtests each.

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
  "source": "claude-generated",
  "verified": false
}
```

Notes: `image` is a path relative to the package dir (`"images/geo-001.png"`) or `null`; `passage` carries the shared stimulus (see below); `verified` flips to `true` only after question-reviewer PASSes it.

`passage` is rendered above the stem with `white-space: pre-wrap`, so line breaks survive but column alignment by spaces does not (the font is proportional). Rules by type:

| Type | `passage` |
|------|-----------|
| `reading`, `analisis_teks` | **required** — the shared text; repeat the identical string in every question of the set |
| `interpretasi_data` | **required unless `image` is set** — a pipe-delimited table, header row first |
| everything else | must be `null` (the validator warns otherwise) |

Table convention for `interpretasi_data` — `|` separators, never space padding:

```
Tingkat Pendidikan | Jumlah Perawat
Vokasi (D3)        | 24
Sarjana (S1)       | 41
Ners               | 18
Spesialis          | 3
```

## The question types

Eleven of the eighteen types are traditional; these seven were added after comparing the bank with real LPDP sample items in `questions/sample/`. Each has a format contract that has to be followed exactly, because candidates recognise these formats on sight.

- **`silogisme`** (verbal, also legal in `pemecahan_masalah`) — premises then `Simpulan yang tepat adalah ...`. The key must follow *necessarily*; the strongest distractors are conclusions that are merely probable, that reverse the implication, or that over-generalise from "tidak semua"/"sebagian". Include some items whose correct answer is a hedge (`... belum tentu ...`), as in real sets.
- **`kalimat_efektif`** (verbal) — a flawed sentence, then five rewrites. Exactly one must be correct under standard *kalimat efektif* rules (no redundant words, clear subject and predicate, consistent conjunction, PUEBI spelling). Every distractor must break a **nameable** rule, and the explanation must name it. Do not write items where two rewrites are both defensible — this is the easiest type to get wrong.
- **`aljabar`** (kuantitatif) — linear equations, two-variable systems, evaluating expressions, symmetric identities. **Script-generated.**
- **`kecukupan_data`** (kuantitatif) — a question, two numbered statements, and the fixed five options (see `OPTIONS` in `kecukupan_data.py`; never re-word them). The key is a claim about three separate facts — (1) alone, (2) alone, both — so it is decided by computation, never by eye. **Script-generated.**
- **`peluang_kombinatorik`** (kuantitatif and pemecahan_masalah) — probability and counting. Probabilities print as reduced fractions (`12/95`), never decimals. **Script-generated.**
- **`interpretasi_data`** (pemecahan_masalah) — a table or chart, then a question whose options are claims about it. Every option must be decidable from the data alone; the classic key is a superlative ("paling sedikit"), and the classic distractor is a plausible claim the table simply does not cover — which must be labelled as such in its explanation.
- **`analisis_teks`** (pemecahan_masalah) — a short argumentative text (an editorial, a report), then a question about its main problem, the writer's stance, or an implied conclusion. Distractors should be statements that appear in the text but are supporting detail rather than the main point.

## Workflow

1. **Generate** — run the `question-generator` agent. Computable types MUST come from the deterministic scripts (they write valid files directly and print what they created):
   ```bash
   python3 questions/generator/deret_angka.py --package 1 --count 4              # next term
   python3 questions/generator/deret_angka.py --package 1 --count 1 --blanks 2   # next two terms
   python3 questions/generator/aritmetika.py --package 1 --count 5 --type aritmetika
   python3 questions/generator/aritmetika.py --package 1 --count 4 --type perbandingan_kuantitatif
   python3 questions/generator/aljabar.py --package 1 --count 3
   python3 questions/generator/kecukupan_data.py --package 1 --count 2
   python3 questions/generator/peluang_kombinatorik.py --package 1 --count 2 --subtest pemecahan_masalah
   ```
   Every script takes `--seed` for reproducible output and `--bank-dir` to write somewhere other than `questions/bank` (use a scratch dir when experimenting — the scripts refuse to overwrite an existing file).

   Verbal, `soal_cerita`, `geometri`, `interpretasi_data`, `analisis_teks` and the pemecahan_masalah logic types are written by the agent. Anything with a number in it — `geometri` answers, the totals in an `interpretasi_data` table — still gets checked with a quick Python calculation via Bash before it is saved.
2. **Validate** — `python3 questions/generator/validate_bank.py` must exit 0 (schema, counts vs blueprint, unique numbers, key ∈ options, all 5 explanations, images exist).
3. **Review** — run the `question-reviewer` agent (blind re-solve). Regenerate every FAIL, then re-validate. Set `"verified": true` on PASSed questions.
4. **Push** — developer-run, needs `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in env:
   ```bash
   python3 questions/generator/push_to_supabase.py --package 1
   ```
   Idempotent upsert; safe to re-run after edits. Never expose the service-role key to the frontend or commit it.

## Style rules for authored content

- Formal Bahasa Indonesia, matching official PUSMENDIK CBT phrasing; no slang, no first person.
- Stems end with `...` for completion-style items (sinonim/antonim show the stimulus word in CAPITALS, e.g. `INSINUASI = ...`).
- Distractors encode believable mistakes (off-by-one in sequences, near-synonyms, reversed analogy order) — never random noise.
- Reading passages: 120–200 words, neutral topics (science, education, environment); questions answerable from the passage alone. `analisis_teks` texts are shorter (80–140 words) and must actually argue something.
- **Vary the item architecture across packages, not just the wording.** A candidate who has sat an earlier package must not be able to shortcut a later one by pattern. Two habits caught in review of package 2: reusing the same reading stem set in the same order (`Gagasan utama ...` → `Berdasarkan bacaan, ... karena ...` → `Simpulan ... paragraf ketiga ...`) with the same key letters and the same "... bukan pada X" closing device, and using a literal reversal of the stimulus pair as a distractor in almost every `analogi` item. Before writing a new package, read the same subtest in the previous one and deliberately pick different stem types (makna kata dalam konteks, tujuan penulis, pernyataan yang tidak sesuai) and different distractor devices. Cap any one distractor device at roughly two items per subtest.
- Numbers follow Indonesian notation: `1.215`, `19,5`, `Rp4.500,00`, and the typographic minus `−` (see `fmt_number` in `common.py`). Probabilities stay as reduced fractions.
- No real living public figures, no politically or religiously charged content, nothing culturally insensitive. Data in an `interpretasi_data` table is invented for the item; never present it as real statistics about a real institution.
