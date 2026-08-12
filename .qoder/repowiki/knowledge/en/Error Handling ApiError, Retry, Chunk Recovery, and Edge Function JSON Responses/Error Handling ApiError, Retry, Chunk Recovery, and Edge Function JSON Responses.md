---
kind: error_handling
name: 'Error Handling: ApiError, Retry, Chunk Recovery, and Edge Function JSON Responses'
category: error_handling
scope:
    - '**'
source_files:
    - web/src/lib/config.ts
    - web/src/lib/api.ts
    - web/src/lib/supabaseApi.ts
    - web/src/lib/localApi.ts
    - web/src/pages/HomePage.tsx
    - web/src/pages/AttemptPage.tsx
    - web/src/pages/ExamPage.tsx
    - supabase/functions/question-report-digest/index.ts
    - web/src-tauri/src/lib.rs
---

## Overview

The repository uses a layered error-handling strategy across three runtime boundaries: the React/Vite frontend SPA, the Supabase Deno edge function, and the thin Tauri Rust shell. Errors are surfaced to users as localized Indonesian messages, while machine-readable error codes (`P0002`–`P0007`, `HUMAN_VERIFICATION_REQUIRED`) flow through the call stack for retry and routing logic.

## Frontend (React/Vite SPA)

### Central error type
- `web/src/lib/config.ts` defines `class ApiError extends Error` with an optional `code?: string` field. Every API-layer violation throws this class, carrying both a user-facing message and a stable code used by callers.
- Domain-specific sentinel codes are exported from the same file: `DEADLINE_PASSED = 'P0004'`, `ALREADY_FINISHED = 'P0003'`, `HUMAN_VERIFICATION_REQUIRED = 'HUMAN_VERIFICATION_REQUIRED'`. The local engine in `localApi.ts` mirrors these codes so client-side and server-side errors share the same vocabulary.

### API layer normalization
- `web/src/lib/supabaseApi.ts` wraps every Supabase RPC in a private `rpc()` helper that calls a `fail(error)` helper which throws `new ApiError(error?.message ?? 'Permintaan ke server gagal', error?.code)`. This centralizes PostgREST error translation into the shared `ApiError` shape.
- `requireSession()` enforces preconditions (Supabase configured, Turnstile CAPTCHA token present) by throwing `ApiError` with human-readable Indonesian messages.

### Retry policy
- `web/src/lib/api.ts` exports `withRetry(fn, attempts = 3)` (NF-2): retries background writes up to 3 times with exponential backoff (`300 * 2^i` ms). It treats Supabase error codes `P0002`–`P0007` as **terminal** — no retry is attempted for rate limits, bad input, or storage capacity reached.
- Pages wrap write operations (save answer, finish section) with `withRetry`; failures surface via `errorMessage(err)` to a UI warning rather than crashing the page.

### Chunk-load recovery
- `isChunkLoadError()` detects dynamic import failures caused by stale deployments (e.g. `chunkloaderror`, `loading chunk .* failed`). On such errors, `api.ts` sets a `sessionStorage` guard key (`tbs-lpdp:chunk-reload-attempted`) and calls `window.location.reload()` once, then returns a pending Promise to keep navigation alive during reload.
- Successful imports clear the guard; if `sessionStorage` is unavailable the fallback path still works.

### Presentation
- `errorMessage(err)` normalizes any thrown value to a string for display. Pages store error strings in React state and render them inside `<div className="notice error">` blocks (see `HomePage.tsx`, `AttemptPage.tsx`, `ExamPage.tsx`).

## Supabase Edge Function

`supabase/functions/question-report-digest/index.ts` handles the question-report digest email pipeline:

- A tiny `jsonResponse(body, status)` helper returns `Response.json` with `Cache-Control: no-store`.
- Configuration validation (`configuredKeys()`) parses `SUPABASE_SECRET_KEYS` JSON and falls back to environment variables; missing keys throw `Error`, caught at the top of `Deno.serve` and returned as `{ error: 'Function is not configured' }` with status 500.
- Input validation rejects non-POST methods (405), invalid JSON (400), malformed UUIDs (400), and unauthenticated requests (401).
- Business-state checks return 409 for already-sent runs or wrong status transitions.
- External provider failures (Resend network error or HTTP failure) record the detailed error via `admin.rpc('fail_question_report_digest', { p_error })` and return a redacted `{ error: 'Email delivery failed' }` with status 502.
- Success records the provider message ID and returns `{ ok: true, provider_message_id }`.

## Tauri Shell (Rust)

The Tauri crate is intentionally thin (`web/src-tauri/src/lib.rs`):

- Only one command is exposed: `print_page`, returning `Result<bool, String>` — platform-dependent success/failure encoded as a boolean, with errors converted to strings via `map_err`.
- The app builder logs at `Info` level only in debug builds and panics on setup failure via `.expect("error while running tauri application")`.
- There is no custom error type; errors bubble as `String` payloads to the frontend's Tauri invoke handler.

## Conventions and Constraints

| Area | Observed convention | Source |
|---|---|---|
| Error type | All API-layer violations throw `ApiError` with a stable `code` string | `web/src/lib/config.ts`, `web/src/lib/supabaseApi.ts`, `web/src/lib/localApi.ts` |
| Error codes | Numeric `Pxxxx` codes encode business states (not found, finished, deadline passed, rate limit, capacity); `HUMAN_VERIFICATION_REQUIRED` signals auth gating | `config.ts`, `localApi.ts`, `api.ts` retry filter |
| User messages | Messages are written in Indonesian (e.g. `'Permintaan ke server gagal'`, `'Verifikasi manusia diperlukan.'`) | `supabaseApi.ts`, `config.ts` |
| Retries | Background writes use `withRetry` with exponential backoff; terminal codes short-circuit | `api.ts` line 98–122 |
| Chunk recovery | Dynamic import failures trigger a single guarded full-page reload | `api.ts` lines 18–67 |
| Edge functions | All responses go through `jsonResponse({ error }, status)`; configuration and auth errors return explicit 4xx/5xx | `question-report-digest/index.ts` |
| External failures | Provider errors are recorded in DB via `admin.rpc('fail_...')` before returning a redacted response | `index.ts` lines 89–106 |
| Tauri commands | Return `Result<T, String>`; errors are plain strings forwarded to the caller | `lib.rs` line 16 |

No `panic!` usage exists outside the Tauri bootstrap `.expect(...)`. No global middleware or interceptors exist beyond the per-RPC `rpc()` wrapper and the edge function's inline guards.