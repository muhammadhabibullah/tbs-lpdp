# Technical Requirements v6 — Offline App (Tauri): Desktop & Android

| | |
|---|---|
| Status | v6.0 — implemented (§10 records what remains an operator step) |
| Date | 2026-08-11 |
| Extends | Core requirements through v5 |
| Scope | Offline desktop/mobile app (macOS, Windows, Linux, Android) built with Tauri 2, released on GitHub Releases via GitHub Actions, with in-app application updates and pull-based question-bank updates; small web-app additions (download menu, open-source footer link) |
| Out of scope | iOS (requires an Apple Developer Program membership for any practical distribution; revisit if one is obtained). App Store / Play Store / winget / Homebrew distribution. Any server component. |

## 1. Goal and limits

Offer the try-out as an installable, fully offline application. The app reuses
the existing SPA unchanged in look and behavior, but runs it against the local
exam engine (today's `mockApi`) instead of Supabase: no account, no CAPTCHA, no
network needed to take a try-out. The git question bank is compiled into a
published artifact that the app both **bundles** (first run works with zero
connectivity) and **refreshes from GitHub** when online, so users receive newly
generated packages without reinstalling. The app binary itself updates through
GitHub Releases.

Honest limits, in the spirit of v5 §1:

- An offline app **must contain answer keys and grading logic on the device**.
  This adds no exposure — the repository is public and the keys are already in
  `questions/bank/` — but it means C-4's "no key reaches the client" guarantee
  is, by design, a property of the *web/Supabase* deployment only (C-28).
- Timing and grading run on the user's machine and are tamperable by the user.
  Acceptable: the try-out is self-assessment; there is no leaderboard.
- Without platform code-signing certificates (Apple Developer ID, Windows EV),
  installers trigger OS warnings (Gatekeeper, SmartScreen). v6 documents the
  workaround for users (FE-42) rather than purchasing certificates; the
  Tauri updater's own minisign signature still protects update integrity.

## 2. Architecture overview

One SPA codebase, three build flavors selected at build time (all inlined by
Vite, so each bundle contains only its own backend):

| Flavor | Selector | Backend | Ships where |
|---|---|---|---|
| Web production | *(default)* | `supabaseApi` | GitHub Pages (unchanged) |
| Dev mock | `VITE_USE_MOCK=true`, dev server only | local engine + Vite middleware bank | never shipped (unchanged) |
| **Offline app** | `VITE_OFFLINE=true` + Tauri shell | local engine + bundled/cached bank | GitHub Releases |

Two independent update planes:

```
questions/bank/ (git, source of truth)
   │  push to main (bank changed)
   ▼
build-bank script ──► GitHub Pages  /tbs-lpdp/bank/manifest.json      ◄── app checks each launch
                                    /tbs-lpdp/bank/bank-<digest>.json      + manual refresh
                                                                            (AP-4: bank update)

git tag app-vX.Y.Z
   ▼
release-app workflow ──► GitHub Release: installers + latest.json     ◄── tauri-plugin-updater
                                                                           (AP-6: app update)
```

Bank version and app version are deliberately decoupled: new question packages
reach every installed app without a new binary; a new binary is only needed
when code or the bank *schema* changes (AP-5 gates that case).

## 3. Requirements

### 3.1 Constraints

| ID | Requirement |
|----|-------------|
| C-28 | The offline app bundles answer keys, explanations, and grading locally. Documentation and UI must not claim otherwise. This does not weaken the web deployment: C-4 continues to hold for GitHub Pages + Supabase, and the published bank artifact exposes nothing that the public repository does not already expose. |
| C-29 | The GitHub Pages web deployment never sets `VITE_OFFLINE` or `VITE_USE_MOCK`. The deploy workflow asserts both are unset before building, so the local engine (and keys) can never enter the web bundle. |
| C-30 | Signing material lives only in GitHub Actions secrets, never in git: the Tauri updater minisign **private** key (+ password) and the Android release keystore (+ passwords). The minisign **public** key is committed in `tauri.conf.json`. Losing the Android keystore permanently breaks in-place APK upgrades — back it up outside GitHub. |
| C-31 | App builds contain no Supabase URL or key, no Turnstile key, and no telemetry. The only network endpoints the app may contact are `muhammadhabibullah.github.io` (bank), `github.com` / release CDN (app updates, opened links), and `api.github.com` (release metadata). |

### 3.2 Offline app (AP)

| ID | Requirement |
|----|-------------|
| AP-1 | A Tauri 2 project lives at `web/src-tauri/` wrapping the existing SPA. `vite.config.ts` switches `base` to `'./'` for Tauri builds (`TAURI_ENV_PLATFORM` set) and keeps `/tbs-lpdp/` otherwise; HashRouter already makes routes host-agnostic. Targets: macOS (aarch64 + x86_64), Windows x64 (NSIS), Linux x64 (AppImage + deb + rpm), Android (arm64 APK). |
| AP-2 | The current `mockApi.ts` is promoted to a shared **local engine** (`localApi.ts`) behind a `BankSource` interface. Dev mock keeps the Vite-middleware source (`/__mock/bank.json`, still `apply: 'serve'` only). The offline flavor uses a source that loads, in order: the verified cached bank in the app data directory, else the bundled snapshot compiled into the app at build time. All release-pinning semantics (immutable `release_id` per attempt) carry over unchanged. |
| AP-3 | A build-bank script (shared with the Vite mock plugin, extracted to `web/vite/bank-reader.ts` + `web/scripts/build-bank.ts`) compiles `questions/bank/` into a single self-contained `bank-<digest>.json` (images inlined as data URIs; revisit if the file exceeds ~10 MB) plus `manifest.json`. `question_version` / `last_updated_at` are derived deterministically from git history (last commit touching each file), not from in-memory counters, so republishing identical content yields an identical digest. |
| AP-4 | **Bank updates:** on every launch, when online, the app fetches `manifest.json` (≤5 s timeout, silent failure offline) and compares `bank_version` with the active bank. If newer and schema-compatible, it downloads the bank file, verifies its SHA-256 against the manifest, writes it atomically (temp file + rename) into the app data dir, hot-swaps the in-memory bank, and shows a toast: *"Bank soal diperbarui (versi <digest>)."* A manual **"Perbarui Bank Soal"** button on the home page runs the same flow with visible progress and a clear result (updated / already latest / offline). In-progress and finished attempts are unaffected — they stay pinned to their stored release. |
| AP-5 | The manifest carries `bank_schema_version` and `min_app_version`. An app that fetches a manifest requiring a newer schema does not download the bank; it keeps its current bank and prompts: *"Versi aplikasi terbaru diperlukan untuk soal terbaru"* with an update action (AP-6/AP-7). This is the only coupling between the two update planes. |
| AP-6 | **Desktop app updates:** `tauri-plugin-updater` pointed at `https://github.com/muhammadhabibullah/tbs-lpdp/releases/latest/download/latest.json`, artifacts signed with the project minisign key. Check on launch (non-blocking) and via a **"Periksa Pembaruan Aplikasi"** action; on a newer version, a Bahasa Indonesia dialog offers download-and-restart (`tauri-plugin-process` relaunch). Covered installers: NSIS (Windows), `.app.tar.gz` (macOS), AppImage (Linux). deb/rpm installs cannot self-update; the dialog links to the release page instead. |
| AP-7 | **Android app updates:** the updater plugin does not cover Android, so the app compares its version against `latest.json` (or `api.github.com/releases/latest`); when newer, a prompt opens the APK download in the browser via `tauri-plugin-opener` and the user installs over the existing app. This requires every APK to be signed with the **same release keystore** (C-30); `versionCode` is derived from the semver so Android accepts the upgrade. |
| AP-8 | **CI:** a new workflow `.github/workflows/release-app.yml` triggers on tags `app-v*` (plus `workflow_dispatch`). Desktop job: `tauri-apps/tauri-action` on a `macos-latest` / `ubuntu-22.04` / `windows-latest` matrix with `includeUpdaterJson: true`, publishing installers, updater signatures, and `latest.json` to one GitHub Release. Android job: Java 17 + Android SDK/NDK + Rust android targets, `tauri android build --apk`, sign with the keystore secret, upload the APK to the same release. The tag version must equal the `tauri.conf.json` version (CI asserts). |
| AP-9 | Offline feature deltas, applied only under `VITE_OFFLINE`: no `MaintenanceGate` or `HumanVerificationGate` (neither concept applies), and package statistics are computed locally and labeled *"Statistik lokal (perangkat ini)"*. The report-question dialog (v2) stores **no** report state on the device: its primary action is *"Kirim via Email"*, which uses the existing prefilled `feedbackMailto()` to open a draft in the device mail app so reports can still reach the maintainer. Because nothing is stored, the reported-state controls — *✓ Sudah dilaporkan*, *Ubah*, *Batalkan laporan* (FE-13/FE-15) — and the *Dilaporkan* filter (FE-16) never appear in the app; every question keeps the plain *Laporkan soal* entry point. The web menu item added by FE-42 is hidden in the app. |
| AP-10 | The app footer/about shows both versions — *"Aplikasi v<semver> · Bank soal <digest> (<tanggal>)"* — next to the two update actions (AP-4, AP-6), so a user can tell at a glance whether they are current. |

### 3.3 Web app additions (FE)

| ID | Requirement |
|----|-------------|
| FE-42 | The web app gains a menu item **"Unduh Aplikasi Offline"** (in `MENU_ITEMS`, web flavor only) anchoring a new home-page section. The section offers **one button**, carrying the installer for the visitor's own device with its file size: OS from the user agent, and on macOS the CPU from `userAgentData.getHighEntropyValues(['architecture'])`, defaulting to Apple Silicon where the browser will not say. The other Mac is a visible link beside the button (guessing wrong yields a build that cannot launch); every other installer sits behind one **"Unduhan untuk perangkat lain"** toggle. Assets resolve at runtime from `api.github.com/repos/muhammadhabibullah/tbs-lpdp/releases/latest` (CORS-open, unauthenticated), filtered to user-facing files — `.sig`, `.json`, `.tar.gz` and `.nsis.zip` are updater plumbing. If the API call fails, is rate-limited, or the newest release is still a draft, the button becomes a plain link to the releases page, which is never wrong, only slower. The **step-by-step install instructions for non-technical users in Bahasa Indonesia** are the release notes (`releaseBody` in `release-app.yml`), which the section footnote links to. Section 6 below is the content source for those instructions. |
| FE-43 | The site footer gains a block titled **"Open Source Code"** placed below the *Kontak* block in `FeedbackFooter.tsx`, linking to `https://github.com/muhammadhabibullah/tbs-lpdp` (opens in a new tab). Shown in both web and app flavors. |

### 3.4 Non-functional

| ID | Requirement |
|----|-------------|
| NF-30 | Update checks never block the UI: the app is interactive immediately from the bundled/cached bank; manifest and updater checks run in the background and fail silently when offline. No retry storms — one check per launch plus manual actions. |
| NF-31 | Bank downloads are integrity-checked (SHA-256 from the manifest) and applied atomically; a failed or corrupted download leaves the previous bank fully functional. Bank files are content-addressed (`bank-<digest>.json`) and immutable once published; only `manifest.json` moves. |
| NF-32 | The published bank artifact is reproducible: two CI runs over the same git tree publish byte-identical bank files (stable JSON key order, git-derived timestamps), so `bank_version` changes if and only if content changed. |

## 4. Bank publishing pipeline

Artifact layout on GitHub Pages (added to the existing `deploy-web.yml` Pages
deployment — the workflow already rebuilds on pushes to `main`; it additionally
runs `build-bank.ts` and copies the output into `dist/bank/`):

```
https://muhammadhabibullah.github.io/tbs-lpdp/bank/
  manifest.json            # small, mutable, fetched with cache-buster
  bank-3f9a1c2e7b41.json   # content-addressed, immutable, cache forever
```

`manifest.json` schema (v1):

```json
{
  "schema_version": 1,
  "bank_schema_version": 1,
  "min_app_version": "0.1.0",
  "bank_version": "3f9a1c2e7b41",
  "generated_at": "2026-08-11T12:00:00Z",
  "bank": {
    "url": "bank-3f9a1c2e7b41.json",
    "sha256": "<full digest>",
    "bytes": 1234567
  }
}
```

Notes:

- `bank_version` is the first 12 hex chars of the bank file's SHA-256.
- The bank JSON reuses the exact shape the local engine already consumes
  (`{ packages, questions }` from `bank-reader.ts`), with `image_url` replaced
  by inline data URIs.
- The same script output is bundled into the app at build time (the release
  workflow runs it too), so a fresh install is at most one `main` push behind.
- `validate_bank.py` remains the gate: the publish step runs it and fails the
  workflow on a non-zero exit, so a broken bank never reaches users.

## 5. One-time setup (operator)

1. `npm run tauri signer generate` → minisign keypair. Commit the **public** key
   into `tauri.conf.json` (`plugins.updater.pubkey`); add secrets
   `TAURI_SIGNING_PRIVATE_KEY` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`.
2. `keytool -genkeypair` → Android release keystore. Add secrets
   `ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`,
   `ANDROID_KEY_PASSWORD`. **Back the keystore up privately** (C-30).
3. First release: bump `web/src-tauri/tauri.conf.json` version, tag
   `app-v0.1.0`, push the tag; verify the drafted release, then publish it.

## 6. Install instructions (FE-42 content)

Rendered per-platform, in Bahasa Indonesia, in the **GitHub Release notes** —
not on the home page. Only someone who has already downloaded a file needs
them, they belong with the installers they describe, and four step-lists inline
turned the download section into a manual. The home page keeps one line per
platform naming the warning that OS shows, and links here.

Roughly:

- **Windows:** Unduh `...-setup.exe` → jalankan → jika muncul layar biru
  "Windows protected your PC", klik **More info** lalu **Run anyway** (aplikasi
  belum memiliki sertifikat Microsoft, bukan berbahaya — kode sumbernya
  terbuka) → ikuti pemasang → aplikasi muncul di Start Menu.
- **macOS:** Unduh `.dmg` → buka → seret aplikasi ke folder Applications →
  saat pertama dibuka macOS menolak aplikasi tanpa tanda tangan Apple: buka
  **System Settings → Privacy & Security → Open Anyway**, atau klik kanan →
  **Open**. Jika masih ditolak, buka Terminal dan jalankan
  `xattr -cr /Applications/<AppName>.app`.
- **Linux:** Unduh `.AppImage` → klik kanan → Properties → centang *Executable*
  (atau `chmod +x`) → jalankan. Pengguna Debian/Ubuntu dapat memakai `.deb`,
  Fedora `.rpm` (pembaruan otomatis hanya tersedia pada AppImage).
- **Android:** Unduh `.apk` di perangkat → buka berkas → izinkan
  *Install unknown apps* untuk browser Anda saat diminta → Install. Pembaruan
  cukup memasang APK versi baru di atasnya (data tersimpan aman).

The notes open with the same disclaimer the download section repeats once: the
app is unsigned because it is a free open-source project; verify you downloaded
from `github.com/muhammadhabibullah/tbs-lpdp` only.

GitHub renders release notes with hard line breaks enabled, so each paragraph
and list item in `releaseBody` is one source line however long — wrapping the
YAML wraps the rendered page too.

## 7. Planned file changes

| File | Change |
|------|--------|
| `web/src-tauri/**` | New Tauri 2 project: config, Rust shell, capabilities, icons; plugins: updater, dialog, process, opener, fs |
| `web/src/lib/localApi.ts` | Renamed/refactored from `mockApi.ts`; `BankSource` injection; unchanged exam semantics |
| `web/src/lib/bankSource.ts` | Dev-server source, offline (cached→bundled) source, manifest check/download/verify/swap (AP-4, AP-5, NF-31) |
| `web/src/lib/api.ts`, `config.ts` | `VITE_OFFLINE` flavor selection; offline flag exported for UI deltas (AP-9) |
| `web/vite/bank-reader.ts` | Bank compilation extracted from `mock-bank-plugin.ts`; git-derived versions (AP-3, NF-32) |
| `web/scripts/build-bank.ts` | CLI: emit `bank-<digest>.json` + `manifest.json` (validates via `validate_bank.py` first) |
| `web/vite.config.ts` | Conditional `base` for Tauri builds (AP-1) |
| `web/src/components/MenuBar.tsx`, `pages/HomePage.tsx` | "Unduh Aplikasi Offline" menu + one-button section resolving the visitor's installer from the latest release (FE-42); install steps live in the release notes |
| `web/src/components/FeedbackFooter.tsx` | "Open Source Code" block below Kontak (FE-43) |
| `web/src/components/UpdateControls.tsx` | App-flavor: version display, bank refresh, app update check (AP-4, AP-6, AP-10) |
| `.github/workflows/release-app.yml` | New: tag-triggered desktop matrix + Android build → GitHub Release (AP-8) |
| `.github/workflows/deploy-web.yml` | Add bank artifact to Pages deploy; assert `VITE_OFFLINE`/`VITE_USE_MOCK` unset (C-29) |
| `CLAUDE.md`, `web/README.md` | Document flavors, release procedure, secrets |

## 8. Acceptance criteria

| # | Check | Expected |
|---|-------|----------|
| A-1 | Fresh install, network disabled, on each of macOS/Windows/Linux/Android | Full exam flow (all 3 subtests, grading, review with explanations) works from the bundled bank |
| A-2 | Launch while online after a bank change was pushed to `main` | Toast "Bank soal diperbarui"; new package appears; a previously finished attempt still reviews against its old release |
| A-3 | "Perbarui Bank Soal" with no newer bank / while offline | Clear "sudah terbaru" / offline message; no error state |
| A-4 | Corrupt the cached bank file, relaunch | App falls back (hash mismatch → re-download or bundled snapshot); never crashes |
| A-5 | Publish release `app-v(N+1)`; launch desktop app vN | Update dialog appears; accepting installs and relaunches as v(N+1) |
| A-6 | Same on Android | Prompt opens APK download; installing over vN succeeds (same signature) |
| A-7 | Manifest with `bank_schema_version` above the app's | Bank not downloaded; "update the app" prompt shown; current bank keeps working |
| A-8 | Inspect app bundle | No Supabase URL/key, no Turnstile key (C-31); updater pubkey present |
| A-9 | Inspect Pages web bundle after deploy | No local engine, no answer keys (C-29); `bank/manifest.json` served with valid digest |
| A-10 | Web home page, on each of Windows/macOS/Linux/Android | "Unduh Aplikasi Offline" menu scrolls to a single button already carrying that device's installer and size; the toggle lists the rest; install steps reachable in the release notes; footer shows "Open Source Code" below Kontak |
| A-11 | Offline app UI | No download-app menu, no maintenance/CAPTCHA gates; local-statistics label; version line + both update actions visible; report dialog offers only *Batal* / *Kirim via Email*, with no reported-state controls and no *Dilaporkan* filter |
| A-12 | Two consecutive bank publishes with no content change | Identical `bank_version` (NF-32); apps report "sudah terbaru" |
| A-13 | "Unduh PDF" on the review screen, desktop app | Native print dialog opens with the whole attempt — all three subtests, every question — and "Save as PDF" writes it. Button absent on Android |

## 9. Phased rollout

1. **Engine refactor** — AP-2/AP-3: extract `bank-reader`, `localApi`,
   `bankSource`, build-bank script; dev mock behavior unchanged (regression:
   existing mock flow still passes).
2. **Desktop shell + releases** — AP-1/AP-6/AP-8 (desktop matrix), C-30 setup,
   first `app-v0.1.0` release with updater verified via a follow-up `0.1.1`.
3. **Bank update plane** — AP-4/AP-5, Pages publishing (C-29 assert), NF-30–32.
4. **Android** — AP-7 + keystore, APK in the same release.
5. **Web additions** — FE-42/FE-43 (independent; can ship any time after the
   first release exists).

## 10. Implementation notes

Everything in §3 is implemented; §7's file list matches the tree, with these
decisions worth recording.

**Flavor isolation is enforced by constant folding.** `vite.config.ts` `define`s
`import.meta.env.VITE_USE_MOCK` and `import.meta.env.VITE_OFFLINE` as string
literals. Vite only inlines env vars it actually holds, and an *undefined*
selector never folds — without folding, Rollup keeps both backends in every
bundle, which breaks C-29 and C-31 simultaneously. `api.ts` also compares those
literals inline rather than through a re-exported constant, because only a
module-local comparison lets Rollup drop the other dynamic import's chunk.
`deploy-web.yml` re-checks the result: it fails if either flag is set, and again
if the built bundle contains the local engine's storage key.

**Bank versions come from `git log`, once per compile.** `bank-reader.ts` reads
the whole bank history in a single `git log --name-only` pass and derives, for
each file *and each directory prefix*, a commit count (the version) and the
newest author date. That makes a package's version count the commits touching
any of its files. `generated_at` in the manifest is the newest bank commit, not
wall-clock time, so the manifest is reproducible too (NF-32) — verified: two
runs over the same tree emit byte-identical `manifest.json` and bank files.
`build-bank.ts` **fails** when no history is available, since a shallow CI
checkout would silently reset every question to version 1; the dev middleware
degrades to mtimes instead.

**The bundled snapshot is the published artifact.** `bank-asset-plugin.ts`
emits the same `bank/manifest.json` + `bank/bank-<digest>.json` pair into the
app's assets, so the bundled and cached paths share one loader and one
verification routine. The cached copy is content-addressed and its manifest is
written last, so a crash mid-update leaves the previous pair intact (NF-31).

**macOS builds are ad-hoc signed** (`bundle.macOS.signingIdentity: "-"`).
Apple Silicon refuses to launch a bundle with no valid signature at all, and
reports it as *"…is damaged and can't be opened"* — which reads to a user as a
corrupt download rather than a policy decision. An ad-hoc signature costs
nothing, needs no Apple account, and turns that into the ordinary
unidentified-developer prompt the FE-42 instructions already cover. It is not a
substitute for a Developer ID: §1's honest limit still holds, and Gatekeeper
still requires **System Settings → Privacy & Security → Open Anyway**. Replacing
`"-"` with a real identity is the only change needed if a membership is ever
obtained.

**The download button reads the Releases API, not `latest.json`.** The updater
manifest looks like the natural index — it is one file listing every platform —
but it is the wrong one. `ReleaseManifestPlatform` carries `{url, signature}`
and nothing else, and each `url` is the *update payload*: `.app.tar.gz` on
macOS, `-setup.nsis.zip` on Windows. Handing those to a person instead of the
`.dmg` or `.exe` gives them a file their OS will not install. It also has no
Android key, since `tauri-plugin-updater` has no Android implementation (AP-7),
and no file sizes. The Releases API has all of it, is equally CORS-open, and is
one request either way.

Two consequences worth knowing: `releases/latest` skips **drafts**, so the
button stays on its releases-page fallback until a release is actually
published; and while the repository is private, both the API and the asset URLs
404 for anonymous visitors, so the fallback is all a stranger would see.

**"Unduh PDF" goes through the shell, and the print copy is always in the DOM.**
The macOS WKWebView implements `window.print()` as a no-op, so FE-20's button
did nothing in the app. The shell exposes one command, `print_page`, which calls
`WebviewWindow::print` — `NSPrintOperation` on macOS, the GTK dialog on Linux,
and `window.print()` on Windows, where it works. It is the app's own command,
not a plugin's, so it needs no capability entry; only plugin commands and remote
origins are ACL-gated. `WebviewWindow::print` is desktop-only and wry's Android
implementation does nothing, so the command reports `false` there and
`canPrint()` hides the button rather than leave it dead.

That native dialog never reports back — no `afterprint`, and
`runOperationModalForWindow` returns as soon as the sheet is up — so ReviewPage
no longer swaps the full attempt into the DOM for the duration of a print. It
renders `.print-body` up front, hidden outside `@media print`, and the on-screen
list (one subtest, one filter) sits in a `.no-print` wrapper. Nothing to reset,
nothing to get stuck; the browser's own Ctrl-P gets the same complete document,
which it previously did not. The document title is set for the page's lifetime
rather than around the call, because every print dialog reads the PDF filename
from it at the moment it opens.

**Reachable network endpoints are pinned twice** (C-31): by the CSP
`connect-src` in `tauri.conf.json`, and by the opener scope in
`capabilities/default.json`. Filesystem access is scoped to `$APPDATA/bank`.

**AP-7 uses `api.github.com`, not the `latest.json` download URL.** GitHub
release-asset redirects are not CORS-open, so the Android version check reads
the releases API, which is.

Two things remain operator steps, exactly as §5 describes, and are *not* done in
this repository:

1. `plugins.updater.pubkey` in `web/src-tauri/tauri.conf.json` is still the
   literal `REPLACE_WITH_MINISIGN_PUBLIC_KEY`. Generating the minisign keypair
   creates the project's update-signing identity and its private half must never
   leave the operator's hands, so it is theirs to create.
   `release-app.yml` refuses to run while the placeholder is present.
2. The Android release keystore does not exist yet; the same job fails with a
   pointed message when `ANDROID_KEYSTORE_B64` is unset.

Until step 1 is done, `npm run app:build` still produces working installers only
with `TAURI_SIGNING_PRIVATE_KEY` set, because `createUpdaterArtifacts` is on;
`npm run tauri build -- --no-bundle` compiles without it.

Acceptance criteria A-9 through A-12 and the offline halves of A-1/A-3 were
verified locally (flavor isolation greps, reproducible publishes, the full exam
flow and Pembahasan running off the bundled bank, SHA-256 of the served bank
matching its manifest). A-2, A-4 through A-7 depend on a published Pages bank
artifact and a published release, so they are first checkable after the initial
deploy and `app-v0.1.0`.
