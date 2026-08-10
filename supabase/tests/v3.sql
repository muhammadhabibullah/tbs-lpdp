-- v3 integration assertions.
-- Run after schema.sql -> schema_v2_reports.sql -> schema_v3.sql and after
-- publishing package 1. Everything is rolled back.

begin;

do $$
declare
  v_user_id uuid := '00000000-0000-4000-8000-000000000003';
  v_release_1 uuid;
  v_release_2 uuid;
  v_revision_1 uuid;
  v_revision_2 uuid;
  v_attempt_1 uuid;
  v_attempt_2 uuid;
  v_section_id uuid;
  v_question_id text;
  v_old_key char(1);
  v_new_key char(1);
  v_result jsonb;
  v_review jsonb;
  v_started_before bigint;
  v_completed_before bigint;
  v_sum_before bigint;
begin
  assert not has_table_privilege('authenticated', 'public.question_revisions', 'select'),
    'authenticated must not read versioned answer keys';
  assert has_function_privilege('authenticated', 'public.get_package_catalog()', 'execute'),
    'authenticated catalogue grant missing';
  assert not has_function_privilege('authenticated', 'public.publish_package_release(jsonb)', 'execute'),
    'publisher must be service-role only';

  select current_release_id into v_release_1 from public.packages where id = 1;
  assert v_release_1 is not null, 'publish package 1 before running v3 tests';
  insert into auth.users (id) values (v_user_id) on conflict (id) do nothing;
  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  select attempts_started_total, attempts_completed_total, score_sum
    into v_started_before, v_completed_before, v_sum_before
    from public.package_statistics where package_id = 1;

  v_result := public.start_attempt(1)::jsonb;
  v_attempt_1 := (v_result #>> '{attempt,id}')::uuid;
  assert (v_result #>> '{attempt,package_release_id}')::uuid = v_release_1,
    'attempt was not pinned to current release';
  assert (public.start_attempt(1)::jsonb #>> '{attempt,id}')::uuid = v_attempt_1,
    'start_attempt did not resume the active attempt';
  assert (select attempts_started_total from public.package_statistics where package_id = 1)
         = v_started_before + 1,
    'resuming an attempt incremented the started counter';

  v_result := public.start_section(v_attempt_1)::jsonb;
  v_section_id := (v_result #>> '{section_attempt,id}')::uuid;
  v_question_id := v_result #>> '{questions,0,id}';
  select prq.question_revision_id, qr.correct_option
    into v_revision_1, v_old_key
    from public.package_release_questions prq
    join public.question_revisions qr on qr.id = prq.question_revision_id
   where prq.package_release_id = v_release_1 and prq.question_id = v_question_id;
  perform public.save_answer(v_section_id, v_question_id, v_old_key);

  -- Publish a synthetic new release/key after attempt 1 started. The attempt
  -- must continue grading/reviewing revision 1.
  v_new_key := case when v_old_key = 'A' then 'B' else 'A' end;
  insert into public.question_revisions
    (question_id, version, qtype, question_text, passage, image_url, image_sha256,
     difficulty, correct_option, explanations, content_hash)
  select question_id, version + 1, qtype, question_text, passage, image_url,
         image_sha256, difficulty, v_new_key, explanations, repeat('a', 64)
    from public.question_revisions where id = v_revision_1
  returning id into v_revision_2;
  insert into public.question_revision_options (question_revision_id, key, text)
  select v_revision_2, key, text from public.question_revision_options
   where question_revision_id = v_revision_1;
  insert into public.package_releases
    (package_id, version, title, description, difficulty, ai_model, content_hash)
  select package_id, version + 1, title, description, difficulty, ai_model, repeat('b', 64)
    from public.package_releases where id = v_release_1
  returning id into v_release_2;
  insert into public.package_release_questions
    (package_release_id, package_id, question_id, question_revision_id, subtest_id, number)
  select v_release_2, package_id, question_id,
         case when question_id = v_question_id then v_revision_2 else question_revision_id end,
         subtest_id, number
    from public.package_release_questions where package_release_id = v_release_1;
  update public.packages set current_release_id = v_release_2 where id = 1;

  v_result := public.finish_section(v_section_id)::jsonb;
  assert (v_result ->> 'score')::integer = 5,
    'old attempt was regraded against the new answer key';
  v_review := public.get_review(v_attempt_1)::jsonb;
  assert v_review #>> '{sections,0,questions,0,correct_option}' = v_old_key,
    'old review returned the new answer key';
  perform public.report_question(v_question_id, 'wrong_key', 'old revision', v_attempt_1);

  -- Finish the remaining two sections; no answers means total score stays 5.
  for v_result in select public.start_section(v_attempt_1)::jsonb loop
    exit when coalesce((v_result ->> 'done')::boolean, false);
    perform public.finish_section((v_result #>> '{section_attempt,id}')::uuid);
  end loop;
  -- The loop above starts one section per iteration; explicitly finish the last.
  while (select status from public.attempts where id = v_attempt_1) = 'active' loop
    v_result := public.start_section(v_attempt_1)::jsonb;
    exit when coalesce((v_result ->> 'done')::boolean, false);
    perform public.finish_section((v_result #>> '{section_attempt,id}')::uuid);
  end loop;
  assert (select total_score from public.attempts where id = v_attempt_1) = 5,
    'attempt total is incorrect';

  v_result := public.start_attempt(1)::jsonb;
  v_attempt_2 := (v_result #>> '{attempt,id}')::uuid;
  assert (v_result #>> '{attempt,package_release_id}')::uuid = v_release_2,
    'new attempt did not use the new release';
  v_result := public.start_section(v_attempt_2)::jsonb;
  perform public.finish_section((v_result #>> '{section_attempt,id}')::uuid);
  perform public.report_question(v_question_id, 'wrong_key', 'new revision', v_attempt_2);
  assert (select count(*) from public.question_reports
           where user_id = v_user_id and question_id = v_question_id) = 2,
    'reports were not unique per immutable revision';

  assert (select attempts_started_total from public.package_statistics where package_id = 1)
         = v_started_before + 2, 'started aggregate incorrect';
  assert (select attempts_completed_total from public.package_statistics where package_id = 1)
         = v_completed_before + 1, 'completed aggregate incorrect';
  assert (select score_sum from public.package_statistics where package_id = 1)
         = v_sum_before + 5, 'score sum aggregate incorrect';

  delete from public.attempts where id in (v_attempt_1, v_attempt_2);
  assert (select attempts_started_total from public.package_statistics where package_id = 1)
         = v_started_before + 2, 'attempt deletion changed durable started count';
  assert (select attempts_completed_total from public.package_statistics where package_id = 1)
         = v_completed_before + 1, 'attempt deletion changed durable completed count';
  assert (select score_sum from public.package_statistics where package_id = 1)
         = v_sum_before + 5, 'attempt deletion changed durable score sum';
end;
$$;

do $$
declare
  v_run_id uuid;
  v_hash text;
  v_claim jsonb;
begin
  v_run_id := public._prepare_question_report_digest_run(now() - interval '1 day', now());
  select payload_sha256 into v_hash from public.question_report_digest_runs where id = v_run_id;
  v_claim := public.claim_question_report_digest(v_run_id)::jsonb;
  assert v_claim #>> '{run,status}' = 'sending', 'digest run was not claimed';
  perform public.fail_question_report_digest(v_run_id, 'synthetic failure');
  v_claim := public.claim_question_report_digest(v_run_id)::jsonb;
  assert v_claim #>> '{run,status}' = 'sending', 'failed digest was not retryable';
  assert (v_claim #>> '{run,payload_sha256}') = v_hash, 'digest retry changed frozen payload';
  perform public.complete_question_report_digest(v_run_id, 'test-message-id');
  assert (select status from public.question_report_digest_runs where id = v_run_id) = 'sent',
    'digest run was not completed';
end;
$$;

rollback;
