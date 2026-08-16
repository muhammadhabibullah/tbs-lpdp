---
kind: logging_system
name: Logging System — Minimal Console Output and Tauri Debug Logging
category: logging_system
scope:
    - '**'
source_files:
    - web/src-tauri/src/lib.rs
    - questions/generator/figures.py
    - questions/generator/push_to_supabase.py
    - questions/generator/validate_bank.py
    - supabase/functions/question-report-digest/index.ts
---

## What system/approach is used

This repository does **not** implement a centralized logging framework. Each component uses its own minimal, ad-hoc output strategy:

- **Tauri (Rust shell)**: Uses `tauri_plugin_log` with the `log` crate, configured to emit at `Info` level only in debug builds (`cfg!(debug_assertions)`). This is the only structured log sink in the codebase.
- **Python question generator**: Uses bare `print()` / `print(..., file=sys.stderr)` statements for progress and warnings. No logging module, no log levels, no structured fields.
- **Supabase Edge Function (Deno)**: No logging calls at all. Errors are surfaced via HTTP status codes and JSON error bodies; failures are recorded in the database through Supabase RPCs (`fail_question_report_digest`).
- **Web SPA (React/Vite)**: No console logging found in `web/src`. The SPA relies on UI state and network responses rather than client-side logs.

## Key files and packages

- `web/src-tauri/src/lib.rs` — Tauri app entry point; registers `tauri_plugin_log` with `LevelFilter::Info` inside the `.setup()` closure guarded by `debug_assertions`.
- `questions/generator/figures.py`, `questions/generator/push_to_supabase.py`, `questions/generator/validate_bank.py`, `questions/generator/*.py` — All use `print()` for progress output and `print(..., file=sys.stderr)` for warnings/errors.
- `supabase/functions/question-report-digest/index.ts` — Deno edge function with zero logging; errors propagate as HTTP responses and DB state changes.

## Architecture and conventions

1. **No shared logger abstraction.** There is no common logging utility, no central configuration file, and no cross-component log aggregation.
2. **Environment-driven behavior, not log-level driven.** The only conditional behavior tied to an environment flag is the Tauri log plugin, which is enabled only when compiled with `debug_assertions` (i.e., development/debug builds).
3. **Errors are surfaced via domain-specific channels:**
   - Python generators write human-readable progress to stdout and warnings to stderr.
   - The Supabase edge function returns JSON error responses and persists failure details via `fail_question_report_digest` RPC.
   - The Tauri shell exposes commands that return `Result<bool, String>` error strings to the frontend.
4. **Structured fields do not exist.** Log-like outputs are plain text lines (e.g., `"wrote <path>"`, `"WARN <p>"`, `"ok      <label>"`) without timestamps, levels, or machine-parsable structure.
5. **No log rotation, sinks, or external backends.** Logs go to process stdout/stderr (Python) or the Tauri plugin's default destination (console during debug builds).

## Conventions and constraints

- **Tauri logging is opt-in for debug builds only.** Production builds skip the `tauri_plugin_log` entirely, so no Rust-side logs are emitted in release binaries.
- **Python scripts treat stdout as progress and stderr as warnings.** Warnings explicitly write to `sys.stderr` (e.g., `print(f"WARN    {p}", file=sys.stderr)`), while normal progress goes to stdout.
- **Edge functions rely on idempotency keys and DB state instead of logs.** The digest function uses `Idempotency-Key: tbs-report-digest/{runId}` when calling Resend and records outcomes via Supabase RPCs rather than printing logs.
- **Frontend emits no console logs.** A search of `web/src/**/*.ts,tsx` finds no `console.log/error/warn/info/debug` calls, indicating the SPA intentionally avoids client-side logging.