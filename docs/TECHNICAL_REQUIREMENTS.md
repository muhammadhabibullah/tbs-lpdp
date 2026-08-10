# Technical Requirements — TBS LPDP Try Out Website

| | |
|---|---|
| Status | Draft v1.0 |
| Date | 2026-08-09 |
| Source | [README.md](../README.md), exambrowser UI screenshots (`exambrowser-ui/`), [ruangtes.id LPDP kisi-kisi](https://ruangtes.id/kisi-kisi/lpdp) |
| Stack | GitHub Pages (frontend) + Supabase (backend) — no self-hosted servers |

## 1. Purpose & Scope

A free web-based try-out (mock test) platform for the LPDP scholarship **Tes Bakat Skolastik (TBS)**. Users take a timed exam that mimics the official PUSMENDIK CBT "exambrowser" experience, then review their results with per-question explanations.

Two core use cases:

1. **Do exam** — timed, sectioned, with the same interaction model as the real CBT app.
2. **Review results** — score per section and total, plus per-question review with the correct answer and an explanation for every option.

Out of scope for v1: payment, leaderboards, essay/interview simulation, proctoring, native mobile apps.

## 2. System Overview

```
┌─────────────────────┐          ┌──────────────────────────────┐
│   GitHub Pages       │  HTTPS   │   Supabase                   │
│   React + Vite + TS  │ ───────► │   Postgres + PostgREST (API) │
│   SPA (static)       │          │   Auth (anonymous sign-in)   │
│                      │          │   Storage (question images)  │
└─────────────────────┘          └──────────────────────────────┘
          ▲                                     ▲
          │ deploy (GitHub Actions)             │ push question bank
┌─────────┴─────────────────────────────────────┴───────────────┐
│  Repo: question bank (JSON) + generator scripts + Claude      │
│  agents/skills that generate → validate → review → push       │
└───────────────────────────────────────────────────────────────┘
```

- **Frontend**: React 18 + Vite + TypeScript SPA, deployed to GitHub Pages via GitHub Actions. Uses `supabase-js` directly; there is no custom server.
- **Backend**: Supabase project. All exam logic that must be trusted (timing, grading, answer-key secrecy) lives in Postgres functions (RPC) and Row Level Security policies.
- **Content pipeline**: questions are authored by an LLM agent into `questions/bank/` (git-versioned JSON), validated and reviewed by scripts/agents, then pushed to Supabase by a Python script run by the developer.

## 3. Constraints

| ID | Constraint |
|----|-----------|
| C-1 | Hosting is GitHub Pages only: static files, no server-side code, no secrets in the bundle. Only the Supabase URL and `anon` public key may ship to the client. |
| C-2 | Backend is Supabase only (free tier assumed): Postgres, PostgREST, GoTrue auth, Storage. No edge servers of our own; Database Functions (RPC) are the compute layer. |
| C-3 | GitHub Pages serves from a sub-path (`/tbs-lpdp/`) unless a custom domain is added — the SPA router and Vite `base` must handle this. |
| C-4 | The answer key must never be readable by the client before the relevant section is finished (C-2 means this must be enforced in the database, not in JS). |
| C-5 | Question bank JSON in git is the source of truth; Supabase is a derived copy (re-pushable at any time, idempotently). |

## 4. Exam Format (source of truth)

Based on the LPDP TBS blueprint (ruangtes.id, checked 2026-08-09). One try-out **package** = one full TBS run:

| # | Subtest | Key | Questions | Duration | Passing grade* |
|---|---------|-----|-----------|----------|----------------|
| 1 | Penalaran Verbal | `verbal` | 23 | 30 min | 70 |
| 2 | Penalaran Kuantitatif | `kuantitatif` | 25 | 40 min | 75 |
| 3 | Pemecahan Masalah | `pemecahan_masalah` | 12 | 20 min | 35 |
| | **Total** | | **60** | **90 min** | **180 / 300** |

*Passing grades are indicative benchmarks (selection is competitive/rank-based); shown to the user in the result screen for context.

**Scoring**: correct = **+5**, wrong or blank = **0** (no negative marking). Max score 300.

**Question types per subtest** (used by the generator; each question is tagged):

- `verbal`: `sinonim`, `antonim`, `analogi`, `silogisme` (deductive conclusions), `kalimat_efektif` (sentence correction), `reading` (reading comprehension with a shared passage)
- `kuantitatif`: `aritmetika`, `aljabar`, `deret_angka` (number sequences, one or two blanks), `perbandingan_kuantitatif`, `kecukupan_data` (data sufficiency), `peluang_kombinatorik` (probability and counting), `soal_cerita` (word problems), `geometri`
- `pemecahan_masalah`: `logika_analitis` (analytical puzzles), `penalaran_kasus` (case reasoning), `interpretasi_data` (table/chart interpretation), `analisis_teks` (argumentative text analysis), plus `silogisme`, `soal_cerita` and `peluang_kombinatorik`

A type may be legal in more than one subtest; the authoritative mapping is `TYPES_BY_SUBTEST` in `questions/generator/common.py`, enforced by `validate_bank.py`.

Subtests are taken **in order** (verbal → kuantitatif → pemecahan_masalah); a finished section can never be re-entered.

## 5. Functional Requirements

### 5.1 Question generation pipeline (QG)

| ID | Requirement |
|----|-------------|
| QG-1 | A machine-readable question format is defined by `questions/schema.json` (JSON Schema). Every question has: id, package, subtest, number, type, question text, optional image, exactly five options `A`–`E`, exactly one `correct_option`, and an `explanations` object covering **all five** options (why correct / why wrong). |
| QG-2 | Questions live in git at `questions/bank/<package_id>/<subtest_key>/<NNN>.json` (one file per question); optional images at `questions/bank/<package_id>/images/`. Each package folder has a `package.json` manifest (title, description, subtest list). |
| QG-3 | The LLM agent (Claude Code, see §11) generates questions into the bank. For computable types (`deret_angka`, `aritmetika`, `perbandingan_kuantitatif`, `aljabar`, `kecukupan_data`, `peluang_kombinatorik`) the agent MUST use the deterministic Python generators in `questions/generator/` so the correct answer is computed, not guessed. `geometri` has no generator yet and is hand-written with its arithmetic verified in Bash. |
| QG-4 | `questions/generator/validate_bank.py` validates the whole bank: schema conformance, unique question numbers per subtest, correct counts per the §4 blueprint, `correct_option` exists among options, explanations present for all options, referenced images exist. CI-runnable (exit code ≠ 0 on failure). |
| QG-5 | A reviewer agent independently re-solves each generated question and rejects any question with zero or multiple defensible correct answers, or with an explanation that contradicts the key. |
| QG-6 | `questions/generator/push_to_supabase.py` idempotently upserts a package (questions, options, answer keys) to Supabase using the `service_role` key from environment variables (never committed), and uploads images to the `question-images` Storage bucket. Re-running it after edits updates in place (stable IDs from QG-2 paths). |
| QG-7 | All question content is in Bahasa Indonesia. |
| QG-8 | Figures are generated, not drawn: `questions/generator/figures.py` derives each `geometri` item's SVG from the numbers its stem states, so `--check` proves the committed images match the bank and a corrected question yields a corrected figure. A figure may label **only** quantities the stem gives — derived values (the trapezoid's height, the sector's arc length) are computed for layout but never drawn, since they are the work being asked for. |

### 5.2 Frontend (FE) — exambrowser UI mock

The UI replicates the PUSMENDIK CBT application shown in `exambrowser-ui/` screenshots.

| ID | Requirement |
|----|-------------|
| FE-1 | **Home / package list**: user picks a try-out package and starts an attempt with one click (anonymous auth happens transparently, see BE-1). Shows previous attempts with scores and a "review" link. |
| FE-2 | **Section start page**: before each subtest, show the subtest name, question count, duration, and instructions, with a **Mulai** button gated by a short countdown (per screenshot 4: "waktu tunggu untuk membaca petunjuk"). |
| FE-3 | **Question page** (screenshot 1): header with question number ("Soal nomor N") and package label; remaining-time display ("Sisa Waktu mm:ss"); **Informasi Soal** and **Daftar Soal** buttons; font-size control (A− / A / A+) applying to the question body; question text with optional image; five radio options A–E. |
| FE-4 | **Action buttons**: `Soal Sebelumnya` (red, prev), `Ragu-Ragu` (yellow, toggle doubt), `Simpan Jawaban` (green, save), `Soal Selanjutnya` (blue, next). On the **last question** of a section, `Soal Selanjutnya` becomes **Selesai** (screenshot 3). Selecting an option and pressing next/save both persist the answer (BE-3). |
| FE-5 | **Daftar Soal navigation grid** (screenshot 2) with the official color code — black: answered; blue: current question; white: unanswered; yellow: marked ragu-ragu. Clicking a number jumps to that question. |
| FE-6 | **Finish flow**: pressing Selesai with time remaining opens the **Konfirmasi Tes** dialog showing remaining time; user must tick a confirmation checkbox before the SELESAI button submits the section (screenshot 3). |
| FE-7 | **Timer enforcement**: countdown is derived from the server-issued section deadline (BE-2), not the device clock. When it reaches 0 the section auto-submits with whatever answers are saved, then transitions to the next section (or the result page after the last one). |
| FE-8 | **Result & review**: after the final section — total score, per-section score vs. passing grade, and a per-question review (user's answer, correct answer, all five explanations, doubt marks). Review data is only fetchable post-finish (BE-5). |
| FE-9 | **Resilience**: refresh/crash mid-section resumes the same attempt at the same deadline (state restored from Supabase). Leaving a section does not pause its timer. |
| FE-10 | Desktop-first layout matching the screenshots; must remain usable at ≥ 768 px width. Bahasa Indonesia UI copy. |

### 5.3 Backend (BE) — Supabase

| ID | Requirement |
|----|-------------|
| BE-1 | **Identity**: Supabase **anonymous sign-in**. The SPA silently creates/reuses an anonymous user per browser; all attempt data is keyed to `auth.uid()`. (Future: link to email without data loss.) |
| BE-2 | **Attempt lifecycle** via RPC (`security definer` Postgres functions): `start_attempt(package_id)`, `start_section(attempt_id)` → returns questions **without answer keys** plus a server-computed `deadline_at = now() + duration`; `finish_section(attempt_id)` → grades server-side and locks the section. Deadlines are enforced in SQL: writes after `deadline_at` (+5 s grace) are rejected, and `finish_section` is idempotent. |
| BE-3 | **Event log**: every user action is stored as an append-only event row — `start`, `save_answer`, `mark_doubt`, `unmark_doubt`, `finish` — with question id, payload (e.g. selected option), and server timestamp. Current answer state (latest answer + doubt flag per question) is kept in an `answers` table updated by the same RPC (`save_answer`, `toggle_doubt`). |
| BE-4 | **Questions API**: one question may have one image (public URL from the `question-images` bucket). Question text/options are readable only through `start_section`/`get_section_questions` for the caller's own active attempt. |
| BE-5 | **Answer-key secrecy** (C-4): `answer_keys` (correct option + explanations) has **no client-readable RLS policy**. Grading happens inside `finish_section`; `get_review(attempt_id)` returns keys and explanations only for sections the caller has finished. |
| BE-6 | **RLS everywhere**: users can only read/write their own attempts, answers, and events. Content tables (`packages`, `subtests`) are read-only to clients; all writes to them go through the service-role push script (QG-6). |
| BE-7 | **Scoring**: per §4 — `score = 5 × correct_count`, stored per section attempt at finish time, summed for the attempt total. |
| BE-15 | **Attempt-creation budget** (added for the public launch): `start_attempt` refuses to create an 11th attempt for the same user within a rolling hour, raising `P0005`. Only creation is capped — resuming an existing active attempt is never blocked. Bounds both the row growth and the scripted `get_review` key dump a loop over this RPC would otherwise produce. |
| BE-16 | **Event-log cap** (added for the public launch): `save_answer` / `toggle_doubt` stop appending to `answer_events` once a section attempt holds 500 rows; the write itself still succeeds. `answers` is bounded by its primary key, so this makes an attempt's total storage bounded too. `start` and `finish` events are never dropped. |

## 6. Data Model (Postgres)

Full DDL in [`supabase/schema.sql`](../supabase/schema.sql).

```
packages        (id, title, description, is_published, created_at)
subtests        (id, package_id→packages, key, name, position,
                 question_count, duration_seconds, passing_grade)
questions       (id, subtest_id→subtests, number, qtype, question_text,
                 image_url, difficulty)
question_options(question_id→questions, key 'A'..'E', text)         -- PK (question_id, key)
answer_keys     (question_id PK→questions, correct_option, explanations jsonb)
                                                                    -- NO client SELECT
attempts        (id, user_id→auth.users, package_id, status, started_at, finished_at,
                 total_score)
section_attempts(id, attempt_id→attempts, subtest_id, started_at, deadline_at,
                 finished_at, score, status 'active'|'finished')
answers         (section_attempt_id, question_id, selected_option, is_doubtful,
                 updated_at)                                        -- PK (section_attempt_id, question_id)
answer_events   (id, section_attempt_id, question_id, event_type, payload jsonb,
                 created_at)                                        -- append-only
```

Storage: bucket `question-images` (public read), objects named `<package_id>/<question_file_id>.<ext>`.

## 7. API Surface (RPC)

All client access goes through `supabase-js`: anonymous auth + these Postgres functions (PostgREST `/rpc/*`). No table is written directly by the client.

| Function | Args | Returns | Notes |
|----------|------|---------|-------|
| `start_attempt` | `p_package_id` | attempt row | Creates attempt (or returns the existing active one). |
| `start_section` | `p_attempt_id` | section_attempt + questions (+options, no keys) | Starts next unstarted section, sets `deadline_at`. Idempotent while active. |
| `save_answer` | `p_section_attempt_id, p_question_id, p_option` | ok | Rejects if finished or past deadline+5 s. Logs `save_answer` event. |
| `toggle_doubt` | `p_section_attempt_id, p_question_id, p_doubtful` | ok | Logs `mark_doubt` / `unmark_doubt`. |
| `finish_section` | `p_section_attempt_id` | section score + next subtest info | Grades vs `answer_keys`; idempotent; also called implicitly by any RPC that finds the deadline passed. |
| `get_attempt_state` | `p_attempt_id` | full state for resume | Powers FE-9 (current section, saved answers, deadline). |
| `get_review` | `p_attempt_id` | per-question review incl. keys & explanations | Only for finished sections (BE-5). |

## 8. Security & Integrity

- Only the `anon` key ships in the frontend bundle; the `service_role` key exists solely in the developer's environment for `push_to_supabase.py` (QG-6) and in GitHub Actions secrets if pushing runs in CI.
- RLS is enabled on every table; content tables expose read-only published data; user tables are scoped to `auth.uid()`; `answer_keys` is not client-readable at all (C-4/BE-5).
- Timing is trusted server-side only: `deadline_at` is computed and enforced in Postgres (BE-2); the client countdown is cosmetic.
- This is a practice tool, not a proctored exam — copy-protection/anti-screenshot measures are explicitly out of scope.

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NF-1 | Free-tier friendly: fits GitHub Pages limits and Supabase free tier (500 MB DB, 1 GB storage, 50k MAU). Event rows are small; one full attempt ≈ 200–400 event rows. |
| NF-2 | Question page interactions (save, doubt, navigate) feel instant: optimistic UI with background RPC; failed writes retry with visible warning. |
| NF-3 | Timer display accuracy within ±1 s of the server deadline (clock-skew corrected at `start_section` using server time). |
| NF-4 | The site works on current Chrome/Safari/Firefox/Edge; no browser extensions or lockdown required. |
| NF-5 | All bank content and DDL are reproducible from git (C-5): a fresh Supabase project is fully set up by `schema.sql` + one push-script run per package. |
| NF-10 | **Retention** (added for the public launch): `supabase/maintenance.sql` schedules two daily `pg_cron` sweeps — attempts started more than 7 days ago (cascading to their sections, answers and events), and anonymous `auth.users` untouched for 60 days that filed no question report. The 7-day window is stated to users in the site footer, so the two must stay in sync. Operational only: nothing in the app reads the jobs, and re-applying the schema files never undoes them. Where BE-15/BE-16 bound how fast the database grows, these bound its total. |

## 10. Repository Layout

```
tbs-lpdp/
├── README.md
├── CLAUDE.md                     # Claude Code project instructions
├── docs/
│   └── TECHNICAL_REQUIREMENTS.md # this document
├── .claude/
│   ├── agents/
│   │   ├── question-generator.md # writes bank questions (QG-3)
│   │   └── question-reviewer.md  # independent re-solve & veto (QG-5)
│   └── skills/
│       └── lpdp-question-generation/
│           └── SKILL.md          # format spec + generate→validate→review→push workflow
├── questions/
│   ├── schema.json               # JSON Schema for one question (QG-1)
│   ├── bank/                     # git-versioned question bank (QG-2)
│   │   └── <package_id>/
│   │       ├── package.json
│   │       ├── images/
│   │       └── <subtest_key>/<NNN>.json
│   └── generator/                # Python tooling (QG-3/4/6)
│       ├── common.py             # shared helpers (load schema, write question files)
│       ├── deret_angka.py        # number-sequence generator (1 or 2 blanks)
│       ├── aritmetika.py         # arithmetic/quant generator (computed answers)
│       ├── aljabar.py            # algebra generator (computed answers)
│       ├── kecukupan_data.py     # data-sufficiency generator (rank-decided keys)
│       ├── peluang_kombinatorik.py # probability/counting generator
│       ├── figures.py            # SVG figures for geometri items (QG-8)
│       ├── validate_bank.py      # bank validator, CI-runnable
│       ├── push_to_supabase.py   # idempotent upsert to Supabase
│       └── requirements.txt
├── supabase/
│   └── schema.sql                # tables, RLS, RPC functions (§6–§7)
├── exambrowser-ui/               # UI reference screenshots
└── web/                          # React + Vite + TS SPA (to be scaffolded)
```

## 11. Development Workflow (Claude Code agents & scripts)

Question production is agent-driven and gated by deterministic checks:

1. Developer asks Claude Code: *"generate package 1"* (or a single subtest). The **lpdp-question-generation** skill loads the format spec and blueprint.
2. The **question-generator** agent writes question JSON into `questions/bank/`, calling `deret_angka.py` / `aritmetika.py` for computable types so keys are provably correct (QG-3).
3. `validate_bank.py` must pass (QG-4).
4. The **question-reviewer** agent re-solves every question blind (without seeing the key), then compares; failures are regenerated (QG-5).
5. Developer runs `push_to_supabase.py --package 1` with service-role credentials (QG-6), then commits the bank to git.

## 12. Deployment

- **Frontend**: GitHub Actions workflow builds `web/` (`vite build` with `base: '/tbs-lpdp/'`) on push to `master` and deploys to GitHub Pages. `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are provided as repo Actions variables (they are public by design).
- **Backend**: `supabase/schema.sql` applied to the Supabase project (SQL editor or `supabase db push`), then `supabase/schema_v2_reports.sql`, then `supabase/maintenance.sql` (NF-10, once); anonymous sign-in enabled in Auth settings; `question-images` bucket created public-read.
- **Content**: push script per package (§11 step 5).

## 13. Milestones

| M | Deliverable | Depends on |
|---|-------------|-----------|
| M1 | Supabase schema + RLS + RPCs live; schema.sql in repo | — |
| M2 | Package 1 question bank generated, validated, reviewed, pushed | M1, agents/scripts |
| M3 | SPA: attempt flow (FE-1…FE-7, FE-9) against package 1 | M1 |
| M4 | Result & review screens (FE-8) | M2, M3 |
| M5 | GitHub Pages CI deploy + polish (FE-10, NF-2/3) | M3 |
| M6 | Package 2 content; repeatable content pipeline proven | M2 |

## 14. References

- LPDP TBS blueprint: https://ruangtes.id/kisi-kisi/lpdp (60 questions / 90 min / 3 subtests; +5 per correct, no penalty; benchmark 180/300)
- Exambrowser UI reference: `exambrowser-ui/*.png` (PUSMENDIK CBT Application guide)
- Supabase docs: anonymous sign-in, RLS, Database Functions, Storage
- GitHub Pages + Vite `base` path deployment
