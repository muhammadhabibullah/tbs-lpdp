import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { IS_OFFLINE_APP } from '../lib/config'

/**
 * Section anchors on the home page. `webOnly` items are dropped inside the
 * offline app, where they make no sense — you do not download the app from
 * inside the app (FE-42, AP-9).
 */
export const MENU_ITEMS = [
  { id: 'paket', label: 'Paket Try Out' },
  { id: 'riwayat', label: 'Riwayat Pengerjaan' },
  { id: 'unduh', label: 'Unduh Aplikasi Offline', webOnly: true },
  { id: 'tentang', label: 'Tentang TBS' },
  { id: 'disclaimer', label: 'Disclaimer' },
] as const

export const VISIBLE_MENU_ITEMS = MENU_ITEMS.filter(
  (item) => !IS_OFFLINE_APP || !('webOnly' in item && item.webOnly),
)

export function scrollToSection(id: string): void {
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  document.getElementById(id)?.scrollIntoView({
    behavior: reduceMotion ? 'auto' : 'smooth',
    block: 'start',
  })
}

/**
 * Masthead navigation. These are buttons, not `<a href="#paket">` — the app is
 * on a HashRouter (C-3), where the fragment *is* the route, so a real anchor
 * would navigate away instead of scrolling. From another page the target does
 * not exist yet, so the click routes home and hands the anchor to HomePage
 * through the location state.
 *
 * On desktop (≥768px), nav items display horizontally inline without a burger icon.
 * On narrow screens (<768px), a hamburger toggle button is provided to toggle the menu.
 */
export default function MenuBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(false)

  // Close menu on route or location state change
  useEffect(() => {
    setIsOpen(false)
  }, [location])

  // Close menu on Escape key press
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  function go(id: string): void {
    setIsOpen(false)
    if (location.pathname === '/') scrollToSection(id)
    else navigate('/', { state: { scrollTo: id } })
  }

  return (
    <nav className={`app-nav ${isOpen ? 'is-open' : ''}`} aria-label="Navigasi utama">
      <div className="app-nav-header">
        <button
          type="button"
          className="menu-toggle"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-label={isOpen ? 'Tutup menu' : 'Buka menu'}
        >
          <span className="menu-toggle-icon" aria-hidden="true">
            {isOpen ? (
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </span>
          <span className="menu-toggle-text">Menu</span>
        </button>
      </div>
      <div className={`app-nav-inner ${isOpen ? 'is-open' : ''}`}>
        {VISIBLE_MENU_ITEMS.map((item) => (
          <button key={item.id} type="button" onClick={() => go(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  )
}
