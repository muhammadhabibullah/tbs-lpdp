-- =============================================================================
-- TBS LPDP Try Out — Supabase base schema (v1 tables, RLS, RPC)
-- Apply in the Supabase SQL editor (or `supabase db push`), then apply
-- `schema_v2_reports.sql`, then `schema_v3.sql`, then `maintenance.sql`.
-- Prereqs: enable Anonymous sign-in (Auth → Providers), create public bucket
--          `question-images` (Storage).
-- Design: docs/TECHNICAL_REQUIREMENTS.md §6–§8. Clients NEVER write tables
--         directly — all mutations go through the RPCs below. answer_keys has
--         no client-readable policy (constraint C-4).
-- Re-running this file is safe and idempotent, but it reverts later RPC/grant
-- definitions. Re-apply v2 and v3 afterwards; v3 must be last.
-- =============================================================================

-- ---------------------------------------------------------------- content ---

create table if not exists public.packages (
  id            integer primary key,
  title         text not null,
  description   text not null default '',
  is_published  boolean not null default false,
  created_at    timestamptz not null default now()
);

create table if not exists public.subtests (
  id               text primary key,              -- '<package>-<key>'
  package_id       integer not null references public.packages (id) on delete cascade,
  key              text not null check (key in ('verbal','kuantitatif','pemecahan_masalah')),
  name             text not null,
  position         integer not null,
  question_count   integer not null,
  duration_seconds integer not null,
  passing_grade    integer not null,
  unique (package_id, key),
  unique (package_id, position)
);

create table if not exists public.questions (
  id            text primary key,                 -- '<package>-<subtest>-<NNN>'
  subtest_id    text not null references public.subtests (id) on delete cascade,
  number        integer not null,
  qtype         text not null,
  question_text text not null,
  passage       text,
  image_url     text,
  difficulty    text not null check (difficulty in ('easy','medium','hard')),
  unique (subtest_id, number)
);

create table if not exists public.question_options (
  question_id text not null references public.questions (id) on delete cascade,
  key         char(1) not null check (key in ('A','B','C','D','E')),
  text        text not null,
  primary key (question_id, key)
);

create table if not exists public.answer_keys (
  question_id    text primary key references public.questions (id) on delete cascade,
  correct_option char(1) not null check (correct_option in ('A','B','C','D','E')),
  explanations   jsonb not null
);

-- -------------------------------------------------------------- user data ---

create table if not exists public.attempts (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  package_id  integer not null references public.packages (id),
  status      text not null default 'active' check (status in ('active','finished')),
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  total_score integer
);
create index if not exists attempts_user_idx on public.attempts (user_id, started_at desc);

create table if not exists public.section_attempts (
  id          uuid primary key default gen_random_uuid(),
  attempt_id  uuid not null references public.attempts (id) on delete cascade,
  subtest_id  text not null references public.subtests (id),
  status      text not null default 'active' check (status in ('active','finished')),
  started_at  timestamptz not null default now(),
  deadline_at timestamptz not null,
  finished_at timestamptz,
  score       integer,
  unique (attempt_id, subtest_id)
);

create table if not exists public.answers (
  section_attempt_id uuid not null references public.section_attempts (id) on delete cascade,
  question_id        text not null references public.questions (id),
  selected_option    char(1) check (selected_option in ('A','B','C','D','E')),
  is_doubtful        boolean not null default false,
  updated_at         timestamptz not null default now(),
  primary key (section_attempt_id, question_id)
);

create table if not exists public.answer_events (
  id                 bigint generated always as identity primary key,
  section_attempt_id uuid not null references public.section_attempts (id) on delete cascade,
  question_id        text,
  event_type         text not null check
    (event_type in ('start','save_answer','mark_doubt','unmark_doubt','finish')),
  payload            jsonb not null default '{}'::jsonb,
  created_at         timestamptz not null default now()
);
create index if not exists answer_events_section_idx
  on public.answer_events (section_attempt_id, created_at);

-- -------------------------------------------------------------- capacity ----
-- BE-18: one row, holding how full the project is and where the ceiling sits.
-- The free tier stops at 500 MB of database; past that Postgres starts refusing
-- writes, which would corrupt a try-out in progress. Rather than discover that
-- at 100%, the app stops taking on NEW attempts at the soft limit below and
-- lets everything already running finish.
--
-- The limits are data, not code: raise `limit_bytes` from the SQL editor (no
-- redeploy) if the plan changes.
--   update public.service_capacity set limit_bytes = 900 * 1024 * 1024;

create table if not exists public.service_capacity (
  id                 boolean primary key default true check (id),  -- single row
  db_bytes           bigint      not null default 0,
  attempt_rows       bigint      not null default 0,
  limit_bytes        bigint      not null default 400 * 1024 * 1024,
  limit_attempt_rows bigint      not null default 2000000,
  -- 'epoch' so the very first read always measures rather than trusting a zero.
  measured_at        timestamptz not null default 'epoch'
);

insert into public.service_capacity (id) values (true) on conflict (id) do nothing;

-- ------------------------------------------------------------------- RLS ----

alter table public.packages         enable row level security;
alter table public.subtests         enable row level security;
alter table public.questions        enable row level security;
alter table public.question_options enable row level security;
alter table public.answer_keys      enable row level security;   -- NO policies: never client-readable
alter table public.attempts         enable row level security;
alter table public.section_attempts enable row level security;
alter table public.answers          enable row level security;
alter table public.answer_events    enable row level security;
alter table public.service_capacity enable row level security;   -- NO policies: read it through get_service_status()

-- Policies are dropped first so the whole file stays re-appliable (NF-9);
-- Postgres has no `create policy if not exists`.

-- Published content is listable; question bodies are only served through RPCs.
drop policy if exists packages_read on public.packages;
create policy packages_read on public.packages
  for select to authenticated using (is_published);
drop policy if exists subtests_read on public.subtests;
create policy subtests_read on public.subtests
  for select to authenticated using (
    exists (select 1 from public.packages p where p.id = package_id and p.is_published)
  );
-- questions / question_options / answer_keys: intentionally NO client policies.

-- Users read their own attempt data (writes only via RPC).
drop policy if exists attempts_read on public.attempts;
create policy attempts_read on public.attempts
  for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists section_attempts_read on public.section_attempts;
create policy section_attempts_read on public.section_attempts
  for select to authenticated using (
    exists (select 1 from public.attempts a
            where a.id = attempt_id and a.user_id = (select auth.uid()))
  );
drop policy if exists answers_read on public.answers;
create policy answers_read on public.answers
  for select to authenticated using (
    exists (select 1 from public.section_attempts sa
            join public.attempts a on a.id = sa.attempt_id
            where sa.id = section_attempt_id and a.user_id = (select auth.uid()))
  );
drop policy if exists answer_events_read on public.answer_events;
create policy answer_events_read on public.answer_events
  for select to authenticated using (
    exists (select 1 from public.section_attempts sa
            join public.attempts a on a.id = sa.attempt_id
            where sa.id = section_attempt_id and a.user_id = (select auth.uid()))
  );

-- --------------------------------------------------------------- helpers ----

-- Grade + close a section (called by finish_section and by deadline sweeps).
create or replace function public._grade_section(p_section_attempt_id uuid)
returns integer
language plpgsql security definer set search_path = public
as $$
declare
  v_score integer;
  v_attempt uuid;
  v_all_done boolean;
begin
  select coalesce(count(*) filter (where ans.selected_option = ak.correct_option), 0) * 5
    into v_score
    from public.answers ans
    join public.answer_keys ak on ak.question_id = ans.question_id
   where ans.section_attempt_id = p_section_attempt_id;

  update public.section_attempts
     set status = 'finished', finished_at = now(), score = v_score
   where id = p_section_attempt_id and status = 'active'
  returning attempt_id into v_attempt;

  if v_attempt is null then  -- already finished: keep stored score (idempotent)
    select score, attempt_id into v_score, v_attempt
      from public.section_attempts where id = p_section_attempt_id;
    return v_score;
  end if;

  insert into public.answer_events (section_attempt_id, event_type, payload)
  values (p_section_attempt_id, 'finish', jsonb_build_object('score', v_score));

  -- Close the attempt when every subtest of the package has a finished section.
  select not exists (
           select 1
             from public.subtests st
             join public.attempts a on a.package_id = st.package_id
            where a.id = v_attempt
              and not exists (
                    select 1 from public.section_attempts sa
                     where sa.attempt_id = v_attempt
                       and sa.subtest_id = st.id
                       and sa.status = 'finished'))
    into v_all_done;

  if v_all_done then
    update public.attempts a
       set status = 'finished', finished_at = now(),
           total_score = (select coalesce(sum(sa.score), 0)
                            from public.section_attempts sa
                           where sa.attempt_id = a.id)
     where a.id = v_attempt and a.status = 'active';
  end if;

  return v_score;
end;
$$;

-- BE-17: append one row to the event log unless this section has already hit
-- the cap. `answers` is bounded by its primary key, so this log is the only
-- table a client could grow without limit — capping it bounds an attempt's
-- total storage, which is what keeps a scripted write loop from filling the
-- free tier's 500 MB. A normal section logs well under 200 rows (NF-1).
create or replace function public._log_event(
  p_section_attempt_id uuid, p_question_id text, p_event_type text, p_payload jsonb)
returns void
language plpgsql security definer set search_path = public
as $$
begin
  if (select count(*) from public.answer_events
       where section_attempt_id = p_section_attempt_id) >= 500 then
    return;
  end if;

  insert into public.answer_events (section_attempt_id, question_id, event_type, payload)
  values (p_section_attempt_id, p_question_id, p_event_type, coalesce(p_payload, '{}'::jsonb));
end;
$$;

-- BE-18: measure the project and stamp the snapshot. `pg_database_size` is a
-- directory stat (sub-millisecond); the row counts come from the planner's
-- estimates rather than count(*), so this stays O(1) no matter how big the
-- tables get. reltuples is -1 on a table that autovacuum has not analysed yet.
create or replace function public._refresh_capacity()
returns public.service_capacity
language plpgsql security definer set search_path = public
as $$
declare
  v_row public.service_capacity;
begin
  update public.service_capacity
     set db_bytes     = pg_database_size(current_database()),
         attempt_rows = (
           select coalesce(sum(greatest(c.reltuples, 0)), 0)::bigint
             from pg_class c
             join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public'
              and c.relkind = 'r'
              and c.relname in ('attempts','section_attempts','answers','answer_events')),
         measured_at  = now()
   where id
  returning * into v_row;
  return v_row;
end;
$$;

-- The snapshot, re-measured on read when it is older than 5 minutes. Deliberately
-- self-healing: the pg_cron job in maintenance.sql only keeps it warm, so the
-- guard still works on a project where cron was never set up.
create or replace function public._capacity()
returns public.service_capacity
language plpgsql security definer set search_path = public
as $$
declare
  v_row public.service_capacity;
begin
  select * into v_row from public.service_capacity where id;
  if v_row.id is null then
    insert into public.service_capacity (id) values (true) on conflict (id) do nothing;
    select * into v_row from public.service_capacity where id;
  end if;
  if v_row.measured_at < now() - interval '5 minutes' then
    v_row := public._refresh_capacity();
  end if;
  return v_row;
end;
$$;

-- Assert the caller owns an ACTIVE, not-past-deadline section; auto-finish if
-- the deadline passed. Returns the section row.
create or replace function public._assert_active_section(p_section_attempt_id uuid)
returns public.section_attempts
language plpgsql security definer set search_path = public
as $$
declare
  v_sa public.section_attempts;
begin
  select sa.* into v_sa
    from public.section_attempts sa
    join public.attempts a on a.id = sa.attempt_id
   where sa.id = p_section_attempt_id
     and a.user_id = (select auth.uid());
  if v_sa.id is null then
    raise exception 'section attempt not found' using errcode = 'P0002';
  end if;
  if v_sa.status = 'finished' then
    raise exception 'section already finished' using errcode = 'P0003';
  end if;
  if now() > v_sa.deadline_at + interval '5 seconds' then
    perform public._grade_section(v_sa.id);
    raise exception 'section deadline passed' using errcode = 'P0004';
  end if;
  return v_sa;
end;
$$;

-- ------------------------------------------------------------------ RPCs ----

create or replace function public.start_attempt(p_package_id integer)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_attempt public.attempts;
  v_cap public.service_capacity;
begin
  if (select auth.uid()) is null then
    raise exception 'not authenticated';
  end if;
  if not exists (select 1 from public.packages
                  where id = p_package_id and is_published) then
    raise exception 'package not found or unpublished' using errcode = 'P0002';
  end if;

  select * into v_attempt
    from public.attempts
   where user_id = (select auth.uid())
     and package_id = p_package_id and status = 'active'
   order by started_at desc limit 1;

  -- Everything below only gates *creating* an attempt: whatever a user already
  -- has open stays resumable, gradeable and reviewable no matter how full the
  -- project is. Refusing someone mid-exam would cost them their answers.
  if v_attempt.id is null then
    -- BE-18: global storage ceiling.
    v_cap := public._capacity();
    if v_cap.db_bytes >= v_cap.limit_bytes
       or v_cap.attempt_rows >= v_cap.limit_attempt_rows then
      raise exception 'storage capacity reached' using errcode = 'P0007';
    end if;

    -- BE-16: per-user hourly budget. Bounds the row growth (and the scripted
    -- key dump) a loop over this RPC would otherwise produce.
    if (select count(*) from public.attempts
         where user_id = (select auth.uid())
           and started_at > now() - interval '1 hour') >= 10 then
      raise exception 'too many attempts' using errcode = 'P0005';
    end if;

    insert into public.attempts (user_id, package_id)
    values ((select auth.uid()), p_package_id)
    returning * into v_attempt;
  end if;

  return json_build_object('attempt', row_to_json(v_attempt),
                           'server_time', now());
end;
$$;

-- BE-18: what the home page needs to know before it offers the button (FE-19).
-- Returns a coarse percentage, never the raw byte counts — the client has no
-- use for them, and a public "how full is the database" gauge is free recon.
create or replace function public.get_service_status()
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_cap public.service_capacity;
  v_usage numeric;
begin
  v_cap := public._capacity();
  v_usage := greatest(
    v_cap.db_bytes::numeric     / nullif(v_cap.limit_bytes, 0),
    v_cap.attempt_rows::numeric / nullif(v_cap.limit_attempt_rows, 0));
  v_usage := coalesce(v_usage, 0);

  return json_build_object(
    'accepting_attempts', v_usage < 1,
    'usage_percent', least(100, round(v_usage * 100))::integer,
    'measured_at', v_cap.measured_at,
    'server_time', now());
end;
$$;

create or replace function public.start_section(p_attempt_id uuid)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_attempt public.attempts;
  v_sa public.section_attempts;
  v_subtest public.subtests;
begin
  select * into v_attempt from public.attempts
   where id = p_attempt_id and user_id = (select auth.uid());
  if v_attempt.id is null then
    raise exception 'attempt not found' using errcode = 'P0002';
  end if;

  -- Sweep: auto-finish any of the caller's sections past deadline.
  perform public._grade_section(sa.id)
     from public.section_attempts sa
    where sa.attempt_id = p_attempt_id and sa.status = 'active'
      and now() > sa.deadline_at + interval '5 seconds';

  -- Resume an active section if one remains.
  select sa.* into v_sa from public.section_attempts sa
   where sa.attempt_id = p_attempt_id and sa.status = 'active'
   limit 1;

  if v_sa.id is null then
    -- Next unstarted subtest by position.
    select st.* into v_subtest
      from public.subtests st
     where st.package_id = v_attempt.package_id
       and not exists (select 1 from public.section_attempts sa
                        where sa.attempt_id = p_attempt_id
                          and sa.subtest_id = st.id)
     order by st.position limit 1;

    if v_subtest.id is null then
      return json_build_object('done', true, 'server_time', now());
    end if;

    insert into public.section_attempts (attempt_id, subtest_id, deadline_at)
    values (p_attempt_id, v_subtest.id,
            now() + make_interval(secs => v_subtest.duration_seconds))
    returning * into v_sa;

    insert into public.answer_events (section_attempt_id, event_type, payload)
    values (v_sa.id, 'start', jsonb_build_object('subtest', v_subtest.key));
  else
    select * into v_subtest from public.subtests where id = v_sa.subtest_id;
  end if;

  return json_build_object(
    'section_attempt', row_to_json(v_sa),
    'subtest', row_to_json(v_subtest),
    'server_time', now(),
    'questions', (
      select coalesce(json_agg(json_build_object(
               'id', q.id, 'number', q.number, 'qtype', q.qtype,
               'question_text', q.question_text, 'passage', q.passage,
               'image_url', q.image_url,
               'options', (select json_agg(json_build_object('key', o.key, 'text', o.text)
                                           order by o.key)
                             from public.question_options o
                            where o.question_id = q.id)
             ) order by q.number), '[]'::json)
        from public.questions q
       where q.subtest_id = v_sa.subtest_id),
    'answers', (
      select coalesce(json_agg(json_build_object(
               'question_id', ans.question_id,
               'selected_option', ans.selected_option,
               'is_doubtful', ans.is_doubtful)), '[]'::json)
        from public.answers ans
       where ans.section_attempt_id = v_sa.id)
  );
end;
$$;

create or replace function public.save_answer(
  p_section_attempt_id uuid, p_question_id text, p_option char(1))
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_sa public.section_attempts;
begin
  v_sa := public._assert_active_section(p_section_attempt_id);
  if p_option is not null and p_option not in ('A','B','C','D','E') then
    raise exception 'invalid option';
  end if;
  if not exists (select 1 from public.questions
                  where id = p_question_id and subtest_id = v_sa.subtest_id) then
    raise exception 'question not in this section' using errcode = 'P0002';
  end if;

  insert into public.answers (section_attempt_id, question_id, selected_option)
  values (p_section_attempt_id, p_question_id, p_option)
  on conflict (section_attempt_id, question_id)
  do update set selected_option = excluded.selected_option, updated_at = now();

  perform public._log_event(p_section_attempt_id, p_question_id, 'save_answer',
                            jsonb_build_object('option', p_option));

  return json_build_object('ok', true, 'server_time', now());
end;
$$;

create or replace function public.toggle_doubt(
  p_section_attempt_id uuid, p_question_id text, p_doubtful boolean)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_sa public.section_attempts;
begin
  v_sa := public._assert_active_section(p_section_attempt_id);
  if not exists (select 1 from public.questions
                  where id = p_question_id and subtest_id = v_sa.subtest_id) then
    raise exception 'question not in this section' using errcode = 'P0002';
  end if;

  insert into public.answers (section_attempt_id, question_id, is_doubtful)
  values (p_section_attempt_id, p_question_id, p_doubtful)
  on conflict (section_attempt_id, question_id)
  do update set is_doubtful = excluded.is_doubtful, updated_at = now();

  perform public._log_event(p_section_attempt_id, p_question_id,
                            case when p_doubtful then 'mark_doubt' else 'unmark_doubt' end,
                            '{}'::jsonb);

  return json_build_object('ok', true, 'server_time', now());
end;
$$;

create or replace function public.finish_section(p_section_attempt_id uuid)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_score integer;
  v_attempt public.attempts;
begin
  -- Ownership check (allows finishing even past deadline — it grades as-is).
  if not exists (select 1 from public.section_attempts sa
                   join public.attempts a on a.id = sa.attempt_id
                  where sa.id = p_section_attempt_id
                    and a.user_id = (select auth.uid())) then
    raise exception 'section attempt not found' using errcode = 'P0002';
  end if;

  v_score := public._grade_section(p_section_attempt_id);

  select a.* into v_attempt
    from public.attempts a
    join public.section_attempts sa on sa.attempt_id = a.id
   where sa.id = p_section_attempt_id;

  return json_build_object(
    'score', v_score,
    'attempt_status', v_attempt.status,
    'total_score', v_attempt.total_score,
    'server_time', now());
end;
$$;

create or replace function public.get_attempt_state(p_attempt_id uuid)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_attempt public.attempts;
begin
  select * into v_attempt from public.attempts
   where id = p_attempt_id and user_id = (select auth.uid());
  if v_attempt.id is null then
    raise exception 'attempt not found' using errcode = 'P0002';
  end if;

  return json_build_object(
    'attempt', row_to_json(v_attempt),
    'server_time', now(),
    'sections', (
      select coalesce(json_agg(json_build_object(
               'section_attempt', row_to_json(sa),
               'subtest', (select row_to_json(st) from public.subtests st
                            where st.id = sa.subtest_id)
             ) order by sa.started_at), '[]'::json)
        from public.section_attempts sa
       where sa.attempt_id = p_attempt_id));
end;
$$;

-- NOTE (v2): schema_v2_reports.sql re-creates this function with an extra
-- `my_report` field per question. Re-applying THIS file reverts that, so run
-- schema_v2_reports.sql again afterwards (it is idempotent).
create or replace function public.get_review(p_attempt_id uuid)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_attempt public.attempts;
begin
  select * into v_attempt from public.attempts
   where id = p_attempt_id and user_id = (select auth.uid());
  if v_attempt.id is null then
    raise exception 'attempt not found' using errcode = 'P0002';
  end if;

  -- Keys/explanations ONLY for finished sections of the caller's own attempt.
  return json_build_object(
    'attempt', row_to_json(v_attempt),
    'sections', (
      select coalesce(json_agg(json_build_object(
        'subtest', (select row_to_json(st) from public.subtests st
                     where st.id = sa.subtest_id),
        'score', sa.score,
        'questions', (
          select json_agg(json_build_object(
                   'id', q.id, 'number', q.number, 'qtype', q.qtype,
                   'question_text', q.question_text, 'passage', q.passage,
                   'image_url', q.image_url,
                   'options', (select json_agg(json_build_object('key', o.key, 'text', o.text)
                                               order by o.key)
                                 from public.question_options o
                                where o.question_id = q.id),
                   'selected_option', ans.selected_option,
                   'is_doubtful', coalesce(ans.is_doubtful, false),
                   'correct_option', ak.correct_option,
                   'explanations', ak.explanations
                 ) order by q.number)
            from public.questions q
            join public.answer_keys ak on ak.question_id = q.id
            left join public.answers ans
              on ans.question_id = q.id and ans.section_attempt_id = sa.id
           where q.subtest_id = sa.subtest_id)
      ) order by (select position from public.subtests where id = sa.subtest_id)),
      '[]'::json)
        from public.section_attempts sa
       where sa.attempt_id = p_attempt_id and sa.status = 'finished'));
end;
$$;

-- --------------------------------------------------------------- storage ----
-- Public-read bucket for question images (BE-4). Idempotent so a fresh project
-- is fully provisioned by this file alone (NF-5); uploads use service_role.

insert into storage.buckets (id, name, public)
values ('question-images', 'question-images', true)
on conflict (id) do update set public = true;

-- If this errors with "must be owner of table objects", the project restricts
-- policy DDL on storage.objects: create the same read policy from the Storage
-- dashboard instead (bucket question-images → public read).
drop policy if exists question_images_public_read on storage.objects;
create policy question_images_public_read on storage.objects
  for select to anon, authenticated using (bucket_id = 'question-images');

-- ---------------------------------------------------------------- grants ----

revoke all on all tables in schema public from anon;
revoke all on all functions in schema public from anon, authenticated, public;

grant execute on function
  public.get_service_status(),
  public.start_attempt(integer),
  public.start_section(uuid),
  public.save_answer(uuid, text, char),
  public.toggle_doubt(uuid, text, boolean),
  public.finish_section(uuid),
  public.get_attempt_state(uuid),
  public.get_review(uuid)
to authenticated;

-- The revoke above also strips the v2 report RPCs, so if schema_v2_reports.sql
-- has been applied, run it again after this file (it re-grants them).
