# Offline App Architecture

<cite>
**Referenced Files in This Document**
- [tauri.conf.json](file://web/src-tauri/tauri.conf.json)
- [Cargo.toml](file://web/src-tauri/Cargo.toml)
- [main.rs](file://web/src-tauri/src/main.rs)
- [lib.rs](file://web/src-tauri/src/lib.rs)
- [package.json](file://web/package.json)
- [vite.config.ts](file://web/vite.config.ts)
- [App.tsx](file://web/src/App.tsx)
- [bankSource.ts](file://web/src/lib/bankSource.ts)
- [appUpdate.ts](file://web/src/lib/appUpdate.ts)
- [localApi.ts](file://web/src/lib/localApi.ts)
- [config.ts](file://web/src/lib/config.ts)
- [appRuntime.ts](file://web/src/lib/appRuntime.ts)
- [bank-asset-plugin.ts](file://web/vite/bank-asset-plugin.ts)
- [ExamPage.tsx](file://web/src/pages/ExamPage.tsx)
- [AppShell.tsx](file://web/src/components/AppShell.tsx)
- [LaporSoal.tsx](file://web/src/components/LaporSoal.tsx)
- [ReviewPage.tsx](file://web/src/pages/ReviewPage.tsx)
- [FeedbackFooter.tsx](file://web/src/components/FeedbackFooter.tsx)
</cite>

## Update Summary
**Changes Made**
- Updated reporting system section to reflect email-only submission in offline mode
- Added new subsection on enhanced offline reporting workflow
- Updated LaporSoal component documentation to show simplified offline UI
- Modified ReviewPage integration to document hidden reported-state controls
- Updated security implications to cover email-based report transmission

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the offline-first architecture of the TBS LPDP Try Out application built with a React single-page application (SPA) and a Rust-based Tauri 2 shell. The same SPA is bundled into native applications for Windows, macOS, Linux, and Android that run entirely without network connectivity during exams. All question materials are included in the installer, answers are graded locally, and updates are handled via GitHub Releases while preserving offline functionality.

**Updated** Enhanced offline reporting system now uses email-only submission via native mail client instead of local storage persistence, providing a streamlined user experience in offline environments.

## Project Structure
The project is organized into three main layers:
- Tauri shell (Rust): minimal native entry point, platform integrations, and optional updater plugin on desktop.
- Web SPA (React + Vite): exam UI, local engine, bank source abstraction, update checks, runtime helpers, and enhanced offline reporting.
- Question bank assets: compiled JSON artifacts emitted into the app bundle for offline use.

```mermaid
graph TB
subgraph "Tauri Shell"
RUST_MAIN["main.rs"]
RUST_LIB["lib.rs"]
TAURI_CONF["tauri.conf.json"]
CARGO["Cargo.toml"]
end
subgraph "Web SPA"
APP_TSX["App.tsx"]
EXAM_PAGE["ExamPage.tsx"]
APP_SHELL["AppShell.tsx"]
BANK_SRC["bankSource.ts"]
LOCAL_API["localApi.ts"]
UPDATE["appUpdate.ts"]
RUNTIME["appRuntime.ts"]
CONFIG["config.ts"]
VITE_CFG["vite.config.ts"]
BANK_PLUGIN["bank-asset-plugin.ts"]
LAPOR_SOAL["LaporSoal.tsx"]
REVIEW_PAGE["ReviewPage.tsx"]
FEEDBACK["FeedbackFooter.tsx"]
end
RUST_MAIN --> RUST_LIB
RUST_LIB --> TAURI_CONF
RUST_LIB --> CARGO
APP_TSX --> APP_SHELL
APP_TSX --> EXAM_PAGE
APP_TSX --> UPDATE
EXAM_PAGE --> LOCAL_API
LOCAL_API --> BANK_SRC
UPDATE --> RUNTIME
BANK_SRC --> CONFIG
VITE_CFG --> BANK_PLUGIN
LAPOR_SOAL --> FEEDBACK
REVIEW_PAGE --> LAPOR_SOAL
```

**Diagram sources**
- [main.rs:1-7](file://web/src-tauri/src/main.rs#L1-L7)
- [lib.rs:1-57](file://web/src-tauri/src/lib.rs#L1-L57)
- [tauri.conf.json:1-98](file://web/src-tauri/tauri.conf.json#L1-L98)
- [Cargo.toml:1-42](file://web/src-tauri/Cargo.toml#L1-L42)
- [App.tsx:1-63](file://web/src/App.tsx#L1-L63)
- [ExamPage.tsx:1-380](file://web/src/pages/ExamPage.tsx#L1-L380)
- [AppShell.tsx:1-56](file://web/src/components/AppShell.tsx#L1-L56)
- [bankSource.ts:1-323](file://web/src/lib/bankSource.ts#L1-L323)
- [localApi.ts:1-560](file://web/src/lib/localApi.ts#L1-L560)
- [appUpdate.ts:1-153](file://web/src/lib/appUpdate.ts#L1-L153)
- [appRuntime.ts:1-73](file://web/src/lib/appRuntime.ts#L1-L73)
- [config.ts:1-68](file://web/src/lib/config.ts#L1-L68)
- [vite.config.ts:1-54](file://web/vite.config.ts#L1-L54)
- [bank-asset-plugin.ts:1-58](file://web/vite/bank-asset-plugin.ts#L1-L58)
- [LaporSoal.tsx:1-199](file://web/src/components/LaporSoal.tsx#L1-L199)
- [ReviewPage.tsx:1-423](file://web/src/pages/ReviewPage.tsx#L1-L423)
- [FeedbackFooter.tsx:1-31](file://web/src/components/FeedbackFooter.tsx#L1-L31)

**Section sources**
- [tauri.conf.json:1-98](file://web/src-tauri/tauri.conf.json#L1-L98)
- [Cargo.toml:1-42](file://web/src-tauri/Cargo.toml#L1-L42)
- [main.rs:1-7](file://web/src-tauri/src/main.rs#L1-L7)
- [lib.rs:1-57](file://web/src-tauri/src/lib.rs#L1-L57)
- [package.json:1-46](file://web/package.json#L1-L46)
- [vite.config.ts:1-54](file://web/vite.config.ts#L1-L54)

## Core Components
- Tauri shell: A thin Rust layer that initializes plugins (dialog, filesystem, opener, process), registers a print command, and conditionally enables the updater plugin on desktop. It runs the webview with CSP and capabilities configured for offline operation.
- Local exam engine: A full client-side implementation of the exam API that persists attempts, sections, answers, statistics, and reports to localStorage. It pins each attempt to an immutable release snapshot from the question bank so hot-swapping the bank does not affect active attempts.
- Bundled question bank: A manifest plus content-addressed bank JSON emitted by a Vite plugin into the app bundle for offline use. At runtime, the offline bank source prefers a verified cached copy in the app data directory, then falls back to the bundled snapshot.
- Update mechanism: Desktop uses the Tauri updater plugin to install signed updates; Android compares versions against GitHub Releases and opens the APK download in the system browser. Both flows degrade gracefully when offline.
- **Enhanced offline reporting**: Email-only submission system that opens native mail client drafts with pre-filled report details, eliminating local storage dependencies and server communication requirements.

**Section sources**
- [lib.rs:1-57](file://web/src-tauri/src/lib.rs#L1-L57)
- [tauri.conf.json:26-96](file://web/src-tauri/tauri.conf.json#L26-L96)
- [localApi.ts:27-36](file://web/src/lib/localApi.ts#L27-L36)
- [bankSource.ts:6-18](file://web/src/lib/bankSource.ts#L6-L18)
- [bank-asset-plugin.ts:1-58](file://web/vite/bank-asset-plugin.ts#L1-L58)
- [appUpdate.ts:1-153](file://web/src/lib/appUpdate.ts#L1-L153)
- [LaporSoal.tsx:70-80](file://web/src/components/LaporSoal.tsx#L70-L80)

## Architecture Overview
The offline app runs entirely within a Tauri webview. The SPA loads the bundled question bank, starts attempts pinned to immutable snapshots, saves answers locally, and grades sections offline. Updates check GitHub Releases but do not block offline usage. Reporting in offline mode uses email drafts instead of server communication.

```mermaid
sequenceDiagram
participant User as "User"
participant SPA as "React SPA"
participant Engine as "Local Exam Engine"
participant Bank as "Bank Source"
participant FS as "Filesystem (App Data)"
participant Updater as "Updater / Release Check"
participant Mail as "Native Mail Client"
User->>SPA : Launch app
SPA->>Bank : load()
alt Cached bank available
Bank->>FS : read manifest + bank
FS-->>Bank : verified content
else No cache
Bank->>Bank : load bundled snapshot
end
SPA->>Engine : startAttempt(startSection)
Engine->>Engine : pin release snapshot
loop During exam
SPA->>Engine : saveAnswer/toggleDoubt
Engine->>Engine : persist to localStorage
end
SPA->>Engine : finishSection
Engine->>Engine : grade locally, update stats
Note over SPA,Engine : All operations work offline
SPA->>Updater : checkForAppUpdate()
Updater-->>SPA : current or available (offline-safe)
Note over SPA,Mail : Offline reporting flow
SPA->>Mail : Open mailto : link with report details
Mail-->>User : Pre-filled email draft ready to send
```

**Diagram sources**
- [bankSource.ts:199-317](file://web/src/lib/bankSource.ts#L199-L317)
- [localApi.ts:405-496](file://web/src/lib/localApi.ts#L405-L496)
- [appUpdate.ts:102-110](file://web/src/lib/appUpdate.ts#L102-L110)
- [LaporSoal.tsx:73-80](file://web/src/components/LaporSoal.tsx#L73-L80)
- [FeedbackFooter.tsx:20-31](file://web/src/components/FeedbackFooter.tsx#L20-L31)

## Detailed Component Analysis

### Tauri Shell (Rust)
- Entry points: `main.rs` delegates to the library; `lib.rs` builds the Tauri app, registers plugins, exposes `print_page`, and enables the updater only on desktop targets.
- Security: CSP restricts origins; asset protocol disabled; capabilities scoped to default and desktop features.
- Platform behavior: Print dialog is delegated to the OS on desktop; Android returns false since WebView lacks a print path.

```mermaid
flowchart TD
Start(["App launch"]) --> Init["Initialize Tauri Builder"]
Init --> Plugins["Register plugins<br/>dialog, fs, opener, process"]
Plugins --> UpdaterCheck{"Desktop target?"}
UpdaterCheck --> |Yes| AddUpdater["Add updater plugin"]
UpdaterCheck --> |No| SkipUpdater["Skip updater"]
AddUpdater --> Run["Run webview with context"]
SkipUpdater --> Run
Run --> End(["Ready"])
```

**Diagram sources**
- [lib.rs:29-55](file://web/src-tauri/src/lib.rs#L29-L55)
- [Cargo.toml:20-35](file://web/src-tauri/Cargo.toml#L20-L35)

**Section sources**
- [main.rs:1-7](file://web/src-tauri/src/main.rs#L1-L7)
- [lib.rs:1-57](file://web/src-tauri/src/lib.rs#L1-L57)
- [Cargo.toml:1-42](file://web/src-tauri/Cargo.toml#L1-L42)
- [tauri.conf.json:26-96](file://web/src-tauri/tauri.conf.json#L26-L96)

### Local Exam Engine
- Persistence: Attempts, sections, answers, reports, releases, and statistics are stored in localStorage under versioned keys.
- Immutability: Each attempt pins to a release snapshot created at start time; hot-swapping the bank does not alter ongoing attempts.
- Grading: Sections are graded locally when finished or when deadlines pass; scoring rules enforce minimum answered questions per subtest for statistics eligibility.
- Error handling: Deadline passed and already-finished states are enforced with specific error codes.

```mermaid
flowchart TD
S(["finishSection(sectionId)"]) --> ReadState["Read state"]
ReadState --> Grade["gradeSection(sectionId)"]
Grade --> ComputeScore["Count correct answers * 5"]
ComputeScore --> MarkFinished["Mark section finished<br/>set score and timestamps"]
MarkFinished --> CheckAllDone{"All subtests done?"}
CheckAllDone --> |Yes| FinishAttempt["Mark attempt finished<br/>compute total_score"]
CheckAllDone --> |No| Persist["Write state"]
FinishAttempt --> Persist
Persist --> Return(["Return {score, attempt_status, total_score}"])
```

**Diagram sources**
- [localApi.ts:489-496](file://web/src/lib/localApi.ts#L489-L496)
- [localApi.ts:213-260](file://web/src/lib/localApi.ts#L213-L260)

**Section sources**
- [localApi.ts:27-36](file://web/src/lib/localApi.ts#L27-L36)
- [localApi.ts:183-207](file://web/src/lib/localApi.ts#L183-L207)
- [localApi.ts:213-260](file://web/src/lib/localApi.ts#L213-L260)
- [localApi.ts:405-496](file://web/src/lib/localApi.ts#L405-L496)

### Enhanced Offline Reporting System
- **Email-only submission**: In offline mode, reports are submitted via native mail client using `mailto:` links instead of local storage persistence or server communication.
- **Simplified UI**: Offline mode displays only "Batal" (Cancel) and "Kirim via Email" (Send via Email) buttons, hiding complex reported-state controls.
- **Pre-filled email drafts**: Report details including package title, question number, reason, and comments are automatically populated in the email draft.
- **No local persistence**: Reports are not stored locally in offline mode, eliminating data synchronization concerns.
- **Platform integration**: Uses Tauri's opener capability to open mailto: links through the system's default mail client.

```mermaid
sequenceDiagram
participant User as "User"
participant LaporSoal as "LaporSoal Component"
participant Feedback as "FeedbackFooter"
participant Tauri as "Tauri Opener"
participant Mail as "System Mail Client"
User->>LaporSoal : Click "Kirim via Email"
LaporSoal->>Feedback : feedbackMailto(subject, extraLines)
Feedback-->>LaporSoal : mailto : URL with pre-filled content
LaporSoal->>Tauri : externalLinkProps(href)
Tauri->>Mail : Open mailto : link
Mail-->>User : Display pre-filled email draft
Note over User,Mail : User reviews and sends email manually
```

**Diagram sources**
- [LaporSoal.tsx:73-80](file://web/src/components/LaporSoal.tsx#L73-L80)
- [LaporSoal.tsx:96-115](file://web/src/components/LaporSoal.tsx#L96-L115)
- [FeedbackFooter.tsx:20-31](file://web/src/components/FeedbackFooter.tsx#L20-L31)

**Section sources**
- [LaporSoal.tsx:70-80](file://web/src/components/LaporSoal.tsx#L70-L80)
- [LaporSoal.tsx:96-115](file://web/src/components/LaporSoal.tsx#L96-L115)
- [LaporSoal.tsx:137-139](file://web/src/components/LaporSoal.tsx#L137-L139)
- [FeedbackFooter.tsx:20-31](file://web/src/components/FeedbackFooter.tsx#L20-L31)

### Bundled Question Bank System
- Build-time artifact: A Vite plugin emits a manifest and a content-addressed bank JSON into the app bundle for offline use.
- Runtime resolution: The offline bank source first tries a verified cached copy in the app data directory; if missing or corrupted, it falls back to the bundled snapshot.
- Integrity: Cached bank files are validated using SHA-256 against the manifest before use.
- Hot-swap: When a newer bank is downloaded and verified, the app swaps it in and notifies listeners to refresh package listings.

```mermaid
sequenceDiagram
participant SPA as "SPA"
participant Bank as "Offline Bank Source"
participant Store as "App Data FS"
participant Bundle as "Bundled Assets"
SPA->>Bank : load()
Bank->>Store : read(manifest, bank)
alt Cache exists and valid
Store-->>Bank : verified bank
Bank-->>SPA : bank
else No cache or invalid
Bank->>Bundle : fetch manifest + bank
Bundle-->>Bank : bundled bank
Bank-->>SPA : bank
end
```

**Diagram sources**
- [bank-asset-plugin.ts:13-55](file://web/vite/bank-asset-plugin.ts#L13-L55)
- [bankSource.ts:199-242](file://web/src/lib/bankSource.ts#L199-L242)
- [bankSource.ts:218-235](file://web/src/lib/bankSource.ts#L218-L235)

**Section sources**
- [bank-asset-plugin.ts:1-58](file://web/vite/bank-asset-plugin.ts#L1-L58)
- [bankSource.ts:6-18](file://web/src/lib/bankSource.ts#L6-L18)
- [bankSource.ts:133-197](file://web/src/lib/bankSource.ts#L133-L197)
- [bankSource.ts:199-317](file://web/src/lib/bankSource.ts#L199-L317)

### Update Mechanism
- Desktop: Uses the Tauri updater plugin to check for signed updates and install them in place; relaunches automatically after installation. Package managers like .deb/.rpm cannot self-update and fall back to opening the release page.
- Android: Compares the installed version with the latest GitHub Release tag; if newer, opens the APK download URL in the system browser for overlay installation.
- Offline safety: Network failures or timeouts return an "offline" status and never block normal app usage.

```mermaid
sequenceDiagram
participant SPA as "SPA"
participant Updater as "Updater Logic"
participant Tauri as "Tauri Updater Plugin"
participant GH as "GitHub Releases"
SPA->>Updater : checkForAppUpdate()
alt Desktop
Updater->>Tauri : check(timeout)
Tauri->>GH : GET latest.json
GH-->>Tauri : update metadata
Tauri-->>Updater : update or none
Updater-->>SPA : current or available
else Android
Updater->>GH : GET releases/latest
GH-->>Updater : release info
Updater-->>SPA : current or available
end
```

**Diagram sources**
- [appUpdate.ts:39-110](file://web/src/lib/appUpdate.ts#L39-L110)
- [lib.rs:37-40](file://web/src-tauri/src/lib.rs#L37-L40)
- [tauri.conf.json:87-96](file://web/src-tauri/tauri.conf.json#L87-L96)

**Section sources**
- [appUpdate.ts:1-153](file://web/src/lib/appUpdate.ts#L1-L153)
- [lib.rs:37-40](file://web/src-tauri/src/lib.rs#L37-L40)
- [tauri.conf.json:87-96](file://web/src-tauri/tauri.conf.json#L87-L96)

### Platform-Specific Considerations
- Windows: Console window suppressed in release; NSIS installer supports multiple languages and user-scoped installs.
- macOS: Minimum system version set; signing identity configured; print dialog driven natively due to WKWebView limitations.
- Linux: Debian packages declare required dependencies (GTK/WebKit).
- Android: Updater plugin is excluded; update flow opens APK downloads; print capability is hidden because WebView lacks a print path.

**Section sources**
- [tauri.conf.json:62-85](file://web/src-tauri/tauri.conf.json#L62-L85)
- [lib.rs:15-27](file://web/src-tauri/src/lib.rs#L15-L27)
- [appRuntime.ts:17-47](file://web/src/lib/appRuntime.ts#L17-L47)

### Security Implications of Local Exam Logic
- Answer grading occurs only in offline and dev-mock builds; production web bundles exclude the local engine and answer keys.
- CSP restricts external connections; asset protocol disabled; capabilities limit IPC exposure.
- Question bank integrity is enforced via SHA-256 verification against the manifest before caching or use.
- Update verification relies on minisign signatures managed by the updater plugin on desktop.
- **Enhanced reporting security**: Email-based reporting eliminates local storage vulnerabilities and server communication risks in offline mode.

**Section sources**
- [config.ts:11-43](file://web/src/lib/config.ts#L11-L43)
- [bankSource.ts:79-86](file://web/src/lib/bankSource.ts#L79-L86)
- [bankSource.ts:218-235](file://web/src/lib/bankSource.ts#L218-L235)
- [tauri.conf.json:26-35](file://web/src-tauri/tauri.conf.json#L26-L35)
- [LaporSoal.tsx:70-80](file://web/src/components/LaporSoal.tsx#L70-L80)

### Distribution Strategy and Installation
- Desktop packaging targets include app archives, DMG, NSIS, AppImage, DEB, and RPM.
- Android builds produce debug suffixes for development; distribution uses signed APKs that can be installed over existing apps.
- The updater plugin is enabled only on non-mobile targets; Android uses a browser-based download-and-install flow.

**Section sources**
- [tauri.conf.json:37-85](file://web/src-tauri/tauri.conf.json#L37-L85)
- [Cargo.toml:31-35](file://web/src-tauri/Cargo.toml#L31-L35)

## Dependency Analysis
The SPA composes several modules with clear boundaries:
- `App.tsx` orchestrates routing and update watching based on build flags.
- `ExamPage.tsx` drives the exam UI and interacts with the local engine.
- `localApi.ts` implements the exam API and depends on `bankSource.ts` for question material.
- `bankSource.ts` abstracts where questions come from (dev mock vs offline bundled/cached).
- `appUpdate.ts` handles update checks and integrates with Tauri or GitHub Releases.
- `appRuntime.ts` provides environment detection and platform helpers.
- `config.ts` defines build-time flags and shared constants.
- **Enhanced reporting**: `LaporSoal.tsx` integrates with `FeedbackFooter.tsx` for email generation and `ReviewPage.tsx` for offline-specific filtering.

```mermaid
graph LR
App["App.tsx"] --> Router["HashRouter"]
App --> Gates["Maintenance/Human Verification"]
App --> UpdateWatch["AppUpdateWatcher"]
Exam["ExamPage.tsx"] --> LocalAPI["localApi.ts"]
LocalAPI --> BankSrc["bankSource.ts"]
UpdateWatch --> UpdateMod["appUpdate.ts"]
UpdateMod --> Runtime["appRuntime.ts"]
BankSrc --> Config["config.ts"]
LaporSoal["LaporSoal.tsx"] --> Feedback["FeedbackFooter.tsx"]
ReviewPage["ReviewPage.tsx"] --> LaporSoal
ReviewPage --> Config
```

**Diagram sources**
- [App.tsx:1-63](file://web/src/App.tsx#L1-L63)
- [ExamPage.tsx:1-380](file://web/src/pages/ExamPage.tsx#L1-L380)
- [localApi.ts:1-560](file://web/src/lib/localApi.ts#L1-L560)
- [bankSource.ts:1-323](file://web/src/lib/bankSource.ts#L1-L323)
- [appUpdate.ts:1-153](file://web/src/lib/appUpdate.ts#L1-L153)
- [appRuntime.ts:1-73](file://web/src/lib/appRuntime.ts#L1-L73)
- [config.ts:1-68](file://web/src/lib/config.ts#L1-L68)
- [LaporSoal.tsx:1-199](file://web/src/components/LaporSoal.tsx#L1-L199)
- [ReviewPage.tsx:1-423](file://web/src/pages/ReviewPage.tsx#L1-L423)
- [FeedbackFooter.tsx:1-31](file://web/src/components/FeedbackFooter.tsx#L1-L31)

**Section sources**
- [App.tsx:1-63](file://web/src/App.tsx#L1-L63)
- [ExamPage.tsx:1-380](file://web/src/pages/ExamPage.tsx#L1-L380)
- [localApi.ts:1-560](file://web/src/lib/localApi.ts#L1-L560)
- [bankSource.ts:1-323](file://web/src/lib/bankSource.ts#L1-L323)
- [appUpdate.ts:1-153](file://web/src/lib/appUpdate.ts#L1-L153)
- [appRuntime.ts:1-73](file://web/src/lib/appRuntime.ts#L1-L73)
- [config.ts:1-68](file://web/src/lib/config.ts#L1-L68)
- [LaporSoal.tsx:1-199](file://web/src/components/LaporSoal.tsx#L1-L199)
- [ReviewPage.tsx:1-423](file://web/src/pages/ReviewPage.tsx#L1-L423)
- [FeedbackFooter.tsx:1-31](file://web/src/components/FeedbackFooter.tsx#L1-L31)

## Performance Considerations
- Dead code elimination: Build-time flags ensure offline and web builds exclude unrelated code paths (e.g., local engine in web production, updater in Android).
- Optimistic UI: Answers are saved with debounced writes to reduce I/O overhead during rapid interactions.
- Efficient bank loading: Cached banks are preferred and verified once; bundled fallback avoids network calls on first launch.
- Minimal native surface: The Rust shell stays thin, delegating most logic to the SPA to keep startup fast and bundle sizes small.
- **Reporting performance**: Email-based reporting eliminates local storage operations and network requests, improving offline responsiveness.

## Troubleshooting Guide
- Section deadline passed: If a section times out, the engine auto-grades and rejects further writes; users should proceed to the next section or review.
- Already finished: Writes to completed sections are rejected; navigate to review or start a new attempt.
- Bank verification failure: If a downloaded bank fails SHA-256 checks, the app keeps the previous bank and logs an error; retry later or reinstall.
- Update unavailable offline: Update checks return "offline"; the app continues functioning normally until connectivity is restored.
- Print button not working on Android: The shell disables printing on Android due to WebView limitations; use device share or screenshot options instead.
- **Email client not opening**: Ensure system has a default mail client configured; verify Tauri opener permissions allow mailto: URLs.

**Section sources**
- [localApi.ts:262-275](file://web/src/lib/localApi.ts#L262-L275)
- [localApi.ts:489-496](file://web/src/lib/localApi.ts#L489-L496)
- [bankSource.ts:293-310](file://web/src/lib/bankSource.ts#L293-L310)
- [appUpdate.ts:72-110](file://web/src/lib/appUpdate.ts#L72-L110)
- [lib.rs:15-27](file://web/src-tauri/src/lib.rs#L15-L27)
- [tauri.conf.json:39-41](file://web/src-tauri/tauri.conf.json#L39-L41)

## Conclusion
The TBS LPDP Try Out application delivers a fully offline experience by combining a lightweight Tauri shell with a robust React SPA. The local exam engine ensures secure, server-independent grading and persistence, while the bundled question bank guarantees availability without network access. Updates are handled safely across platforms, with graceful degradation when offline. The enhanced offline reporting system provides a streamlined email-based workflow that maintains complete offline functionality while enabling user feedback collection. This design balances security, performance, and usability across desktop and mobile environments.

## Appendices

### Build-Time Flavors and Environment Flags
- Default web production: Supabase-backed API, base path for GitHub Pages.
- Dev mock: Local engine with mock bank middleware for development.
- Offline app: Local engine with bundled/cached bank, no backend dependencies, email-only reporting.

**Section sources**
- [vite.config.ts:10-17](file://web/vite.config.ts#L10-L17)
- [vite.config.ts:18-52](file://web/vite.config.ts#L18-L52)
- [config.ts:11-43](file://web/src/lib/config.ts#L11-L43)

### Runtime Helpers and Capabilities
- Environment detection: Determines Tauri presence, Android target, and printable capabilities.
- External links: Opens URLs through the opener plugin when inside Tauri.
- Version retrieval: Reads installed app version for update comparisons.

**Section sources**
- [appRuntime.ts:1-73](file://web/src/lib/appRuntime.ts#L1-L73)

### Offline Reporting Configuration
- **Email generation**: Uses `feedbackMailto()` function to create pre-filled mailto: links with report details.
- **UI simplification**: Hides reported-state controls and filters in offline mode for cleaner user experience.
- **Platform integration**: Leverages Tauri's opener capability to open mail clients through system defaults.

**Section sources**
- [FeedbackFooter.tsx:20-31](file://web/src/components/FeedbackFooter.tsx#L20-L31)
- [LaporSoal.tsx:96-115](file://web/src/components/LaporSoal.tsx#L96-L115)
- [ReviewPage.tsx:299-305](file://web/src/pages/ReviewPage.tsx#L299-L305)
- [tauri.conf.json:39-41](file://web/src-tauri/tauri.conf.json#L39-L41)