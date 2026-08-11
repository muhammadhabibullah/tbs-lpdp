# Technical Requirements v3.1 — Package Statistics and Metadata Help

| | |
|---|---|
| Status | v3.1 — implemented; optional retained-attempt backfill prepared for operator application |
| Date | 2026-08-11 |
| Extends | [`TECHNICAL_REQUIREMENTS_V3.md`](TECHNICAL_REQUIREMENTS_V3.md) and [`TECHNICAL_REQUIREMENTS_V4.md`](TECHNICAL_REQUIREMENTS_V4.md) |
| Scope | Hide aggregate statistics behind a card action, exclude low-engagement completions from score statistics, add the median, make package difficulty deterministic, and explain AI-model labels |

## 1. Goal and decisions

The v3 package card currently gives permanent visual space to aggregate data that
does not describe the visitor's own result. This improvement keeps the card
focused on the package and moves those aggregates into an on-demand statistics
popover opened from the top-right corner.

The statistics also need a clearer population. v3 already excludes a user who
starts a package and leaves before completing all three subtests: only a full
`attempts.status = 'finished'` transition contributes to the mean. v3.1 adds a
second gate for a user who manually or automatically completes the flow after
answering too little of it to represent a meaningful score sample.

The decisions are:

- **Percobaan selesai** remains the count of every full-package completion.
- Mean and median use a separate **sampel statistik** population defined in
  §2.1. A low score is never by itself grounds for exclusion.
- An exact score histogram, rather than retained attempt rows, powers the
  deletion-safe median.
- The schema migration starts conservatively at zero. An explicit operator
  backfill may include retained pre-boundary attempts only while every durable
  completion still has its detail row; otherwise it fails instead of exposing
  a partial historical sample.
- Package difficulty is calculated from the 60 per-question difficulty tags.
  It is no longer an unconstrained editorial label.
- Difficulty and AI-model help is available on hover, keyboard focus, and tap;
  it is not implemented with an inaccessible native `title` alone.
- The statistics popover and both metadata explanations contain aggregates or
  package metadata only. They never expose another user's identity or result.

This document supersedes v3 §1.1/§1.2/§1.3 and FE-20/FE-21, BE-26/BE-27/BE-28
only where the rules below differ. Version pinning, all-version aggregation,
retention, RLS, answer-key secrecy, and the v4 maintenance gate are unchanged.

## 2. Product rules

### 2.1 Statistically eligible attempt

At the one transaction that changes an attempt from `active` to `finished`, the
server calculates:

```text
answered_total = number of the release's 60 questions whose saved selected_option is non-null
answered_verbal = answered questions among the 23 verbal questions
answered_kuantitatif = answered questions among the 25 quantitative questions
answered_pemecahan_masalah = answered questions among the 12 problem-solving questions

statistics_eligible =
  all three required subtests are finished
  AND answered_total >= 48                 # at least 80% overall
  AND answered_verbal >= 12                # at least half of 23
  AND answered_kuantitatif >= 13            # at least half of 25
  AND answered_pemecahan_masalah >= 6       # at least half of 12
```

The per-subtest floors prevent a fully skipped subtest from being hidden by
high coverage in the other two. The 80% overall floor tolerates timeout or a
small number of deliberately unanswered items without treating a substantially
abandoned run as representative.

The gate deliberately does **not** use:

- a minimum score, because excluding genuine low scores would inflate both
  mean and median;
- elapsed time, because a fast legitimate attempt would be penalised while an
  abandoned browser tab could satisfy a time threshold;
- raw event count, because repeated saves and doubt toggles measure UI activity,
  not answer coverage.

This is an abandonment/coverage rule, not a claim that random answering or user
motivation can be detected perfectly.

### 2.2 Public statistics

The popover shows:

| Label | Definition |
|-------|------------|
| **Percobaan selesai** | All full-package completions across every release since the original completion-count coverage boundary |
| **Sampel statistik** | Completions satisfying §2.1 since the v3.1 score-statistics coverage boundary |
| **Rata-rata skor** | Arithmetic mean of `total_score` in the statistical sample |
| **Median skor** | Middle statistical-sample score; for an even sample, the arithmetic mean of the two middle scores |

Scores remain in the range 0–300 and in five-point increments. The median can
therefore end in `.5` for an even sample. Mean and median are rounded to at most
one decimal for display. If the sample count is zero, both show **Belum ada
hasil**; neither renders `0 / 300`.

The compact explanation in the popover is:

> Semua versi. Rata-rata dan median hanya memakai try out yang selesai, menjawab
> minimal 48 dari 60 soal, dan menjawab minimal separuh soal di setiap mata uji.

It also shows **Statistik skor tercatat sejak D MMM YYYY**. The original
completion-count coverage date remains available separately because the two
boundaries may differ after migration. When the optional §4.1 backfill proves
that every historical completion is still retained, the score-statistics date
moves back to the earliest classified retained completion.

### 2.3 Package difficulty

Per-question difficulty remains an author/reviewer classification, using this
rubric:

| Question tag | Editorial rubric |
|--------------|------------------|
| `easy` | Direct application or a familiar pattern, normally one or two reasoning steps and limited distractor interaction |
| `medium` | Several linked steps or one meaningful interpretation step, with plausible distractors |
| `hard` | Multi-step constraint synthesis, dense information, or closely competing distractors; still solvable within the subtest time budget |

The package label is deterministic. For a complete 60-question release:

```text
difficulty_index = (1 × easy_count + 2 × medium_count + 3 × hard_count) / 60

Easy   : difficulty_index < 1.90
Medium : 1.90 <= difficulty_index < 2.20
Hard   : difficulty_index >= 2.20
```

The current bank already fits the rule:

| Package | Easy / Medium / Hard | Index | Label |
|---------|----------------------|-------|-------|
| 1 | 17 / 31 / 12 | 1.92 | Medium |
| 2 | 15 / 31 / 14 | 1.98 | Medium |
| 3 | 15 / 29 / 16 | 2.02 | Medium |
| 4 | 9 / 26 / 25 | 2.27 | Hard |
| 5 | 19 / 29 / 12 | 1.88 | Easy |
| 6 | 9 / 26 / 25 | 2.27 | Hard |

Hover/focus/tap copy names the active band and says that the label describes
the composition of the package, not a guaranteed score for a particular user.
For example:

> Medium: indeks kesulitan paket 1,90–2,19 berdasarkan komposisi 60 soal. Label
> ini tidak memprediksi skor setiap peserta.

### 2.4 AI-model information

`ai_model` remains the short product label. Each package manifest and immutable
release adds a required `ai_company` (the company that develops/owns the model)
and `ai_model_description` (1–300 characters) so an unknown future model does
not require a frontend deployment or a hard-coded lookup.

The initial ownership mapping is:

| Model | AI company |
|-------|------------|
| Opus 5 | Anthropic |
| Fable-5 | Anthropic |
| 5.6 Sol | OpenAI |

Primary references: [Anthropic Claude model overview](https://platform.claude.com/docs/en/about-claude/models/overview),
[Anthropic's Fable 5 announcement](https://www.anthropic.com/news/claude-fable-5-mythos-5),
and [OpenAI's GPT-5.6 Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol).

The help surface visibly says **Dikembangkan oleh <company>**, followed by a
short factual model description and this common disclaimer:

> Label model bukan jaminan tingkat kesulitan; soal tetap divalidasi dan
> ditinjau sebelum dipublikasikan.

A capability or company claim may be changed only when the manifest has a
maintained authoritative source; the package card itself does not make
comparative quality claims.

## 3. Requirements

### 3.1 Constraints

| ID | Requirement |
|----|-------------|
| C-20 | Public score aggregates include only attempts satisfying §2.1. The eligibility decision is server-derived at the exactly-once full-attempt completion transition and cannot be supplied by the browser. |
| C-21 | A low score with sufficient answer coverage remains in the sample. Eligibility cannot depend on correctness, score, model, package release, elapsed time, or another user's data. |
| C-22 | Median remains exact after NF-10 deletes attempts. Retention never decrements the eligible counter, eligible score sum, or histogram. |
| C-23 | Package difficulty is derived from the current release's 60 immutable question revisions using §2.3; client code cannot override it. |
| C-24 | Statistics, difficulty help, and AI help expose aggregate/package metadata only. No per-user result, user identifier, attempt identifier, or answer detail is added to the catalogue response. |

### 3.2 Frontend

| ID | Requirement |
|----|-------------|
| FE-31 | Remove the always-visible `.package-stats` block. Add a statistics icon button at the top-right of each package card with `aria-label="Lihat statistik <judul paket>"`, `aria-expanded`, and `aria-controls`. The button does not compete visually with **Mulai Try Out**. |
| FE-32 | Clicking or tapping the icon opens an anchored popover containing the four values in §2.2, the eligibility explanation, all-version qualifier, and relevant coverage dates. Only one card popover is open at a time; outside click, `Escape`, or the trigger closes it and focus returns to the trigger after `Escape`. |
| FE-33 | The popover is keyboard navigable, remains inside the viewport at the 768 px minimum width, does not alter card height while closed, and uses an inline SVG statistics icon so no icon dependency is added. |
| FE-34 | The difficulty chip opens the §2.3 explanation on pointer hover, keyboard focus, or tap. The trigger retains visible text (`Easy`, `Medium`, or `Hard`), uses `aria-describedby`, and does not rely on colour or a native `title`. |
| FE-35 | The AI chip opens `ai_company` and `ai_model_description` on pointer hover, keyboard focus, or tap. Its visible label remains `AI: <model>` and the help begins **Dikembangkan oleh <company>**. Model information is descriptive attribution, not an endorsement or accuracy guarantee. |
| FE-36 | `Package` and mock catalogue types add `statistics_sample_total`, `median_score`, `score_statistics_coverage_started_at`, `ai_company`, and `ai_model_description`; `mean_score` is redefined to use the eligible sample. Number/date formatting remains `id-ID`/`Asia/Jakarta`. |
| FE-37 | Mock mode applies the same eligibility formula, exactly-once counters, histogram/median semantics, popovers, and accessible help behavior as Supabase mode. Existing v3 mock local storage upgrades without treating its historical aggregate as v3.1-eligible data. |

Target card hierarchy:

```text
┌──────────────────────────────────────────────────────┐
│ TBS LPDP Try Out — Paket N            [statistics]  │
│ [Difficulty] [AI: model] [Versi …]                   │
│ description                                          │
│ subtests                                             │
│ total                                                │
│                                                      │
│ [                 Mulai Try Out                  ]   │
└──────────────────────────────────────────────────────┘
```

### 3.3 Question pipeline

| ID | Requirement |
|----|-------------|
| QG-16 | Every package manifest adds a non-empty `ai_company` of at most 100 characters and `ai_model_description` of at most 300 characters. Both are included in the package release canonical hash and immutable release metadata. |
| QG-17 | `validate_bank.py` calculates the §2.3 difficulty index from all 60 question files and rejects a manifest whose `difficulty` does not match the calculated band. `publish_package_release` repeats this validation server-side before publication. |
| QG-18 | The question generator/reviewer assigns each per-question difficulty tag using the qualitative rubric in §2.3. The package band is calculated after generation; it is not achieved by relabelling questions without changing their actual difficulty. |

### 3.4 Backend

| ID | Requirement |
|----|-------------|
| BE-38 | `package_statistics` adds `statistics_sample_total`, `statistics_score_sum`, and `score_statistics_coverage_started_at`. Existing `attempts_completed_total` remains the all-completion count; existing historical `score_sum` may remain private for compatibility but no longer powers public mean. |
| BE-39 | `package_score_histogram(package_id, score, attempt_count)` stores at most 61 non-zero buckets per package. `score` is constrained to 0–300 and divisible by 5; counts are non-negative. RLS is enabled with no client table policy. |
| BE-40 | When `_grade_section` performs the guarded final `active -> finished` attempt update, it always increments the completion count. In the same transaction it computes §2.1; only an eligible attempt increments sample count/sum and its histogram bucket. Concurrent/idempotent finish calls contribute at most once. |
| BE-41 | `get_package_catalog()` returns completion count, eligible sample count, eligible mean, exact median, both coverage dates, `ai_company`, and `ai_model_description` in its existing single response. It returns no raw sum, histogram, or eligibility details for an individual attempt. |
| BE-42 | Median is selected from cumulative histogram counts. Odd samples use rank `(n + 1) / 2`; even samples average ranks `n / 2` and `n / 2 + 1`. The query scans at most 61 buckets per package and returns `null` for an empty sample. |
| BE-43 | The migration initially starts the eligible sample at its own transaction timestamp and does not reinterpret the old all-completion score sum. A separate operator backfill may reconstruct pre-boundary eligibility only from retained answer detail and only when retained finished-row counts exactly match every durable package completion count. If retention has removed even one completion, the operation fails closed. |
| BE-44 | `package_releases` and package publication payloads add immutable `ai_company` and `ai_model_description`. The publisher validates their lengths and verifies that the supplied package difficulty matches the revisions' server-calculated index. |
| BE-45 | `backfill_v3_1_retained_statistics()` serializes on one advisory lock, locks aggregate tables in the normal completion-update order, validates histogram/sample/sum invariants, adds only `finished_at < score_statistics_coverage_started_at` eligible attempts, moves the score boundary to the earliest classified completion, and writes one immutable aggregate-only audit marker. Repeated calls return `already_applied` without changing data. |

### 3.5 Non-functional

| ID | Requirement |
|----|-------------|
| NF-23 | Opening metadata/statistics help performs no network request. All values arrive in the catalogue RPC, preserving FE-22 and avoiding N+1 queries. |
| NF-24 | Statistics maintenance is O(1) per completed attempt. Catalogue median work is bounded by 61 score buckets per package, independent of retained attempt count. |
| NF-25 | Help surfaces meet keyboard and touch requirements in addition to the requested hover behavior; information never exists only in hover state. |
| NF-26 | The migration is re-applicable, preserves v3 counts/releases, and initialises the new score-statistics boundary once. Reapplying it cannot reset or double-count v3.1 samples. |
| NF-27 | Historical backfill is optional and O(retained attempt detail), never part of catalogue loading or routine grading. It exposes no user/attempt identifiers and refuses partial reconstruction after retention. |

## 4. Data and API plan

The migration remains in `supabase/schema_v3.sql` while v3.1 is unreleased; the
fresh-project apply order does not gain another SQL file. A live project applies
the revised v3 file after a backup, then reapplies v4 because v4 owns the final
maintenance RPC/grants:

```text
schema.sql -> schema_v2_reports.sql -> revised schema_v3.sql
           -> schema_v4_maintenance_mode.sql -> maintenance.sql
```

Conceptual additions:

```sql
alter table public.package_statistics
  add column statistics_sample_total bigint not null default 0,
  add column statistics_score_sum bigint not null default 0,
  add column score_statistics_coverage_started_at timestamptz;

create table public.package_score_histogram (
  package_id    integer not null references public.packages(id),
  score         smallint not null check (score between 0 and 300 and score % 5 = 0),
  attempt_count bigint not null check (attempt_count >= 0),
  primary key (package_id, score)
);

alter table public.package_releases
  add column ai_company text,
  add column ai_model_description text;
```

The migration sets required values and constraints after guarded backfill of
release descriptions. Exact idempotent SQL belongs in the implementation, not
in this planning sketch.

### 4.1 Optional retained-attempt backfill

The automatic migration deliberately creates an empty qualified sample because
the old `score_sum` cannot supply a median or the answer-coverage gate. While
the seven-day detail is still present, the operator may apply:

```text
revised schema_v3.sql -> schema_v4_maintenance_mode.sql
                      -> backfill_v3_1_statistics.sql
```

The script first proves, package by package, that retained `finished` rows equal
the durable `attempts_completed_total`. This makes the current database a
complete reconstruction source, rather than merely a surviving retention
window. It then classifies only attempts before the original v3.1 boundary,
adds qualified counts/sums/histogram buckets, moves the displayed boundary to
the earliest classified completion, and records an immutable audit summary.

If those counts do not match, no supported approximation exists: the old mean
could be recovered from `score_sum`, but the qualified mean and exact median
cannot. The script therefore raises an exception and leaves every aggregate
unchanged.

Catalogue shape:

```ts
interface PackageCatalogItem extends Package {
  completed_attempts_total: number
  statistics_sample_total: number
  mean_score: number | null
  median_score: number | null
  statistics_coverage_started_at: string
  score_statistics_coverage_started_at: string
  ai_company: string
  ai_model_description: string
}
```

## 5. Implementation sequence

1. Extend manifests, canonical package hashing, validation, publication payload,
   release schema, and seed descriptions.
2. Add qualified-stat columns, histogram, eligibility calculation, exact-once
   updates, median helper, catalogue fields, RLS, and grants.
3. Extend SQL integration tests for completion versus eligibility, odd/even
   median, concurrency, migration boundaries, and retention invariance.
4. Extend TypeScript and mock storage/statistics behavior.
5. Build reusable accessible help/popover primitives; replace the visible
   statistics block and wire difficulty/AI help.
6. Run whole-bank validation, SQL tests, mock-mode manual accessibility checks,
   and the production frontend build.

## 6. Acceptance criteria

| # | Check | Expected |
|---|-------|----------|
| A-1 | Load a package card without interaction | No attempt count, mean, or median is visible; a labelled statistics icon is present at the top right |
| A-2 | Open statistics by mouse, keyboard, and touch | Same popover opens with completion count, sample count, mean, median, eligibility rule, all-version qualifier, and coverage date |
| A-3 | Press `Escape`, click outside, and open another card's statistics | Popover closes correctly; focus returns after `Escape`; at most one remains open |
| A-4 | Start and abandon a package before all three subtests finish | Completion count and statistical sample do not increment |
| A-5 | Finish all subtests with only 47 answers | Completion count increments; sample count, sum, histogram, mean, and median do not |
| A-6 | Finish with 48 answers but fewer than the per-subtest floor in one subtest | Completion count increments; statistical aggregates do not |
| A-7 | Finish with sufficient coverage and a score of 0 | Both completion and sample counts increment; the zero-score histogram bucket increments |
| A-8 | Finish the same attempt twice/concurrently | Every applicable count, sum, and bucket increments exactly once |
| A-9 | Eligible scores are 100, 150, 200 | Median is 150; mean is 150 |
| A-10 | Add eligible score 250 | Median is 175; mean is 175 |
| A-11 | Delete all contributing attempt rows through retention | Public completion/sample counts, mean, median, and histogram-derived values remain unchanged |
| A-12 | Package has completions but zero v3.1-eligible samples | Popover shows the completion count and sample `0`; mean and median both show **Belum ada hasil** |
| A-13 | Hover/focus/tap each difficulty chip | Band rule and non-prediction disclaimer appear; the same information is accessible without hover |
| A-14 | Hover/focus/tap each AI chip | The release's model description appears; no comparison or guarantee is shown |
| A-15 | Change question difficulty so a manifest label no longer matches §2.3 | Local validator and publication RPC both reject the package |
| A-16 | Inspect catalogue network traffic | One catalogue request only; opening any help surface adds zero requests |
| A-17 | Run `python3 questions/generator/validate_bank.py` and `cd web && npm run build` | Both exit 0 |
| A-18 | Run the retained-statistics backfill twice while all completions are retained | First run reconstructs the qualified sample and exact histogram; second returns `already_applied`; counters, sums, median, and audit row remain unchanged |
| A-19 | Remove one retained finished row without adjusting the durable completion counter, then run the backfill | It aborts before mutation because complete historical reconstruction can no longer be proven |

## 7. Deliverables

| File | Planned change |
|------|----------------|
| `docs/TECHNICAL_REQUIREMENTS_V3_1.md` | This improvement plan |
| `questions/bank/1..6/package.json` | Add `ai_company` and `ai_model_description` |
| `questions/generator/validate_bank.py` | Validate model description and calculated package difficulty |
| `questions/generator/push_to_supabase.py` | Hash/publish model description and deterministic difficulty |
| `supabase/schema_v3.sql` | Eligible aggregates, score histogram, median, release description, catalogue response, RLS/grants |
| `supabase/backfill_v3_1_statistics.sql` | Optional, audited, exactly-once reconstruction from complete retained detail |
| `supabase/tests/v3.sql` | Eligibility, histogram, median, idempotency, migration, and retention checks |
| `web/src/lib/types.ts` | New catalogue fields |
| `web/src/lib/mockApi.ts` | Eligibility, histogram, median, and local-state upgrade |
| `web/src/pages/HomePage.tsx` | Statistics trigger/popover and metadata help wiring |
| `web/src/components/PackageStatisticsPopover.tsx` | Accessible aggregate statistics popover |
| `web/src/components/InfoTooltip.tsx` | Hover/focus/tap help shared by difficulty and AI chips |
| `web/src/styles.css` | Top-right action and responsive/focus/overlay presentation |

## 8. Implementation status

All v3.1 deliverables above are implemented in the repository. Local verification
on 2026-08-11–12 covered:

- all 360 bank questions and the six calculated package difficulty bands;
- dry-run hashing plus live publication of all six packages to local Supabase,
  including company/description metadata and server-side difficulty validation;
- unchanged republish idempotency after reapplying the v3/v4 schemas;
- SQL integration assertions for low coverage, the per-subtest floor, a valid
  zero score, exactly-once completion, histogram RLS, odd/even mean and median,
  deletion-safe aggregates, and digest regression;
- TypeScript plus production Vite build;
- mock-mode browser checks at the normal viewport and 768 px: hidden-by-default
  statistics, single open popover, outside/Escape dismissal, focus return,
  difficulty/model help, company attribution, viewport containment, and an
  empty browser console;
- the retained-statistics backfill's completeness guard, qualified zero-score
  restoration, exact histogram/median, immutable private audit row, successful
  first run, and no-op `already_applied` second run.

Production backfill remains an operator step. Reapply the revised v3 schema and
v4 final definitions, then run `backfill_v3_1_statistics.sql` as described in
§4.1. Package releases do not need to be republished for this aggregate-only
operation.
