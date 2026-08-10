-- =============================================================================
-- TBS LPDP Try Out — scheduled maintenance (NF-10)
--
-- Apply LAST, after schema.sql and schema_v2_reports.sql, in the Supabase SQL
-- editor. Unlike those two files this one is *operational*, not part of the
-- application contract: nothing in the app depends on it, and re-applying the
-- schema files never undoes it.
--
-- Why it exists: the free tier caps the database at 500 MB, and two things grow
-- forever without a sweeper — the append-only event log, and the anonymous
-- auth users that one-per-browser sign-in creates (BE-1). The per-attempt caps
-- (BE-15/BE-16) bound how fast that happens; these jobs bound the total.
--
-- Fully idempotent: cron.schedule() replaces a job of the same name.
-- =============================================================================

-- Enable pg_cron once (Database → Extensions in the dashboard does the same).
create extension if not exists pg_cron;

-- ---------------------------------------------------------- 1. event log ----
-- answer_events is written by the RPCs and read by nobody but the developer
-- (it exists to reconstruct what happened during a section). 30 days is far
-- longer than any dispute about a try-out is going to stay interesting.

select cron.schedule(
  'prune-answer-events',
  '0 3 * * *',                       -- 03:00 UTC daily
  $$delete from public.answer_events where created_at < now() - interval '30 days'$$
);

-- ----------------------------------------------------- 2. anonymous users ----
-- Every browser that opens the site becomes a permanent auth.users row that
-- counts toward the MAU quota. Deleting one cascades to their attempts,
-- sections, answers, events and reports (all FKs are `on delete cascade`), so
-- anyone who took the trouble to file feedback is deliberately kept: their
-- report is evidence about a question and must outlive their session.
--
-- Runs as the role that scheduled it. If it fails with a permission error on
-- auth.users, delete through the Auth admin API instead (service-role key)
-- rather than granting the cron role rights over the auth schema.

select cron.schedule(
  'prune-anonymous-users',
  '30 3 * * *',                      -- 03:30 UTC daily, after the log sweep
  $$
  delete from auth.users u
   where u.is_anonymous
     and coalesce(u.last_sign_in_at, u.created_at) < now() - interval '60 days'
     and not exists (select 1 from public.question_reports r where r.user_id = u.id)
  $$
);

-- ------------------------------------------------------------------ checks ---
-- Scheduled jobs:            select jobid, jobname, schedule, active from cron.job;
-- Last runs (and failures):  select jobname, status, return_message, start_time
--                              from cron.job_run_details order by start_time desc limit 20;
-- Unschedule one:            select cron.unschedule('prune-answer-events');
--
-- Watch the number that actually matters (free tier ceiling: 500 MB):
--   select pg_size_pretty(pg_database_size(current_database()));
--   select relname, pg_size_pretty(pg_total_relation_size(c.oid)) as size
--     from pg_class c join pg_namespace n on n.oid = c.relnamespace
--    where n.nspname in ('public','auth') and c.relkind = 'r'
--    order by pg_total_relation_size(c.oid) desc limit 10;
-- =============================================================================
