---
kind: build_system
name: Vite + Tauri Monorepo Build & Release Pipeline
category: build_system
scope:
    - '**'
source_files:
    - .github/workflows/deploy-web.yml
    - .github/workflows/pr.yml
    - .github/workflows/release-app.yml
    - web/package.json
    - web/vite.config.ts
    - web/vite/bank-asset-plugin.ts
    - web/vite/bank-artifact.ts
    - web/vite/mock-bank-plugin.ts
    - web/src-tauri/tauri.conf.json
    - web/src-tauri/Cargo.toml
    - scripts/bump_version.py
    - questions/generator/requirements.txt
    - supabase/functions/question-report-digest/index.ts
---

## What system/approach is used

The project builds a single React/Vite SPA that ships in two flavors from one codebase: a GitHub Pages web app and an offline desktop/Android application built with Tauri. The build pipeline is entirely driven by Vite scripts, npm workspaces (single `web/` package), Python helpers for the question bank, and three GitHub Actions workflows under `.github/workflows/`. There are no Makefiles or Dockerfiles; versioning is coordinated via a shared Python script.

## Key files and packages

- **Web build entry**: `web/package.json` defines `dev`, `build`, `build:bank`, `dev:app`, `build:app`, `tauri`, `app:dev`, `app:build`, `app:android`, `app:version` scripts. Node engine pinned to `>=22.18`; CI uses Node 22 and Python 3.12.
- **Build configuration**: `web/vite.config.ts` selects between three flavors at compile time via `define`: default (Supabase-backed web), mock (`VITE_USE_MOCK=true`), and offline app (`VITE_OFFLINE=true`). It sets `base` to `/tbs-lpdp/` for Pages and `./` for Tauri, and applies the `bankAssetPlugin` only in offline mode.
- **Bank bundling plugins**: `web/vite/bank-asset-plugin.ts` emits `bank/manifest.json` and `bank/bank-<digest>.json` into the offline bundle; `web/vite/mock-bank-plugin.ts` serves the same artifact during development; `web/vite/bank-reader.ts` and `web/vite/bank-artifact.ts` generate the digest from `questions/bank`.
- **Tauri packaging**: `web/src-tauri/tauri.conf.json` declares targets `app, dmg, nsis, appimage, deb, rpm, android`, updater endpoint pointing at GitHub Releases `latest/download/latest.json`, CSP, and signing identity placeholders. `web/src-tauri/Cargo.toml` and `Cargo.lock` are updated alongside `tauri.conf.json` by the version script.
- **Version coordination**: `scripts/bump_version.py` bumps semver across `web/src-tauri/tauri.conf.json`, `web/src-tauri/Cargo.toml`, `web/src-tauri/Cargo.lock`, and `web/package.json` simultaneously, accepting `patch | minor | major | X.Y.Z`.
- **CI pipelines**:
  - `.github/workflows/deploy-web.yml` — pushes to GitHub Pages on push to `master` when `web/**` or `questions/**` change. Runs `npm ci && npm run build`, asserts neither `VITE_OFFLINE` nor `VITE_USE_MOCK` is set (C-29), then runs `npm run build:bank -- --out dist/bank` to publish the question bank artifact under `/tbs-lpdp/bank/`.
  - `.github/workflows/pr.yml` — validates the question bank via `python3 questions/generator/validate_bank.py` on PRs touching `questions/**`.
  - `.github/workflows/release-app.yml` — triggered by tags `app-v*`. A guard job verifies the tag matches `tauri.conf.json` version and that the updater pubkey is configured. Desktop matrix builds macOS (aarch64/x86_64), Ubuntu 22.04 AppImage/.deb/.rpm, Windows NSIS installer. Android job signs APK with a keystore secret and uploads it to the same draft release. A final `publish` job unpublishes the draft once all artifacts are present.

## Architecture and conventions

- **Single codebase, flavor-based branching**: Three runtime backends (Supabase API, local mock engine, offline bundled engine) are selected at build time through Vite's `define` so dead branches are tree-shaken out. This enforces C-29 (no local engine or answer key in the Pages bundle) and C-31 (no Supabase/Turnstile keys in the offline app).
- **Base path convention**: Pages deployment uses base `/tbs-lpdp/`; Tauri uses relative `./`. The bank artifact URL is resolved as `BASE_URL + 'bank/…'`, which works identically in both contexts.
- **Question bank as build artifact**: The bank lives outside `web/` under `questions/bank/<package>/...` as JSON question files plus images. The `build:bank` script (via `vite/bank-artifact.ts`) computes a content digest per package and emits a `manifest.json` + `bank-<digest>.json` pair. The manifest records versions derived from git log, so the checkout must use `fetch-depth: 0` (enforced in CI).
- **Offline-first app model**: The offline flavor bundles the latest bank artifact directly into the app assets so a fresh install works with zero connectivity. The app checks for updates against the GitHub Releases `latest.json` via the Tauri updater plugin.
- **Release flow**: Version is stored in four places and bumped atomically by `scripts/bump_version.py`. Releases are tagged `app-vX.Y.Z`; the tag value is read by CI and must match `tauri.conf.json`. Signing material (desktop private key, Android keystore) lives exclusively in GitHub Secrets.
- **Supabase Edge Function build**: The `question-report-digest` function is a Deno service (`supabase/functions/question-report-digest/index.ts`) invoked via POST with an automation API key; it renders a digest and emails it through Resend. No separate build step is needed — Supabase deploys Deno functions directly.

## Conventions and constraints

- **Node/Python toolchain**: Node 22 + npm (lockfile-driven via `package-lock.json`); Python 3.12 for generator/validation/version bumping. CI caches pip/npm/Rust toolchains.
- **TypeScript typecheck before build**: `npm run build` runs `tsc --noEmit && vite build`, so type errors fail CI.
- **Flavor isolation enforced at CI level**: The Pages workflow explicitly rejects any environment variable or `.env` file that would enable the local-engine flavor, and performs a post-build grep to confirm the mock engine module name does not appear in `dist/assets`.
- **Immutable bank artifacts**: Bank publishing uses `--all --publish` with `push_to_supabase.py`, which calls a server-authoritative RPC that is content-hashed; unchanged packages produce no new revisions.
- **App signing policy**: Android APKs are verified with `apksigner verify --print-certs` before upload; the workflow comments that an unsigned or differently-signed APK cannot install over a previous version (AP-7). Desktop installers are signed with a minisign private key supplied via secrets.
- **GitHub Pages base path**: The repo comment in `vite.config.ts` documents that GitHub Pages serves this repository from `/tbs-lpdp/`, which drives the `base` setting and asset paths throughout the build.
- **Tag-to-version contract**: The release workflow requires the Git tag to be exactly `app-v<version>` where `<version>` is read from `web/src-tauri/tauri.conf.json`; mismatches abort the pipeline.