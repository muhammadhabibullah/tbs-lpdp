import { createContext, useContext } from 'react'
import type { MaintenancePhase, MaintenanceStatus } from '../lib/types'

export interface MaintenanceContextValue {
  status: MaintenanceStatus | null
  phase: MaintenancePhase
  warningDismissed: boolean
  refreshing: boolean
  dismissWarning(): void
  refresh(): void
}

export const MaintenanceContext = createContext<MaintenanceContextValue>({
  status: null,
  phase: 'open',
  warningDismissed: false,
  refreshing: false,
  dismissWarning: () => undefined,
  refresh: () => undefined,
})

export function useMaintenance(): MaintenanceContextValue {
  return useContext(MaintenanceContext)
}
