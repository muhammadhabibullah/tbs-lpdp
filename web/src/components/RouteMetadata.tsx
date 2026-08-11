import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const HOME_TITLE = 'Try Out TBS LPDP Gratis — Simulasi Tes Bakat Skolastik'
const HOME_DESCRIPTION =
  'Latihan try out TBS LPDP gratis: 60 soal Tes Bakat Skolastik, simulasi 90 menit, skor otomatis, dan pembahasan lengkap untuk setiap soal.'

function updateNamedMeta(name: string, content: string): void {
  document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.setAttribute('content', content)
}

/**
 * Hash routes share one physical GitHub Pages document. Keep the public home
 * page indexable, but mark private attempt/review states as noindex after the
 * client resolves the route.
 */
export default function RouteMetadata() {
  const { pathname } = useLocation()

  useEffect(() => {
    const isHome = pathname === '/'
    document.title = isHome
      ? HOME_TITLE
      : pathname.endsWith('/review')
        ? 'Pembahasan Try Out | TBS LPDP'
        : 'Try Out Sedang Berlangsung | TBS LPDP'

    updateNamedMeta('description', HOME_DESCRIPTION)
    updateNamedMeta(
      'robots',
      isHome
        ? 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
        : 'noindex, nofollow, noarchive',
    )
  }, [pathname])

  return null
}
