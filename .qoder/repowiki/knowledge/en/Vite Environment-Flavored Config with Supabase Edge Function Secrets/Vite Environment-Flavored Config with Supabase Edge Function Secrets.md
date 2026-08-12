---
kind: configuration_system
name: Vite Environment-Flavored Config with Supabase Edge Function Secrets
category: configuration_system
scope:
    - '**'
source_files:
    - web/.env.example
    - web/.env.local
    - web/.env.app
    - web/src/lib/config.ts
    - web/vite.config.ts
    - web/src/lib/supabase.ts
    - web/src/contexts/MaintenanceContext.ts
    - supabase/config.toml
    - supabase/functions/question-report-digest/index.ts
    - web/src-tauri/tauri.conf.json
---

## What system/approach is used

The repository uses a **Vite environment-variable-driven configuration** layered over three distinct build flavors (web, mock, offline/Tauri) plus a separate Supabase project config. There is no runtime config loader — all configuration is resolved at build time via `import.meta.env` and Vite's `loadEnv`, then inlined into the bundle so dead branches are tree-shaken away.

## Key files and packages

- `web/.env.example` — template of public-only env vars (`VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_TURNSTILE_SITE_KEY`, `VITE_USE_MOCK`, `VITE_BYPASS_MAINTENANCE`). Secret keys are explicitly excluded by comment.
- `web/.env.local` — developer copy with real values; mirrors `.env.example`.
- `web/src/lib/config.ts` — single source of truth for frontend config: exports `IS_OFFLINE_APP`, `SUPABASE_URL`, `SUPABASE_PUBLIC_KEY`, `TURNSTILE_SITE_KEY`, `isSupabaseConfigured`, plus shared error/status constants. Reads from `import.meta.env` and nulls out network-related values when `IS_OFFLINE_APP` is true.
- `web/vite.config.ts` — defines the three build flavors via `mode`: web production (default), dev mock (`VITE_USE_MOCK=true`), offline app (`VITE_OFFLINE=true`). Forces literals for `VITE_USE_MOCK` and `VITE_OFFLINE` through `define:` so Rollup can eliminate unused backend code per constraints C-29/C-31. Also sets `base` to `/tbs-lpdp/` for GitHub Pages or `./` for Tauri.
- `web/src/lib/supabase.ts` — lazy-loaded Supabase client constructed from `config.ts` values; guarded behind dynamic import in `lib/api.ts` to keep the ~110 kB client out of the eager bundle.
- `web/.env.app` — offline-app flavor file read only by `vite --mode app` (used by `npm run dev:app`, `build:app`, and the Tauri CLI); contains `VITE_OFFLINE=true`. The Pages deploy asserts it is unset so the local engine and answer keys stay out of the web bundle.
- `supabase/config.toml` — Supabase project identifier and edge function settings (`verify_jwt = false` for `question-report-digest`).
- `supabase/functions/question-report-digest/index.ts` — Deno edge function that reads secrets from Deno environment variables: `SUPABASE_SECRET_KEYS` (JSON map of named keys), `AUTOMATIONS_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_URL`, `RESEND_API_KEY`, `REPORT_DIGEST_TO`, `REPORT_DIGEST_FROM`.
- `web/src-tauri/tauri.conf.json` — desktop/mobile app metadata, window dimensions, CSP, updater endpoints, signing identity, and platform-specific targets.
- `web/src/contexts/MaintenanceContext.ts` — React context providing maintenance-mode state consumed by UI components; actual maintenance status is fetched at runtime from Supabase (not baked in).

## Architecture and conventions

1. **Three build flavors, one codebase.** `vite.config.ts` selects behavior based on `mode`:
   - Web production: connects to Supabase, base path `/tbs-lpdp/`.
   - Dev mock: runs against the local `questions/bank/` directory via `mockBankPlugin`, no network needed.
   - Offline app (`--mode app`): bundles the question bank as assets via `bankAssetPlugin`, strips all Supabase/Turnstile keys, serves from relative base `./`.

2. **Environment variable prefix convention.** All frontend-configurable values use the `VITE_` prefix so Vite exposes them as `import.meta.env.VITE_*`. This is enforced by `loadEnv(mode, process.cwd(), 'VITE_')` in `vite.config.ts`.

3. **Public vs secret separation.** Public keys (Supabase publishable/anon key, Turnstile site key) live in `.env.*` files committed to the repo (see comments in `.env.example` and `.env.local` marking them "PUBLIC by design (C-1)"). Service-role / automation / Resend API keys never enter the frontend bundle — they are injected at runtime into Supabase Edge Functions via platform environment variables.

4. **Offline-first nulling.** When `IS_OFFLINE_APP` is true, `config.ts` returns `undefined` for `SUPABASE_URL`, `SUPABASE_PUBLIC_KEY`, and `TURNSTILE_SITE_KEY`. Downstream code must handle these as absent; the constraint C-31 forbids any Supabase or Turnstile key leaking into the offline bundle.

5. **Lazy loading of heavy dependencies.** The Supabase client lives in `lib/supabase.ts` and is imported only from `lib/api.ts` via dynamic import, keeping it out of the initial bundle. `config.ts` deliberately avoids importing `@supabase/supabase-js` so it stays in the eager bundle.

6. **Maintenance mode is runtime-fetched.** `MaintenanceContext` provides a React context with default no-op values; the actual maintenance status is polled from Supabase at runtime, not baked into any env var.

7. **Edge function secrets via JSON map.** The digest function accepts either a flat `AUTOMATIONS_API_KEY`/`SUPABASE_SERVICE_ROLE_KEY` or a structured `SUPABASE_SECRET_KEYS` JSON object mapping names to keys, falling back gracefully if malformed.

## Conventions and constraints

- **Never commit secrets.** `.env.example` explicitly states service_role keys must not be placed there; `.env.local` is gitignored by convention.
- **Public keys are intentionally committed.** Comments in `.env.example` and `.env.local` mark Supabase publishable/anon keys and Turnstile site keys as "PUBLIC by design" — they are safe to embed in the bundle because they are RLS-bound.
- **Offline builds must not contain backend references.** Constraint C-29 requires the GitHub Pages build to have no local engine or answer keys; constraint C-31 requires the Tauri app bundle to hard-null Supabase and Turnstile keys. `vite.config.ts` enforces this by forcing `VITE_OFFLINE` and `VITE_USE_MOCK` to string literals before Rollup sees them.
- **Dev-only flags require `import.meta.env.DEV`.** `VITE_BYPASS_MAINTENANCE` is ignored in production builds even if accidentally configured, because the gating code checks `import.meta.env.DEV`.
- **Tauri builds override base path.** When `TAURI_ENV_PLATFORM` is set, `base` switches from `/tbs-lpdp/` to `./` so the app works from its own root inside the WebView.
- **Supabase Edge Functions validate required secrets.** The digest function throws an explicit error if `SUPABASE_URL`, `RESEND_API_KEY`, `REPORT_DIGEST_TO`, or `REPORT_DIGEST_FROM` are missing, returning HTTP 500 with a descriptive message.