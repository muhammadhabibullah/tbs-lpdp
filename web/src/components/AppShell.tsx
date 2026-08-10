import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import FeedbackFooter from './FeedbackFooter'

/** Blue masthead + light page body, mirroring the PUSMENDIK CBT chrome. */
export default function AppShell({
  children,
  participant,
  /** Suppressed while a section is running: a mailto would send the candidate
      out of the app, and the deadline keeps ticking server-side. */
  hideFeedback = false,
}: {
  children: ReactNode
  participant?: string
  hideFeedback?: boolean
}) {
  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <Link to="/" className="brand">
            <span className="brand-emblem" aria-hidden="true">
              <svg viewBox="0 0 48 48" width="34" height="34">
                <circle cx="24" cy="24" r="23" fill="#fff" opacity="0.14" />
                <circle cx="24" cy="24" r="17" fill="none" stroke="#fff" strokeWidth="1.6" opacity="0.7" />
                <path d="M12 21 24 15l12 6-12 6-12-6Z" fill="#fff" />
                <path d="M17 24.5V30c0 2 3.5 3.5 7 3.5s7-1.5 7-3.5v-5.5" fill="none" stroke="#fff" strokeWidth="2.2" />
              </svg>
            </span>
            <span className="brand-text">
              <strong>TBS LPDP</strong>
              <em>Try Out Application</em>
            </span>
          </Link>
          <div className="masthead-user">
            <span className="participant">{participant ?? 'PESERTA'}</span>
            <span className="participant-avatar" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="#fff">
                <path d="M12 3 1 8l11 5 9-4.09V16h2V8L12 3Z" />
                <path d="M5 12.18v3.5L12 19l7-3.32v-3.5L12 15.5 5 12.18Z" />
              </svg>
            </span>
          </div>
        </div>
      </header>
      <main className="page">{children}</main>
      {hideFeedback ? null : <FeedbackFooter />}
    </div>
  )
}
