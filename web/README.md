# web/ — TBS LPDP try-out SPA

React 18 + Vite + TypeScript. One codebase, **three build flavors** (v6 §2);
the selector is inlined by Vite, so each bundle contains only its own backend:

| Flavor | Selector | Backend | Ships to |
|---|---|---|---|
| Web production | *(default)* | `supabaseApi` | GitHub Pages |
| Dev mock | `VITE_USE_MOCK=true`, dev server only | local engine + Vite bank middleware | never |
| Offline app | `--mode app` (`.env.app` sets `VITE_OFFLINE=true`) + Tauri | local engine + bundled/cached bank | GitHub Releases |

`vite.config.ts` `define`s both selectors as literals on purpose — an undefined
`import.meta.env.VITE_*` does not fold to a constant, and without folding Rollup
keeps *both* backends in every bundle, which is exactly what C-29 (no local
engine or answer key on GitHub Pages) and C-31 (no Supabase or Turnstile key in
the app) forbid.

The web flavor deploys to GitHub Pages under `/tbs-lpdp/`; all its state lives
in Supabase and is reached through the RPCs in
[`../supabase/schema.sql`](../supabase/schema.sql) and
[`../supabase/schema_v2_reports.sql`](../supabase/schema_v2_reports.sql), with
the final versioned RPC contracts in
[`../supabase/schema_v3.sql`](../supabase/schema_v3.sql), plus
[`../supabase/schema_v4_maintenance_mode.sql`](../supabase/schema_v4_maintenance_mode.sql)
for the global maintenance schedule. There is no custom application server;
the v3 report digest is a private Supabase Edge Function.

## Run it

```bash
npm install

# A. Against the git question bank, no Supabase project needed (dev only):
VITE_USE_MOCK=true npm run dev

# B. Against a real Supabase project:
cp .env.example .env.local   # fill VITE_SUPABASE_URL + VITE_SUPABASE_PUBLISHABLE_KEY
npm run dev

# C. Against Supabase while its maintenance window is active (dev only):
VITE_USE_MOCK=false VITE_BYPASS_MAINTENANCE=true npm run dev

# D. The offline app's UI in an ordinary browser (no Tauri, no persistence):
npm run dev:app

npm run build       # tsc --noEmit && vite build → dist/
npm run build:app   # same, offline flavor (bank artifact emitted into dist/bank)
npm run build:bank  # publishable bank artifact → dist/bank (validates first)
npm run typecheck
```

Node ≥ 22.18 is required: `scripts/*.ts` run under Node's native TypeScript
type stripping, with no extra tooling.

### Robot protection

Production can require Cloudflare Turnstile before Supabase creates a new
anonymous user. Existing browser sessions pass silently, and mock mode never
loads the challenge. Configure both halves; the browser widget by itself is not
a security boundary:

1. Create a Turnstile widget for the site and set its public site key as
   `VITE_TURNSTILE_SITE_KEY`.
2. In Supabase Dashboard, open **Authentication → Bot and Abuse Protection**,
   select Cloudflare Turnstile, enter the private secret, and enable CAPTCHA.

The secret must exist only in Supabase. See
[`../docs/TECHNICAL_REQUIREMENTS_V5.md`](../docs/TECHNICAL_REQUIREMENTS_V5.md)
for safe rollout/rollback order and the limits of scraper deterrence.

Open http://localhost:5173/tbs-lpdp/ (the `base` path matters).

### Search and social metadata

`index.html` defines the canonical GitHub Pages URL, search description, Open
Graph/Twitter cards, and JSON-LD for the educational app and its visible FAQ.
`public/sitemap.xml` and `public/robots.txt` are copied into the production
build. Private hash routes for active attempts and reviews are marked `noindex`
at runtime by `components/RouteMetadata.tsx`.

If the deployment moves to a custom domain, update the absolute origin in
`index.html`, `public/sitemap.xml`, and `public/robots.txt` together. Submit the
sitemap URL to Google Search Console or Bing Webmaster Tools after deployment;
GitHub project sites cannot place a project-specific robots file at the shared
`muhammadhabibullah.github.io/robots.txt` host root.

### Mock mode

`vite/mock-bank-plugin.ts` serves `questions/bank/` at `/__mock/bank.json`, and
`src/lib/localApi.ts` reimplements the RPC semantics (immutable release
snapshots, attempt pinning, server deadline + 5 s grace, idempotent finish,
keys only for finished sections, and monotonic package statistics) against
`localStorage`. The plugin is `apply: 'serve'`, and `VITE_USE_MOCK` is inlined at
build time, so **neither the mock nor any answer key can reach the web
production bundle** (C-4/C-11/C-29). Reset a mock run by clearing the
`tbs-lpdp.mock.v3` key.

To rehearse the maintenance UI in mock mode, set a window in the browser
console and reload. ISO timestamps may use `Z` or an explicit offset:

```js
localStorage.setItem('tbs-lpdp.mock.maintenance', JSON.stringify({
  enabled: true,
  starts_at: '2026-08-15T22:00:00+07:00',
  ends_at: '2026-08-16T01:00:00+07:00',
  message: 'Maintenance sistem sedang dilakukan.'
}))
```

Use a start within the next four hours for the warning banner, or a start in
the past and end in the future for the blocking screen. Remove the key to turn
the mock schedule off.

For a faster fixed state, restart the dev server with
`VITE_MOCK_MAINTENANCE_PHASE=warning` or
`VITE_MOCK_MAINTENANCE_PHASE=maintenance` alongside `VITE_USE_MOCK=true`.

## Layout

```
src/
├── lib/
│   ├── types.ts        # RPC payload shapes, the ExamApi interface, Bank shapes
│   ├── api.ts          # lazy backend pick (supabase | local) + retry helper
│   ├── supabaseApi.ts  # supabase-js: anonymous auth + v3 RPCs
│   ├── localApi.ts     # local exam engine — dev mock and offline app (AP-2)
│   ├── bankSource.ts   # dev / offline bank sources, manifest check + swap (AP-4)
│   ├── bankSchema.ts   # manifest contract, shared with scripts/build-bank.ts
│   ├── appRuntime.ts   # Tauri seam: openExternal, app version, platform
│   ├── appUpdate.ts    # AP-6 desktop updater, AP-7 Android version check
│   ├── supabase.ts     # client + ApiError + pg error codes
│   └── clock.ts        # server-time skew, countdown formatting (NF-3)
├── contexts/
│   └── MaintenanceContext.ts # global warning/block state
├── pages/
│   ├── HomePage.tsx    # FE-1 packages + attempt history
│   ├── AttemptPage.tsx # flow controller: intro → exam → next → review
│   ├── SectionIntro.tsx# FE-2 countdown-gated Mulai
│   ├── ExamPage.tsx    # FE-3/4/5/6/7 question screen
│   └── ReviewPage.tsx  # FE-8 score + explanations, FE-11…16 report a question
└── components/         # AppShell, Modal, DaftarSoal, InformasiSoal, KonfirmasiTes,
                        # LaporSoal, MaintenanceGate, HumanVerificationGate,
                        # DownloadApp (FE-42), UpdateControls (AP-4/6/10)

vite/
├── bank-reader.ts       # compiles questions/bank → { packages, questions } (AP-3)
├── bank-artifact.ts     # bank-<digest>.json + manifest.json (NF-32)
├── mock-bank-plugin.ts  # dev middleware for the above (serve only)
└── bank-asset-plugin.ts # bundles the artifact into the offline app
scripts/
├── build-bank.ts             # CLI: publishable bank artifact
└── patch-android-signing.ts  # release signing for the generated Gradle project
src-tauri/                    # Tauri 2 shell: config, Rust entry, capabilities
```

## Notes

- **Routing is hash-based on purpose.** GitHub Pages has no rewrites, so a
  refresh mid-exam on `/tbs-lpdp/attempt/<id>` would 404 (C-3 + FE-9).
- **The countdown is cosmetic.** It is derived from the server-issued
  `deadline_at` corrected by the skew measured from each RPC's `server_time`;
  the database rejects late writes regardless of what the browser shows.
- **The intro screen renders before `start_section`**, so reading the
  instructions never eats section time.
- **Reporting a question is only possible from Pembahasan** (v2 §1.1): the RPC
  itself refuses any question whose section the caller has not finished, so the
  report surface can never leak which answer is right mid-exam.
- **Attempts are pinned to a package release.** Active questions, grading,
  history, review, and reports resolve through that immutable release even
  after a corrected package is published.
- **Writes are optimistic** (NF-2): selecting an option updates the UI at once
  and retries the RPC 3× with backoff; a terminal failure shows a warning strip,
  and a `P0004` (deadline passed) response moves the user on.
- **Maintenance is frontend-only** (v4 C-18): the global gate probes before
  routes mount and blocks the official SPA during the configured window, but
  existing Supabase RPCs deliberately remain callable.
- **Local maintenance bypass is development-only.** Set
  `VITE_BYPASS_MAINTENANCE=true` when running `npm run dev` against Supabase.
  The bypass also requires Vite's built-in `import.meta.env.DEV`, which is
  always `false` in a production build; configuring the flag in GitHub Actions
  cannot bypass maintenance on the deployed site.

## Offline app (v6)

The Tauri 2 shell in `src-tauri/` wraps this same SPA and runs it against the
local exam engine: no account, no CAPTCHA, no network needed to take a try-out.
Two update planes, deliberately decoupled:

- **Question bank (AP-4).** `deploy-web.yml` publishes
  `https://muhammadhabibullah.github.io/tbs-lpdp/bank/{manifest.json,bank-<digest>.json}`
  on every push that touches the bank. The app checks the manifest once per
  launch (5 s timeout, silent when offline) and on the **Perbarui Bank Soal**
  button, verifies the SHA-256, writes it atomically into the app data
  directory, and hot-swaps it. Running and finished attempts are unaffected —
  they stay pinned to the release snapshot stored with the attempt.
- **Application (AP-6/AP-7).** `release-app.yml` publishes signed installers and
  `latest.json`. Desktop updates in place through `tauri-plugin-updater`;
  Android compares versions against `api.github.com` and opens the APK download,
  since the updater plugin has no Android implementation. `.deb`/`.rpm` installs
  cannot self-update — the dialog links to the release page instead.

Versions are visible together on the home page: *Aplikasi v… · Bank soal …*
(AP-10). `bank_schema_version` in the manifest is the only coupling: a bank that
needs a newer app is not downloaded, and the app says so (AP-5).

### Run it

```bash
npm run app:dev       # tauri dev  (Rust toolchain required)
npm run app:build     # tauri build → installers in src-tauri/target/release/bundle
npm run app:android   # tauri android build --apk  (Java 17 + Android SDK/NDK)
```

`npm run dev:app` runs the same UI in an ordinary browser — useful for layout
work. Outside Tauri there is no persistent bank cache and no updater, so the app
falls back to the bundled snapshot on each load.

### One-time operator setup (v6 §5)

Both keys live **only** in GitHub Actions secrets, never in git (C-30):

1. `npm run tauri signer generate -- -w ~/.tauri/tbs-lpdp.key` → commit the
   **public** key into `src-tauri/tauri.conf.json` (`plugins.updater.pubkey`,
   currently the placeholder `REPLACE_WITH_MINISIGN_PUBLIC_KEY`), and add
   secrets `TAURI_SIGNING_PRIVATE_KEY` and
   `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. `release-app.yml` refuses to run while
   the placeholder is still there.
2. `keytool -genkeypair -v -keystore release.jks -keyalg RSA -keysize 2048 \
   -validity 10000 -alias tbs-lpdp` → add secrets `ANDROID_KEYSTORE_B64`
   (`base64 -i release.jks`), `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`,
   `ANDROID_KEY_PASSWORD`. **Back the keystore up privately** — losing it
   permanently breaks in-place APK upgrades for every existing install.

### Cutting a release

```bash
# bump "version" in src-tauri/tauri.conf.json, commit, then:
git tag app-v0.1.0 && git push origin app-v0.1.0
```

CI asserts the tag matches the config version, builds the desktop matrix
(macOS aarch64 + x86_64, Windows NSIS, Linux AppImage/deb/rpm) and a signed
arm64 APK into one **draft** release. Review it, then publish. The web home
page resolves its download links from the latest published release at runtime,
so no site rebuild is needed.

## Deployment

`.github/workflows/deploy-web.yml` builds on pushes to `master` that touch
`web/` or `questions/`. Set repo **variables** (Settings → Secrets and variables
→ Actions → Variables) `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, and
`VITE_TURNSTILE_SITE_KEY`. All are public values; the Supabase privileged key
and Turnstile secret must never appear here. The workflow asserts that
`VITE_OFFLINE` and `VITE_USE_MOCK` are unset and that the built bundle carries
no local engine (C-29), then publishes the bank artifact alongside the site.

### Which key?

Newer Supabase projects issue a **publishable** key (`sb_publishable_…`); older
ones issue the legacy **anon** JWT. They are the same thing for our purposes —
a public, RLS-bound client key — so the app reads
`VITE_SUPABASE_PUBLISHABLE_KEY` and falls back to `VITE_SUPABASE_ANON_KEY`. The
matching privileged key (**secret** `sb_secret_…`, formerly `service_role`)
belongs only in `push_to_supabase.py`'s environment.
