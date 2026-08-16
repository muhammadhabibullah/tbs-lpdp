# Technical Requirements v2 — Question Feedback (Laporkan Soal)

| | |
|---|---|
| Status | v2.0 — implemented (see §14 for what is verified and what still needs a live Supabase) |
| Date | 2026-08-10 |
| Extends | [`TECHNICAL_REQUIREMENTS.md`](TECHNICAL_REQUIREMENTS.md) (v1.0) — everything there still applies |
| Scope | One feature: users report a defective question from the **Pembahasan** (review) screen; reports are stored in Supabase |
| Stack | Unchanged — GitHub Pages (frontend) + Supabase (Postgres + RLS + RPC) |

## 1. Purpose

v1 ships a working try-out and a per-question **Pembahasan** page with the key and five explanations. Questions are LLM-generated; some will be wrong (bad key, ambiguous stem, typo, explanation that contradicts the key). Today a user who spots one has nowhere to say so, and we have no signal about which bank items to fix.

v2 adds a report button on every question in Pembahasan. A report is **captured and stored, nothing more** — no triage UI, no notifications, no automated bank changes. The deliverable of this stage is a trustworthy, queryable `question_reports` table plus the UI that fills it. The planned daily operator digest and immutable report/question revisions are specified separately in [`TECHNICAL_REQUIREMENTS_V3.md`](TECHNICAL_REQUIREMENTS_V3.md).

### 1.1 Why the Pembahasan page only

Reporting is deliberately **not** available during an active section:

- The report dialog names failure modes ("kunci jawaban salah") that would be a hint mid-exam.
- A report RPC callable during an attempt is an enumeration surface over questions the user has not yet earned the right to see (v1 C-4/BE-5 exists precisely to prevent this).
- A user cannot meaningfully judge a question before seeing the key and explanation.

So the server gate for reporting is exactly the v1 review gate: **the section containing the question must be finished by that user**.

### 1.2 Out of scope for v2

Moderation/triage UI, report dashboards, statuses driven by anyone but the developer's own SQL, email or webhook notifications, public report counts, auto-hiding reported questions, editing the bank from reports, user identity/contact collection, and voting/upvoting on existing reports. Stage 1 stores reports; acting on them is manual (§9) and a later stage.

## 2. Requirement ID convention

v2 **continues v1's ID space** — `FE-11…`, `BE-8…`, `C-6…`, `NF-6…` — so an ID quoted in an issue or commit is unambiguous across both documents. No v1 ID is renumbered or retired. Where v2 modifies a v1 requirement, the v1 ID is cited explicitly (only `get_review` / BE-5 is touched, additively).

## 3. Constraints (additions to v1 §3)

| ID | Constraint |
|----|-----------|
| C-6 | A report is user-supplied free text. It is stored raw, never rendered as HTML, never shown to any user other than its author, and never echoed into another user's review payload. |
| C-7 | The report endpoint must not become an answer-key oracle: it returns nothing derived from `answer_keys`, and its success/failure behaviour is identical regardless of whether the reported question's key is right or wrong. This is C-4 applied to the new surface. |
| C-8 | Reports reference questions by the stable `questions.id` from v1 QG-2 (`<package>-<subtest>-<NNN>`). `push_to_supabase.py` only upserts and never deletes, so re-pushing an edited bank preserves existing reports — which is why a report must record *which version* of the question it was filed against (BE-9). |

## 4. Functional Requirements — Frontend (FE)

Entry point is `web/src/pages/ReviewPage.tsx`, in the `Pembahasan` card, on each `<article className="review-question">`.

| ID | Requirement |
|----|-------------|
| FE-11 | **Report affordance**: every question card in Pembahasan carries a low-emphasis **Laporkan soal** button (ghost/link style, in the card header row next to the tags, or at the card footer — it must not compete with the explanation content). It is the only entry point to reporting; no report control appears anywhere in the exam flow (§1.1). |
| FE-12 | **Report dialog** (reuse `components/Modal.tsx`, new `components/LaporSoal.tsx`): title "Laporkan Soal nomor N", a required single-choice reason list (§4.1), an optional free-text `Catatan` textarea (max 1000 chars, live character counter), and **Kirim laporan** / **Batal** buttons. The comment becomes **required** when reason = `other`. Submit is disabled until the form is valid. |
| FE-13 | **Submission feedback**: on success the dialog closes and the card's button becomes a non-interactive-looking **✓ Sudah dilaporkan** chip with **Ubah** and **Batalkan laporan** actions. On failure the dialog stays open, keeps everything the user typed, and shows the error inline (Bahasa Indonesia); the request retries per NF-2 (`withRetry`) before surfacing anything. |
| FE-14 | **Existing reports are visible on load**: `get_review` returns the caller's own report per question (BE-11), so a reloaded/revisited Pembahasan renders the reported state without an extra round trip. Re-opening the dialog for an already-reported question pre-fills the previous reason and comment (an edit, not a second report — BE-10). |
| FE-15 | **Withdraw**: **Batalkan laporan** asks for confirmation in the same modal pattern, then deletes the report (BE-12) and restores the plain **Laporkan soal** button. |
| FE-16 | **Filter chip**: the existing review filter row gains a **Dilaporkan (n)** filter alongside `Semua soal / Jawaban salah / Tidak dijawab / Ditandai ragu-ragu`, showing only questions the user has reported in the active subtest. |
| FE-17 | **Mock parity**: `web/src/lib/mockApi.ts` implements the same `ExamApi` methods against `localStorage` (including the one-report-per-question rule and the reported state in `getReview`), so the whole flow is developable with `VITE_USE_MOCK=true` and no Supabase. |
| FE-18 | All new copy is Bahasa Indonesia; reason codes, types, and comments in the source stay English (project convention). The dialog is keyboard-usable: focus moves into it on open, `Esc` cancels, and the reason list is a real radio group with labels. |

**Offline app delta (v6 AP-9):** in the offline Tauri app the stored-report flow above is replaced by an email-only one: the dialog's primary action is *Kirim via Email* (the prefilled `mailto:` draft) instead of **Kirim laporan**, no report state is persisted on the device, and consequently the reported-state controls (FE-13/FE-15) and the *Dilaporkan* filter (FE-16) are not shown. FE-11, FE-12, and FE-18 apply unchanged.

### 4.1 Reason codes and UI labels

Codes are stable identifiers (English, stored in DB); labels are what the user sees.

| Code | Label (Bahasa Indonesia) | Meaning |
|------|--------------------------|---------|
| `wrong_key` | Kunci jawaban salah | The marked correct option is not correct |
| `ambiguous` | Soal ambigu / lebih dari satu jawaban benar | Zero or multiple defensible answers |
| `bad_explanation` | Pembahasan keliru atau tidak sesuai | Explanation contradicts the key or is nonsense |
| `typo` | Salah ketik atau kalimat rancu | Wording/typo problem that does not change the key |
| `image_issue` | Gambar tidak tampil atau tidak sesuai | Missing/incorrect image |
| `other` | Lainnya | Anything else — comment required |

These codes are mirrored by a `check` constraint (BE-8) and by the `ReportReason` union in `web/src/lib/types.ts`. Adding a code later means: SQL constraint + TS union + label map, in that order.

## 5. Functional Requirements — Backend (BE)

| ID | Requirement |
|----|-------------|
| BE-8 | **Storage**: new table `public.question_reports` (§6). One row per `(user_id, question_id)`. Reason constrained to §4.1; comment ≤ 1000 chars; status enum defaults to `open` and is only ever changed by the developer via `service_role`. |
| BE-9 | **Version snapshot**: the RPC records `content_hash` — `md5(question_text ‖ passage ‖ each option A–E in key order)` of the question **as it exists at report time**, computed server-side by `_question_content_hash()`. Because the bank is re-pushable in place (C-8), this is how triage later knows whether a report still applies to the current text. `md5()` is core Postgres — no extension needed, and no answer-key material enters the hash. |
| BE-10 | **`report_question` RPC** (`security definer`): validates that the caller owns a **finished** section containing the question (same gate as `get_review`, C-7), validates reason/comment, then **upserts** on `(user_id, question_id)` — a second submission edits the existing report and bumps `updated_at` rather than creating a duplicate. Returns the caller's own report row only. |
| BE-11 | **Review integration**: `get_review` (v1 BE-5 / §7) gains a per-question `my_report` field — `null` or `{reason, comment, status, created_at, updated_at}` — scoped to `auth.uid()`. This is additive; every existing field and the answer-key gating are unchanged. |
| BE-12 | **`delete_question_report` RPC**: deletes the caller's own report for a question. Idempotent — deleting a nonexistent report succeeds silently (so a double-click cannot produce an error). |
| BE-13 | **Rate limit**: at most **20** report writes per user per rolling hour, enforced inside `report_question`, raising `P0005`. Combined with the `(user_id, question_id)` unique key this bounds abuse without blocking a genuine "this whole subtest is broken" session (60 questions ÷ 20/h is the deliberate friction point; raise the constant if it proves wrong in practice). |
| BE-14 | **RLS**: `question_reports` has RLS enabled with a select-own policy (`user_id = auth.uid()`) and **no** insert/update/delete policy — all writes go through the RPCs (v1 BE-6 convention). No client can read another user's report, count reports on a question, or learn that a question has been reported at all. |
| BE-15 | **Grants**: `execute` on the two new functions granted to `authenticated` only, added to the existing grant block; `anon` keeps zero access. |

### 5.1 Error codes

Continues v1's `P000x` scheme (v1 uses `P0002` not-found, `P0003` section finished, `P0004` deadline passed):

| Code | Meaning | Frontend copy |
|------|---------|---------------|
| `P0002` | Question not found, or not in a section this user has finished | "Soal ini belum bisa dilaporkan. Selesaikan mata ujinya terlebih dahulu." |
| `P0005` | Rate limit exceeded | "Terlalu banyak laporan dalam satu jam. Coba lagi nanti." |
| `P0006` | Invalid input (unknown reason, comment too long, `other` without comment) | "Periksa kembali isian laporan Anda." |

`P0005` and `P0006` are terminal for `withRetry` — add them to the no-retry list in `web/src/lib/api.ts` alongside `P0002`/`P0003`/`P0004`.

## 6. Data Model (addition to v1 §6)

Lives in its own script, [`supabase/schema_v2_reports.sql`](../supabase/schema_v2_reports.sql), so a
project already running v1 is upgraded by executing **one new file** instead of re-running the whole
schema. Provisioning order is `schema.sql` → `schema_v2_reports.sql`; both are idempotent, and v1
NF-5 (a fresh project is reproducible from git) still holds with two files instead of one. See §6.1
for the one coupling between them.

```sql
create table if not exists public.question_reports (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references auth.users (id)      on delete cascade,
  question_id        text not null references public.questions (id) on delete cascade,
  attempt_id         uuid          references public.attempts (id)  on delete set null,
  section_attempt_id uuid          references public.section_attempts (id) on delete set null,
  reason             text not null check (reason in
                       ('wrong_key','ambiguous','bad_explanation','typo','image_issue','other')),
  comment            text not null default '' check (char_length(comment) <= 1000),
  selected_option    char(1)       check (selected_option in ('A','B','C','D','E')),
  content_hash       text not null,                    -- BE-9: question text+options at report time
  status             text not null default 'open' check (status in
                       ('open','reviewing','accepted','rejected','duplicate')),
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (user_id, question_id)                        -- BE-10: one report per user per question
);

create index if not exists question_reports_question_idx
  on public.question_reports (question_id, created_at desc);   -- triage: "worst questions first"
create index if not exists question_reports_user_recent_idx
  on public.question_reports (user_id, updated_at desc);       -- BE-13: rate-limit window scan
```

- `selected_option` is a snapshot of what the user answered — a report from someone who answered the option they claim is correct is a stronger signal than one from a blank.
- `attempt_id` / `section_attempt_id` are `on delete set null`: the report outlives the attempt it came from.
- Row size is well under 1.5 KB worst case; even a few thousand reports are noise against the Supabase free-tier 500 MB budget (NF-1).

### 6.1 The one coupling between the two files

`get_review` is defined in `schema.sql` and **re-created** by `schema_v2_reports.sql` with the extra
`my_report` field (BE-11). Everything else in v2 is purely additive. Two consequences, both called
out in the file headers:

1. **Re-applying `schema.sql` reverts `my_report`** and, via its blanket
   `revoke all on all functions in schema public`, also strips `execute` on the two report RPCs.
2. **Therefore: any time `schema.sql` is re-applied, re-apply `schema_v2_reports.sql` after it.**
   Running it twice is harmless.

If `get_review` in `schema.sql` is ever edited, the copy in the v2 file must be updated to match —
it is a verbatim copy plus `my_report`.

## 7. API Surface (addition to v1 §7)

| Function | Args | Returns | Notes |
|----------|------|---------|-------|
| `report_question` | `p_question_id text, p_reason text, p_comment text default '', p_attempt_id uuid default null` | the caller's report row (json) | Gate: caller has a **finished** section containing the question. Upsert on `(user_id, question_id)`. Computes `content_hash`, snapshots `selected_option` from `answers`. Rate-limited (BE-13). Never touches `answer_keys`. |
| `delete_question_report` | `p_question_id text` | `{ deleted: boolean }` | Idempotent; own rows only. |
| `get_review` *(modified)* | `p_attempt_id uuid` | unchanged **+** `my_report` per question | Additive only (BE-11); v1 clients keep working. |

Sketch of the gate every write shares — it is the same predicate `get_review` uses, which is what makes C-7 hold by construction:

```sql
-- caller must own a FINISHED section that contains this question
exists (
  select 1
    from public.section_attempts sa
    join public.attempts a  on a.id = sa.attempt_id
    join public.questions  q on q.subtest_id = sa.subtest_id
   where a.user_id  = (select auth.uid())
     and sa.status  = 'finished'
     and q.id       = p_question_id
)
```

Client wiring:

- `web/src/lib/types.ts` — add `ReportReason`, `QuestionReport`, `my_report: QuestionReport | null` on `ReviewQuestion`, and `reportQuestion` / `deleteQuestionReport` on the `ExamApi` interface.
- `web/src/lib/supabaseApi.ts` — two `rpc(...)` calls following the existing pattern (`await requireSession()` first).
- `web/src/lib/mockApi.ts` — same two methods over the existing `localStorage` state (FE-17).
- `web/src/lib/api.ts` — delegate both, and extend the terminal-error list (§5.1).

## 8. Security & Integrity

- **No key leakage** (C-7): `report_question` never selects from `answer_keys`; it validates only ownership + section-finished + input shape. A user who reports a question learns nothing they could not already see on the Pembahasan page.
- **No cross-user visibility** (C-6/BE-14): select-own RLS, no aggregate counts exposed, no report data in any payload other than the reporter's own `get_review`.
- **Free text is untrusted**: length-capped at the DB, stored raw (never sanitised into something lossy), and rendered in React as text — never `dangerouslySetInnerHTML`. Since it is only ever redisplayed to its own author, the XSS surface is nil today; the rule exists so a future triage UI inherits it.
- **Identity**: reporters are v1 anonymous users. There is no email, name, or contact field — we cannot follow up with a reporter, and that is intentional for this stage. A user who clears browser storage loses the anonymous identity and therefore the ability to edit or withdraw their earlier reports; the reports themselves persist.
- **Abuse bounds**: unique `(user_id, question_id)` + 20/hour (BE-13). Nothing in v2 lets a report affect what any other user sees, so the worst case of a spam campaign is junk rows the developer ignores.

## 9. Reading the reports (manual, stage 1)

No tooling is in scope. The developer reads reports with `service_role` in the Supabase SQL editor
(the first query below is also kept as a comment at the foot of `schema_v2_reports.sql`).
`content_hash` is compared against the live question so stale reports are visible as such:

```sql
select r.question_id,
       q.qtype,
       r.reason,
       r.status,
       r.comment,
       r.selected_option,
       r.content_hash <> public._question_content_hash(q.id)
         as question_changed_since_report,
       r.created_at
  from public.question_reports r
  join public.questions q on q.id = r.question_id
 where r.status = 'open'
 order by r.question_id, r.created_at desc;
```

Aggregate view for prioritising bank fixes:

```sql
select question_id, count(*) as reports,
       count(*) filter (where reason in ('wrong_key','ambiguous')) as severe
  from public.question_reports
 where status = 'open'
 group by question_id
 order by severe desc, reports desc;
```

When a bank question is actually fixed, the loop closes outside this system: edit `questions/bank/...`, re-run `validate_bank.py`, re-run the reviewer agent, `push_to_supabase.py --package N`, then set the relevant reports to `accepted` (or `rejected`) by hand.

## 10. Non-Functional Requirements (additions to v1 §9)

| ID | Requirement |
|----|-------------|
| NF-6 | Report writes are off the critical path: the Pembahasan page renders and stays fully usable while a report is in flight, and a failed report never discards the user's typed comment (FE-13). |
| NF-7 | Reporting adds **zero** extra round trips to the review page load — the reported state rides along with `get_review` (BE-11). |
| NF-8 | Storage growth stays negligible on the free tier (NF-1): capped comment length, one row per user per question, and no event-log rows for reports. |
| NF-9 | Upgrading a live v1 project means executing exactly one new file, `schema_v2_reports.sql`, and touching nothing that already works. It is re-appliable and loses no data — `create table if not exists`, `create index if not exists`, `create or replace function`, `drop policy if exists` before `create policy`. (`schema.sql` was also made re-appliable — its policy block now drops before creating, since Postgres has no `create policy if not exists` — but v2 does not require re-running it.) |

## 11. Acceptance Criteria

| # | Check | Expected |
|---|-------|----------|
| A-1 | Report a question from Pembahasan with reason `wrong_key` | Row in `question_reports`; card shows "Sudah dilaporkan" after reload |
| A-2 | Report the same question again with a different reason | Still exactly one row; `reason` updated, `updated_at` bumped, `created_at` unchanged |
| A-3 | Withdraw the report, then withdraw again | Row gone; second call succeeds with `{deleted:false}`, no error shown |
| A-4 | Call `report_question` for a question in an **unfinished/unstarted** section | `P0002`; no row written |
| A-5 | Call `report_question` for a question from **another user's** attempt | `P0002`; no row written |
| A-6 | `select * from question_reports` as another authenticated user | Zero rows (RLS) |
| A-7 | Direct `insert`/`update`/`delete` on `question_reports` from the client | Rejected — no policy exists |
| A-8 | Reason `other` with an empty comment; comment > 1000 chars; unknown reason code | `P0006` in all three cases |
| A-9 | 21 report writes within an hour | 21st raises `P0005`; UI shows the rate-limit copy and does not retry |
| A-10 | `get_review` response shape | All v1 fields intact, `my_report` present per question, **no** report data from other users |
| A-11 | Edit the question text in the bank, re-push, then compare | The pre-existing report survives and `question_changed_since_report` is `true` (§9) |
| A-12 | Full flow with `VITE_USE_MOCK=true` | Report / edit / withdraw / filter all work without Supabase (FE-17) |
| A-13 | `cd web && npm run build` | Typecheck + build pass |
| A-14 | Exam flow (v1 FE-3…FE-7) | No report control visible anywhere during an active section (§1.1) |

## 12. Deliverables

| File | Change |
|------|--------|
| `supabase/schema_v2_reports.sql` | **New**: `question_reports` table + indexes, RLS policy, `_question_content_hash`, `report_question`, `delete_question_report`, `get_review` re-created with `my_report`, grants |
| `supabase/schema.sql` | Unchanged in behaviour; policy block made idempotent, header/`get_review` comments point at the v2 file (§6.1) |
| `web/src/lib/types.ts` | `ReportReason`, `QuestionReport`, `ReviewQuestion.my_report`, two `ExamApi` methods |
| `web/src/lib/supabaseApi.ts` | Two RPC wrappers |
| `web/src/lib/mockApi.ts` | localStorage implementation of the same two methods (FE-17) |
| `web/src/lib/api.ts` | Delegation + terminal error codes `P0005`/`P0006` |
| `web/src/components/LaporSoal.tsx` | New report dialog (FE-12) |
| `web/src/pages/ReviewPage.tsx` | Report button, reported state, withdraw, `Dilaporkan` filter (FE-11/13/15/16) |
| `web/src/styles.css` | Styles for the report button, reported chip, dialog |
| `docs/TECHNICAL_REQUIREMENTS_V2.md` | This document |
| `CLAUDE.md` | One line pointing at this document alongside the v1 spec |

Not touched: `questions/schema.json`, the question bank, the generators, `push_to_supabase.py`, `validate_bank.py`, the deploy workflow.

## 13. Milestones

| M | Deliverable | Depends on |
|---|-------------|-----------|
| M7 | Schema: `schema_v2_reports.sql` (table, RLS, both RPCs, `get_review` extension) applied to Supabase | v1 M1 |
| M8 | Mock-mode UI complete: dialog, reported state, withdraw, filter (FE-11…FE-18 against `mockApi`) | M7 (types settled) |
| M9 | Live wiring against Supabase + acceptance run (§11) + docs/CLAUDE.md updated | M7, M8 |

## 14. Implementation status (2026-08-10)

All deliverables in §12 are written. `cd web && npm run build` (typecheck + vite build) passes.

**Verified by running the app** (`VITE_USE_MOCK=true npm run dev`, review page driven in Chrome):

| Check | Result |
|-------|--------|
| A-1 report → stored, chip after reload | pass (report rendered from `get_review`, no refetch) |
| A-2 re-report same question | pass (still one row; reason updated, `created_at` kept, `updated_at` bumped) |
| A-3 withdraw | pass (row gone, card returns to "Laporkan soal", filter count back to 0) |
| A-8 `other` with empty comment | pass (label flips to "(wajib)", submit disabled) |
| A-9 21st report within the hour | pass (`P0005`; dialog stays open with the rate-limit copy, no retry) |
| A-12 whole flow in mock mode | pass, console clean |
| A-13 `npm run build` | pass |
| FE-14 edit prefill | pass (reason + comment pre-filled, button reads "Simpan perubahan") |
| FE-16 `Dilaporkan (n)` filter | pass |

**Not yet verified — needs `schema_v2_reports.sql` applied to a Supabase project:** A-4
(unfinished-section gate), A-5 (another user's attempt), A-6/A-7 (RLS read/write isolation), A-10
(`get_review` shape from the real RPC), A-11 (`content_hash` staleness after a re-push). The SQL has
not been executed anywhere — no local Postgres was available — so treat the first apply as the
syntax check.
A-14 (no report control during an exam section) holds by construction: the only entry point is in
`ReviewPage.tsx`.
