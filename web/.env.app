# Build flavor: offline app (v6 §2). Loaded by `vite --mode app`, which is what
# `npm run dev:app` / `npm run build:app` — and therefore the Tauri CLI — use.
#
# Committed on purpose: this file carries no secrets, and the app must never
# receive a Supabase URL, Supabase key, or Turnstile key (C-31). `config.ts`
# hard-nulls those three regardless of what the build environment holds.
#
# The GitHub Pages deploy never runs in this mode and asserts the flag is unset
# (C-29), so the local engine and its answer keys cannot reach the web bundle.
VITE_OFFLINE=true
