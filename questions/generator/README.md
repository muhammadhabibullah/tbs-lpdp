# Question Generator

Scripts used by the Claude Code agents (and developers) to generate, validate, and publish questions. Be specific per question type: computable types get their own deterministic script so answer keys are computed, never guessed.

Setup: `pip install -r requirements.txt`

| Script | Purpose |
|--------|---------|
| `common.py` | Shared helpers: blueprint, allowed types per subtest, schema loading, canonical paths, number formatting, question assembly |
| `deret_angka.py` | Number sequences (`--package 1 --count 5 [--blanks 2] [--seed N]`); `--blanks 2` asks for the next **two** terms |
| `aritmetika.py` | Arithmetic / quantitative comparison (`--type aritmetika\|perbandingan_kuantitatif`) |
| `aljabar.py` | Linear equations, two-variable systems, quadratic evaluation, symmetric identities |
| `kecukupan_data.py` | Data sufficiency — decides the key by exact rank analysis and backs every "not sufficient" with a witness pair; `--kind geometry` draws from the three families that come with a figure |
| `peluang_kombinatorik.py` | Probability and counting (`--subtest kuantitatif\|pemecahan_masalah`) |
| `figures.py` | Every SVG in the bank (`--check` in CI, `--link` to point questions at their file). Measured figures for hand-authored `geometri`; schematic ones, shared per family and carrying no values at all, for generated `kecukupan_data` |
| `validate_bank.py` | Validate the whole bank; `--strict` also enforces blueprint counts. Must exit 0 before review/push |
| `push_to_supabase.py` | Validate/hash a complete package, upload content-addressed images, and atomically publish an immutable release (`--package 1 --dry-run` or `--package 1 --publish`); live runs need `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` |

All generators accept `--seed` (reproducible output) and `--bank-dir` (write to a scratch directory instead of `questions/bank`). They refuse to overwrite an existing question file.

Non-computable types (verbal, `soal_cerita`, `geometri`, `logika_analitis`, `penalaran_kasus`, `interpretasi_data`, `analisis_teks`) are written by the `question-generator` agent following `.claude/skills/lpdp-question-generation/SKILL.md`, then verified by the `question-reviewer` agent.

To add a new computable type: copy `deret_angka.py` as a template, compute the answer from the construction, encode believable mistakes as `(value, reason)` pairs so every "Salah." explanation names a specific slip, and screen the candidate against rival readings before writing it. Where the key is a *claim* rather than a number — as in `kecukupan_data` — decide it from the computation and discard draws whose computed key disagrees with what the template intended.

To add a figure: write a builder in `figures.py` returning a `Drawing`, register it (in `FIGURES` for a hand-authored question, in `SHARED_FIGURES` for a family a generator writes), and run `python3 figures.py --link`. Never edit an SVG by hand — `--check` compares every file in the bank against what its builder produces and fails CI on any difference. A figure may label only what its stem already gives; a schematic one labels nothing, which is why a builder for it takes no arguments.
