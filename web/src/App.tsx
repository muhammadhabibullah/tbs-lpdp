import { useEffect } from 'react'
import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AttemptPage from './pages/AttemptPage'
import HomePage from './pages/HomePage'
import ReviewPage from './pages/ReviewPage'
import MaintenanceGate from './components/MaintenanceGate'

function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [pathname])

  return null
}

/**
 * HashRouter, deliberately: GitHub Pages has no rewrite rules, so a deep link
 * to /tbs-lpdp/attempt/<id> would 404 on refresh mid-exam (C-3, FE-9).
 */
export default function App() {
  return (
    <HashRouter>
      <ScrollToTop />
      <MaintenanceGate>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/attempt/:attemptId" element={<AttemptPage />} />
          <Route path="/attempt/:attemptId/review" element={<ReviewPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </MaintenanceGate>
    </HashRouter>
  )
}
