-- =============================================================================
-- TBS LPDP Try Out — v3
-- Immutable question/package releases, pinned attempts, durable package stats,
-- revision-aware reports, package catalogue, and report-digest outbox.
--
-- Apply AFTER schema.sql and schema_v2_reports.sql. Re-apply this file whenever
-- either earlier schema file is re-applied: v3 owns the final RPC definitions
-- and grants. Apply maintenance.sql last.
--
-- Design: docs/TECHNICAL_REQUIREMENTS_V3.md
-- =============================================================================

create extension if not exists pgcrypto with schema extensions;

-- --------------------------------------------------------------- hashing ----

create or replace function public._v3_hash_jsonb(p_value jsonb)
returns text
language sql immutable
set search_path = public, extensions
as $$
  select encode(digest(convert_to(p_value::text, 'UTF8'), 'sha256'), 'hex');
$$;

create or replace function public._v3_question_hash(
  p_id text,
  p_subtest text,
  p_number integer,
  p_qtype text,
  p_question_text text,
  p_passage text,
  p_image_sha256 text,
  p_difficulty text,
  p_options jsonb,
  p_correct_option char(1),
  p_explanations jsonb)
returns text
language sql immutable
set search_path = public, extensions
as $$
  select public._v3_hash_jsonb(jsonb_build_object(
    'id', p_id,
    'subtest', p_subtest,
    'number', p_number,
    'type', p_qtype,
    'question_text', p_question_text,
    'passage', p_passage,
    'image_sha256', p_image_sha256,
    'difficulty', p_difficulty,
    'options', p_options,
    'correct_option', p_correct_option,
    'explanations', p_explanations));
$$;

-- -------------------------------------------------------------- revisions ---

create table if not exists public.question_revisions (
  id             uuid primary key default gen_random_uuid(),
  question_id    text not null references public.questions (id),
  version        integer not null check (version > 0),
  qtype          text not null,
  question_text  text not null,
  passage        text,
  image_url      text,
  image_sha256   text check (image_sha256 is null or length(image_sha256) = 64),
  difficulty     text not null check (difficulty in ('easy','medium','hard')),
  correct_option char(1) not null check (correct_option in ('A','B','C','D','E')),
  explanations   jsonb not null,
  content_hash   text not null check (length(content_hash) = 64),
  published_at   timestamptz not null default now(),
  unique (question_id, version),
  unique (id, question_id)
);
create index if not exists question_revisions_hash_idx
  on public.question_revisions (question_id, content_hash);

create table if not exists public.question_revision_options (
  question_revision_id uuid not null references public.question_revisions (id),
  key                  char(1) not null check (key in ('A','B','C','D','E')),
  text                 text not null,
  primary key (question_revision_id, key)
);

create table if not exists public.package_releases (
  id           uuid primary key default gen_random_uuid(),
  package_id   integer not null references public.packages (id),
  version      integer not null check (version > 0),
  title        text not null,
  description  text not null default '',
  difficulty   text not null check (difficulty in ('easy','medium','hard')),
  ai_model     text not null check (btrim(ai_model) <> ''),
  content_hash text not null check (length(content_hash) = 64),
  published_at timestamptz not null default now(),
  unique (package_id, version),
  unique (id, package_id)
);
create index if not exists package_releases_hash_idx
  on public.package_releases (package_id, content_hash);

create table if not exists public.package_release_questions (
  package_release_id   uuid not null,
  package_id           integer not null,
  question_id          text not null references public.questions (id),
  question_revision_id uuid not null,
  subtest_id           text not null references public.subtests (id),
  number               integer not null,
  primary key (package_release_id, question_id),
  unique (package_release_id, subtest_id, number),
  foreign key (package_release_id, package_id)
    references public.package_releases (id, package_id),
  foreign key (question_revision_id, question_id)
    references public.question_revisions (id, question_id)
);
create index if not exists package_release_questions_subtest_idx
  on public.package_release_questions (package_release_id, subtest_id, number);

alter table public.packages
  add column if not exists current_release_id uuid references public.package_releases (id);
alter table public.attempts
  add column if not exists package_release_id uuid references public.package_releases (id);
alter table public.answers
  add column if not exists question_revision_id uuid references public.question_revisions (id);
alter table public.question_reports
  add column if not exists question_revision_id uuid references public.question_revisions (id);

-- The old v2 constraint allowed only one report for a logical question. v3
-- allows a user to report each immutable revision independently.
alter table public.question_reports
  drop constraint if exists question_reports_user_id_question_id_key;
create unique index if not exists question_reports_user_revision_uidx
  on public.question_reports (user_id, question_revision_id)
  where question_revision_id is not null;

-- ------------------------------------------------------------- statistics ---

create table if not exists public.package_statistics (
  package_id               integer primary key references public.packages (id),
  attempts_started_total   bigint not null default 0 check (attempts_started_total >= 0),
  attempts_completed_total bigint not null default 0 check (attempts_completed_total >= 0),
  score_sum                bigint not null default 0 check (score_sum >= 0),
  coverage_started_at      timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  check (attempts_completed_total <= attempts_started_total)
);

-- ---------------------------------------------------------- digest outbox ---

create table if not exists public.question_report_digest_runs (
  id                  uuid primary key default gen_random_uuid(),
  window_start        timestamptz not null,
  window_end          timestamptz not null check (window_end > window_start),
  status              text not null default 'pending' check
                        (status in ('pending','sending','sent','failed','manual_attention')),
  delivery_attempts   integer not null default 0 check (delivery_attempts >= 0),
  lease_until         timestamptz,
  email_payload       jsonb not null,
  payload_sha256      text not null check (length(payload_sha256) = 64),
  provider_message_id text,
  last_error          text,
  created_at          timestamptz not null default now(),
  sent_at             timestamptz,
  updated_at          timestamptz not null default now(),
  unique (window_start, window_end)
);
-- A manual-attention run deliberately blocks later windows: advancing would
-- create a gap in the operator's digest history.
create unique index if not exists question_report_digest_one_unsent_uidx
  on public.question_report_digest_runs ((true))
  where status <> 'sent';

-- ----------------------------------------------------------- immutability ---

create or replace function public._v3_reject_immutable_change()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  raise exception '% is immutable; publish a new revision/release', tg_table_name
    using errcode = '55000';
end;
$$;

-- ---------------------------------------------------------- JSON helpers ----

create or replace function public._v3_release_package_json(p_release_id uuid)
returns json
language sql stable security definer
set search_path = public
as $$
  select json_build_object(
    'id', pr.package_id,
    'title', pr.title,
    'description', pr.description,
    'is_published', p.is_published,
    'created_at', p.created_at,
    'difficulty', pr.difficulty,
    'ai_model', pr.ai_model,
    'question_version', pr.version,
    'last_updated_at', pr.published_at,
    'completed_attempts_total', coalesce(ps.attempts_completed_total, 0),
    'mean_score', case when coalesce(ps.attempts_completed_total, 0) = 0 then null
                       else round(ps.score_sum::numeric / ps.attempts_completed_total, 1) end,
    'statistics_coverage_started_at', ps.coverage_started_at,
    'subtests', (
      select coalesce(json_agg(row_to_json(st) order by st.position), '[]'::json)
        from public.subtests st where st.package_id = pr.package_id))
    from public.package_releases pr
    join public.packages p on p.id = pr.package_id
    left join public.package_statistics ps on ps.package_id = pr.package_id
   where pr.id = p_release_id;
$$;

-- ----------------------------------------------------------- catalogue -----

create or replace function public.get_package_catalog()
returns json
language sql stable security definer
set search_path = public
as $$
  select coalesce(json_agg(public._v3_release_package_json(p.current_release_id) order by p.id), '[]'::json)
    from public.packages p
   where p.is_published and p.current_release_id is not null;
$$;

create or replace function public.get_attempt_summaries()
returns json
language sql stable security definer
set search_path = public
as $$
  select coalesce(json_agg(json_build_object(
           'id', a.id,
           'package_id', a.package_id,
           'package_title', pr.title,
           'package_version', pr.version,
           'status', a.status,
           'started_at', a.started_at,
           'total_score', a.total_score,
           'finished_sections', (select count(*) from public.section_attempts sa
                                  where sa.attempt_id = a.id and sa.status = 'finished'),
           'total_sections', (select count(*) from public.subtests st
                               where st.package_id = a.package_id)
         ) order by a.started_at desc), '[]'::json)
    from (select * from public.attempts
           where user_id = (select auth.uid())
           order by started_at desc limit 25) a
    join public.package_releases pr on pr.id = a.package_release_id;
$$;

-- --------------------------------------------------------------- grading ---

create or replace function public._grade_section(p_section_attempt_id uuid)
returns integer
language plpgsql security definer
set search_path = public
as $$
declare
  v_score integer;
  v_attempt_id uuid;
  v_all_done boolean;
  v_finished_attempt public.attempts;
begin
  select coalesce(count(*) filter (
           where ans.selected_option = qr.correct_option), 0) * 5
    into v_score
    from public.answers ans
    join public.question_revisions qr on qr.id = ans.question_revision_id
   where ans.section_attempt_id = p_section_attempt_id;

  update public.section_attempts
     set status = 'finished', finished_at = now(), score = v_score
   where id = p_section_attempt_id and status = 'active'
  returning attempt_id into v_attempt_id;

  if v_attempt_id is null then
    select score, attempt_id into v_score, v_attempt_id
      from public.section_attempts where id = p_section_attempt_id;
    return v_score;
  end if;

  insert into public.answer_events (section_attempt_id, event_type, payload)
  values (p_section_attempt_id, 'finish', jsonb_build_object('score', v_score));

  select not exists (
           select 1 from public.subtests st
           join public.attempts a on a.package_id = st.package_id
            where a.id = v_attempt_id
              and not exists (
                    select 1 from public.section_attempts sa
                     where sa.attempt_id = v_attempt_id
                       and sa.subtest_id = st.id and sa.status = 'finished'))
    into v_all_done;

  if v_all_done then
    update public.attempts a
       set status = 'finished', finished_at = now(),
           total_score = (select coalesce(sum(sa.score), 0)
                            from public.section_attempts sa where sa.attempt_id = a.id)
     where a.id = v_attempt_id and a.status = 'active'
    returning a.* into v_finished_attempt;

    -- Only the transaction that changed active -> finished gets a returned row.
    if v_finished_attempt.id is not null then
      insert into public.package_statistics as ps
        (package_id, attempts_started_total, attempts_completed_total, score_sum)
      values (v_finished_attempt.package_id, 1, 1, v_finished_attempt.total_score)
      on conflict (package_id) do update set
        attempts_completed_total = ps.attempts_completed_total + 1,
        score_sum = ps.score_sum + excluded.score_sum,
        updated_at = now();
    end if;
  end if;
  return v_score;
end;
$$;

-- --------------------------------------------------------------- attempts ---

create or replace function public.start_attempt(p_package_id integer)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_attempt public.attempts;
  v_cap public.service_capacity;
  v_release_id uuid;
begin
  if (select auth.uid()) is null then raise exception 'not authenticated'; end if;
  select current_release_id into v_release_id
    from public.packages where id = p_package_id and is_published;
  if v_release_id is null then
    raise exception 'package not found, unpublished, or has no release' using errcode = 'P0002';
  end if;

  select * into v_attempt from public.attempts
   where user_id = (select auth.uid()) and package_id = p_package_id and status = 'active'
   order by started_at desc limit 1;

  if v_attempt.id is null then
    v_cap := public._capacity();
    if v_cap.db_bytes >= v_cap.limit_bytes
       or v_cap.attempt_rows >= v_cap.limit_attempt_rows then
      raise exception 'storage capacity reached' using errcode = 'P0007';
    end if;
    if (select count(*) from public.attempts
         where user_id = (select auth.uid())
           and started_at > now() - interval '1 hour') >= 10 then
      raise exception 'too many attempts' using errcode = 'P0005';
    end if;

    insert into public.attempts (user_id, package_id, package_release_id)
    values ((select auth.uid()), p_package_id, v_release_id)
    returning * into v_attempt;

    insert into public.package_statistics as ps
      (package_id, attempts_started_total)
    values (p_package_id, 1)
    on conflict (package_id) do update set
      attempts_started_total = ps.attempts_started_total + 1,
      updated_at = now();
  end if;

  return json_build_object('attempt', row_to_json(v_attempt),
                           'package', public._v3_release_package_json(v_attempt.package_release_id),
                           'server_time', now());
end;
$$;

create or replace function public.start_section(p_attempt_id uuid)
returns json
language plpgsql security definer
set search_path = public
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

  perform public._grade_section(sa.id)
    from public.section_attempts sa
   where sa.attempt_id = p_attempt_id and sa.status = 'active'
     and now() > sa.deadline_at + interval '5 seconds';

  select sa.* into v_sa from public.section_attempts sa
   where sa.attempt_id = p_attempt_id and sa.status = 'active' limit 1;
  if v_sa.id is null then
    select st.* into v_subtest from public.subtests st
     where st.package_id = v_attempt.package_id
       and not exists (select 1 from public.section_attempts sa
                        where sa.attempt_id = p_attempt_id and sa.subtest_id = st.id)
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
    'package', public._v3_release_package_json(v_attempt.package_release_id),
    'server_time', now(),
    'questions', (
      select coalesce(json_agg(json_build_object(
               'id', prq.question_id,
               'number', prq.number,
               'qtype', qr.qtype,
               'question_text', qr.question_text,
               'passage', qr.passage,
               'image_url', qr.image_url,
               'difficulty', qr.difficulty,
               'question_version', qr.version,
               'question_updated_at', qr.published_at,
               'options', (select json_agg(json_build_object('key', ro.key, 'text', ro.text)
                                            order by ro.key)
                             from public.question_revision_options ro
                            where ro.question_revision_id = qr.id)
             ) order by prq.number), '[]'::json)
        from public.package_release_questions prq
        join public.question_revisions qr on qr.id = prq.question_revision_id
       where prq.package_release_id = v_attempt.package_release_id
         and prq.subtest_id = v_sa.subtest_id),
    'answers', (
      select coalesce(json_agg(json_build_object(
               'question_id', ans.question_id,
               'selected_option', ans.selected_option,
               'is_doubtful', ans.is_doubtful)), '[]'::json)
        from public.answers ans where ans.section_attempt_id = v_sa.id));
end;
$$;

create or replace function public.save_answer(
  p_section_attempt_id uuid, p_question_id text, p_option char(1))
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_sa public.section_attempts;
  v_revision_id uuid;
begin
  v_sa := public._assert_active_section(p_section_attempt_id);
  if p_option is not null and p_option not in ('A','B','C','D','E') then
    raise exception 'invalid option' using errcode = 'P0006';
  end if;
  select prq.question_revision_id into v_revision_id
    from public.section_attempts sa
    join public.attempts a on a.id = sa.attempt_id
    join public.package_release_questions prq
      on prq.package_release_id = a.package_release_id
     and prq.subtest_id = sa.subtest_id
   where sa.id = p_section_attempt_id and prq.question_id = p_question_id;
  if v_revision_id is null then
    raise exception 'question not in pinned section' using errcode = 'P0002';
  end if;

  insert into public.answers
    (section_attempt_id, question_id, question_revision_id, selected_option)
  values (p_section_attempt_id, p_question_id, v_revision_id, p_option)
  on conflict (section_attempt_id, question_id) do update
    set selected_option = excluded.selected_option,
        question_revision_id = excluded.question_revision_id,
        updated_at = now();
  perform public._log_event(p_section_attempt_id, p_question_id, 'save_answer',
                            jsonb_build_object('option', p_option));
  return json_build_object('ok', true, 'server_time', now());
end;
$$;

create or replace function public.toggle_doubt(
  p_section_attempt_id uuid, p_question_id text, p_doubtful boolean)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_sa public.section_attempts;
  v_revision_id uuid;
begin
  v_sa := public._assert_active_section(p_section_attempt_id);
  select prq.question_revision_id into v_revision_id
    from public.section_attempts sa
    join public.attempts a on a.id = sa.attempt_id
    join public.package_release_questions prq
      on prq.package_release_id = a.package_release_id
     and prq.subtest_id = sa.subtest_id
   where sa.id = p_section_attempt_id and prq.question_id = p_question_id;
  if v_revision_id is null then
    raise exception 'question not in pinned section' using errcode = 'P0002';
  end if;

  insert into public.answers
    (section_attempt_id, question_id, question_revision_id, is_doubtful)
  values (p_section_attempt_id, p_question_id, v_revision_id, p_doubtful)
  on conflict (section_attempt_id, question_id) do update
    set is_doubtful = excluded.is_doubtful,
        question_revision_id = excluded.question_revision_id,
        updated_at = now();
  perform public._log_event(
    p_section_attempt_id, p_question_id,
    case when p_doubtful then 'mark_doubt' else 'unmark_doubt' end, '{}'::jsonb);
  return json_build_object('ok', true, 'server_time', now());
end;
$$;

create or replace function public.finish_section(p_section_attempt_id uuid)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_score integer;
  v_attempt public.attempts;
begin
  if not exists (select 1 from public.section_attempts sa
                   join public.attempts a on a.id = sa.attempt_id
                  where sa.id = p_section_attempt_id
                    and a.user_id = (select auth.uid())) then
    raise exception 'section attempt not found' using errcode = 'P0002';
  end if;
  v_score := public._grade_section(p_section_attempt_id);
  select a.* into v_attempt from public.attempts a
  join public.section_attempts sa on sa.attempt_id = a.id
  where sa.id = p_section_attempt_id;
  return json_build_object(
    'score', v_score, 'attempt_status', v_attempt.status,
    'total_score', v_attempt.total_score, 'server_time', now());
end;
$$;

drop trigger if exists question_revisions_immutable on public.question_revisions;
create trigger question_revisions_immutable
  before update or delete on public.question_revisions
  for each row execute function public._v3_reject_immutable_change();
drop trigger if exists question_revision_options_immutable on public.question_revision_options;
create trigger question_revision_options_immutable
  before update or delete on public.question_revision_options
  for each row execute function public._v3_reject_immutable_change();
drop trigger if exists package_releases_immutable on public.package_releases;
create trigger package_releases_immutable
  before update or delete on public.package_releases
  for each row execute function public._v3_reject_immutable_change();
drop trigger if exists package_release_questions_immutable on public.package_release_questions;
create trigger package_release_questions_immutable
  before update or delete on public.package_release_questions
  for each row execute function public._v3_reject_immutable_change();

-- --------------------------------------------------------------- RLS --------

alter table public.question_revisions          enable row level security;
alter table public.question_revision_options   enable row level security;
alter table public.package_releases            enable row level security;
alter table public.package_release_questions   enable row level security;
alter table public.package_statistics          enable row level security;
alter table public.question_report_digest_runs enable row level security;

-- No policies: all projections come through narrowly granted RPCs. This is
-- especially important because question_revisions contains answer keys.
revoke all on public.question_revisions,
              public.question_revision_options,
              public.package_releases,
              public.package_release_questions,
              public.package_statistics,
              public.question_report_digest_runs
from anon, authenticated;

-- ------------------------------------------------------- migration snapshot -
-- Seed one immutable revision from each current mutable question. Old image
-- URLs are preserved as the v3 baseline and are never overwritten by the new
-- content-addressed publisher.

insert into public.question_revisions
  (question_id, version, qtype, question_text, passage, image_url,
   image_sha256, difficulty, correct_option, explanations, content_hash)
select q.id,
       1,
       q.qtype,
       q.question_text,
       q.passage,
       q.image_url,
       null,
       q.difficulty,
       ak.correct_option,
       ak.explanations,
       public._v3_question_hash(
         q.id,
         st.key,
         q.number,
         q.qtype,
         q.question_text,
         q.passage,
         null,
         q.difficulty,
         (select jsonb_agg(jsonb_build_object('key', o.key, 'text', o.text) order by o.key)
            from public.question_options o where o.question_id = q.id),
         ak.correct_option,
         ak.explanations)
  from public.questions q
  join public.subtests st on st.id = q.subtest_id
  join public.answer_keys ak on ak.question_id = q.id
 where not exists (select 1 from public.question_revisions qr where qr.question_id = q.id);

insert into public.question_revision_options (question_revision_id, key, text)
select qr.id, o.key, o.text
  from public.question_revisions qr
  join public.question_options o on o.question_id = qr.question_id
 where qr.version = 1
   and not exists (
         select 1 from public.question_revision_options ro
          where ro.question_revision_id = qr.id and ro.key = o.key);

-- Seed release 1 for every package that has a complete current projection.
do $$
declare
  v_package public.packages;
  v_release_id uuid;
  v_difficulty text;
  v_ai_model text;
  v_hash text;
begin
  for v_package in select * from public.packages order by id loop
    if exists (select 1 from public.package_releases pr where pr.package_id = v_package.id) then
      if v_package.current_release_id is null then
        update public.packages
           set current_release_id = (
             select pr.id from public.package_releases pr
              where pr.package_id = v_package.id order by pr.version desc limit 1)
         where id = v_package.id;
      end if;
      continue;
    end if;

    if (select count(*) from public.questions q join public.subtests st on st.id = q.subtest_id
         where st.package_id = v_package.id) <> 60
       or (select count(*) from public.questions q join public.subtests st on st.id = q.subtest_id
            where st.package_id = v_package.id and st.key = 'verbal') <> 23
       or (select count(*) from public.questions q join public.subtests st on st.id = q.subtest_id
            where st.package_id = v_package.id and st.key = 'kuantitatif') <> 25
       or (select count(*) from public.questions q join public.subtests st on st.id = q.subtest_id
            where st.package_id = v_package.id and st.key = 'pemecahan_masalah') <> 12 then
      if exists (select 1 from public.attempts a where a.package_id = v_package.id) then
        raise exception 'cannot pin retained attempts: package % is not a complete 23/25/12 snapshot',
          v_package.id;
      end if;
      continue;
    end if;

    if (select count(*)
          from public.questions q
          join public.subtests st on st.id = q.subtest_id
          join public.question_revisions qr on qr.question_id = q.id
         where st.package_id = v_package.id and qr.version = 1) <> 60 then
      raise exception 'package % cannot be snapshotted: revision/key data is incomplete',
        v_package.id;
    end if;

    v_difficulty := case v_package.id
      when 4 then 'hard' when 5 then 'easy' when 6 then 'hard' else 'medium' end;
    v_ai_model := case
      when v_package.id between 1 and 3 then 'Opus 5'
      when v_package.id = 4 then 'Fable-5'
      when v_package.id between 5 and 6 then '5.6 Sol'
      else 'Unknown' end;

    select public._v3_hash_jsonb(jsonb_build_object(
             'id', v_package.id,
             'title', v_package.title,
             'description', v_package.description,
             'difficulty', v_difficulty,
             'ai_model', v_ai_model,
             'questions', jsonb_agg(jsonb_build_array(q.id, qr.content_hash) order by q.id)))
      into v_hash
      from public.questions q
      join public.subtests st on st.id = q.subtest_id
      join lateral (
        select qr0.* from public.question_revisions qr0
         where qr0.question_id = q.id order by qr0.version desc limit 1
      ) qr on true
     where st.package_id = v_package.id;

    insert into public.package_releases
      (package_id, version, title, description, difficulty, ai_model, content_hash)
    values
      (v_package.id, 1, v_package.title, v_package.description,
       v_difficulty, v_ai_model, v_hash)
    returning id into v_release_id;

    insert into public.package_release_questions
      (package_release_id, package_id, question_id, question_revision_id, subtest_id, number)
    select v_release_id, v_package.id, q.id, qr.id, q.subtest_id, q.number
      from public.questions q
      join public.subtests st on st.id = q.subtest_id
      join lateral (
        select qr0.* from public.question_revisions qr0
         where qr0.question_id = q.id order by qr0.version desc limit 1
      ) qr on true
     where st.package_id = v_package.id;

    update public.packages set current_release_id = v_release_id where id = v_package.id;
  end loop;
end;
$$;

-- Pin retained attempts/answers to the migration snapshot. This cannot recover
-- versions overwritten before v3; docs/TECHNICAL_REQUIREMENTS_V3.md §11.1.
update public.attempts a
   set package_release_id = p.current_release_id
  from public.packages p
 where p.id = a.package_id and a.package_release_id is null;

update public.answers ans
   set question_revision_id = prq.question_revision_id
  from public.section_attempts sa
  join public.attempts a on a.id = sa.attempt_id
  join public.package_release_questions prq
    on prq.package_release_id = a.package_release_id
 where ans.section_attempt_id = sa.id
   and ans.question_id = prq.question_id
   and ans.question_revision_id is null;

-- Link a v2 report only when its old visible-content hash still matches the
-- current question. Stale reports remain nullable legacy triage evidence.
update public.question_reports r
   set question_revision_id = prq.question_revision_id
  from public.questions q
  join public.subtests st on st.id = q.subtest_id
  join public.packages p on p.id = st.package_id
  join public.package_release_questions prq
    on prq.package_release_id = p.current_release_id and prq.question_id = q.id
 where r.question_id = q.id
   and r.question_revision_id is null
   and r.content_hash = public._question_content_hash(q.id);

insert into public.package_statistics
  (package_id, attempts_started_total, attempts_completed_total,
   score_sum, coverage_started_at)
select p.id,
       count(a.id),
       count(a.id) filter (where a.status = 'finished'),
       coalesce(sum(a.total_score) filter (where a.status = 'finished'), 0),
       now()
  from public.packages p
  left join public.attempts a on a.package_id = p.id
 group by p.id
on conflict (package_id) do nothing;

-- All retained rows should now be pinned. Fail loudly rather than silently
-- running a half-versioned exam if the pre-v3 database was inconsistent.
alter table public.attempts alter column package_release_id set not null;
alter table public.answers alter column question_revision_id set not null;

-- ------------------------------------------------------- package publisher --

create or replace function public.publish_package_release(p_payload jsonb)
returns json
language plpgsql security definer
set search_path = public, extensions
as $$
declare
  v_package_json jsonb := p_payload -> 'package';
  v_subtests jsonb := p_payload -> 'subtests';
  v_questions jsonb := p_payload -> 'questions';
  v_package_id integer;
  v_title text;
  v_description text;
  v_difficulty text;
  v_ai_model text;
  v_publish boolean;
  v_current_release public.package_releases;
  v_question jsonb;
  v_option jsonb;
  v_mapping jsonb;
  v_mappings jsonb := '[]'::jsonb;
  v_hash_pairs jsonb := '[]'::jsonb;
  v_options jsonb;
  v_explanations jsonb;
  v_q_hash text;
  v_package_hash text;
  v_revision_id uuid;
  v_release_id uuid;
  v_revision_version integer;
  v_release_version integer;
  v_current_revision public.question_revisions;
  v_new_revisions integer := 0;
  v_previous_id text := '';
  v_key text;
  v_expected integer;
  v_expected_position integer;
  v_expected_duration integer;
  v_expected_passing integer;
  v_expected_name text;
begin
  if jsonb_typeof(v_package_json) <> 'object'
     or jsonb_typeof(v_subtests) <> 'array'
     or jsonb_typeof(v_questions) <> 'array' then
    raise exception 'invalid publish payload' using errcode = 'P0006';
  end if;

  v_package_id := (v_package_json ->> 'id')::integer;
  v_title := btrim(coalesce(v_package_json ->> 'title', ''));
  v_description := coalesce(v_package_json ->> 'description', '');
  v_difficulty := v_package_json ->> 'difficulty';
  v_ai_model := btrim(coalesce(v_package_json ->> 'ai_model', ''));
  v_publish := case when jsonb_typeof(v_package_json -> 'is_published') = 'boolean'
                    then (v_package_json ->> 'is_published')::boolean else null end;
  if v_package_id is null or v_package_id < 1 or v_title = '' or v_ai_model = ''
     or v_difficulty not in ('easy','medium','hard') then
    raise exception 'invalid package metadata' using errcode = 'P0006';
  end if;
  if jsonb_array_length(v_subtests) <> 3 or jsonb_array_length(v_questions) <> 60 then
    raise exception 'a release must contain 3 subtests and 60 questions'
      using errcode = 'P0006';
  end if;

  insert into public.packages as p (id, title, description, is_published)
  values (v_package_id, v_title, v_description, coalesce(v_publish, false))
  on conflict (id) do update
     set title = excluded.title,
         description = excluded.description,
         is_published = coalesce(v_publish, p.is_published);
  perform 1 from public.packages where id = v_package_id for update;

  -- Validate and upsert the fixed subtest blueprint.
  for v_mapping in select value from jsonb_array_elements(v_subtests) loop
    v_key := v_mapping ->> 'key';
    case v_key
      when 'verbal' then
        v_expected := 23; v_expected_position := 1;
        v_expected_duration := 1800; v_expected_passing := 70;
        v_expected_name := 'Penalaran Verbal';
      when 'kuantitatif' then
        v_expected := 25; v_expected_position := 2;
        v_expected_duration := 2400; v_expected_passing := 75;
        v_expected_name := 'Penalaran Kuantitatif';
      when 'pemecahan_masalah' then
        v_expected := 12; v_expected_position := 3;
        v_expected_duration := 1200; v_expected_passing := 35;
        v_expected_name := 'Pemecahan Masalah';
      else
        raise exception 'invalid subtest blueprint for %', coalesce(v_key, '(null)')
          using errcode = 'P0006';
    end case;
    if (v_mapping ->> 'id') <> v_package_id || '-' || v_key
       or (v_mapping ->> 'name') <> v_expected_name
       or (v_mapping ->> 'position')::integer <> v_expected_position
       or (v_mapping ->> 'question_count')::integer <> v_expected
       or (v_mapping ->> 'duration_seconds')::integer <> v_expected_duration
       or (v_mapping ->> 'passing_grade')::integer <> v_expected_passing then
      raise exception 'invalid subtest blueprint for %', coalesce(v_key, '(null)')
        using errcode = 'P0006';
    end if;
    insert into public.subtests as st
      (id, package_id, key, name, position, question_count, duration_seconds, passing_grade)
    values
      (v_mapping ->> 'id', v_package_id, v_key, v_mapping ->> 'name',
       (v_mapping ->> 'position')::integer, v_expected,
       (v_mapping ->> 'duration_seconds')::integer,
       (v_mapping ->> 'passing_grade')::integer)
    on conflict (id) do update set
      name = excluded.name,
      position = excluded.position,
      question_count = excluded.question_count,
      duration_seconds = excluded.duration_seconds,
      passing_grade = excluded.passing_grade;
  end loop;
  if (select count(distinct value ->> 'key') from jsonb_array_elements(v_subtests)) <> 3 then
    raise exception 'duplicate or missing subtest key' using errcode = 'P0006';
  end if;

  select pr.* into v_current_release
    from public.packages p
    left join public.package_releases pr on pr.id = p.current_release_id
   where p.id = v_package_id;

  -- Input order is part of the canonical package hash; require stable ID order.
  for v_question in select value from jsonb_array_elements(v_questions) loop
    if coalesce(v_question ->> 'id', '') <= v_previous_id then
      raise exception 'questions must be strictly ordered by stable id'
        using errcode = 'P0006';
    end if;
    v_previous_id := v_question ->> 'id';
    v_key := v_question ->> 'subtest';
    v_expected := case v_key
      when 'verbal' then 23 when 'kuantitatif' then 25
      when 'pemecahan_masalah' then 12 else null end;
    if v_expected is null
       or (v_question ->> 'subtest_id') <> v_package_id || '-' || v_key
       or (v_question ->> 'id') !~ ('^' || v_package_id || '-' || v_key || '-[0-9]{3}$')
       or (v_question ->> 'number')::integer not between 1 and v_expected
       or btrim(coalesce(v_question ->> 'qtype', '')) = ''
       or btrim(coalesce(v_question ->> 'question_text', '')) = ''
       or (v_question ->> 'difficulty') not in ('easy','medium','hard') then
      raise exception 'invalid question identity/metadata: %', v_question ->> 'id'
        using errcode = 'P0006';
    end if;
    v_options := v_question -> 'options';
    v_explanations := v_question -> 'explanations';
    if jsonb_typeof(v_options) <> 'array' or jsonb_array_length(v_options) <> 5
       or jsonb_typeof(v_explanations) <> 'object'
       or (v_question ->> 'correct_option') not in ('A','B','C','D','E')
       or (select string_agg(value ->> 'key', '' order by ordinality)
             from jsonb_array_elements(v_options) with ordinality) <> 'ABCDE'
       or not (v_explanations ?& array['A','B','C','D','E']) then
      raise exception 'invalid options/key/explanations: %', v_question ->> 'id'
        using errcode = 'P0006';
    end if;

    v_q_hash := public._v3_question_hash(
      v_question ->> 'id', v_key, (v_question ->> 'number')::integer,
      v_question ->> 'qtype', v_question ->> 'question_text',
      v_question ->> 'passage', v_question ->> 'image_sha256',
      v_question ->> 'difficulty', v_options,
      (v_question ->> 'correct_option')::char(1), v_explanations);
    if nullif(v_question ->> 'client_content_hash', '') is not null
       and v_question ->> 'client_content_hash' <> v_q_hash then
      raise exception 'publisher/server question hash mismatch: %', v_question ->> 'id'
        using errcode = 'P0006';
    end if;

    select qr.* into v_current_revision
      from public.package_release_questions prq
      join public.question_revisions qr on qr.id = prq.question_revision_id
     where prq.package_release_id = v_current_release.id
       and prq.question_id = v_question ->> 'id';

    -- Keep the stable/current compatibility projection in sync.
    insert into public.questions as q
      (id, subtest_id, number, qtype, question_text, passage, image_url, difficulty)
    values
      (v_question ->> 'id', v_question ->> 'subtest_id',
       (v_question ->> 'number')::integer, v_question ->> 'qtype',
       v_question ->> 'question_text', v_question ->> 'passage',
       nullif(v_question ->> 'image_url', ''), v_question ->> 'difficulty')
    on conflict (id) do update set
      subtest_id = excluded.subtest_id, number = excluded.number,
      qtype = excluded.qtype, question_text = excluded.question_text,
      passage = excluded.passage, image_url = excluded.image_url,
      difficulty = excluded.difficulty;

    if v_current_revision.id is not null and v_current_revision.content_hash = v_q_hash then
      v_revision_id := v_current_revision.id;
    else
      select coalesce(max(version), 0) + 1 into v_revision_version
        from public.question_revisions where question_id = v_question ->> 'id';
      insert into public.question_revisions
        (question_id, version, qtype, question_text, passage, image_url,
         image_sha256, difficulty, correct_option, explanations, content_hash)
      values
        (v_question ->> 'id', v_revision_version, v_question ->> 'qtype',
         v_question ->> 'question_text', v_question ->> 'passage',
         nullif(v_question ->> 'image_url', ''),
         nullif(v_question ->> 'image_sha256', ''),
         v_question ->> 'difficulty',
         (v_question ->> 'correct_option')::char(1), v_explanations, v_q_hash)
      returning id into v_revision_id;

      for v_option in select value from jsonb_array_elements(v_options) loop
        insert into public.question_revision_options (question_revision_id, key, text)
        values (v_revision_id, (v_option ->> 'key')::char(1), v_option ->> 'text');
      end loop;
      v_new_revisions := v_new_revisions + 1;
    end if;

    -- Compatibility options/keys are mutable projections, never used to grade.
    delete from public.question_options where question_id = v_question ->> 'id';
    for v_option in select value from jsonb_array_elements(v_options) loop
      insert into public.question_options (question_id, key, text)
      values (v_question ->> 'id', (v_option ->> 'key')::char(1), v_option ->> 'text');
    end loop;
    insert into public.answer_keys as ak (question_id, correct_option, explanations)
    values (v_question ->> 'id', (v_question ->> 'correct_option')::char(1), v_explanations)
    on conflict (question_id) do update set
      correct_option = excluded.correct_option, explanations = excluded.explanations;

    v_mappings := v_mappings || jsonb_build_array(jsonb_build_object(
      'question_id', v_question ->> 'id',
      'question_revision_id', v_revision_id,
      'subtest_id', v_question ->> 'subtest_id',
      'number', (v_question ->> 'number')::integer));
    v_hash_pairs := v_hash_pairs || jsonb_build_array(jsonb_build_array(
      v_question ->> 'id', v_q_hash));
  end loop;

  -- Exact 23/25/12 membership; IDs and numbers are also protected by the
  -- release mapping's unique constraints.
  if (select count(*) from jsonb_array_elements(v_questions) where value ->> 'subtest' = 'verbal') <> 23
     or (select count(*) from jsonb_array_elements(v_questions) where value ->> 'subtest' = 'kuantitatif') <> 25
     or (select count(*) from jsonb_array_elements(v_questions) where value ->> 'subtest' = 'pemecahan_masalah') <> 12 then
    raise exception 'release question counts must be 23/25/12' using errcode = 'P0006';
  end if;

  v_package_hash := public._v3_hash_jsonb(jsonb_build_object(
    'id', v_package_id, 'title', v_title, 'description', v_description,
    'difficulty', v_difficulty, 'ai_model', v_ai_model,
    'questions', v_hash_pairs));
  if nullif(v_package_json ->> 'client_content_hash', '') is not null
     and v_package_json ->> 'client_content_hash' <> v_package_hash then
    raise exception 'publisher/server package hash mismatch for package %', v_package_id
      using errcode = 'P0006';
  end if;

  if v_current_release.id is not null and v_current_release.content_hash = v_package_hash then
    return json_build_object(
      'created', false, 'release_id', v_current_release.id,
      'version', v_current_release.version,
      'new_question_revisions', v_new_revisions,
      'content_hash', v_package_hash, 'server_time', now());
  end if;

  select coalesce(max(version), 0) + 1 into v_release_version
    from public.package_releases where package_id = v_package_id;
  insert into public.package_releases
    (package_id, version, title, description, difficulty, ai_model, content_hash)
  values
    (v_package_id, v_release_version, v_title, v_description,
     v_difficulty, v_ai_model, v_package_hash)
  returning id into v_release_id;

  for v_mapping in select value from jsonb_array_elements(v_mappings) loop
    insert into public.package_release_questions
      (package_release_id, package_id, question_id, question_revision_id, subtest_id, number)
    values
      (v_release_id, v_package_id, v_mapping ->> 'question_id',
       (v_mapping ->> 'question_revision_id')::uuid,
       v_mapping ->> 'subtest_id', (v_mapping ->> 'number')::integer);
  end loop;
  update public.packages set current_release_id = v_release_id where id = v_package_id;
  insert into public.package_statistics (package_id) values (v_package_id)
  on conflict (package_id) do nothing;

  return json_build_object(
    'created', true, 'release_id', v_release_id, 'version', v_release_version,
    'new_question_revisions', v_new_revisions,
    'content_hash', v_package_hash, 'server_time', now());
end;
$$;

-- ------------------------------------------------------- state and review ---

create or replace function public.get_attempt_state(p_attempt_id uuid)
returns json
language plpgsql security definer
set search_path = public
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
    'package', public._v3_release_package_json(v_attempt.package_release_id),
    'server_time', now(),
    'sections', (
      select coalesce(json_agg(json_build_object(
               'section_attempt', row_to_json(sa),
               'subtest', (select row_to_json(st) from public.subtests st where st.id = sa.subtest_id)
             ) order by sa.started_at), '[]'::json)
        from public.section_attempts sa where sa.attempt_id = p_attempt_id));
end;
$$;

create or replace function public.get_review(p_attempt_id uuid)
returns json
language plpgsql security definer
set search_path = public
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
    'package', public._v3_release_package_json(v_attempt.package_release_id),
    'sections', (
      select coalesce(json_agg(json_build_object(
        'subtest', (select row_to_json(st) from public.subtests st where st.id = sa.subtest_id),
        'score', sa.score,
        'questions', (
          select coalesce(json_agg(json_build_object(
                   'id', prq.question_id,
                   'number', prq.number,
                   'qtype', qr.qtype,
                   'question_text', qr.question_text,
                   'passage', qr.passage,
                   'image_url', qr.image_url,
                   'difficulty', qr.difficulty,
                   'question_version', qr.version,
                   'question_updated_at', qr.published_at,
                   'options', (select json_agg(json_build_object('key', ro.key, 'text', ro.text)
                                                order by ro.key)
                                 from public.question_revision_options ro
                                where ro.question_revision_id = qr.id),
                   'selected_option', ans.selected_option,
                   'is_doubtful', coalesce(ans.is_doubtful, false),
                   'correct_option', qr.correct_option,
                   'explanations', qr.explanations,
                   'my_report', (
                     select json_build_object(
                              'reason', r.reason, 'comment', r.comment,
                              'status', r.status, 'created_at', r.created_at,
                              'updated_at', r.updated_at)
                       from public.question_reports r
                      where r.question_revision_id = qr.id
                        and r.user_id = (select auth.uid()))
                 ) order by prq.number), '[]'::json)
            from public.package_release_questions prq
            join public.question_revisions qr on qr.id = prq.question_revision_id
            left join public.answers ans
              on ans.question_revision_id = qr.id and ans.section_attempt_id = sa.id
           where prq.package_release_id = v_attempt.package_release_id
             and prq.subtest_id = sa.subtest_id)
      ) order by (select position from public.subtests where id = sa.subtest_id)), '[]'::json)
        from public.section_attempts sa
       where sa.attempt_id = p_attempt_id and sa.status = 'finished'));
end;
$$;

-- ------------------------------------------------ revision-aware reports ---

-- v2 declared defaults on the final two parameters; PostgreSQL cannot remove
-- parameter defaults with CREATE OR REPLACE, so replace the signature cleanly.
drop function if exists public.report_question(text,text,text,uuid);
create or replace function public.report_question(
  p_question_id text,
  p_reason text,
  p_comment text,
  p_attempt_id uuid)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_uid uuid := (select auth.uid());
  v_comment text := btrim(coalesce(p_comment, ''));
  v_section_id uuid;
  v_revision_id uuid;
  v_selected char(1);
  v_report public.question_reports;
begin
  if v_uid is null then raise exception 'not authenticated'; end if;
  if p_reason is null or p_reason not in
     ('wrong_key','ambiguous','bad_explanation','typo','image_issue','other')
     or char_length(v_comment) > 1000
     or (p_reason = 'other' and v_comment = '') then
    raise exception 'invalid report input' using errcode = 'P0006';
  end if;

  select sa.id, prq.question_revision_id into v_section_id, v_revision_id
    from public.attempts a
    join public.section_attempts sa on sa.attempt_id = a.id
    join public.package_release_questions prq
      on prq.package_release_id = a.package_release_id
     and prq.subtest_id = sa.subtest_id
   where a.id = p_attempt_id and a.user_id = v_uid
     and sa.status = 'finished' and prq.question_id = p_question_id
   limit 1;
  if v_revision_id is null then
    raise exception 'question not available for reporting' using errcode = 'P0002';
  end if;
  if (select count(*) from public.question_reports r
       where r.user_id = v_uid and r.updated_at > now() - interval '1 hour') >= 20 then
    raise exception 'too many reports' using errcode = 'P0005';
  end if;
  select selected_option into v_selected from public.answers
   where section_attempt_id = v_section_id and question_id = p_question_id;

  insert into public.question_reports as r
    (user_id, question_id, question_revision_id, attempt_id, section_attempt_id,
     reason, comment, selected_option, content_hash)
  select v_uid, p_question_id, v_revision_id, p_attempt_id, v_section_id,
         p_reason, v_comment, v_selected, qr.content_hash
    from public.question_revisions qr where qr.id = v_revision_id
  on conflict (user_id, question_revision_id) where question_revision_id is not null
  do update set
    reason = excluded.reason,
    comment = excluded.comment,
    attempt_id = excluded.attempt_id,
    section_attempt_id = excluded.section_attempt_id,
    selected_option = excluded.selected_option,
    updated_at = now()
  returning * into v_report;

  return json_build_object('report', json_build_object(
    'reason', v_report.reason, 'comment', v_report.comment,
    'status', v_report.status, 'created_at', v_report.created_at,
    'updated_at', v_report.updated_at), 'server_time', now());
end;
$$;

create or replace function public.delete_question_report(
  p_question_id text, p_attempt_id uuid)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_revision_id uuid;
  v_deleted integer;
begin
  select prq.question_revision_id into v_revision_id
    from public.attempts a
    join public.section_attempts sa on sa.attempt_id = a.id
    join public.package_release_questions prq
      on prq.package_release_id = a.package_release_id and prq.subtest_id = sa.subtest_id
   where a.id = p_attempt_id and a.user_id = (select auth.uid())
     and sa.status = 'finished' and prq.question_id = p_question_id
   limit 1;
  if v_revision_id is not null then
    delete from public.question_reports
     where user_id = (select auth.uid()) and question_revision_id = v_revision_id;
  end if;
  get diagnostics v_deleted = row_count;
  return json_build_object('deleted', v_deleted > 0, 'server_time', now());
end;
$$;

-- Transitional v2 overload. The v3 SPA uses the attempt-specific signature.
create or replace function public.delete_question_report(p_question_id text)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_deleted integer;
begin
  delete from public.question_reports
   where id = (select id from public.question_reports
                where user_id = (select auth.uid()) and question_id = p_question_id
                order by updated_at desc limit 1);
  get diagnostics v_deleted = row_count;
  return json_build_object('deleted', v_deleted > 0, 'server_time', now());
end;
$$;

-- ---------------------------------------------------------- digest outbox ---

create or replace function public._prepare_question_report_digest_run(
  p_window_start timestamptz, p_window_end timestamptz)
returns uuid
language plpgsql security definer
set search_path = public, extensions
as $$
declare
  v_existing uuid;
  v_run_id uuid;
  v_payload jsonb;
  v_activity_count integer;
begin
  if p_window_end <= p_window_start then raise exception 'invalid digest window'; end if;
  select id into v_existing from public.question_report_digest_runs
   where status <> 'sent' order by created_at limit 1;
  if v_existing is not null then return v_existing; end if;

  select count(*) into v_activity_count from public.question_reports
   where updated_at >= p_window_start and updated_at < p_window_end;

  v_payload := jsonb_build_object(
    'window_start', p_window_start,
    'window_end', p_window_end,
    'activity_count', v_activity_count,
    'open_backlog_count', (select count(*) from public.question_reports where status = 'open'),
    'truncated_count', greatest(v_activity_count - 200, 0),
    'reason_summary', coalesce((
      select jsonb_object_agg(reason, amount) from (
        select reason, count(*) amount from public.question_reports
         where updated_at >= p_window_start and updated_at < p_window_end
         group by reason order by reason) grouped), '{}'::jsonb),
    'reports', coalesce((
      select jsonb_agg(jsonb_build_object(
               'question_id', detail.question_id,
               'package_id', detail.package_id,
               'subtest', detail.subtest_key,
               'number', detail.number,
               'question_version', detail.question_version,
               'is_current_revision', detail.is_current_revision,
               'reason', detail.reason,
               'status', detail.status,
               'selected_option', detail.selected_option,
               'comment', detail.comment,
               'created_at', detail.created_at,
               'updated_at', detail.updated_at)
             order by detail.updated_at, detail.id)
        from (
          select r.id, r.question_id, st.package_id, st.key subtest_key, q.number,
                 qr.version question_version,
                 exists (select 1 from public.packages p
                         join public.package_release_questions prq
                           on prq.package_release_id = p.current_release_id
                          and prq.question_id = r.question_id
                          and prq.question_revision_id = r.question_revision_id
                        where p.id = st.package_id) is_current_revision,
                 r.reason, r.status, r.selected_option, r.comment,
                 r.created_at, r.updated_at
            from public.question_reports r
            join public.questions q on q.id = r.question_id
            join public.subtests st on st.id = q.subtest_id
            left join public.question_revisions qr on qr.id = r.question_revision_id
           where r.updated_at >= p_window_start and r.updated_at < p_window_end
           order by r.updated_at, r.id limit 200
        ) detail), '[]'::jsonb));

  insert into public.question_report_digest_runs
    (window_start, window_end, email_payload, payload_sha256)
  values (p_window_start, p_window_end, v_payload, public._v3_hash_jsonb(v_payload))
  returning id into v_run_id;
  return v_run_id;
end;
$$;

create or replace function public.claim_question_report_digest(p_run_id uuid)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_run public.question_report_digest_runs;
begin
  update public.question_report_digest_runs
     set status = 'manual_attention', lease_until = null, updated_at = now(),
         last_error = coalesce(last_error, 'Automatic retry window expired')
   where id = p_run_id and status in ('failed','sending')
     and created_at < now() - interval '23 hours';

  update public.question_report_digest_runs
     set status = 'sending', lease_until = now() + interval '5 minutes',
         delivery_attempts = delivery_attempts + 1, updated_at = now()
   where id = p_run_id
     and (status in ('pending','failed')
          or (status = 'sending' and lease_until < now()))
  returning * into v_run;
  if v_run.id is null then
    select * into v_run from public.question_report_digest_runs where id = p_run_id;
  end if;
  if v_run.id is null then raise exception 'digest run not found' using errcode = 'P0002'; end if;
  return json_build_object('run', row_to_json(v_run), 'server_time', now());
end;
$$;

create or replace function public.complete_question_report_digest(
  p_run_id uuid, p_provider_message_id text)
returns json
language plpgsql security definer
set search_path = public
as $$
begin
  update public.question_report_digest_runs
     set status = 'sent', provider_message_id = p_provider_message_id,
         sent_at = now(), lease_until = null, last_error = null, updated_at = now()
   where id = p_run_id and status = 'sending';
  if not found then raise exception 'digest run is not sending' using errcode = 'P0003'; end if;
  return json_build_object('ok', true, 'server_time', now());
end;
$$;

create or replace function public.fail_question_report_digest(
  p_run_id uuid, p_error text)
returns json
language plpgsql security definer
set search_path = public
as $$
begin
  update public.question_report_digest_runs
     set status = case when created_at < now() - interval '23 hours'
                       then 'manual_attention' else 'failed' end,
         lease_until = null,
         last_error = left(coalesce(p_error, 'Unknown provider error'), 500),
         updated_at = now()
   where id = p_run_id and status = 'sending';
  return json_build_object('ok', found, 'server_time', now());
end;
$$;

-- --------------------------------------------------------------- grants -----

revoke all on function public._v3_hash_jsonb(jsonb),
  public._v3_question_hash(text,text,integer,text,text,text,text,text,jsonb,char,jsonb),
  public._v3_release_package_json(uuid),
  public.publish_package_release(jsonb),
  public._prepare_question_report_digest_run(timestamptz,timestamptz),
  public.claim_question_report_digest(uuid),
  public.complete_question_report_digest(uuid,text),
  public.fail_question_report_digest(uuid,text)
from anon, authenticated, public;

revoke all on function public.get_package_catalog(),
  public.get_attempt_summaries(),
  public.start_attempt(integer),
  public.start_section(uuid),
  public.save_answer(uuid,text,char),
  public.toggle_doubt(uuid,text,boolean),
  public.finish_section(uuid),
  public.get_attempt_state(uuid),
  public.get_review(uuid),
  public.report_question(text,text,text,uuid),
  public.delete_question_report(text,uuid),
  public.delete_question_report(text)
from anon, authenticated, public;

grant execute on function public.get_package_catalog(),
  public.get_attempt_summaries(),
  public.start_attempt(integer),
  public.start_section(uuid),
  public.save_answer(uuid,text,char),
  public.toggle_doubt(uuid,text,boolean),
  public.finish_section(uuid),
  public.get_attempt_state(uuid),
  public.get_review(uuid),
  public.report_question(text,text,text,uuid),
  public.delete_question_report(text,uuid),
  public.delete_question_report(text)
to authenticated;

grant execute on function public.publish_package_release(jsonb),
  public.claim_question_report_digest(uuid),
  public.complete_question_report_digest(uuid,text),
  public.fail_question_report_digest(uuid,text)
to service_role;

-- =============================================================================
