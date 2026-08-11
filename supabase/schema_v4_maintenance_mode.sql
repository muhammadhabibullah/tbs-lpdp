-- =============================================================================
-- TBS LPDP Try Out — v4 scheduled frontend maintenance mode
--
-- Apply after the latest application schema. Today that is:
--   schema.sql -> schema_v2_reports.sql -> schema_v4_maintenance_mode.sql
-- When schema_v3.sql is implemented, apply this file after v3 as well.
--
-- Re-running schema.sql revokes every public function grant, including the
-- pre-auth probe below. Re-apply this file after any core schema re-apply.
-- Design: docs/TECHNICAL_REQUIREMENTS_V4.md
-- =============================================================================

-- One operator-managed schedule. Keeping it as data means scheduling,
-- postponing, or cancelling maintenance never requires a frontend redeploy.
create table if not exists public.site_maintenance (
  id         boolean primary key default true check (id), -- singleton row
  enabled    boolean not null default false,
  starts_at  timestamptz,
  ends_at    timestamptz,
  message    text not null default
    'Kami sedang melakukan pemeliharaan terjadwal agar layanan tetap andal.',
  updated_at timestamptz not null default now(),
  check (not enabled or (starts_at is not null and ends_at is not null)),
  check (starts_at is null or ends_at is null or ends_at > starts_at),
  check (char_length(btrim(message)) between 1 and 500)
);

insert into public.site_maintenance (id)
values (true)
on conflict (id) do nothing;

alter table public.site_maintenance enable row level security;

-- The table has no client policy. The RPC returns only the public schedule and
-- server-derived phase; updates stay an operator/service-role action.
revoke all on table public.site_maintenance from anon, authenticated;

create or replace function public.get_maintenance_status()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'enabled', sm.enabled,
    'starts_at', sm.starts_at,
    'ends_at', sm.ends_at,
    'message', sm.message,
    'phase', case
      when not sm.enabled or sm.starts_at is null or sm.ends_at is null then 'open'
      when now() >= sm.starts_at and now() < sm.ends_at then 'maintenance'
      when now() >= sm.starts_at - interval '4 hours' and now() < sm.starts_at then 'warning'
      else 'open'
    end,
    'server_time', now()
  )
  from public.site_maintenance sm
  where sm.id = true;
$$;

revoke all on function public.get_maintenance_status() from public, anon, authenticated;
grant execute on function public.get_maintenance_status() to anon, authenticated;

-- ---------------------------------------------------------------------------
-- Operator examples (run in the Supabase SQL editor; timestamps include zone):
--
-- Schedule a window:
-- update public.site_maintenance
--    set enabled = true,
--        starts_at = '2026-08-15 22:00:00+07',
--        ends_at = '2026-08-16 01:00:00+07',
--        message = 'Maintenance sistem sedang dilakukan.',
--        updated_at = now()
--  where id = true;
--
-- Cancel/disable it without deleting the schedule history:
-- update public.site_maintenance
--    set enabled = false, updated_at = now()
--  where id = true;
-- =============================================================================
