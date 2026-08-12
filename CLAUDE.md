# CLAUDE.md — TBS LPDP Try Out Website

Free LPDP **Tes Bakat Skolastik (TBS)** try-out website. Frontend on **GitHub Pages** (React + Vite + TypeScript in `web/`), backend on **Supabase** (Postgres + RLS + RPC, anonymous auth, Storage). No other infrastructure — all trusted logic (timing, grading, answer-key secrecy) lives in `supabase/schema.sql`.

The same SPA also ships as an **offline desktop/Android app** (v6, Tauri 2 in `web/src-tauri/`) that runs the exam against a local engine and a bundled question bank. That build has no Supabase at all; see "Build flavors" below.

**Read `docs/TECHNICAL_REQUIREMENTS.md` before non-trivial work**, plus `docs/TECHNICAL_REQUIREMENTS_V2.md` for the question-feedback feature (users reporting defective questions from Pembahasan) and `docs/TECHNICAL_REQUIREMENTS_V6.md` for the offline app. Requirement IDs (FE-x, BE-x, QG-x, AP-x, C-x, NF-x) used in issues/commits refer to those documents — each version continues the previous numbering, so an ID means one thing across all of them.

## Build flavors (v6 §2) — three, one codebase

| Flavor | Selector | Backend | Ships to |
|---|---|---|---|
| Web production | *(default)* | `supabaseApi` | GitHub Pages |
| Dev mock | `VITE_USE_MOCK=true`, dev server only | local engine + Vite bank middleware | never |
| Offline app | `vite --mode app` (`.env.app`) + Tauri | local engine + bundled/cached bank | GitHub Releases |

Both selectors are `define`d as literals in `vite.config.ts` so the dead branch is provably dead. **Never remove that `define`**: without constant folding Rollup keeps both backends in every bundle, putting the local engine (and answer keys) on GitHub Pages (C-29) or a Supabase key in the app (C-31). Both invariants are asserted in CI.

## Exam format (do not change without updating docs)

3 subtests, taken in order — `verbal` (23 q / 30 min), `kuantitatif` (25 q / 40 min), `pemecahan_masalah` (12 q / 20 min). Scoring: +5 correct, 0 otherwise, max 300. Five options A–E, exactly one correct. All content in Bahasa Indonesia.

## Repository map

- `docs/TECHNICAL_REQUIREMENTS.md` — the spec; source of truth for behavior
- `docs/TECHNICAL_REQUIREMENTS_V2.md` — v2: report-a-question feedback captured in `question_reports`
- `questions/schema.json` — JSON Schema every bank question must pass
- `questions/bank/<package_id>/<subtest_key>/<NNN>.json` — question bank (git = source of truth; Supabase is a derived copy)
- `questions/sample/` — real LPDP sample items collected from public tip sites; reference for which formats the bank must cover (not schema-valid, and some of their keys are wrong)
- `questions/generator/` — Python tooling: deterministic generators (`deret_angka.py`, `aritmetika.py`, `aljabar.py`, `kecukupan_data.py`, `peluang_kombinatorik.py`), `figures.py` (every SVG in the bank: measured figures for `geometri`, schematic value-free ones shared by the `kecukupan_data` geometry families), `validate_bank.py`, `push_to_supabase.py`
- `supabase/schema.sql` — full DDL, RLS policies, RPC functions (apply first)
- `supabase/schema_v2_reports.sql` — v2 question-feedback DDL/RPCs (apply after `schema.sql`; re-apply it whenever `schema.sql` is re-applied)
- `supabase/maintenance.sql` — `pg_cron` retention jobs (NF-10); apply last, once. Operational only — re-applying the schema files never undoes it
- `docs/CAPACITY_GUARD.md` — how the storage ceiling (BE-18/FE-19/NF-11) stops new attempts before the free tier fills
- `exambrowser-ui/` — PUSMENDIK CBT screenshots; the UI must mimic these
- `web/` — the SPA (React + Vite + TS, hash routing; `base: '/tbs-lpdp/'` on the web, `'./'` under Tauri); see `web/README.md`
- `web/src-tauri/` — the offline app shell (Tauri 2: config, Rust entry, capabilities, icons)
- `web/src-tauri/icon-source/` — icon manifest + the three Android adaptive layers; `npm run app:icons` regenerates `web/src-tauri/icons/` from them. Android launcher icons must be regenerated *after* `tauri android init`, which otherwise leaves the Tauri logo on the APK
- `web/vite/bank-reader.ts`, `web/vite/bank-artifact.ts`, `web/scripts/build-bank.ts` — compile `questions/bank/` into the published `manifest.json` + `bank-<digest>.json`; versions come from git history so the output is reproducible (AP-3/NF-32)
- `.github/workflows/deploy-web.yml` — builds `web/`, publishes the bank artifact, deploys to GitHub Pages
- `.github/workflows/release-app.yml` — tag `app-v*` → desktop matrix + signed Android APK → one GitHub Release

## Question work — use the skill and agents

For any question generation/editing, follow `.claude/skills/lpdp-question-generation/SKILL.md`. Key rules:

- Use the **question-generator** agent to write questions; use the **question-reviewer** agent to verify them before considering the work done.
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
python3 questions/generator/push_to_supabase.py --package 1   # needs env below

cd web && npm install                                  # once (Node ≥ 22.18)
cd web && VITE_USE_MOCK=true npm run dev               # run the SPA off questions/bank, no Supabase
cd web && npm run build                                # typecheck + web production build
cd web && npm run build:bank -- --out dist/bank        # publishable bank artifact (validates first)
cd web && npm run dev:app                              # offline-app UI in a plain browser
cd web && npm run app:dev                              # the Tauri app (needs a Rust toolchain)
cd web && npm run app:build                            # installers → src-tauri/target/release/bundle
cd web && npm run app:icons                            # regenerate app icons from web/public/favicon.svg
```

`VITE_USE_MOCK=true` is a **dev-only** path: it serves the bank (answer keys included) from a
Vite middleware that cannot exist in a production build. Never set it for a deployed build.

The offline app *does* contain answer keys and grading by design (C-28) — it has to, to work
offline — and this costs nothing, because `questions/bank/` is already public. C-4 ("no key
reaches the client") remains a property of the **web/Supabase** deployment only.

`push_to_supabase.py` requires env vars `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. **Never commit or print the service-role key; never put it in `web/`.** Only the anon key may reach the client bundle.

## Conventions

- Question file IDs are derived from their path (`<package>-<subtest>-<NNN>`) — never rename bank files after they've been pushed.
- Figures are generated, never hand-drawn: add a builder to `figures.py` and run it. A figure may label only what its stem already gives, and a `kecukupan_data` figure labels no value at all — a drawing faithful enough to measure would answer the item.
- Client never writes tables directly; every mutation goes through the RPCs in `schema.sql` (`start_attempt`, `start_section`, `save_answer`, `toggle_doubt`, `finish_section`, `get_attempt_state`, `get_review`) or `schema_v2_reports.sql` (`report_question`, `delete_question_report`).
- `answer_keys` must never gain a client-readable RLS policy (constraint C-4).
- Signing material — the Tauri updater minisign private key and the Android release keystore — lives only in GitHub Actions secrets, never in git (C-30). `web/src-tauri/tauri.conf.json` carries the **public** key; `release-app.yml` refuses to run while it is still the placeholder.
- UI copy in Bahasa Indonesia; code, comments, and docs in English.
