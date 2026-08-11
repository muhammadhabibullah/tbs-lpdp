# Technical Requirements v3 — Versioned Questions, Report Digest, Package Metadata, and Durable Statistics

| | |
|---|---|
| Status | v3.0 — implemented; production deployment requires the secrets and apply order in §9.3/§11 |
| Date | 2026-08-11 |
| Extends | [`TECHNICAL_REQUIREMENTS.md`](TECHNICAL_REQUIREMENTS.md) (v1) and [`TECHNICAL_REQUIREMENTS_V2.md`](TECHNICAL_REQUIREMENTS_V2.md) (v2) |
| Implemented follow-up | [`TECHNICAL_REQUIREMENTS_V3_1.md`](TECHNICAL_REQUIREMENTS_V3_1.md) — on-demand statistics, qualified mean/median, and metadata help |
| Scope | Daily operator email for question reports; immutable question/package versions; public package metadata; deletion-safe package attempt statistics |
| Stack | GitHub Pages + Supabase Postgres/RLS/RPC/Cron/Edge Functions; Resend is the email transport only |

## 1. Purpose and decisions

v3 closes four gaps in the implemented v1/v2 system:

1. `question_reports` are stored but the operator must remember to query them.
2. Questions and answer keys are currently overwritten in place, so an old attempt's score and Pembahasan can change after a bank push.
3. The package list does not explain package difficulty, the model that authored it, or which content version is live.
4. The seven-day retention sweep deletes attempts, so counts and score averages computed from `attempts` are temporary.

The implementation decisions that resolve those gaps are:

- A **question revision** is immutable. Any change to the stem, passage, image, options, key, explanations, type, or per-question difficulty creates a new revision.
- A **package release** is an immutable set of exactly 60 question revisions plus package metadata. An attempt is pinned to one release when `start_attempt` creates it; all three subtests use that release even if a newer one is published mid-attempt.
- The package card shows editorial package-level difficulty, authoring-model label, package release number/date, completed-attempt count, and arithmetic mean score. Per-question difficulty remains separate and is not exposed during an active exam.
- Statistics are incremented transactionally when an attempt is created/finished and live independently of attempt rows. The retention cron never decrements them.
- A Supabase Cron job freezes the report window into a private outbox row and calls one private Supabase Edge Function daily. The function claims that payload with a Supabase secret key and sends the operator's digest through Resend.

### 1.1 “Average” and “mean”

Arithmetic average and arithmetic mean are the same statistic. v3 exposes one field, `mean_score`, and one UI value, **Rata-rata skor**. It does not show two duplicate values. `mean_score` is the mean of `total_score` for **finished full-package attempts only**, ranges from 0 to 300, is rounded to one decimal for display, and is `null` when no attempt has finished.

The public attempt count is likewise the number of finished full-package attempts. An internal started count is retained for operations, but abandoned attempts do not appear in the public count and do not depress the mean.

Both values aggregate all releases of the same package from the statistics coverage boundary; publishing a new version does not reset them. The package card or its accessible tooltip says **semua versi** so the current release label is not mistaken for release-specific analytics.

### 1.2 Package metadata seed values

Package difficulty is editorial metadata in `package.json`; it is not calculated from the mix of per-question difficulty tags. The initial values are:

| Package | Difficulty | AI model display label |
|---------|------------|------------------------|
| 1 | `medium` / Medium | Opus 5 |
| 2 | `medium` / Medium | Opus 5 |
| 3 | `medium` / Medium | Opus 5 |
| 4 | `hard` / Hard | Fable-5 |
| 5 | `easy` / Easy | 5.6 Sol |
| 6 | `hard` / Hard | 5.6 Sol |

`ai_model` is free text rather than a database enum so later packages do not require a migration. `difficulty` is constrained to `easy`, `medium`, or `hard`.

### 1.3 Scope boundaries

v3 does not add a moderation dashboard, user-visible public report counts, score leaderboards, percentile/ranking calculations, median/mode, report emails to users, or automatic question changes based on reports. The digest is an operator notification; question triage remains manual.

## 2. Requirement ID convention

v3 continues the shared v1/v2 ID space. It starts at `FE-20`, `BE-19`, `QG-9`, `C-9`, and `NF-12`. Existing IDs retain their original meaning. Where v3 changes an old contract—especially QG-6, BE-2/BE-5/BE-7, BE-9/BE-10/BE-11/BE-12, C-2/C-5/C-8, and NF-10—the old ID is cited.

## 3. Constraints

| ID | Constraint |
|----|------------|
| C-9 | **Immutable history**: once a question revision or package release is published, application and service-role update/delete operations must not mutate it. Corrections create a new revision/release. |
| C-10 | **Attempt pinning**: a created attempt references exactly one package release. Question delivery, answer validation, grading, and review all resolve through that release, never through the package's current release. |
| C-11 | **Versioned key secrecy**: revision rows contain answer keys and explanations and therefore have no client-readable RLS policy. Only trusted RPCs may project safe active-exam fields or post-finish review fields. This is v1 C-4 applied to revisions. |
| C-12 | **Immutable images**: a revision's image object is content-addressed and never overwritten. Keeping an old URL while replacing the bytes at that URL does not satisfy C-9. |
| C-13 | **Transactional publication**: a package becomes current in one database transaction after all 60 revisions and release mappings validate. A user can observe either the previous complete release or the next complete release, never a partially pushed mix. |
| C-14 | **No administrative secrets in the SPA or git**: the report destination, sender, email-provider key, and Cron-to-Function credential live only in Supabase Edge Function secrets or Vault. The digest function is not callable with a user JWT or publishable key. |
| C-15 | **Monotonic statistics**: attempt retention, anonymous-user deletion, and report deletion never decrement the durable counters or score sum. Corrections require an explicit audited operator adjustment, not a rebuild from the seven-day attempt window. |
| C-16 | **Narrow external dependency**: v3 amends v1 C-2 only for outbound email transport. The application, database, schedules, authoritative state, and trusted business logic remain on GitHub Pages/Supabase; Resend only transports the digest and may retain normal delivery metadata under its own service policy. |
| C-17 | **Migration boundary**: the immutable-history guarantee applies to attempts created after the v3 migration. Existing retained attempts are pinned to whatever content is live at migration time; content overwritten before v3 cannot be reconstructed from the database. |

## 4. Functional requirements — question pipeline (QG)

| ID | Requirement |
|----|-------------|
| QG-9 | Every `questions/bank/<package>/package.json` adds required `difficulty` (`easy\|medium\|hard`) and `ai_model` (non-empty string) fields. `validate_bank.py` validates them and the seed mapping in §1.2 is committed. |
| QG-10 | `push_to_supabase.py` canonicalises each complete question—including type, stem, passage, image content hash, difficulty, ordered options, correct option, and all explanations—and computes SHA-256. Content identical to the **current** revision reuses it; any difference from current, including reverting to older text, creates `version + 1`. |
| QG-11 | Images upload to `question-images/<package>/<question-id>/<sha256>.<ext>`. Existing objects are never upserted in place. An upload can be skipped when the content-addressed object already exists. Orphan objects from a failed database transaction are harmless and may be cleaned manually. |
| QG-12 | QG-6 is replaced by one service-role-only `publish_package_release(payload jsonb)` RPC call per package. Direct table upserts are no longer the publish path. The RPC validates the full blueprint, creates/reuses revisions, creates/reuses a release, and atomically changes `packages.current_release_id`. |
| QG-13 | A payload identical to the current release is idempotent: it does not create a revision, increment the package release, or change `published_at`. A metadata change or deliberate rollback creates a release even when its hash matches an older release. The publisher locks the package row so concurrent pushes cannot allocate the same version. |
| QG-14 | Git remains the content source of truth (v1 C-5), but database revision numbers and publish timestamps are server-assigned. They must not be hand-written into question JSON. An offline dry run validates the complete payload and prints its deterministic content hash/content-addressed paths without writing. The live RPC response reports whether a release was created and how many revisions changed. |
| QG-15 | `validate_bank.py` still finishes every content change and additionally rejects a manifest without v3 metadata, duplicate/unstable question IDs, noncanonical option order, or a package whose blueprint is not exactly 23/25/12. |

### 4.1 Canonical content hash

The Python publisher and the SQL RPC use the same documented canonical JSON shape:

```json
{
  "id": "1-verbal-001",
  "subtest": "verbal",
  "number": 1,
  "type": "analogi",
  "question_text": "...",
  "passage": null,
  "image_sha256": null,
  "difficulty": "medium",
  "options": [{"key": "A", "text": "..."}],
  "correct_option": "C",
  "explanations": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}
}
```

Keys are UTF-8 and the options array is ordered A–E. The canonical bytes are PostgreSQL's normalized `jsonb::text` representation: object keys use jsonb's UTF-8 byte-length/byte-value ordering and its standard comma/colon spacing. The Python publisher mirrors that representation. The server recomputes the hash and rejects a mismatched diagnostic hash; it does not trust a hash supplied by the publisher. Including key/explanations is deliberate: a key-only correction must produce a new revision even if the active-exam content is unchanged.

The package release hash covers the package title, description, package difficulty, AI-model label, and the ordered list of `(question_id, question_revision_content_hash)` pairs. It does not include timestamps or database UUIDs.

## 5. Functional requirements — frontend (FE)

| ID | Requirement |
|----|-------------|
| FE-20 | Each Home package card shows three metadata chips: **Easy/Medium/Hard**, the exact `ai_model` label, and **Versi N · diperbarui D MMM YYYY**. Dates use `id-ID` formatting in `Asia/Jakarta`; the stored value remains UTC. |
| FE-21 | Each package card also shows **N percobaan selesai** and **Rata-rata skor X / 300**, identified in visible secondary text or an accessible tooltip as an aggregate across **semua versi**. When there are no finished attempts it shows **Belum ada hasil** instead of `0 / 300`. Counts use Indonesian thousands formatting and the mean uses one decimal only when needed. |
| FE-22 | Package list metadata and statistics arrive in the same `get_package_catalog` response as the existing package/subtest data. Rendering the labels adds no per-card queries and no N+1 request pattern. |
| FE-23 | Pembahasan shows **Versi soal N · diperbarui D MMM YYYY** on each question card. It describes the revision that attempt used, not the current revision. The report state beside it is likewise revision-specific. |
| FE-24 | The active exam does not show per-question difficulty or model attribution; doing so can influence responses and would clutter the PUSMENDIK-style screen. The package identity/release remains available in **Informasi Soal**, and every delivered question silently carries its pinned revision metadata for resume consistency. |
| FE-25 | `VITE_USE_MOCK=true` models immutable releases, pins an attempt on creation, and maintains deletion-safe aggregate counters in local storage. A mock bank reload must not alter an already-created mock attempt's review. |
| FE-26 | UI copy remains Bahasa Indonesia except the user-requested difficulty values and model product names. Metadata chips have text, not colour alone, and remain readable at the v1 minimum width. |

## 6. Functional requirements — backend (BE)

| ID | Requirement |
|----|-------------|
| BE-19 | **Question revisions**: `question_revisions` and `question_revision_options` store immutable full content, key, explanations, `version`, `content_hash`, and `published_at`. `(question_id, version)` is unique; content hashes are indexed but may repeat after a deliberate rollback. |
| BE-20 | **Package releases**: `package_releases` and `package_release_questions` store immutable complete release membership and the release's title/description/difficulty/model. `(package_id, version)` is unique; release hashes are indexed but may repeat after a rollback. `packages.current_release_id` is the sole pointer changed at publish time. |
| BE-21 | **Attempt pin**: `attempts.package_release_id` is set from `packages.current_release_id` in the same transaction that inserts the attempt. `start_attempt` raises `P0002` when a published package has no current complete release. Resuming an active attempt keeps its original release. |
| BE-22 | **Versioned exam path**: `start_section`, `save_answer`, and `toggle_doubt` validate question membership through the attempt's release. `answers.question_revision_id` is set server-side from that mapping and cannot be selected by the caller. |
| BE-23 | **Versioned grading**: `_grade_section` compares the saved option with `question_revisions.correct_option`, using `answers.question_revision_id`. It never joins the mutable compatibility projection in `answer_keys`. Its existing idempotency and deadline behaviour remain unchanged. |
| BE-24 | **Versioned review**: `get_review` builds question text, image, options, key, and explanations from the pinned revisions and returns `question_version` plus `question_updated_at`. A later publish cannot change the JSON for an old finished attempt. |
| BE-25 | **Version-aware reports**: `question_reports` gains nullable `question_revision_id`. New writes always populate it and are unique per `(user_id, question_revision_id)`, allowing the same user to report a later revision of the same logical question. `report_question` and `delete_question_report` require `p_attempt_id` so the server resolves the exact revision from the reviewed attempt. |
| BE-26 | **Package catalogue**: authenticated `get_package_catalog()` returns published package/subtest data, current release metadata, `completed_attempts_total`, and `mean_score`. It exposes no revision IDs, report counts, raw sums, or answer-key fields. |
| BE-27 | **Durable statistics**: `package_statistics` stores started count, completed count, score sum, coverage timestamp, and update timestamp per package. Creation increments started count only after a new attempt row is inserted; returning an existing active attempt does not increment it. |
| BE-28 | **Exactly-once completion aggregate**: the transaction that changes an attempt from `active` to `finished` also increments completed count and adds the final score. The update is guarded by `attempts.status = 'active'`, so concurrent/idempotent finish calls contribute once. If either write fails, the transaction rolls back. |
| BE-29 | **Daily digest function**: private Edge Function `question-report-digest` accepts only the named Supabase secret key `automations`, claims one database-frozen digest payload with the admin client, sends the email, and records the provider message ID. Browser sessions and publishable keys receive 401. |
| BE-30 | **Digest outbox**: `question_report_digest_runs` stores an immutable `[window_start, window_end)` and frozen email payload plus `pending\|sending\|sent\|failed\|manual_attention`, lease, attempts, provider ID, redacted error, and timestamps. Only one unsent run may exist. A retry sends the exact stored payload with the same run ID/provider idempotency key; it never rebuilds the body from mutable reports. |
| BE-31 | **Cron schedule**: `pg_cron` + `pg_net` create/invoke the daily run at `01:00 UTC` (`08:00 WIB`; Jakarta has no DST). A second job retries an eligible unsent run every 30 minutes, without creating extra daily emails. The queue reuses an unsent run or creates a window beginning at the last sent cutoff, so an outage produces one catch-up digest rather than losing a day. Automatic ambiguous retries stop before Resend's 24-hour idempotency window expires and become `manual_attention`. |
| BE-32 | **Digest content**: every daily email is sent, including a zero-report heartbeat. It contains the time window in WIB, new/edited count, open backlog count, and rows grouped by logical question and revision with reason/status/comment. User IDs, attempt IDs, auth data, and answer keys are omitted. Free text is HTML-escaped (or sent as plain text). |
| BE-33 | **Digest secrets**: `RESEND_API_KEY`, `REPORT_DIGEST_TO`, and `REPORT_DIGEST_FROM` are Edge Function secrets. The project URL and named `automations` secret used by `pg_net` are stored in Supabase Vault. No service-role/secret key is stored in a public table or request body. |
| BE-34 | **RLS/grants**: revision/key tables, release mappings, statistics, and digest-run tables have RLS enabled and no client table policies. Clients receive projections only through named RPCs. `publish_package_release` is revoked from `anon`, `authenticated`, and `public`; only service-role operation can execute it. |

## 7. Data model

The v3 migration lives in `supabase/schema_v3.sql`, applied after v1 and v2. This is the target model; SQL details may add supporting checks/indexes but may not weaken the constraints.

```sql
-- Stable logical identity remains in public.questions.
create table public.question_revisions (
  id              uuid primary key default gen_random_uuid(),
  question_id     text not null references public.questions(id),
  version         integer not null check (version > 0),
  qtype           text not null,
  question_text   text not null,
  passage         text,
  image_url       text,
  image_sha256    text,
  difficulty      text not null check (difficulty in ('easy','medium','hard')),
  correct_option  char(1) not null check (correct_option in ('A','B','C','D','E')),
  explanations    jsonb not null,
  content_hash    text not null check (length(content_hash) = 64),
  published_at    timestamptz not null default now(),
  unique (question_id, version),
  unique (id, question_id)
);
create index question_revisions_hash_idx
  on public.question_revisions (question_id, content_hash);

create table public.question_revision_options (
  question_revision_id uuid not null references public.question_revisions(id),
  key                  char(1) not null check (key in ('A','B','C','D','E')),
  text                 text not null,
  primary key (question_revision_id, key)
);

create table public.package_releases (
  id            uuid primary key default gen_random_uuid(),
  package_id    integer not null references public.packages(id),
  version       integer not null check (version > 0),
  title         text not null,
  description   text not null default '',
  difficulty    text not null check (difficulty in ('easy','medium','hard')),
  ai_model      text not null check (btrim(ai_model) <> ''),
  content_hash  text not null check (length(content_hash) = 64),
  published_at  timestamptz not null default now(),
  unique (package_id, version),
  unique (id, package_id)
);
create index package_releases_hash_idx
  on public.package_releases (package_id, content_hash);

create table public.package_release_questions (
  package_release_id   uuid not null,
  package_id           integer not null,
  question_id          text not null,
  question_revision_id uuid not null,
  subtest_id           text not null,
  number               integer not null,
  primary key (package_release_id, question_id),
  unique (package_release_id, subtest_id, number),
  foreign key (package_release_id, package_id)
    references public.package_releases(id, package_id),
  foreign key (question_revision_id, question_id)
    references public.question_revisions(id, question_id)
);

alter table public.packages add column current_release_id uuid;
alter table public.attempts add column package_release_id uuid;
alter table public.answers add column question_revision_id uuid;
alter table public.question_reports add column question_revision_id uuid;

-- Composite foreign keys (plus equivalent subtest/number checks) prevent a
-- valid revision UUID from being paired with the wrong package/question.
alter table public.packages add constraint packages_current_release_same_package_fk
  foreign key (current_release_id, id) references public.package_releases(id, package_id);
alter table public.attempts add constraint attempts_release_same_package_fk
  foreign key (package_release_id, package_id) references public.package_releases(id, package_id);
alter table public.answers add constraint answers_revision_same_question_fk
  foreign key (question_revision_id, question_id) references public.question_revisions(id, question_id);
alter table public.question_reports add constraint reports_revision_same_question_fk
  foreign key (question_revision_id, question_id) references public.question_revisions(id, question_id);

create table public.package_statistics (
  package_id               integer primary key references public.packages(id),
  attempts_started_total   bigint not null default 0 check (attempts_started_total >= 0),
  attempts_completed_total bigint not null default 0 check (attempts_completed_total >= 0),
  score_sum                bigint not null default 0 check (score_sum >= 0),
  coverage_started_at      timestamptz not null,
  updated_at               timestamptz not null default now(),
  check (attempts_completed_total <= attempts_started_total)
);

create table public.question_report_digest_runs (
  id                  uuid primary key default gen_random_uuid(),
  window_start        timestamptz not null,
  window_end          timestamptz not null check (window_end > window_start),
  status              text not null check (status in
                        ('pending','sending','sent','failed','manual_attention')),
  delivery_attempts   integer not null default 0,
  lease_until         timestamptz,
  email_payload       jsonb,
  payload_sha256      text,
  provider_message_id text,
  last_error          text,
  created_at          timestamptz not null default now(),
  sent_at             timestamptz,
  updated_at          timestamptz not null default now(),
  unique (window_start, window_end)
);
```

An immutability trigger rejects `UPDATE` and `DELETE` on the four revision/release tables. Composite foreign keys (or equivalent deferred constraint triggers for the existing table shapes) additionally enforce that every release belongs to its package, every revision belongs to its logical question, and every mapped subtest/number agrees with that question's stable placement. Foreign keys from attempts, reports, and release membership prevent accidental removal. `questions`, `question_options`, and `answer_keys` remain temporarily as the **current-release compatibility projection** during v3 rollout, but application RPCs stop reading their content. They can be removed in a later major migration after all operational SQL uses revisions.

### 7.1 Statistics projection

`get_package_catalog` calculates:

```sql
case when attempts_completed_total = 0 then null
     else round(score_sum::numeric / attempts_completed_total, 1)
end as mean_score
```

The raw sum and started count remain private. The aggregate is all-time **from the v3 tracking boundary**. Migration can include the retained attempt rows that still exist, but attempts already deleted by NF-10 cannot be recovered; the UI should initially describe the count as **tercatat sejak <coverage date>** in a tooltip until the project owner decides that qualifier is no longer useful.

### 7.2 Question-report migration

The old unique constraint on `(user_id, question_id)` is replaced with a partial unique index on `(user_id, question_revision_id) where question_revision_id is not null`.

For each v2 report:

- if its `content_hash` matches the v3 migration snapshot of the current visible question, attach it to that initial revision;
- otherwise leave `question_revision_id = null` and retain `question_id` plus `content_hash` as legacy triage evidence;
- all reports submitted after the migration must have a non-null revision resolved from `p_attempt_id`;
- `get_review` only selects `my_report` whose revision matches the reviewed attempt. A stale legacy report remains available to the operator but is not guessed onto a revision.

## 8. API changes

| Function | Change |
|----------|--------|
| `get_package_catalog()` | **New** authenticated RPC. Returns published package/subtest data, current release version/date/difficulty/model, completed count, mean, and coverage date. Replaces direct package/subtest catalogue reads in the SPA. |
| `publish_package_release(p_payload jsonb)` | **New** service-role-only transactional publisher. Validates hashes/blueprint, creates or reuses revisions/release, updates current pointer, and refreshes compatibility projections. |
| `start_attempt(p_package_id)` | Adds `package_release_id` internally and returns safe `package_version`/`package_updated_at` metadata. Existing rate/capacity behaviour remains. |
| `start_section(p_attempt_id)` | Reads pinned release membership/revisions. Safe question JSON adds `question_version` and `question_updated_at`; still has no key/explanations. |
| `save_answer`, `toggle_doubt` | Resolve and validate the question revision from the section's attempt release; caller arguments remain stable. |
| `finish_section` / `_grade_section` | Grade pinned revision keys; update package statistics exactly once when the full attempt closes. |
| `get_review(p_attempt_id)` | Reads the pinned release and returns revision metadata plus the report for that exact revision. |
| `report_question(...)` | `p_attempt_id` becomes required and resolves `question_revision_id`; upsert target becomes `(user_id, question_revision_id)`. |
| `delete_question_report(p_question_id, p_attempt_id)` | New version-specific signature. The one-argument v2 overload may remain for one frontend deployment as a compatibility wrapper, then is revoked/dropped. |
| `_queue_question_report_digest()` | **New** private SQL helper: advisory-locks, reuses/creates one unsent run, and calls the Edge Function through `pg_net`. Not granted to clients. |

### 8.1 Catalogue response

The fields added to each package are:

```ts
interface PackageCatalogItem extends Package {
  difficulty: 'easy' | 'medium' | 'hard'
  ai_model: string
  question_version: number
  last_updated_at: string
  completed_attempts_total: number
  mean_score: number | null
  statistics_coverage_started_at: string
}
```

Postgres `bigint` may exceed JavaScript's safe integer range, so the RPC must either cap/cast the public completed count to a safe numeric range or return it as a decimal string and parse it deliberately. Given the existing capacity limit, casting after `least(value, 9007199254740991)` is acceptable.

## 9. Daily question-report email

### 9.1 Flow

```text
01:00 UTC pg_cron
  -> _queue_question_report_digest()
       -> reuse pending/failed run, or create [last sent cutoff, now)
       -> pg_net POST /functions/v1/question-report-digest {run_id}
            -> authenticate named `automations` secret
            -> claim the database-frozen payload for that run
            -> send through Resend with idempotency key `tbs-report-digest/<run_id>`
            -> mark run sent with provider message ID
```

The Edge Function never accepts arbitrary dates or recipient addresses from its request. `run_id` must identify the one server-created unsent run. It atomically claims `pending/failed -> sending` with a short lease; an already `sent` run returns 200 without another send. The first claimant snapshots the bounded detail/summary into `email_payload` and records its SHA-256 before calling Resend. Every retry renders that same snapshot, because Resend rejects reuse of an idempotency key with a different payload.

On mail-provider failure the function records a redacted error and marks `failed`; the 30-minute retry job reuses the window, snapshot, and idempotency key. [Resend idempotency keys](https://resend.com/docs/dashboard/emails/idempotency-keys) expire after 24 hours, so an ambiguously delivered run is retried automatically only inside a 23-hour budget. After that it becomes `manual_attention`; the operator checks Resend delivery logs and either marks it sent or explicitly authorises a new send. This avoids claiming impossible exactly-once delivery across an expired third-party deduplication window.

### 9.2 Email format

Subject:

```text
[TBS LPDP] 4 laporan soal — 10 Agu 2026
```

Body:

- period in WIB and whether this is a catch-up window;
- new/edited reports in the window and current open backlog count;
- package, subtest, question number/ID, reported revision, and whether that revision is current;
- reason, status, selected option, created/updated time, and comment;
- zero-report text when applicable, proving that the daily automation still ran.

Comments are untrusted input. Prefer a plain-text body; if an HTML companion is sent, escape `& < > " '` before interpolation. Do not log full comments or the generated email body in Edge Function logs.

### 9.3 Supabase configuration

Supabase officially supports scheduling Edge Functions with `pg_cron` + `pg_net`, recommends Vault for the invocation credential, and documents email sending from Edge Functions with Resend:

- [Scheduling Edge Functions](https://supabase.com/docs/guides/functions/schedule-functions)
- [Securing Edge Functions](https://supabase.com/docs/guides/functions/auth)
- [Sending Emails](https://supabase.com/docs/guides/functions/examples/send-emails)
- [Edge Function secrets](https://supabase.com/docs/guides/functions/secrets)

Required one-time configuration (values are examples/placeholders and are never committed):

```bash
supabase secrets set RESEND_API_KEY=... REPORT_DIGEST_TO=... REPORT_DIGEST_FROM=...
supabase functions deploy question-report-digest --no-verify-jwt
```

Create a named Supabase secret API key called `automations`; put that key and the project URL in Vault for `pg_net`. The function uses service-to-service authentication (`apikey`, not `Authorization: Bearer`) and accepts only that named key.

Resend requires a verified sender domain for a real `REPORT_DIGEST_FROM`. The mail provider is replaceable; changing it must not change the database outbox/window contract.

## 10. Security and integrity

- **No historical key oracle**: active-exam RPCs project revision content without `correct_option`/`explanations`; direct revision-table access is denied.
- **No current-release substitution**: every exam RPC begins from the caller-owned attempt and its stored `package_release_id`.
- **No mixed publish**: the service-role publisher receives all 60 questions and moves one current-release pointer only after validation.
- **No image mutation**: the URL includes the image bytes' SHA-256; an old review cannot silently receive a new image.
- **No public statistics internals**: only count and calculated mean are returned; report counts and score sums remain private.
- **No report-email public endpoint**: the named automation secret is distinct from the publishable key, kept in Vault, and can be rotated independently.
- **No email XSS/log spill**: comments are escaped/plain text and omitted from logs. Provider errors stored in Postgres are truncated and stripped of credentials/response headers.
- **No lost digest window**: a fixed database outbox window is marked sent only after a successful provider response. Retries reuse its ID.

## 11. Migration and deployment order

The live upgrade is performed in this order:

1. Back up the database and record current package/question/report counts.
2. Apply `schema_v3.sql` while package publishing is paused. It creates revision/release/stat/digest tables and policies.
3. Seed the package difficulty/model mapping in §1.2, snapshot current content as question revision 1 and package release 1, pin every retained attempt to the appropriate release, populate `answers.question_revision_id`, migrate matching reports, and initialise statistics once. Active attempts may continue against that snapshot. The initial `published_at` is the migration time because earlier update timestamps were not recorded.
4. Add `NOT NULL` constraints for new attempt/answer paths after backfill validation. Legacy unmatched report revisions remain the only permitted nulls.
5. Commit the six package manifest metadata values and deploy the revised validator/publisher. Dry-run, validate the whole bank, then publish packages 1–6. An identical content snapshot is reused; the added package metadata may legitimately create the next release.
6. Deploy `question-report-digest`, configure Edge Function secrets, create the named automation key/Vault entries, and invoke one manual test run to a controlled recipient.
7. Deploy the frontend catalogue/review/mock changes only after the v3 RPCs exist.
8. Apply the updated `maintenance.sql` last to schedule the digest after the function is reachable. Keep the attempt/user retention jobs unchanged.
9. Run the acceptance suite and observe the first scheduled digest plus `cron.job_run_details`, `net._http_response`, Edge Function logs, and `question_report_digest_runs`.

Fresh-project order becomes:

```text
schema.sql -> schema_v2_reports.sql -> schema_v3.sql -> package pushes
           -> Edge Function/secrets/Vault -> maintenance.sql
```

Reapplying `schema.sql` still replaces core RPCs/grants. Therefore always reapply `schema_v2_reports.sql` and then `schema_v3.sql` afterwards. v3 owns the final definitions of `start_attempt`, `start_section`, `_grade_section`, `get_review`, report RPCs, and the grant block.

### 11.1 Irrecoverable pre-v3 history

The migration can preserve only the question content that exists when it runs. If package 1 question 10 was overwritten three times before v3, neither its earlier body nor the exact key used by an old retained attempt exists in Supabase. That attempt is pinned to the migration snapshot as a best effort. This limitation must be recorded in the deployment notes; it is not fixable without a backup or git commit identifying the content each attempt saw.

Similarly, the initial durable statistics can include attempts that still exist in the seven-day window, but cron-deleted attempt counts/scores cannot be reconstructed. From the migration transaction onward, the aggregate is deletion-safe and exact.

## 12. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NF-12 | Publishing a six-package bank is deterministic and idempotent. A no-change re-push produces zero new revisions/releases and unchanged update dates. |
| NF-13 | Version pinning adds only mapping/UUID joins to exam RPCs. Indexes on release membership and revision PKs keep `start_section`/`get_review` bounded to 23–60 questions. |
| NF-14 | Version storage grows with content edits, not attempts. Revisions and content-addressed images are not automatically deleted because package releases/reports are audit history; monitor them under the existing capacity guard. |
| NF-15 | Statistics updates are O(1), transactional, and add no query over historical attempts to package-page load. Attempt retention can delete millions of detail rows without changing catalogue values. |
| NF-16 | Digest delivery is at-least-once at the outbox level and deduplicated at the provider within Resend's documented 24-hour idempotency window. Automated retries use a frozen payload and stop at 23 hours; an older ambiguous run requires operator resolution. A failed send never advances the report window. |
| NF-17 | The digest completes within the Supabase Edge Function free-plan runtime by limiting detailed rows (default 200) and summarising any excess by question/reason; it never emits an unbounded email. |
| NF-18 | All v3 migrations and schedules are re-applicable. Data backfills are guarded by a migration marker and cannot double-increment statistics or duplicate revision 1. |
| NF-19 | `cd web && npm run build`, whole-bank validation, SQL integration tests, and Edge Function unit tests must pass before deployment. |

## 13. Acceptance criteria

| # | Check | Expected |
|---|-------|----------|
| A-1 | Push an unchanged package twice | Same question revision IDs, package release/version, and `published_at`; no duplicate rows |
| A-2 | Change only one explanation and push | That question gets `version + 1`; package gets `version + 1`; other question revisions are reused |
| A-3 | Replace an image without renaming the bank file | New SHA-256 object URL/revision; old attempt still renders old bytes |
| A-4 | Start an attempt, then publish a new package release before its second subtest | Every subtest and review uses the release pinned at attempt creation |
| A-5 | Change a correct key after an attempt finishes | Stored score and `get_review` for that attempt remain byte-for-byte unchanged |
| A-6 | Query revision/key tables as an authenticated browser user | No rows / permission denied; active-exam payload still contains no key/explanations |
| A-7 | Report the same logical question from two attempts using different revisions | Two revision-specific rows are allowed; each review shows only its matching report |
| A-8 | Migrate a v2 report whose content hash matches current content | It is linked to initial revision and remains editable/withdrawable from that matching review |
| A-9 | Migrate a stale v2 report whose content hash does not match | It is retained with null revision for operator triage and not guessed onto a review |
| A-10 | Create one attempt, call `start_attempt` repeatedly while it is active | Started counter increments once |
| A-11 | Finish final section twice/concurrently | Completed counter and score sum increment once; mean is correct |
| A-12 | Run `prune-attempts` after attempts age past seven days | Attempt detail disappears; public completed count and mean are unchanged |
| A-13 | Package has no finished attempts | Card shows `0 percobaan selesai` and `Belum ada hasil`, never `0 / 300` |
| A-14 | Inspect packages 1–6 | Difficulty/model labels exactly match §1.2 and release date uses WIB Indonesian formatting |
| A-15 | Invoke digest with a publishable key or user JWT | 401; no report data and no email |
| A-16 | Successful digest with no report activity | Operator receives the daily zero-report heartbeat; run is `sent` |
| A-17 | Successful digest with reports | Email contains correct fixed window, revision-aware details and backlog summary, but no user/attempt IDs or answer keys |
| A-18 | Provider succeeds but caller retries the same run within 24 hours | Same frozen payload/idempotency key; no second delivered email; database run ends `sent` |
| A-19 | Provider fails | Run is `failed`, cutoff does not advance, 30-minute retry reuses the run/window/payload; an ambiguous run older than 23 hours becomes `manual_attention` |
| A-20 | Full mock flow, page refresh, then simulated bank update | Existing mock attempt/review remains pinned; new attempt uses new release; mock aggregate stays durable |
| A-21 | `python3 questions/generator/validate_bank.py` and `cd web && npm run build` | Both exit 0 |

## 14. Deliverables

| File | Change |
|------|--------|
| `docs/TECHNICAL_REQUIREMENTS_V3.md` | This implementation specification |
| `supabase/schema_v3.sql` | Revision/release model, migration/backfill, versioned exam/report RPCs, catalogue RPC, statistics, digest outbox, RLS/grants |
| `supabase/maintenance.sql` | Enable `pg_net`; schedule daily queue at 01:00 UTC plus 30-minute retry; retain existing jobs |
| `supabase/functions/question-report-digest/index.ts` | Private revision-aware daily email function with outbox/idempotent delivery |
| `supabase/config.toml` | Function auth configuration (`verify_jwt = false`; named secret checked in function) |
| `supabase/functions/question-report-digest/render.test.ts` | Escaping, zero-report heartbeat, and revision-detail rendering tests; delivery lifecycle is covered by SQL integration tests and provider idempotency |
| `questions/bank/1..6/package.json` | Add package `difficulty` and `ai_model` values from §1.2 |
| `questions/generator/validate_bank.py` | Validate manifest metadata and v3 publish invariants |
| `questions/generator/push_to_supabase.py` | Canonical hashes, content-addressed uploads, dry-run diff, one transactional publish RPC |
| `web/src/lib/types.ts` | Package/revision/stat response types and version-specific report method signatures |
| `web/src/lib/supabaseApi.ts` | Catalogue RPC and changed report calls |
| `web/src/lib/mockApi.ts` | Release pinning and durable aggregate parity |
| `web/src/pages/HomePage.tsx` | Metadata/stat chips and empty-stat state |
| `web/src/pages/ReviewPage.tsx` | Revision/date label and revision-specific report state |
| `web/src/styles.css` | Responsive, accessible metadata/stat presentation |
| `supabase/tests/v3.sql` | Pinning, grading, RLS, report migration, exact-once stats, retention invariance integration tests |

## 15. Implementation milestones

M1–M7 are implemented in this repository and locally verified. M8's live
deployment/observed delivery remains an operator step because it requires the
production Supabase project, Vault keys, Resend account, and recipient address.

| Milestone | Work | Depends on |
|-----------|------|------------|
| M1 | Schema tables, immutable triggers, migration snapshot/backfill, RLS | v1 + v2 schema |
| M2 | Transactional version publisher + validator/manifests + content-addressed images | M1 |
| M3 | Version-pinned attempt delivery, answers, grading, review | M1–M2 |
| M4 | Version-aware question reports and v2 report migration | M1 + M3 |
| M5 | Durable statistics and catalogue RPC | M3 |
| M6 | Home/Review UI and mock parity | M3–M5 |
| M7 | Digest outbox, Edge Function, secrets/Vault, Cron schedule | M1 + M4 |
| M8 | Integration/security tests, live migration rehearsal, deployment | M1–M7 |

M3 is the release blocker: no bank push may use the v3 publisher in production until all exam and review RPCs read pinned revisions. M7 may deploy later without weakening version/history correctness, but v3 is not complete until the scheduled email has one observed successful live run.
