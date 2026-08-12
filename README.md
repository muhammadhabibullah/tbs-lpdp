# TBS LPDP Try Out

Free, browser-based practice tests for the LPDP **Tes Bakat Skolastik (TBS)**. It
reproduces the timed, section-by-section PUSMENDIK CBT experience and gives
scores, answer reviews, and an explanation for every option once a section ends.

**[Open the live application](https://muhammadhabibullah.github.io/tbs-lpdp/)** —
also available as an **offline app** for Windows, macOS, Linux, and Android from
the [releases page](https://github.com/muhammadhabibullah/tbs-lpdp/releases), no
account and no internet required.

> An independent practice project. Not affiliated with, endorsed by, or an
> official service of LPDP or PUSMENDIK.

## Exam format

| Subtest | Questions | Time | Benchmark |
|---|---:|---:|---:|
| Penalaran Verbal | 23 | 30 minutes | 70 |
| Penalaran Kuantitatif | 25 | 40 minutes | 75 |
| Pemecahan Masalah | 12 | 20 minutes | 35 |
| **Total** | **60** | **90 minutes** | **180 / 300** |

Each correct answer is worth 5 points; wrong and unanswered questions score 0,
with no negative marking. Benchmarks are practice references, not official
selection thresholds.

## What is included

- Eight complete try-out packages with 480 Bahasa Indonesia questions.
- Server-authoritative deadlines, grading, and answer-key protection.
- Saved answers, doubt marks, navigation, auto-submit on timeout, refresh recovery.
- Per-section and total results with a full **Pembahasan** for every option.
- Revision-pinned attempts, so later corrections never alter a past attempt.
- Question reporting from the review page, with revision-aware operator digests.
- Package difficulty, authoring metadata, and deletion-safe score statistics.
- Capacity controls, rate limits, retention jobs, and a scheduled maintenance screen.
- Server-verified Turnstile protection for new anonymous identities.

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

On the web, the browser never grades an attempt and cannot read answer keys for
an active section: trusted exam logic lives in Supabase database functions, and
Row Level Security scopes attempt data to the current anonymous user. Git is the
source of truth for question content; Supabase stores immutable published
releases.

The offline app necessarily carries keys and grading on the device — it could
not work without a network otherwise — which exposes nothing new, since this
repository is public and `questions/bank/` already contains every key. Both
builds come from one codebase with the flavor fixed at compile time, so the
deployed website contains no grading engine and the app contains no Supabase
credentials.

## Quick start

Node.js 22.18+ and npm. No Supabase project needed — mock mode runs the whole
exam flow off the Git question bank:

```bash
cd web && npm install
VITE_USE_MOCK=true npm run dev     # http://localhost:5173/tbs-lpdp/
```

Mock mode is excluded from production builds, so question keys are never bundled
into the deployed site. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the Supabase
setup, the question-bank workflow, and the pre-pull-request checks, and
[`web/README.md`](web/README.md) for frontend implementation notes.

## Repository structure

```text
.
├── web/                         React, Vite, and TypeScript SPA (+ src-tauri/)
├── supabase/                    Schemas, migrations, tests, Cron, Edge Function
├── questions/
│   ├── bank/                    Git-versioned question packages
│   ├── generator/               Generation, figure, validation, and publish tools
│   ├── sample/                  Public format references (not canonical keys)
│   └── schema.json              Question JSON Schema
├── exambrowser-ui/              PUSMENDIK CBT visual references
├── docs/                        Requirements and operational documentation
└── .github/workflows/           GitHub Pages deployment and application releases
```

## Documentation

[`docs/TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md) is the source
of truth for behavior; each later version continues its numbering.

| Document | Covers |
|---|---|
| [V1](docs/TECHNICAL_REQUIREMENTS.md) | core exam, frontend, backend, security |
| [V2](docs/TECHNICAL_REQUIREMENTS_V2.md) | question feedback from Pembahasan |
| [V3](docs/TECHNICAL_REQUIREMENTS_V3.md) | immutable releases, statistics, report digest |
| [V3.1](docs/TECHNICAL_REQUIREMENTS_V3_1.md) | qualified mean/median and metadata help |
| [V4](docs/TECHNICAL_REQUIREMENTS_V4.md) | scheduled frontend maintenance mode |
| [V5](docs/TECHNICAL_REQUIREMENTS_V5.md) | Turnstile sign-in and scraper deterrence |
| [V6](docs/TECHNICAL_REQUIREMENTS_V6.md) | the offline desktop and Android app |
| [Capacity guard](docs/CAPACITY_GUARD.md) | free-tier capacity protection and retention |

## Contributing

Bug reports, question fixes, and pull requests are welcome — start with
[`CONTRIBUTING.md`](CONTRIBUTING.md). Defective questions can also be reported
straight from the Pembahasan page in the app, no GitHub account needed.

## License

[MIT](LICENSE).
