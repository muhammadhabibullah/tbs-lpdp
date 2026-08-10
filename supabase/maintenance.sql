-- =============================================================================
-- TBS LPDP Try Out — scheduled maintenance (NF-10)
--
-- Apply LAST, after schema.sql, schema_v2_reports.sql, and schema_v3.sql, in the Supabase SQL
-- editor. Unlike those two files this one is *operational*, not part of the
-- application contract. Re-applying the schema files never unschedules these
-- jobs, but maintenance.sql must be re-applied when a job definition changes.
--
-- Why it exists: the free tier caps the database at 500 MB, and two things grow
-- forever without a sweeper — attempt data (answers plus the append-only event
-- log), and the anonymous auth users that one-per-browser sign-in creates
-- (BE-1). The per-attempt caps (BE-16/BE-17) bound how fast that happens;
-- these jobs bound the total.
--
-- Fully idempotent: cron.schedule() replaces a job of the same name.
-- =============================================================================

-- Enable pg_cron/pg_net once (Database → Extensions in the dashboard does the same).
create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;

-- ------------------------------------------------------- 1. attempt data ----
-- 7 days, as the site footer promises. Deleting an attempt cascades to its
-- section_attempts → answers and answer_events, so this one statement retires
-- a user's whole history including the Pembahasan they can still open today.
-- question_reports survive: their attempt_id is `on delete set null`, because a
-- report is evidence about a question, not about the attempt it came from.
--
-- KEEP IN SYNC with the retention line in web/src/components/FeedbackFooter.tsx.

select cron.schedule(
  'prune-attempts',
  '0 3 * * *',                       -- 03:00 UTC daily
  $$delete from public.attempts where started_at < now() - interval '7 days'$$
);

-- Left over from before the cascade above covered it; unschedule it if this
-- file was applied in an earlier form (harmless to run when absent).
--   select cron.unschedule('prune-answer-events');

-- ------------------------------------------------- 2. capacity snapshot ----
-- Optional, and only a warm-up: public._capacity() re-measures on read whenever
-- the snapshot is older than 5 minutes (BE-18), so the guard works with or
-- without this job. Scheduling it just moves that measurement off the request
-- that would otherwise pay for it.

select cron.schedule(
  'refresh-service-capacity',
  '*/5 * * * *',
  $$select public._refresh_capacity()$$
);

-- ----------------------------------------------------- 3. anonymous users ----
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
  '30 3 * * *',                      -- 03:30 UTC daily, after the attempt sweep
  $$
  delete from auth.users u
   where u.is_anonymous
     and coalesce(u.last_sign_in_at, u.created_at) < now() - interval '60 days'
     and not exists (select 1 from public.question_reports r where r.user_id = u.id)
  $$
);

-- ------------------------------------------ 4. daily question-report email ----
-- v3: the daily job creates one fixed outbox window and invokes the private
-- Edge Function. The retry job only re-invokes an existing unsent run; it
-- never creates another daily email. Required Vault secrets:
--
--   select vault.create_secret('https://PROJECT.supabase.co', 'project_url');
--   select vault.create_secret('sb_secret_...', 'automation_key');
--
-- Deploy `question-report-digest` and configure its RESEND/recipient secrets
-- before scheduling this job. The Edge Function authenticates the named
-- `automations` secret key sent in the `apikey` header.

create or replace function public._queue_question_report_digest(p_create boolean default true)
returns bigint
language plpgsql security definer
set search_path = public, extensions, net, vault
as $$
declare
  v_run public.question_report_digest_runs;
  v_run_id uuid;
  v_window_start timestamptz;
  v_project_url text;
  v_automation_key text;
  v_request_id bigint;
begin
  -- Prevent the daily and retry schedules from racing each other.
  perform pg_advisory_xact_lock(hashtext('tbs-question-report-digest'));

  select * into v_run from public.question_report_digest_runs
   where status <> 'sent' order by created_at limit 1;
  if v_run.id is not null then
    if v_run.status = 'manual_attention'
       or (v_run.status = 'sending' and v_run.lease_until >= now()) then
      return null;
    end if;
    v_run_id := v_run.id;
  elsif p_create then
    select coalesce(max(window_end), now() - interval '1 day')
      into v_window_start from public.question_report_digest_runs where status = 'sent';
    v_run_id := public._prepare_question_report_digest_run(v_window_start, now());
  else
    return null;
  end if;

  select decrypted_secret into v_project_url
    from vault.decrypted_secrets where name = 'project_url' limit 1;
  select decrypted_secret into v_automation_key
    from vault.decrypted_secrets where name = 'automation_key' limit 1;
  if v_project_url is null or v_automation_key is null then
    raise exception 'Vault secrets project_url and automation_key are required';
  end if;

  select net.http_post(
    url := rtrim(v_project_url, '/') || '/functions/v1/question-report-digest',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'apikey', v_automation_key),
    body := jsonb_build_object('run_id', v_run_id),
    timeout_milliseconds := 15000)
  into v_request_id;
  return v_request_id;
end;
$$;

revoke all on function public._queue_question_report_digest(boolean)
from anon, authenticated, public;

select cron.schedule(
  'question-report-digest-daily',
  '0 1 * * *',                       -- 08:00 WIB daily
  $$select public._queue_question_report_digest(true)$$
);

select cron.schedule(
  'question-report-digest-retry',
  '*/30 * * * *',                    -- retries only; no extra daily window
  $$select public._queue_question_report_digest(false)$$
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
