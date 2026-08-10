# web/ — TBS LPDP try-out SPA

React 18 + Vite + TypeScript. Static build deployed to GitHub Pages under
`/tbs-lpdp/`; all state lives in Supabase and is reached through the RPCs in
[`../supabase/schema.sql`](../supabase/schema.sql) and
[`../supabase/schema_v2_reports.sql`](../supabase/schema_v2_reports.sql), with
the final versioned RPC contracts in
[`../supabase/schema_v3.sql`](../supabase/schema_v3.sql). There is no custom
application server; the v3 report digest is a private Supabase Edge Function.

## Run it

```bash
npm install

# A. Against the git question bank, no Supabase project needed (dev only):
VITE_USE_MOCK=true npm run dev

# B. Against a real Supabase project:
cp .env.example .env.local   # fill VITE_SUPABASE_URL + VITE_SUPABASE_PUBLISHABLE_KEY
npm run dev

npm run build       # tsc --noEmit && vite build → dist/
npm run typecheck
```

Open http://localhost:5173/tbs-lpdp/ (the `base` path matters).

### Mock mode

`vite/mock-bank-plugin.ts` serves `questions/bank/` at `/__mock/bank.json`, and
`src/lib/mockApi.ts` reimplements the RPC semantics (immutable release
snapshots, attempt pinning, server deadline + 5 s grace, idempotent finish,
keys only for finished sections, and monotonic package statistics) against
`localStorage`. The plugin is `apply: 'serve'`, and `VITE_USE_MOCK` is inlined at
build time, so **neither the mock nor any answer key can reach a production
bundle** (C-4/C-11). Reset a mock run by clearing the `tbs-lpdp.mock.v3` key.

## Layout

```
src/
├── lib/
│   ├── types.ts        # RPC payload shapes + the ExamApi interface
│   ├── api.ts          # lazy backend pick (supabase | mock) + retry helper
│   ├── supabaseApi.ts  # supabase-js: anonymous auth + v3 RPCs
│   ├── mockApi.ts      # dev-only stand-in (see above)
│   ├── supabase.ts     # client + ApiError + pg error codes
│   └── clock.ts        # server-time skew, countdown formatting (NF-3)
├── pages/
│   ├── HomePage.tsx    # FE-1 packages + attempt history
│   ├── AttemptPage.tsx # flow controller: intro → exam → next → review
│   ├── SectionIntro.tsx# FE-2 countdown-gated Mulai
│   ├── ExamPage.tsx    # FE-3/4/5/6/7 question screen
│   └── ReviewPage.tsx  # FE-8 score + explanations, FE-11…16 report a question
└── components/         # AppShell, Modal, DaftarSoal, InformasiSoal, KonfirmasiTes,
                        # LaporSoal (v2 report dialog)
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

## Deployment

`.github/workflows/deploy-web.yml` builds on pushes to `master` that touch
`web/`. Set repo **variables** (Settings → Secrets and variables → Actions →
Variables) `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`. Both are
public values; the secret / `service_role` key must never appear here.

### Which key?

Newer Supabase projects issue a **publishable** key (`sb_publishable_…`); older
ones issue the legacy **anon** JWT. They are the same thing for our purposes —
a public, RLS-bound client key — so the app reads
`VITE_SUPABASE_PUBLISHABLE_KEY` and falls back to `VITE_SUPABASE_ANON_KEY`. The
matching privileged key (**secret** `sb_secret_…`, formerly `service_role`)
belongs only in `push_to_supabase.py`'s environment.
