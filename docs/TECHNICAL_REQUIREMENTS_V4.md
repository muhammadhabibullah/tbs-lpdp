# Technical Requirements v4 — Scheduled Frontend Maintenance Mode

| | |
|---|---|
| Status | v4.0 — implemented |
| Date | 2026-08-11 |
| Extends | [`TECHNICAL_REQUIREMENTS.md`](TECHNICAL_REQUIREMENTS.md), [`TECHNICAL_REQUIREMENTS_V2.md`](TECHNICAL_REQUIREMENTS_V2.md), and the planned [`TECHNICAL_REQUIREMENTS_V3.md`](TECHNICAL_REQUIREMENTS_V3.md) |
| Scope | One Supabase-configured maintenance window, four-hour warning banner, and frontend route block |

## 1. Goal and scope

An operator can schedule one maintenance window in Supabase without rebuilding
the static site. Four hours before the window, every page shows a dismissible
banner above the masthead. During the window, the SPA does not mount its normal
routes and shows a maintenance screen instead.

This stage is deliberately a **frontend-only block**. The database does not
reject `start_attempt`, `save_answer`, reporting, or any other existing API
call during maintenance. Requests already in flight may finish after the gate
appears, and a caller that bypasses the SPA can still call permitted RPCs.

## 2. Decisions

- The schedule stores `starts_at` and `ends_at`, not a permanent boolean alone;
  an end time lets an open page restore itself automatically.
- One singleton row is sufficient. A new schedule replaces the old values;
  schedule history and recurring windows are out of scope.
- Supabase `timestamptz` is authoritative. The status RPC also returns
  `server_time`, and the SPA uses the existing server-clock offset.
- The warning starts at `starts_at - 4 hours`. Closing it is remembered in
  `sessionStorage` for that exact start/end pair, so navigating or reloading in
  the same tab does not resurrect it. A changed schedule is shown again.
- The client probes every 60 seconds and also sets exact local boundary timers
  for warning start, maintenance start, and maintenance end.
- A failed or five-second timed-out first probe fails open. This avoids an
  unavailable or not-yet-applied maintenance RPC taking down the static site.
  This limitation is unavoidable without backend enforcement, which is
  outside the requested scope.

## 3. Requirements

### 3.1 Constraints

| ID | Requirement |
|----|-------------|
| C-18 | Maintenance is a presentation/access gate in the official SPA only. No existing exam or reporting RPC changes behavior. |
| C-19 | Maintenance configuration is operator-controlled Supabase data. The browser has no direct table read or write policy and receives only the public projection from `get_maintenance_status()`. |

### 3.2 Frontend

| ID | Requirement |
|----|-------------|
| FE-27 | Before mounting any route, the SPA calls `get_maintenance_status()`. Until the first probe resolves, it shows a neutral status message so page-specific API calls do not begin underneath an active maintenance window. |
| FE-28 | From four hours before `starts_at` until `starts_at`, every page—including an active exam page whose normal navigation/footer are hidden—shows a warning banner above the masthead. It displays the window in WIB, the operator message, and an accessible close button. |
| FE-29 | From `starts_at` inclusive until `ends_at` exclusive, normal routes are unmounted and replaced by a Bahasa Indonesia maintenance screen showing the expected end time and a **Periksa lagi** action. At the end boundary, the requested route becomes available again automatically. |
| FE-30 | The SPA refreshes configuration every 60 seconds, changes phase at exact schedule boundaries using the server-clock offset, remembers dismissal per schedule for the browser session, and provides a local-storage schedule override in mock mode. |

### 3.3 Backend

| ID | Requirement |
|----|-------------|
| BE-35 | `public.site_maintenance` is a singleton row with `enabled`, `starts_at`, `ends_at`, a 1–500 character message, and `updated_at`. An enabled schedule requires both timestamps and `ends_at > starts_at`. |
| BE-36 | Public, pre-auth `get_maintenance_status()` returns the schedule, server time, and a server-derived `open\|warning\|maintenance` phase. It exposes no secrets or unrelated operational data. |
| BE-37 | RLS is enabled with no table policy. Only the RPC is granted to `anon` and `authenticated`; schedule mutations remain SQL-editor/service-role operations. |

### 3.4 Non-functional

| ID | Requirement |
|----|-------------|
| NF-20 | The feature adds one small RPC per initial page load and one per minute while open. It introduces no per-page or per-component polling. |
| NF-21 | All timestamps render in `Asia/Jakarta`; phase comparisons use the server-synchronised clock rather than trusting the device clock. |
| NF-22 | If the probe fails or exceeds five seconds, the app preserves any previously fetched schedule; if none exists it fails open. Normal API errors remain handled by their existing pages. |

## 4. Data and API

The migration is [`supabase/schema_v4_maintenance_mode.sql`](../supabase/schema_v4_maintenance_mode.sql).
The public response shape is:

```ts
interface MaintenanceStatus {
  enabled: boolean
  starts_at: string | null
  ends_at: string | null
  message: string
  phase: 'open' | 'warning' | 'maintenance'
  server_time: string
}
```

The SQL function derives `phase` with database `now()`. The browser derives it
again from the returned timestamps as time advances, using the skew established
from `server_time`; the duplicate calculation avoids another request exactly at
each boundary while retaining a server-authoritative initial state.

## 5. Implementation plan and delivered files

1. Add the singleton table, RLS boundary, pre-auth status RPC, grants, and
   operator scheduling examples.
2. Extend `ExamApi`, Supabase, and mock implementations with one status method.
3. Add a global gate above `Routes`, plus a context consumed by `AppShell` so
   the warning appears even when exam chrome is hidden.
4. Add the dismissible banner, blocking page, WIB formatting, polling, boundary
   timers, responsive styles, and session-scoped dismissal.
5. Verify TypeScript and the production Vite build.

| File | Change |
|------|--------|
| `supabase/schema_v4_maintenance_mode.sql` | Table, RLS, public status RPC, grants, operator examples |
| `web/src/lib/types.ts`, `api.ts`, `supabaseApi.ts`, `mockApi.ts` | API contract and implementations |
| `web/src/lib/maintenance.ts` | Phase, boundary, schedule key, and WIB formatting helpers |
| `web/src/components/MaintenanceGate.tsx` | Pre-route probe, polling, fail-open behavior, global block |
| `web/src/contexts/MaintenanceContext.ts` | Shared maintenance state |
| `web/src/components/MaintenanceBanner.tsx` | Four-hour dismissible warning |
| `web/src/pages/MaintenancePage.tsx` | Active-window blocking screen |
| `web/src/components/AppShell.tsx`, `web/src/App.tsx`, `web/src/styles.css` | Global placement and presentation |

## 6. Deployment and operation

Apply the migration **after every other application schema file** because
`schema.sql` performs a blanket function-grant revoke:

```text
schema.sql -> schema_v2_reports.sql -> schema_v4_maintenance_mode.sql
```

When the planned v3 schema exists, the order becomes:

```text
schema.sql -> schema_v2_reports.sql -> schema_v3.sql -> schema_v4_maintenance_mode.sql
```

Schedule from the Supabase SQL editor (example only):

```sql
update public.site_maintenance
   set enabled = true,
       starts_at = '2026-08-15 22:00:00+07',
       ends_at = '2026-08-16 01:00:00+07',
       message = 'Maintenance sistem sedang dilakukan.',
       updated_at = now()
 where id = true;
```

Cancel it with `enabled = false`. Do not delete the singleton row.

## 7. Acceptance criteria

| # | Check | Expected |
|---|-------|----------|
| A-1 | Disabled schedule or time earlier than the four-hour lead | Site renders normally; no banner |
| A-2 | Time is exactly four hours before start | Banner appears above the masthead on Home, attempt intro/exam, and Pembahasan |
| A-3 | Close banner and navigate/reload in the same tab | Banner stays closed for that schedule |
| A-4 | Change the start/end values while the tab stays open | Poll picks up the new schedule and its warning is not considered dismissed |
| A-5 | Time reaches `starts_at` on an open route | Normal route unmounts and maintenance page replaces it |
| A-6 | Load any hash route during the active window | Route-specific data calls do not start; maintenance page renders |
| A-7 | Time reaches `ends_at`, or operator disables the row | Original hash route becomes accessible without a deployment |
| A-8 | Status RPC is missing/unreachable | Site fails open; an already-known schedule is retained until its own end |
| A-9 | Direct table select/update as `anon`/`authenticated` | Rejected; `get_maintenance_status()` remains callable before sign-in |
| A-10 | `cd web && npm run build` | Typecheck and production build exit 0 |
