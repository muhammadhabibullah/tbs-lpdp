# Contributing

Thanks for helping improve this free LPDP TBS try-out. This document covers how
to set the project up, the rules a change has to respect, and what to check
before opening a pull request.

Code, comments, commits, and documentation are written in **English**. Anything
a user reads in the interface — and every question — is in **Bahasa Indonesia**.

## Ways to contribute

- **Report a defective question.** The fastest path needs no Git: open the
  **Pembahasan** page after finishing a section and use the report button. The
  report records the exact question revision you saw.
- **Report a bug or request a feature.** Open a GitHub issue describing what you
  did, what happened, and what you expected. Include the build flavor (website,
  desktop app, or Android app) and its version.
- **Contribute code, questions, or documentation.** Fork, branch, and open a
  pull request as described below.

## Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Node.js + npm | >= 22.18 | the SPA, the bank build scripts |
| Python | 3.12 (3.10+ works) | question generators and validation |
| Rust toolchain | stable | only for building the offline Tauri app |

```bash
git clone https://github.com/muhammadhabibullah/tbs-lpdp.git
cd tbs-lpdp
pip install -r questions/generator/requirements.txt
cd web && npm install
```

## Running it locally

The quickest loop needs no Supabase project at all — mock mode serves
`questions/bank/` through a development-only Vite plugin and keeps attempt state
in `localStorage`:

```bash
cd web
VITE_USE_MOCK=true npm run dev     # open http://localhost:5173/tbs-lpdp/
```

Other flavors:

```bash
npm run dev:app     # the offline app's UI in a plain browser (no Tauri)
npm run app:dev     # the real Tauri app (needs the Rust toolchain)
npm run dev         # against a real Supabase project — see below
```

The `/tbs-lpdp/` base path matters; the bare `localhost:5173` will 404.

### Against a real Supabase project

Only needed when changing backend behavior. Create a project, enable anonymous
sign-ins, then apply the SQL **in this order**:

```text
supabase/schema.sql
supabase/schema_v2_reports.sql
supabase/schema_v3.sql
supabase/schema_v4_maintenance_mode.sql
supabase/maintenance.sql
```

The order is significant — later files own the final RPC definitions and grants.
**Re-applying any application schema means re-applying every later one, in
order.** `maintenance.sql` is operational (`pg_cron` jobs) and goes last.

Then copy `web/.env.example` to `web/.env.local` and fill in
`VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (or the legacy
`VITE_SUPABASE_ANON_KEY`), and `VITE_TURNSTILE_SITE_KEY`. Those three values are
public by design. Turnstile also needs its private secret configured in
**Supabase → Authentication → Bot and Abuse Protection**; deploy a site-key-
enabled frontend *before* enabling the Supabase switch.

## Rules a change must respect

These are enforced in review, and several are asserted in CI. Requirement IDs
(`FE-x`, `BE-x`, `QG-x`, `AP-x`, `C-x`, `NF-x`) refer to the documents in
[`docs/`](docs/) and form one shared sequence across every version.

- **Never remove the `defined` build-flavor literals in `web/vite.config.ts`.**
  Without constant folding, Rollup keeps both backends in every bundle, which
  would put the local exam engine and its answer keys on GitHub Pages (C-29) or
  a Supabase key inside the offline app (C-31).
- **`answer_keys` must never gain a client-readable RLS policy** (C-4). On the
  web, the browser never grades an attempt.
- **The client never writes tables directly.** Every mutation goes through an
  RPC in the Supabase schema files.
- **No secrets in `web/` or in Git.** The `service_role` key, the Turnstile
  secret, the Tauri updater private key, and the Android keystore live only in
  the local process environment or in GitHub Actions secrets (C-30). Anything in
  the frontend bundle is public.
- **`VITE_USE_MOCK=true` is development-only** and must never be set for a
  deployed build.
- **Never rename a question file after it has been published** — its ID is
  derived from its path (`<package>-<subtest>-<number>`).
- **Figures are generated, never hand-drawn.** Add a builder to
  `questions/generator/figures.py` and run it; do not edit committed SVGs.
- **Do not change the exam format** (3 subtests, 23/25/12 questions,
  30/40/20 minutes, +5 per correct answer, max 300) without updating
  `docs/TECHNICAL_REQUIREMENTS.md` in the same change.
- **The interface must keep mimicking the PUSMENDIK CBT** references in
  [`exambrowser-ui/`](exambrowser-ui/).

Read [`docs/TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md) before
non-trivial work; it is the source of truth for behavior.

## Contributing questions

Questions live at `questions/bank/<package>/<subtest>/<number>.json` and must
validate against [`questions/schema.json`](questions/schema.json): exactly five
options, one answer key, and an explanation for **every** option.

Computable types — `deret_angka`, `deret_huruf`, `aritmetika`,
`perbandingan_kuantitatif`, `aljabar`, `kecukupan_data`,
`peluang_kombinatorik` — **must** come from the deterministic Python generators
so their keys are calculated rather than guessed. Never hand-write those keys.

```bash
python3 questions/generator/deret_angka.py --help      # every generator takes --seed / --bank-dir
python3 questions/generator/kecukupan_data.py --package 1 --count 1 --kind geometry
python3 questions/generator/figures.py                 # regenerate every figure
python3 questions/generator/validate_bank.py           # must exit 0
```

A new or edited item should be re-solved independently before it is considered
done — the generators guarantee arithmetic, not that the item is a fair test.
See [`questions/generator/README.md`](questions/generator/README.md) and
[`questions/bank/README.md`](questions/bank/README.md) for the per-type detail.

Publishing to Supabase is a maintainer step and is never run by CI:

```bash
python3 questions/generator/push_to_supabase.py --package 1 --dry-run
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  python3 questions/generator/push_to_supabase.py --package 1 --publish
```

## Before opening a pull request

```bash
python3 questions/generator/validate_bank.py    # exits 0
python3 questions/generator/figures.py --check  # no figure drift

cd web
npm run typecheck
npm run build                                   # what CI runs
npm run build:app                               # if you touched the offline flavor
```

Then:

- Keep the change focused; unrelated refactors belong in their own pull request.
- Update the relevant document in `docs/` when behavior changes, and cite the
  requirement ID in the description.
- Describe how you verified the change, and note which flavors you exercised
  (website, mock, offline app).
- Say explicitly if a change requires re-applying SQL or re-publishing a
  package — those are manual operator steps.

Commit messages are short and imperative; a `type(scope):` prefix is welcome but
not required.

## Releases (maintainers)

- Pushing to `master` with changes under `web/` or `questions/` triggers
  [`deploy-web.yml`](.github/workflows/deploy-web.yml): it type-checks, builds
  the SPA against the repository variables, asserts the web flavor and that no
  local engine reached the bundle, publishes the question-bank artifact, and
  deploys to GitHub Pages.
- Pushing an `app-v*` tag triggers
  [`release-app.yml`](.github/workflows/release-app.yml): desktop installers for
  macOS (Apple Silicon and Intel), Windows, and Linux, plus a signed Android
  APK, collected into one draft GitHub Release with the updater manifest. It
  refuses to run while the updater public key in
  `web/src-tauri/tauri.conf.json` is still the placeholder.
- Backend migrations and question publication are deliberate manual steps.

## License

By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
