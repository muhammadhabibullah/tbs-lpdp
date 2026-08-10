# Capacity guard (BE-18 / FE-19 / NF-11)

How the site stops taking on new attempts before the Supabase free tier runs out
of database, and how the UI says so. Implements requirements BE-18, FE-19 and
NF-11 in [`TECHNICAL_REQUIREMENTS.md`](TECHNICAL_REQUIREMENTS.md).

## 1. Why

The free plan gives ~500 MB of Postgres. Past it, writes start failing — and a
write failing at that moment does not fail politely: it fails inside
`save_answer` for somebody 20 minutes into a timed section, whose answers are
now unsaveable and whose clock keeps running. Every other limit degrades
gracefully; this one destroys work in progress.

So the guard is deliberately asymmetric:

| Operation | At capacity |
|-----------|-------------|
| `start_attempt` (new attempt) | **refused**, `P0007` |
| `start_attempt` (resume an active one) | allowed |
| `start_section`, `save_answer`, `toggle_doubt`, `finish_section` | allowed |
| `get_attempt_state`, `get_review` | allowed |
| `report_question` | allowed — a report is one small row and is the most valuable row in the database |

Nobody mid-exam is ever cut off. The only thing that stops is *taking on new
work*, which is also the only thing that meaningfully adds rows: an attempt
costs ~300 rows (BE-17 caps it), a report costs one.

## 2. What is measured

`public.service_capacity` — a single row, `id boolean primary key default true
check (id)`, so the table can hold exactly one:

| Column | Meaning |
|--------|---------|
| `db_bytes` | `pg_database_size(current_database())` at `measured_at` |
| `attempt_rows` | estimated live rows across `attempts`, `section_attempts`, `answers`, `answer_events` |
| `limit_bytes` | soft ceiling — default `400 * 1024 * 1024` (80 % of the free tier) |
| `limit_attempt_rows` | secondary ceiling — default 2,000,000 |
| `measured_at` | when the snapshot was taken; defaults to `'epoch'` so the first read always measures |

**Bytes are the real guard.** Rows are the number that is easy to reason about,
but bloat and index overhead mean rows and bytes drift apart; the row ceiling is
a backstop for the case where something inflates row counts without inflating
size yet. 2,000,000 rows ≈ 6,600 attempts at BE-17's cap, which lands in the
same neighbourhood as 400 MB.

`attempt_rows` comes from `pg_class.reltuples` (the planner's estimate,
maintained by autovacuum), never `count(*)` — this must stay O(1) as the tables
grow, and an estimate that is a few percent stale cannot change a decision made
at 80 % of a ceiling. `reltuples` is `-1` on a relation that has never been
analysed, hence the `greatest(c.reltuples, 0)`.

**The limits are data, not code.** Raising them needs no deploy:

```sql
update public.service_capacity set limit_bytes = 900 * 1024 * 1024;
```

## 3. How it is read

Two `security definer` helpers in `schema.sql`, neither granted to any client:

- `_refresh_capacity()` — measures and stamps the row, returns it.
- `_capacity()` — returns the row, calling `_refresh_capacity()` first if
  `measured_at` is older than 5 minutes.

The staleness check is what makes this **self-healing**: the guard is correct on
a project where `pg_cron` was never enabled, because any read older than 5
minutes pays for its own measurement. The `refresh-service-capacity` job in
`maintenance.sql` is purely a warm-up — it moves that measurement off a user's
request. If cron stops, nothing breaks.

Cost per measurement: `pg_database_size` is a directory stat (sub-millisecond),
`reltuples` is a catalog lookup. At most one measurement per 5 minutes across
all users, plus whatever cron does.

Concurrency: two sessions can refresh at once. Both run the same idempotent
`UPDATE`; the loser overwrites with an equally-fresh number. No locking needed.

## 4. Enforcement

Inside `start_attempt`, after the existing-active-attempt lookup and before the
`INSERT` — so resuming is never gated — and before the BE-16 per-user rate
limit, since a global stop should not be reported as a personal one:

```sql
v_cap := public._capacity();
if v_cap.db_bytes >= v_cap.limit_bytes
   or v_cap.attempt_rows >= v_cap.limit_attempt_rows then
  raise exception 'storage capacity reached' using errcode = 'P0007';
end if;
```

`P0007` joins the terminal codes in `web/src/lib/api.ts` — `withRetry` must not
retry it, because a retry 300 ms later is still full.

## 5. What the client sees

`get_service_status()` (granted to `authenticated`) returns:

```json
{ "accepting_attempts": true, "usage_percent": 3, "measured_at": "…", "server_time": "…" }
```

Raw byte counts stay server-side. The client has no use for them, and a public
"how full is this database" gauge is free reconnaissance for anyone thinking
about filling it.

`service_capacity` itself has RLS enabled with **no policies**, following the
project convention: clients read through the RPC, never the table.

## 6. UI states (FE-19)

`HomePage` requests the status alongside packages and history. Three states:

| `status` | Start buttons | Banner |
|----------|---------------|--------|
| `accepting_attempts: true` | enabled, "Mulai Try Out" | none |
| `accepting_attempts: false` | **disabled**, relabelled "Kuota Penuh", `title` explains | `notice warn` above the package list |
| `null` (probe failed) | enabled | none |

The `null` case is deliberate. The probe is wrapped in `.catch(() => null)` so a
project on an older schema — no `get_service_status` — keeps working exactly as
before, and a transient failure of the probe never takes down a page that would
otherwise be fine. Unknown means open; the server is still the authority.

That leaves one race: capacity runs out between the page load and the click. The
RPC then raises `P0007`, and `startErrorMessage` maps it to the *same* copy as
the banner, so the user reads one explanation rather than two different ones.
The banner suppresses itself when the error card is already showing that text.

Mock parity (FE-17): `mockApi` reads `localStorage['tbs-lpdp.mock.full']` — set
it to `'true'` to rehearse the full state, including the `P0007` throw from
`startAttempt`, with no Supabase project.

## 7. Operating it

```sql
-- Where are we?
select pg_size_pretty(db_bytes) as used,
       pg_size_pretty(limit_bytes) as soft_limit,
       attempt_rows, measured_at
  from public.service_capacity;

-- Force a measurement now (bypasses the 5-minute window)
select public._refresh_capacity();

-- Biggest tables, when the number surprises you
select relname, pg_size_pretty(pg_total_relation_size(c.oid)) as size
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname in ('public','auth') and c.relkind = 'r'
 order by pg_total_relation_size(c.oid) desc limit 10;
```

If the guard trips, the ordinary remedy is to wait: NF-10's daily sweep drops
attempts older than 7 days, so usage falls on its own. Reclaiming space *now*
means `vacuum full` (locks the table) or lowering the retention window. Raising
`limit_bytes` above ~90 % of the plan only buys the ability to hit the hard wall
described in §1.
