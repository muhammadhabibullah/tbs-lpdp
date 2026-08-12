---
kind: business_term
name: Business Glossary
category: business_term
scope:
    - '**'
---

### LPDP TBS
- Definition：LPDP Tes Bakat Skolastik — the Indonesian scholarship aptitude test this project simulates as a browser-based practice exam with three timed sections: Penalaran Verbal (23 questions), Penalaran Kuantitatif (25 questions), and Pemecahan Masalah (12 questions).
- Aliases：TBS LPDP、Tes Bakat Skolastik、LPDP try out

### package
- Definition：A complete, immutable try-out release consisting of 60 questions across the three subtests (verbal 23 / kuantitatif 25 / pemecahan_masalah 12), stored under `questions/bank/<id>/` with a `package.json` manifest declaring title, difficulty, ai_model, ai_company, and ai_model_description. Each package is published once to Supabase via `push_to_supabase.py` and cannot be altered after publication.
- Aliases：try-out package、question package

### subtest
- Definition：One of the three exam sections — `verbal`, `kuantitatif`, or `pemecahan_masalah` — each with a fixed number of questions, duration, and passing grade defined per package in the database.
- Aliases：section、penalaran verbal、penalaran kuantitatif、pemecahan masalah

### attempt
- Definition：A single run through one package, composed of three section-attempts (one per subtest). An attempt has an `active` or `finished` status, a start time, optional finish time, and total score; answers and events are recorded per section-attempt.
- Aliases：try-out attempt、exam attempt

### answer_keys
- Definition：The protected table holding the correct option and explanations per question; it has no client-readable RLS policy so clients can never read keys directly — grading always happens server-side via RPCs that join `answers` with `answer_keys`.
- Aliases：kunci jawaban

### capacity guard
- Definition：Free-tier protection mechanism that monitors Supabase database size and estimated live row count via `public.service_capacity`. When limits are exceeded, new attempts are refused with error code `P0007` while allowing existing in-progress exams to continue until completion.
- Aliases：storage guard、full quota state

### offline app
- Definition：The Tauri 2 desktop/Android distribution of the same SPA, built with `--mode app` so that grading logic runs locally and no Supabase credentials are bundled; it reads the question bank from the local filesystem instead of fetching from Supabase.
- Aliases：desktop app、Android app、Tauri app

### Pembahasan
- Definition：The explanation view shown after each section ends; it displays the rationale for every option and supports reporting defective questions directly from the UI without a GitHub account.
- Aliases：explanation page、review page

### mock mode
- Definition：Development mode (`VITE_USE_MOCK=true`) that runs the entire exam flow off the Git question bank with no Supabase connection, enabling local development and testing without a backend project.
- Aliases：mock api、local mode
