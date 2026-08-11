-- =============================================================================
-- TBS LPDP Try Out — Supabase schema, part 2 of 2: question feedback (v2)
--
-- Apply AFTER schema.sql and BEFORE schema_v3.sql. This file remains
-- idempotent, but v3 owns the final revision-aware report/review definitions;
-- always re-apply schema_v3.sql after this file.
--
-- Design: docs/TECHNICAL_REQUIREMENTS_V2.md §6–§8. Users report defective
-- questions from the Pembahasan screen; reports are captured and nothing more.
-- Nothing here reads answer_keys, and no report is ever visible to any user
-- but its own author (C-6/C-7).
--
-- Contents:
--   1. table public.question_reports + indexes
--   2. RLS: select-own only, no write policies
--   3. public._question_content_hash()      helper
--   4. public.report_question()             RPC
--   5. public.delete_question_report()      RPC
--   6. public.get_review()                  re-created with `my_report`
--   7. grants
-- =============================================================================

-- ------------------------------------------------------------------ 1. table -
-- In v2, `content_hash` pinned the text while questions were rewritten in
-- place. schema_v3.sql migrates matching rows onto immutable revisions.

create table if not exists public.question_reports (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references auth.users (id) on delete cascade,
  question_id        text not null references public.questions (id) on delete cascade,
  attempt_id         uuid references public.attempts (id) on delete set null,
  section_attempt_id uuid references public.section_attempts (id) on delete set null,
  reason             text not null check (reason in
                       ('wrong_key','ambiguous','bad_explanation','typo','image_issue','other')),
  comment            text not null default '' check (char_length(comment) <= 1000),
  selected_option    char(1) check (selected_option in ('A','B','C','D','E')),
  content_hash       text not null,
  status             text not null default 'open' check (status in
                       ('open','reviewing','accepted','rejected','duplicate')),
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (user_id, question_id)          -- BE-10: one report per user per question
);

-- Triage ("which questions are worst") and the BE-13 rolling-hour write budget.
create index if not exists question_reports_question_idx
  on public.question_reports (question_id, created_at desc);
create index if not exists question_reports_user_recent_idx
  on public.question_reports (user_id, updated_at desc);

-- -------------------------------------------------------------------- 2. RLS -
-- BE-14: reporters read their own reports; no insert/update/delete policy
-- exists, so every write must go through the RPCs below. Nobody can read,
-- count, or even detect another user's report.

alter table public.question_reports enable row level security;

drop policy if exists question_reports_read_own on public.question_reports;
create policy question_reports_read_own on public.question_reports
  for select to authenticated using (user_id = (select auth.uid()));

-- Defence in depth: this table is created AFTER schema.sql's blanket
-- `revoke all on all tables ... from anon`, so it still carries the project's
-- default grant to anon. RLS already denies every row, but drop the privilege
-- too, so the table is never one forgotten policy away from being readable.
revoke all on public.question_reports from anon;

-- ----------------------------------------------------------------- 3. helper -
-- Fingerprint of the question AS SHOWN (stem, passage, options) — no key
-- material. md5() is core Postgres, so this needs no extension.

create or replace function public._question_content_hash(p_question_id text)
returns text
language sql stable security definer set search_path = public
as $$
  select md5(q.question_text || coalesce(q.passage, '') || coalesce(
           (select string_agg(o.key || ':' || o.text, '|' order by o.key)
              from public.question_options o
             where o.question_id = q.id), ''))
    from public.questions q
   where q.id = p_question_id;
$$;

-- ------------------------------------------------------------------ 4. write -
-- Gated by the SAME predicate get_review uses (the caller must own a FINISHED
-- section containing the question), which is what keeps the report surface from
-- becoming an answer-key oracle (C-7): nothing here reads answer_keys, and the
-- outcome does not depend on whether the key is right.

create or replace function public.report_question(
  p_question_id text,
  p_reason      text,
  p_comment     text default '',
  p_attempt_id  uuid default null)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_uid     uuid := (select auth.uid());
  v_comment text := btrim(coalesce(p_comment, ''));
  v_section uuid;
  v_attempt uuid;
  v_selected char(1);
  v_report  public.question_reports;
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  -- Input shape (P0006). The check constraints would catch these too, but a
  -- named errcode lets the UI say something useful instead of "23514".
  if p_reason is null or p_reason not in
     ('wrong_key','ambiguous','bad_explanation','typo','image_issue','other') then
    raise exception 'unknown report reason' using errcode = 'P0006';
  end if;
  if char_length(v_comment) > 1000 then
    raise exception 'comment too long' using errcode = 'P0006';
  end if;
  if p_reason = 'other' and v_comment = '' then
    raise exception 'comment required for reason other' using errcode = 'P0006';
  end if;

  -- The review gate. p_attempt_id only narrows it; it can never widen it.
  select sa.id, sa.attempt_id into v_section, v_attempt
    from public.section_attempts sa
    join public.attempts a on a.id = sa.attempt_id
    join public.questions q on q.subtest_id = sa.subtest_id
   where a.user_id = v_uid
     and sa.status = 'finished'
     and q.id = p_question_id
     and (p_attempt_id is null or a.id = p_attempt_id)
   order by sa.finished_at desc
   limit 1;

  if v_section is null then
    raise exception 'question not available for reporting' using errcode = 'P0002';
  end if;

  -- BE-13: rolling-hour write budget (edits count — they are writes too).
  if (select count(*) from public.question_reports r
       where r.user_id = v_uid
         and r.updated_at > now() - interval '1 hour') >= 20 then
    raise exception 'too many reports' using errcode = 'P0005';
  end if;

  -- What the reporter answered: a report from someone who picked the option
  -- they claim is correct is a stronger signal than one from a blank.
  select ans.selected_option into v_selected
    from public.answers ans
   where ans.section_attempt_id = v_section
     and ans.question_id = p_question_id;

  insert into public.question_reports as r
    (user_id, question_id, attempt_id, section_attempt_id, reason, comment,
     selected_option, content_hash)
  values
    (v_uid, p_question_id, v_attempt, v_section, p_reason, v_comment,
     v_selected, public._question_content_hash(p_question_id))
  on conflict (user_id, question_id) do update      -- BE-10: re-report = edit
     set reason             = excluded.reason,
         comment            = excluded.comment,
         attempt_id         = excluded.attempt_id,
         section_attempt_id = excluded.section_attempt_id,
         selected_option    = excluded.selected_option,
         content_hash       = excluded.content_hash,
         updated_at         = now()
  returning * into v_report;

  return json_build_object(
    'report', json_build_object(
      'reason', v_report.reason, 'comment', v_report.comment,
      'status', v_report.status, 'created_at', v_report.created_at,
      'updated_at', v_report.updated_at),
    'server_time', now());
end;
$$;

-- ----------------------------------------------------------------- 5. delete -
-- Idempotent: withdrawing a report that is not there is a success, so a
-- double-click cannot produce an error (BE-12).

create or replace function public.delete_question_report(p_question_id text)
returns json
language plpgsql security definer set search_path = public
as $$
declare
  v_uid     uuid := (select auth.uid());
  v_deleted integer;
begin
  if v_uid is null then
    raise exception 'not authenticated';
  end if;

  delete from public.question_reports
   where user_id = v_uid and question_id = p_question_id;
  get diagnostics v_deleted = row_count;

  return json_build_object('deleted', v_deleted > 0, 'server_time', now());
end;
$$;

-- ------------------------------------------------------------- 6. get_review -
-- BE-11: identical to the definition in schema.sql except for the `my_report`
-- field, so the review page renders the reported state with no extra round
-- trip (NF-7). KEEP IN SYNC with schema.sql if that function ever changes.

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
                   'explanations', ak.explanations,
                   -- The caller's OWN report, or null. Never anyone else's.
                   'my_report', (
                     select json_build_object(
                              'reason', r.reason, 'comment', r.comment,
                              'status', r.status, 'created_at', r.created_at,
                              'updated_at', r.updated_at)
                       from public.question_reports r
                      where r.question_id = q.id
                        and r.user_id = (select auth.uid()))
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

-- ------------------------------------------------------------------ 7. grants -
-- Narrow by design: anon gets nothing, and the table itself is never granted
-- (reads go through the RLS policy above, writes only through these two RPCs).

revoke all on function
  public._question_content_hash(text),
  public.report_question(text, text, text, uuid),
  public.delete_question_report(text)
from anon, authenticated, public;

grant execute on function
  public.report_question(text, text, text, uuid),
  public.delete_question_report(text),
  public.get_review(uuid)
to authenticated;

-- -----------------------------------------------------------------------------
-- Reading the reports (v2 §9) — service_role only, e.g. in the SQL editor:
--
--   select r.question_id, q.qtype, r.reason, r.status, r.comment,
--          r.selected_option,
--          r.content_hash <> public._question_content_hash(q.id)
--            as question_changed_since_report,
--          r.created_at
--     from public.question_reports r
--     join public.questions q on q.id = r.question_id
--    where r.status = 'open'
--    order by r.question_id, r.created_at desc;
-- -----------------------------------------------------------------------------
