---
kind: external_dependency
name: Supabase (Postgres + Auth + Storage + Edge Functions) — backend for TBS LPDP Try Out
slug: supabase
category: external_dependency
category_hints:
    - vendor_identity
    - sdk_real_api
    - client_constraint
scope:
    - '**'
---

### Identity & role
- Supabase is the hosted Postgres backend for the TBS LPDP Try Out, providing anonymous authentication, Row Level Security policies, RPC functions, storage buckets, and scheduled maintenance jobs.
- Project id is `tbs-lpdp` (`supabase/config.toml`).

### Integration points
- **Web client**: `web/src/lib/supabase.ts` creates a `@supabase/supabase-js` client using `SUPABASE_URL` / `SUPABASE_PUBLIC_KEY` from `lib/config`; the module is dynamically imported so it is never bundled into the offline app build.
- **Publisher**: `questions/generator/push_to_supabase.py` uploads content-addressed images to the `question-images` storage bucket and commits each package release atomically via the `publish_package_release` RPC under `/rest/v1/rpc/...`, authenticated with `SUPABASE_SERVICE_ROLE_KEY` (service-role key passed as both `apikey` header and `Authorization: Bearer ...`).
- **Schema**: base schema in `supabase/schema.sql` plus migrations `schema_v2_reports.sql`, `schema_v3.sql`, `schema_v4_maintenance_mode.sql`, `maintenance.sql`; RLS is enabled on every table and answer keys have no client-readable policy.
- **Edge function**: `supabase/functions/question-report-digest/index.ts` (JWT verification disabled via `verify_jwt = false` in config).

### Durable usage model
- Git is the source of truth for question content; Supabase stores immutable published releases and user attempt data scoped by RLS to the current anonymous user.
- The free-tier capacity guard (`public.service_capacity`) proactively blocks new attempts (`P0007`) when database size or estimated row count exceeds configured limits; existing in-progress attempts are never interrupted.
- Offline desktop/Android builds (Tauri 2) ship the same SPA without Supabase credentials — grading runs locally because the repository is public and contains all answer keys.

### Verify exact API/params against official docs
- Publisher calls `POST /rest/v1/rpc/publish_package_release` and `POST /storage/v1/object/{bucket}/{path}`; confirm headers, error codes, and bucket ACLs against the Supabase REST and Storage APIs.