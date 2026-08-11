import { useLocation, useNavigate } from 'react-router-dom'

/** Section anchors on the home page. */
export const MENU_ITEMS = [
  { id: 'paket', label: 'Paket Try Out' },
  { id: 'riwayat', label: 'Riwayat Pengerjaan' },
  { id: 'tentang', label: 'Tentang TBS' },
  { id: 'disclaimer', label: 'Disclaimer' },
] as const

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
 */
export default function MenuBar() {
  const navigate = useNavigate()
  const location = useLocation()

  function go(id: string): void {
    if (location.pathname === '/') scrollToSection(id)
    else navigate('/', { state: { scrollTo: id } })
  }

  return (
    <nav className="app-nav" aria-label="Navigasi utama">
      <div className="app-nav-inner">
        {MENU_ITEMS.map((item) => (
          <button key={item.id} type="button" onClick={() => go(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  )
}
