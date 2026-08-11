import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { MaintenanceContext } from '../contexts/MaintenanceContext'
import { api } from '../lib/api'
import { serverNow } from '../lib/clock'
import {
  maintenancePhase,
  maintenanceScheduleKey,
  nextMaintenanceBoundary,
} from '../lib/maintenance'
import type { MaintenanceStatus } from '../lib/types'
import MaintenancePage from '../pages/MaintenancePage'

const POLL_INTERVAL_MS = 60_000
const PROBE_TIMEOUT_MS = 5_000
const MAX_TIMEOUT_MS = 2_147_000_000
const DISMISSED_PREFIX = 'tbs-lpdp.maintenance.dismissed.'
// Vite hardcodes DEV=false in production builds, so setting the flag in a
// deployment environment can never disable the production maintenance gate.
const DEV_BYPASS_MAINTENANCE =
  import.meta.env.DEV && import.meta.env.VITE_BYPASS_MAINTENANCE === 'true'

function wasDismissed(scheduleKey: string | null): boolean {
  if (!scheduleKey) return false
  try {
    return sessionStorage.getItem(`${DISMISSED_PREFIX}${scheduleKey}`) === 'true'
  } catch {
    return false
  }
}

/**
 * Loads the public schedule before mounting a route. This is intentionally a
 * frontend-only gate: it does not change or protect any exam RPC (v4 scope).
 */
export default function MaintenanceGate({ children }: { children: ReactNode }) {
  if (DEV_BYPASS_MAINTENANCE) return <>{children}</>
  return <EnforcedMaintenanceGate>{children}</EnforcedMaintenanceGate>
}

function EnforcedMaintenanceGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<MaintenanceStatus | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [boundaryTick, setBoundaryTick] = useState(0)
  const [dismissedSchedule, setDismissedSchedule] = useState<string | null>(null)
  const mounted = useRef(true)
  const requestInFlight = useRef(false)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return
    requestInFlight.current = true
    setRefreshing(true)
    let timeout: number | undefined
    try {
      const next = await Promise.race([
        api.getMaintenanceStatus(),
        new Promise<never>((_, reject) => {
          timeout = window.setTimeout(
            () => reject(new Error('maintenance status probe timed out')),
            PROBE_TIMEOUT_MS,
          )
        }),
      ])
      if (mounted.current) setStatus(next)
    } catch {
      // A frontend-only gate cannot safely invent a maintenance window. Keep a
      // previously known schedule; on the first failed probe, fail open.
    } finally {
      if (timeout !== undefined) window.clearTimeout(timeout)
      if (mounted.current) {
        setLoaded(true)
        setRefreshing(false)
      }
      requestInFlight.current = false
    }
  }, [])

  useEffect(() => {
    void refresh()
    const interval = window.setInterval(() => void refresh(), POLL_INTERVAL_MS)
    return () => window.clearInterval(interval)
  }, [refresh])

  const phase = useMemo(() => maintenancePhase(status, serverNow()), [status, boundaryTick])
  const scheduleKey = maintenanceScheduleKey(status)
  const warningDismissed =
    scheduleKey !== null && (dismissedSchedule === scheduleKey || wasDismissed(scheduleKey))

  // Switch at warning/start/end without waiting for the next 60-second probe.
  useEffect(() => {
    const boundary = nextMaintenanceBoundary(status, serverNow())
    if (boundary === null) return
    const delay = Math.min(MAX_TIMEOUT_MS, Math.max(0, boundary - serverNow() + 25))
    const timeout = window.setTimeout(() => setBoundaryTick((value) => value + 1), delay)
    return () => window.clearTimeout(timeout)
  }, [status, boundaryTick])

  const dismissWarning = useCallback(() => {
    if (!scheduleKey) return
    try {
      sessionStorage.setItem(`${DISMISSED_PREFIX}${scheduleKey}`, 'true')
    } catch {
      // The in-memory state still closes it when storage is unavailable.
    }
    setDismissedSchedule(scheduleKey)
  }, [scheduleKey])

  const value = useMemo(
    () => ({
      status,
      phase,
      warningDismissed,
      refreshing,
      dismissWarning,
      refresh: () => void refresh(),
    }),
    [status, phase, warningDismissed, refreshing, dismissWarning, refresh],
  )

  if (!loaded) {
    return (
      <div className="maintenance-loading" role="status">
        Memuat website…
      </div>
    )
  }

  return (
    <MaintenanceContext.Provider value={value}>
      {phase === 'maintenance' ? <MaintenancePage /> : children}
    </MaintenanceContext.Provider>
  )
}
