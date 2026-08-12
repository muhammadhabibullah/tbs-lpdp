import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AttemptPage from './pages/AttemptPage'
import HomePage from './pages/HomePage'
import ReviewPage from './pages/ReviewPage'
import MaintenanceGate from './components/MaintenanceGate'
import HumanVerificationGate from './components/HumanVerificationGate'
import RouteMetadata from './components/RouteMetadata'
import { AppUpdateWatcher } from './components/UpdateControls'
import { IS_OFFLINE_APP } from './lib/config'

function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [pathname])

  return null
}

/**
 * AP-9: neither gate has a meaning offline. Maintenance is a property of the
 * shared Supabase project, and the CAPTCHA guards anonymous sign-up — the app
 * has no account at all. Written as a component rather than inline branches so
 * `IS_OFFLINE_APP` folds away and the app bundle keeps no Turnstile code.
 */
function Gates({ children }: { children: ReactNode }) {
  if (IS_OFFLINE_APP) return <>{children}</>
  return (
    <MaintenanceGate>
      <HumanVerificationGate>{children}</HumanVerificationGate>
    </MaintenanceGate>
  )
}

/**
 * HashRouter, deliberately: GitHub Pages has no rewrite rules, so a deep link
 * to /tbs-lpdp/attempt/<id> would 404 on refresh mid-exam (C-3, FE-9). It also
 * makes every route host-agnostic, which is what lets the same build run inside
 * the Tauri webview (AP-1).
 */
export default function App() {
  return (
    <HashRouter>
      <ScrollToTop />
      <RouteMetadata />
      {/* AP-9: only the app has update planes to watch; the web build folds
          this away and never pulls the updater or bank-source modules in. */}
      {IS_OFFLINE_APP ? <AppUpdateWatcher /> : null}
      <Gates>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/attempt/:attemptId" element={<AttemptPage />} />
          <Route path="/attempt/:attemptId/review" element={<ReviewPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Gates>
    </HashRouter>
  )
}
