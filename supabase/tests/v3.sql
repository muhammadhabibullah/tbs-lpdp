-- v3 integration assertions.
-- Run after schema.sql -> schema_v2_reports.sql -> schema_v3.sql and after
-- publishing package 1. Everything is rolled back.

begin;

-- A retained completion from before the v3.1 boundary is reconstructed once.
-- The operation first fails closed on a synthetic missing detail row, then
-- succeeds, preserves a real zero score, and is idempotent on its second call.
do $$
declare
  v_user_id uuid := '00000000-0000-4000-8000-000000000007';
  v_attempt_id uuid;
  v_section_id uuid;
  v_result jsonb;
  v_question jsonb;
  v_correct char(1);
  v_wrong char(1);
  v_boundary timestamptz;
  v_sample_before bigint;
  v_bucket_before bigint;
  v_failed_closed boolean := false;
begin
  assert not has_table_privilege(
    'authenticated', 'public.package_statistics_backfill_runs', 'select'),
    'authenticated must not read statistics backfill audit rows';
  assert not has_function_privilege(
    'authenticated', 'public.backfill_v3_1_retained_statistics()', 'execute'),
    'authenticated must not execute the statistics backfill';
  assert not exists (select 1 from public.package_statistics_backfill_runs),
    'backfill test requires a fresh schema';

  insert into auth.users (id) values (v_user_id) on conflict (id) do nothing;
  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  select score_statistics_coverage_started_at, statistics_sample_total
    into v_boundary, v_sample_before
    from public.package_statistics where package_id = 1;
  select coalesce(attempt_count, 0) into v_bucket_before
    from public.package_score_histogram where package_id = 1 and score = 0;
  v_bucket_before := coalesce(v_bucket_before, 0);

  v_result := public.start_attempt(1)::jsonb;
  v_attempt_id := (v_result #>> '{attempt,id}')::uuid;
  while (select status from public.attempts where id = v_attempt_id) = 'active' loop
    v_result := public.start_section(v_attempt_id)::jsonb;
    exit when coalesce((v_result ->> 'done')::boolean, false);
    v_section_id := (v_result #>> '{section_attempt,id}')::uuid;
    for v_question in select value from jsonb_array_elements(v_result -> 'questions') loop
      select qr.correct_option into v_correct
        from public.attempts a
        join public.package_release_questions prq
          on prq.package_release_id = a.package_release_id
         and prq.question_id = v_question ->> 'id'
        join public.question_revisions qr on qr.id = prq.question_revision_id
       where a.id = v_attempt_id;
      v_wrong := case when v_correct = 'A' then 'B' else 'A' end;
      perform public.save_answer(v_section_id, v_question ->> 'id', v_wrong);
    end loop;
    perform public.finish_section(v_section_id);
  end loop;

  -- Recast the normally graded run as a retained pre-boundary migration row:
  -- keep its durable completion, remove only its new qualified aggregate, and
  -- place its finish timestamp before the original v3.1 boundary.
  update public.package_statistics
     set statistics_sample_total = statistics_sample_total - 1
   where package_id = 1;
  update public.package_score_histogram
     set attempt_count = attempt_count - 1
   where package_id = 1 and score = 0;
  delete from public.package_score_histogram
   where package_id = 1 and score = 0 and attempt_count = 0;
  update public.attempts
     set finished_at = v_boundary - interval '1 hour'
   where id = v_attempt_id;

  -- A durable completion without its retained row must abort before mutation.
  update public.package_statistics
     set attempts_started_total = attempts_started_total + 1,
         attempts_completed_total = attempts_completed_total + 1
   where package_id = 1;
  begin
    perform public.backfill_v3_1_retained_statistics();
  exception when sqlstate '55000' then
    v_failed_closed := true;
  end;
  assert v_failed_closed, 'incomplete retained history did not fail closed';
  update public.package_statistics
     set attempts_started_total = attempts_started_total - 1,
         attempts_completed_total = attempts_completed_total - 1
   where package_id = 1;

  v_result := public.backfill_v3_1_retained_statistics();
  assert v_result ->> 'status' = 'applied', 'backfill did not apply';
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before + 1, 'backfill sample count is incorrect';
  assert coalesce((select attempt_count from public.package_score_histogram
                    where package_id = 1 and score = 0), 0) = v_bucket_before + 1,
    'backfill did not restore the eligible zero-score bucket';
  assert public._v3_package_median_score(1) = 0,
    'backfill did not restore the exact median';
  assert (select score_statistics_coverage_started_at
            from public.package_statistics where package_id = 1) < v_boundary,
    'backfill did not move the score-statistics boundary';
  assert (select count(*) from public.package_statistics_backfill_runs) = 1,
    'backfill audit marker is missing';

  v_result := public.backfill_v3_1_retained_statistics();
  assert v_result ->> 'status' = 'already_applied', 'backfill is not idempotent';
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before + 1, 'second backfill changed the sample count';
  assert coalesce((select attempt_count from public.package_score_histogram
                    where package_id = 1 and score = 0), 0) = v_bucket_before + 1,
    'second backfill changed the histogram';
end;
$$;

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
  v_sample_before bigint;
  v_statistics_sum_before bigint;
begin
  assert not has_table_privilege('authenticated', 'public.question_revisions', 'select'),
    'authenticated must not read versioned answer keys';
  assert not has_table_privilege('authenticated', 'public.package_score_histogram', 'select'),
    'authenticated must not read raw score buckets';
  assert has_function_privilege('authenticated', 'public.get_package_catalog()', 'execute'),
    'authenticated catalogue grant missing';
  assert not has_function_privilege('authenticated', 'public.publish_package_release(jsonb)', 'execute'),
    'publisher must be service-role only';

  select current_release_id into v_release_1 from public.packages where id = 1;
  assert v_release_1 is not null, 'publish package 1 before running v3 tests';
  assert coalesce(public._v3_release_package_json(v_release_1)::jsonb ->> 'ai_company', '') <> '',
    'catalogue package metadata is missing the AI company';
  assert public._v3_release_package_json(v_release_1)::jsonb ? 'median_score',
    'catalogue package metadata is missing median_score';
  insert into auth.users (id) values (v_user_id) on conflict (id) do nothing;
  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  select attempts_started_total, attempts_completed_total, score_sum,
         statistics_sample_total, statistics_score_sum
    into v_started_before, v_completed_before, v_sum_before,
         v_sample_before, v_statistics_sum_before
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
    (package_id, version, title, description, difficulty, ai_model,
     ai_company, ai_model_description, content_hash)
  select package_id, version + 1, title, description, difficulty, ai_model,
         ai_company, ai_model_description, repeat('b', 64)
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
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before, 'low-coverage completion entered the statistics sample';
  assert (select statistics_score_sum from public.package_statistics where package_id = 1)
         = v_statistics_sum_before, 'low-coverage completion changed the public score sum';

  delete from public.attempts where id in (v_attempt_1, v_attempt_2);
  assert (select attempts_started_total from public.package_statistics where package_id = 1)
         = v_started_before + 2, 'attempt deletion changed durable started count';
  assert (select attempts_completed_total from public.package_statistics where package_id = 1)
         = v_completed_before + 1, 'attempt deletion changed durable completed count';
  assert (select score_sum from public.package_statistics where package_id = 1)
         = v_sum_before + 5, 'attempt deletion changed durable score sum';
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before, 'attempt deletion changed the statistics sample';
end;
$$;

-- The v3.1 eligibility gate counts answer coverage, never correctness. A
-- fully answered zero-score run is included; a 48-answer run that misses the
-- per-subtest floor is completed but excluded.
do $$
declare
  v_user_id uuid;
  v_attempt_id uuid;
  v_section_id uuid;
  v_result jsonb;
  v_question jsonb;
  v_subtest_key text;
  v_limit integer;
  v_saved integer;
  v_correct char(1);
  v_wrong char(1);
  v_completed_before bigint;
  v_sample_before bigint;
  v_sum_before bigint;
  v_bucket_before bigint;
begin
  v_user_id := '00000000-0000-4000-8000-000000000004';
  insert into auth.users (id) values (v_user_id) on conflict (id) do nothing;
  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  select attempts_completed_total, statistics_sample_total, statistics_score_sum
    into v_completed_before, v_sample_before, v_sum_before
    from public.package_statistics where package_id = 1;
  select coalesce(attempt_count, 0) into v_bucket_before
    from public.package_score_histogram where package_id = 1 and score = 0;
  v_bucket_before := coalesce(v_bucket_before, 0);

  v_result := public.start_attempt(1)::jsonb;
  v_attempt_id := (v_result #>> '{attempt,id}')::uuid;
  while (select status from public.attempts where id = v_attempt_id) = 'active' loop
    v_result := public.start_section(v_attempt_id)::jsonb;
    exit when coalesce((v_result ->> 'done')::boolean, false);
    v_section_id := (v_result #>> '{section_attempt,id}')::uuid;
    for v_question in select value from jsonb_array_elements(v_result -> 'questions') loop
      select qr.correct_option into v_correct
        from public.attempts a
        join public.package_release_questions prq
          on prq.package_release_id = a.package_release_id
         and prq.question_id = v_question ->> 'id'
        join public.question_revisions qr on qr.id = prq.question_revision_id
       where a.id = v_attempt_id;
      v_wrong := case when v_correct = 'A' then 'B' else 'A' end;
      perform public.save_answer(v_section_id, v_question ->> 'id', v_wrong);
    end loop;
    perform public.finish_section(v_section_id);
  end loop;
  assert (select total_score from public.attempts where id = v_attempt_id) = 0,
    'synthetic all-wrong attempt did not score zero';
  assert (select attempts_completed_total from public.package_statistics where package_id = 1)
         = v_completed_before + 1, 'eligible completion count did not increment';
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before + 1, 'fully answered zero score was excluded';
  assert (select statistics_score_sum from public.package_statistics where package_id = 1)
         = v_sum_before, 'zero score changed statistics sum by a non-zero amount';
  assert coalesce((select attempt_count from public.package_score_histogram
                    where package_id = 1 and score = 0), 0) = v_bucket_before + 1,
    'eligible zero-score histogram bucket did not increment';
  perform public.finish_section(v_section_id);
  assert (select attempts_completed_total from public.package_statistics where package_id = 1)
         = v_completed_before + 1, 'repeated finalization double-counted completion';
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before + 1, 'repeated finalization double-counted statistics sample';
  assert coalesce((select attempt_count from public.package_score_histogram
                    where package_id = 1 and score = 0), 0) = v_bucket_before + 1,
    'repeated finalization double-counted the histogram';
  delete from public.attempts where id = v_attempt_id;
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before + 1, 'attempt deletion changed the qualified sample';
  assert coalesce((select attempt_count from public.package_score_histogram
                    where package_id = 1 and score = 0), 0) = v_bucket_before + 1,
    'attempt deletion changed the durable histogram';

  v_user_id := '00000000-0000-4000-8000-000000000005';
  insert into auth.users (id) values (v_user_id) on conflict (id) do nothing;
  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  select attempts_completed_total, statistics_sample_total
    into v_completed_before, v_sample_before
    from public.package_statistics where package_id = 1;
  v_result := public.start_attempt(1)::jsonb;
  v_attempt_id := (v_result #>> '{attempt,id}')::uuid;
  while (select status from public.attempts where id = v_attempt_id) = 'active' loop
    v_result := public.start_section(v_attempt_id)::jsonb;
    exit when coalesce((v_result ->> 'done')::boolean, false);
    v_section_id := (v_result #>> '{section_attempt,id}')::uuid;
    v_subtest_key := v_result #>> '{subtest,key}';
    v_limit := case v_subtest_key
      when 'verbal' then 23 when 'kuantitatif' then 20 else 5 end;
    v_saved := 0;
    for v_question in select value from jsonb_array_elements(v_result -> 'questions') loop
      exit when v_saved >= v_limit;
      select qr.correct_option into v_correct
        from public.attempts a
        join public.package_release_questions prq
          on prq.package_release_id = a.package_release_id
         and prq.question_id = v_question ->> 'id'
        join public.question_revisions qr on qr.id = prq.question_revision_id
       where a.id = v_attempt_id;
      v_wrong := case when v_correct = 'A' then 'B' else 'A' end;
      perform public.save_answer(v_section_id, v_question ->> 'id', v_wrong);
      v_saved := v_saved + 1;
    end loop;
    perform public.finish_section(v_section_id);
  end loop;
  assert (select attempts_completed_total from public.package_statistics where package_id = 1)
         = v_completed_before + 1, 'low-coverage completion was not counted as finished';
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before, '48-answer run below a per-subtest floor entered the sample';

  -- All three per-subtest floors pass, but 47 total answers is still excluded.
  v_user_id := '00000000-0000-4000-8000-000000000006';
  insert into auth.users (id) values (v_user_id) on conflict (id) do nothing;
  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  select attempts_completed_total, statistics_sample_total
    into v_completed_before, v_sample_before
    from public.package_statistics where package_id = 1;
  v_result := public.start_attempt(1)::jsonb;
  v_attempt_id := (v_result #>> '{attempt,id}')::uuid;
  while (select status from public.attempts where id = v_attempt_id) = 'active' loop
    v_result := public.start_section(v_attempt_id)::jsonb;
    exit when coalesce((v_result ->> 'done')::boolean, false);
    v_section_id := (v_result #>> '{section_attempt,id}')::uuid;
    v_subtest_key := v_result #>> '{subtest,key}';
    v_limit := case v_subtest_key
      when 'verbal' then 23 when 'kuantitatif' then 18 else 6 end;
    v_saved := 0;
    for v_question in select value from jsonb_array_elements(v_result -> 'questions') loop
      exit when v_saved >= v_limit;
      select qr.correct_option into v_correct
        from public.attempts a
        join public.package_release_questions prq
          on prq.package_release_id = a.package_release_id
         and prq.question_id = v_question ->> 'id'
        join public.question_revisions qr on qr.id = prq.question_revision_id
       where a.id = v_attempt_id;
      v_wrong := case when v_correct = 'A' then 'B' else 'A' end;
      perform public.save_answer(v_section_id, v_question ->> 'id', v_wrong);
      v_saved := v_saved + 1;
    end loop;
    perform public.finish_section(v_section_id);
  end loop;
  assert (select attempts_completed_total from public.package_statistics where package_id = 1)
         = v_completed_before + 1, '47-answer run was not counted as finished';
  assert (select statistics_sample_total from public.package_statistics where package_id = 1)
         = v_sample_before, '47-answer run entered the statistics sample';
end;
$$;

-- Exact median from durable buckets for odd and even populations, without
-- expanding one row per historical attempt.
do $$
declare
  v_package_id integer := 1;
  v_release_id uuid;
  v_catalogue jsonb;
begin
  delete from public.package_score_histogram where package_id = v_package_id;
  insert into public.package_score_histogram (package_id, score, attempt_count)
  values (v_package_id, 100, 1), (v_package_id, 150, 1), (v_package_id, 200, 1);
  update public.package_statistics
     set attempts_started_total = greatest(attempts_started_total, 4),
         attempts_completed_total = greatest(attempts_completed_total, 4),
         statistics_sample_total = 3,
         statistics_score_sum = 450
   where package_id = v_package_id;
  assert public._v3_package_median_score(v_package_id) = 150,
    'odd histogram median is incorrect';
  select current_release_id into v_release_id from public.packages where id = v_package_id;
  v_catalogue := public._v3_release_package_json(v_release_id)::jsonb;
  assert (v_catalogue ->> 'mean_score')::numeric = 150
     and (v_catalogue ->> 'median_score')::numeric = 150,
    'odd catalogue mean/median is incorrect';
  insert into public.package_score_histogram (package_id, score, attempt_count)
  values (v_package_id, 250, 1);
  update public.package_statistics
     set statistics_sample_total = 4, statistics_score_sum = 700
   where package_id = v_package_id;
  assert public._v3_package_median_score(v_package_id) = 175,
    'even histogram median is incorrect';
  v_catalogue := public._v3_release_package_json(v_release_id)::jsonb;
  assert (v_catalogue ->> 'mean_score')::numeric = 175
     and (v_catalogue ->> 'median_score')::numeric = 175,
    'even catalogue mean/median is incorrect';
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
