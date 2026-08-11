-- =============================================================================
-- TBS LPDP Try Out — one-time v3.1 retained statistics backfill
--
-- Apply only after the revised schema_v3.sql (and then schema_v4) has been
-- applied. This recovers qualified mean/median data from finished attempts
-- that still exist and predate the v3.1 score-statistics boundary.
--
-- Safety properties are enforced by backfill_v3_1_retained_statistics():
--   * aborts unless every durable completion still has a retained attempt row;
--   * derives the 48/60 + per-subtest eligibility rule from saved answers;
--   * locks the aggregate tables while taking a consistent snapshot;
--   * verifies counter/sum/histogram invariants before and after mutation;
--   * records one immutable aggregate-only audit marker;
--   * returns already_applied without changing data on every later run.
--
-- No answer, attempt, or user identifier is returned by this script.
-- =============================================================================

begin;

select public.backfill_v3_1_retained_statistics() as backfill_result;

commit;

