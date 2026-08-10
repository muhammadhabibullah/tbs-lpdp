# AGENTS.md — TBS LPDP Try Out Website

Free LPDP **Tes Bakat Skolastik (TBS)** try-out website. Frontend on **GitHub Pages** (React + Vite + TypeScript in `web/`), backend on **Supabase** (Postgres + RLS + RPC, anonymous auth, Storage). No other infrastructure — all trusted logic (timing, grading, answer-key secrecy) lives in `supabase/schema.sql`.

**Read `docs/TECHNICAL_REQUIREMENTS.md` before non-trivial work**, plus `docs/TECHNICAL_REQUIREMENTS_V2.md` for question feedback and `docs/TECHNICAL_REQUIREMENTS_V3.md` for question/package versioning, the daily report digest, package metadata, and deletion-safe statistics. Requirement IDs (FE-x, BE-x, QG-x, C-x, NF-x) continue one shared sequence across all three documents.

## Exam format (do not change without updating docs)

3 subtests, taken in order — `verbal` (23 q / 30 min), `kuantitatif` (25 q / 40 min), `pemecahan_masalah` (12 q / 20 min). Scoring: +5 correct, 0 otherwise, max 300. Five options A–E, exactly one correct. All content in Bahasa Indonesia.

## Repository map

- `docs/TECHNICAL_REQUIREMENTS.md` — the spec; source of truth for behavior
- `docs/TECHNICAL_REQUIREMENTS_V2.md` — v2: report-a-question feedback captured in `question_reports`
- `docs/TECHNICAL_REQUIREMENTS_V3.md` — v3: immutable releases, daily report email, package metadata/statistics
- `questions/schema.json` — JSON Schema every bank question must pass
- `questions/bank/<package_id>/<subtest_key>/<NNN>.json` — question bank (git = source of truth; Supabase is a derived copy)
- `questions/sample/` — real LPDP sample items collected from public tip sites; reference for which formats the bank must cover (not schema-valid, and some of their keys are wrong)
- `questions/generator/` — Python tooling: deterministic generators (`deret_angka.py`, `aritmetika.py`, `aljabar.py`, `kecukupan_data.py`, `peluang_kombinatorik.py`), `figures.py` (every SVG in the bank: measured figures for `geometri`, schematic value-free ones shared by the `kecukupan_data` geometry families), `validate_bank.py`, `push_to_supabase.py`
- `supabase/schema.sql` — full DDL, RLS policies, RPC functions (apply first)
- `supabase/schema_v2_reports.sql` — v2 question-feedback DDL/RPCs (apply after `schema.sql`; re-apply it whenever `schema.sql` is re-applied)
- `supabase/schema_v3.sql` — v3 release/history/statistics/digest DDL and final RPC definitions (apply after v2; re-apply after either earlier schema)
- `supabase/functions/question-report-digest/` — private daily report email Edge Function
- `supabase/maintenance.sql` — `pg_cron` retention, capacity, and report-digest jobs; apply last
- `docs/CAPACITY_GUARD.md` — how the storage ceiling (BE-18/FE-19/NF-11) stops new attempts before the free tier fills
- `exambrowser-ui/` — PUSMENDIK CBT screenshots; the UI must mimic these
- `web/` — the SPA (React + Vite + TS, `base: '/tbs-lpdp/'`, hash routing); see `web/README.md`
- `.github/workflows/deploy-web.yml` — builds `web/` and deploys to GitHub Pages

## Question work — use the skill and agents

For any question generation/editing, follow `.agents/skills/lpdp-question-generation/SKILL.md`. Key rules:

- Use the **question_generator** agent to write or regenerate questions; use the read-only **question_reviewer** agent to verify them before considering the work done. Route every reviewer failure back to `question_generator`.
- Computable types (`deret_angka`, `aritmetika`, `perbandingan_kuantitatif`, `aljabar`, `kecukupan_data`, `peluang_kombinatorik`) MUST come from the Python generators, never hand-written keys.
- Always finish with `python3 questions/generator/validate_bank.py` — it must exit 0.

## Commands

```bash
pip install -r questions/generator/requirements.txt   # once
python3 questions/generator/validate_bank.py           # validate whole bank
python3 questions/generator/deret_angka.py --help      # generate computable questions
python3 questions/generator/kecukupan_data.py --help   # ... every generator takes --seed / --bank-dir
python3 questions/generator/kecukupan_data.py --package 1 --count 1 --kind geometry  # data sufficiency on a figure
python3 questions/generator/figures.py                 # regenerate every figure (--check in CI)
python3 questions/generator/push_to_supabase.py --package 1 --dry-run
python3 questions/generator/push_to_supabase.py --package 1 --publish   # needs env below

cd web && npm install                                  # once
cd web && VITE_USE_MOCK=true npm run dev               # run the SPA off questions/bank, no Supabase
cd web && npm run build                                # typecheck + production build
```

`VITE_USE_MOCK=true` is a **dev-only** path: it serves the bank (answer keys included) from a
Vite middleware that cannot exist in a production build. Never set it for a deployed build.

`push_to_supabase.py` requires env vars `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. **Never commit or print the service-role key; never put it in `web/`.** Only the anon key may reach the client bundle.

## Conventions

- Question file IDs are derived from their path (`<package>-<subtest>-<NNN>`) — never rename bank files after they've been pushed.
- Figures are generated, never hand-drawn: add a builder to `figures.py` and run it. A figure may label only what its stem already gives, and a `kecukupan_data` figure labels no value at all — a drawing faithful enough to measure would answer the item.
- Client never writes tables directly. The final client RPC definitions live in `schema_v3.sql`; applying `schema.sql` or `schema_v2_reports.sql` requires re-applying v3 afterwards.
- `answer_keys` must never gain a client-readable RLS policy (constraint C-4).
- UI copy in Bahasa Indonesia; code, comments, and docs in English.
