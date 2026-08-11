import { serverNow } from './clock'
import type { MaintenancePhase, MaintenanceStatus } from './types'

export const MAINTENANCE_WARNING_LEAD_MS = 4 * 60 * 60 * 1000

/** Re-evaluated in the browser so an already-open page changes at each boundary. */
export function maintenancePhase(status: MaintenanceStatus | null, nowMs = serverNow()): MaintenancePhase {
  if (!status?.enabled || !status.starts_at || !status.ends_at) return 'open'

  const startsAt = Date.parse(status.starts_at)
  const endsAt = Date.parse(status.ends_at)
  if (Number.isNaN(startsAt) || Number.isNaN(endsAt) || endsAt <= startsAt) return 'open'

  if (nowMs >= startsAt && nowMs < endsAt) return 'maintenance'
  if (nowMs >= startsAt - MAINTENANCE_WARNING_LEAD_MS && nowMs < startsAt) return 'warning'
  return 'open'
}

/** Next instant at which the current schedule changes its visible phase. */
export function nextMaintenanceBoundary(status: MaintenanceStatus | null, nowMs = serverNow()): number | null {
  if (!status?.enabled || !status.starts_at || !status.ends_at) return null

  const boundaries = [
    Date.parse(status.starts_at) - MAINTENANCE_WARNING_LEAD_MS,
    Date.parse(status.starts_at),
    Date.parse(status.ends_at),
  ]
  return boundaries.find((value) => Number.isFinite(value) && value > nowMs) ?? null
}

export function maintenanceScheduleKey(status: MaintenanceStatus | null): string | null {
  if (!status?.enabled || !status.starts_at || !status.ends_at) return null
  return `${status.starts_at}|${status.ends_at}`
}

export function formatMaintenanceDateTime(iso: string): string {
  return new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(iso))
}
