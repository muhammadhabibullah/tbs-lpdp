# TBS LPDP Try Out

Free, browser-based practice tests for the LPDP **Tes Bakat Skolastik (TBS)**. The application reproduces the timed, section-by-section PUSMENDIK CBT experience and provides scores, answer reviews, and an explanation for every option after a section is finished.

[Open the live application](https://muhammadhabibullah.github.io/tbs-lpdp/)

> This is an independent practice project. It is not affiliated with, endorsed by, or an official service of LPDP or PUSMENDIK.

## What is included

- Six complete try-out packages with 360 Bahasa Indonesia questions.
- A 90-minute exam flow split into three ordered subtests.
- Server-authoritative deadlines, grading, and answer-key protection.
- Saved answers, doubt marks, question navigation, automatic timeout submission, and refresh recovery.
- Per-section and total results with a complete **Pembahasan** for every answer option.
- Revision-pinned attempts, so later question corrections cannot change an earlier attempt or review.
- Question reporting from the review page, with revision-aware operator digests.
- Package difficulty, authoring-model metadata, and deletion-safe aggregate mean/median statistics.
- Capacity controls, rate limits, data-retention jobs, and a Supabase-scheduled maintenance screen.
- Server-verified Turnstile protection for creation of new anonymous identities.
- An installable **offline application** for Windows, macOS, Linux, and Android that runs the whole try-out with no account and no internet connection.
- A development-only mock backend that runs directly from the Git question bank without Supabase.

## Exam format

| Subtest | Questions | Time | Benchmark |
|---|---:|---:|---:|
| Penalaran Verbal | 23 | 30 minutes | 70 |
| Penalaran Kuantitatif | 25 | 40 minutes | 75 |
| Pemecahan Masalah | 12 | 20 minutes | 35 |
| **Total** | **60** | **90 minutes** | **180 / 300** |

Each correct answer is worth 5 points. Wrong and unanswered questions receive 0 points; there is no negative marking. The benchmark values are practice references, not official or guaranteed selection thresholds.

## Architecture

```text
Git question bank + Python generators
                |
                | validate, review, publish
                v
GitHub Pages SPA  --------------------->  Supabase
React + Vite + TypeScript                Postgres + RLS + RPC
       |                                 Anonymous Auth + Storage
       |                                 Cron + private Edge Function
       | /bank/manifest.json
       | /bank/bank-<digest>.json
       v
Offline app (Tauri 2)  ------------->  GitHub Releases
same SPA, local exam engine            signed installers + latest.json
bundled question bank
```

On the web, the browser never grades an attempt and cannot read answer keys for an active section. Trusted exam logic lives in Supabase database functions; Row Level Security scopes attempt data to the current anonymous user. Git is the source of truth for question content, while Supabase stores immutable published releases.

The offline application necessarily carries the answer keys and grading on the device — it could not work without a network otherwise. That exposes nothing new: this repository is public and `questions/bank/` already contains every key. The two builds come from one codebase, and the build flavor is fixed at compile time, so the deployed website contains no local grading engine and the application contains no Supabase credentials.

## Quick start with the mock backend

Requirements: Node.js 22+ and npm.

```bash
cd web
npm install
VITE_USE_MOCK=true npm run dev
```

Open <http://localhost:5173/tbs-lpdp/>. Mock mode serves `questions/bank/` through a development-only Vite plugin and stores attempt state in `localStorage`. It is excluded from production builds so question keys are not bundled into the deployed site.

See [`web/README.md`](web/README.md) for mock maintenance states, local-storage details, and frontend implementation notes.

## Run against Supabase

### 1. Configure the database

Create a Supabase project, enable anonymous sign-ins, then apply the SQL files in this order:

```text
supabase/schema.sql
supabase/schema_v2_reports.sql
supabase/schema_v3.sql
supabase/schema_v4_maintenance_mode.sql
supabase/maintenance.sql
```

The order is significant: later schemas own the final RPC definitions and grants. Reapply v2, v3, and v4 in order whenever an earlier application schema is reapplied. `maintenance.sql` is operational and should be applied last.

The optional [`supabase/backfill_v3_1_statistics.sql`](supabase/backfill_v3_1_statistics.sql) reconstructs qualified historical score statistics only when every completion is still retained. It deliberately aborts rather than create a partial sample.

### 2. Configure the frontend

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Set these public client values in `web/.env.local`:

```dotenv
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_<...>
VITE_TURNSTILE_SITE_KEY=<public Turnstile site key>
```

A legacy `VITE_SUPABASE_ANON_KEY` also works. Never put a Supabase secret or `service_role` key in `web/`; anything in the frontend bundle is public.

For production robot protection, also enable Cloudflare Turnstile under
**Supabase Authentication → Bot and Abuse Protection** using the private
Turnstile secret. The site key is public; the secret belongs only in Supabase.
Deploy the site-key-enabled frontend before enabling the Supabase switch. See
[`docs/TECHNICAL_REQUIREMENTS_V5.md`](docs/TECHNICAL_REQUIREMENTS_V5.md) for the
safe rollout order and the limits of AI-scraper deterrence.

### 3. Validate and publish question packages

Requirements: Python 3 and the generator dependencies.

```bash
pip install -r questions/generator/requirements.txt
python3 questions/generator/validate_bank.py
python3 questions/generator/push_to_supabase.py --package 1 --dry-run
```

To publish an immutable release, provide privileged credentials only in the local process environment:

```bash
SUPABASE_URL=https://<project-ref>.supabase.co \
SUPABASE_SERVICE_ROLE_KEY=<secret> \
python3 questions/generator/push_to_supabase.py --package 1 --publish
```

Repeat the publish command for packages 1–6. An unchanged package is idempotent; any content or metadata change creates a new immutable release.

The daily report digest additionally requires the private Edge Function, Resend configuration, a named Supabase automation key, and Vault values described in [`docs/TECHNICAL_REQUIREMENTS_V3.md`](docs/TECHNICAL_REQUIREMENTS_V3.md#93-supabase-configuration).

## Question workflow

Questions live at `questions/bank/<package>/<subtest>/<number>.json` and must conform to [`questions/schema.json`](questions/schema.json). Each item has exactly five options, one answer key, and an explanation for every option.

Computable question types are produced by deterministic Python generators so their keys are calculated rather than guessed. Generated or edited content must then be validated and independently reviewed before publication. Figures are generated by code and checked against their source definitions; committed SVG files should not be edited by hand.

Useful checks:

```bash
python3 questions/generator/validate_bank.py
python3 questions/generator/figures.py --check

cd web
npm run typecheck
npm run build
```

More detail is available in [`questions/generator/README.md`](questions/generator/README.md) and [`questions/bank/README.md`](questions/bank/README.md).

## Repository structure

```text
.
├── web/                         React, Vite, and TypeScript SPA
├── supabase/                    Schemas, migrations, tests, Cron, Edge Function
├── questions/
│   ├── bank/                    Six Git-versioned question packages
│   ├── generator/               Generation, figure, validation, and publish tools
│   ├── sample/                  Public format references (not canonical answer keys)
│   └── schema.json              Question JSON Schema
├── exambrowser-ui/              PUSMENDIK CBT visual references
├── docs/                        Requirements and operational documentation
└── .github/workflows/           GitHub Pages deployment and application releases
```

## Documentation

- [`docs/TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md) — core exam, frontend, backend, and security behavior.
- [`docs/TECHNICAL_REQUIREMENTS_V2.md`](docs/TECHNICAL_REQUIREMENTS_V2.md) — question feedback from Pembahasan.
- [`docs/TECHNICAL_REQUIREMENTS_V3.md`](docs/TECHNICAL_REQUIREMENTS_V3.md) — immutable releases, statistics, and the report digest.
- [`docs/TECHNICAL_REQUIREMENTS_V3_1.md`](docs/TECHNICAL_REQUIREMENTS_V3_1.md) — qualified mean/median statistics and metadata help.
- [`docs/TECHNICAL_REQUIREMENTS_V4.md`](docs/TECHNICAL_REQUIREMENTS_V4.md) — scheduled frontend maintenance mode.
- [`docs/TECHNICAL_REQUIREMENTS_V5.md`](docs/TECHNICAL_REQUIREMENTS_V5.md) — Turnstile-protected anonymous sign-in and AI-scraper deterrence.
- [`docs/TECHNICAL_REQUIREMENTS_V6.md`](docs/TECHNICAL_REQUIREMENTS_V6.md) — the offline desktop and Android application.
- [`docs/CAPACITY_GUARD.md`](docs/CAPACITY_GUARD.md) — free-tier capacity protection and retention strategy.

## Deployment

Pushes to `master` that change `web/` trigger [the GitHub Pages workflow](.github/workflows/deploy-web.yml). Configure these GitHub Actions repository variables:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY` (or the legacy `VITE_SUPABASE_ANON_KEY`)
- `VITE_TURNSTILE_SITE_KEY`

The workflow installs locked dependencies, type-checks the SPA, builds it with the `/tbs-lpdp/` base path, publishes the compiled question-bank artifact under `/tbs-lpdp/bank/`, and deploys `web/dist` to GitHub Pages. Backend migrations and question publication to Supabase are deliberate operator steps and are not run by the Pages workflow.

### Application releases

Pushing a `app-v*` tag triggers [the release workflow](.github/workflows/release-app.yml), which builds installers for macOS (Apple Silicon and Intel), Windows, and Linux, plus a signed Android APK, and collects them into a single draft GitHub Release together with the updater manifest. Signing keys are held only as GitHub Actions secrets. See [`web/README.md`](web/README.md) for the one-time setup and the release procedure.
