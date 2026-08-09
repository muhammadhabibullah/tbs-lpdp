import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import AttemptPage from './pages/AttemptPage'
import HomePage from './pages/HomePage'
import ReviewPage from './pages/ReviewPage'

/**
 * HashRouter, deliberately: GitHub Pages has no rewrite rules, so a deep link
 * to /tbs-lpdp/attempt/<id> would 404 on refresh mid-exam (C-3, FE-9).
 */
export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/attempt/:attemptId" element={<AttemptPage />} />
        <Route path="/attempt/:attemptId/review" element={<ReviewPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}
