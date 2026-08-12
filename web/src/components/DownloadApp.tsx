import { useEffect, useMemo, useState } from 'react'
import { LATEST_RELEASE_API, RELEASES_URL, REPO_URL } from '../lib/appRuntime'
import { externalLinkProps } from './FeedbackFooter'

/**
 * FE-42: the download section of the web home page. Links resolve at runtime
 * from the GitHub Releases API — CORS-open and unauthenticated — so a new
 * release needs no site rebuild. If the call fails or is rate-limited, every
 * card falls back to the releases page, which is never wrong, only slower.
 *
 * The per-platform install steps (v6 §6) live in the release notes, not here:
 * they are only read by someone who has already downloaded a file, they are
 * versioned with the installers they describe, and four step-lists inline turn
 * the home page into a manual. Each card links to them instead.
 */

interface ReleaseAsset {
  name: string
  url: string
  size: number
}

interface Release {
  tag: string
  page: string
  publishedAt: string | null
  assets: ReleaseAsset[]
}

/** Updater plumbing, not something a human downloads. */
function isUserFacing(name: string): boolean {
  return !/\.(sig|json)$|\.tar\.gz$|\.nsis\.zip$/i.test(name)
}

function pick(assets: ReleaseAsset[], test: (name: string) => boolean): ReleaseAsset | null {
  return assets.find((asset) => isUserFacing(asset.name) && test(asset.name.toLowerCase())) ?? null
}

interface PlatformCard {
  id: string
  icon: string
  title: string
  subtitle: string
  /** Primary download, plus any secondary formats worth offering. */
  find: (assets: ReleaseAsset[]) => { label: string; asset: ReleaseAsset | null }[]
  /** One line on what the OS will say the first time — the rest is in the notes. */
  note: string
}

const PLATFORMS: PlatformCard[] = [
  {
    id: 'windows',
    icon: '🪟',
    title: 'Windows',
    subtitle: 'Windows 10 atau 11, 64-bit',
    find: (assets) => [{ label: 'Unduh pemasang (.exe)', asset: pick(assets, (n) => n.endsWith('.exe')) }],
    note: 'Windows menampilkan layar biru “Windows protected your PC” pada pemasangan pertama.',
  },
  {
    id: 'macos',
    icon: '🍎',
    title: 'macOS',
    subtitle: 'Apple Silicon (M1 ke atas) dan Intel',
    find: (assets) => [
      {
        label: 'Unduh .dmg (Apple Silicon)',
        asset: pick(assets, (n) => n.endsWith('.dmg') && (n.includes('aarch64') || n.includes('arm64'))),
      },
      {
        label: 'Unduh .dmg (Intel)',
        asset: pick(assets, (n) => n.endsWith('.dmg') && (n.includes('x64') || n.includes('x86_64'))),
      },
    ],
    note: 'macOS menahan aplikasi tanpa tanda tangan Apple pada pembukaan pertama, kadang dengan pesan “is damaged”.',
  },
  {
    id: 'linux',
    icon: '🐧',
    title: 'Linux',
    subtitle: 'x86-64 — AppImage, Debian/Ubuntu, atau Fedora',
    find: (assets) => [
      { label: 'Unduh .AppImage', asset: pick(assets, (n) => n.endsWith('.appimage')) },
      { label: 'Unduh .deb (Debian/Ubuntu)', asset: pick(assets, (n) => n.endsWith('.deb')) },
      { label: 'Unduh .rpm (Fedora)', asset: pick(assets, (n) => n.endsWith('.rpm')) },
    ],
    note: 'AppImage perlu ditandai executable, dan hanya AppImage yang menerima pembaruan otomatis.',
  },
  {
    id: 'android',
    icon: '🤖',
    title: 'Android',
    subtitle: 'Android 7.0 ke atas, 64-bit (arm64)',
    find: (assets) => [{ label: 'Unduh .apk', asset: pick(assets, (n) => n.endsWith('.apk')) }],
    note: 'Android meminta izin “Instal dari sumber tidak dikenal” untuk browser yang Anda pakai.',
  },
]

function formatSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function DownloadApp() {
  const [release, setRelease] = useState<Release | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), 8_000)

    fetch(LATEST_RELEASE_API, { signal: controller.signal, headers: { Accept: 'application/vnd.github+json' } })
      .then(async (response) => {
        // 404 = no release published yet; treat it like any other miss.
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = (await response.json()) as {
          tag_name?: string
          html_url?: string
          published_at?: string
          assets?: { name?: string; browser_download_url?: string; size?: number }[]
        }
        if (cancelled) return
        setRelease({
          tag: data.tag_name ?? '',
          page: data.html_url ?? RELEASES_URL,
          publishedAt: data.published_at ?? null,
          assets: (data.assets ?? [])
            .filter((asset): asset is { name: string; browser_download_url: string; size?: number } =>
              Boolean(asset.name && asset.browser_download_url),
            )
            .map((asset) => ({ name: asset.name, url: asset.browser_download_url, size: asset.size ?? 0 })),
        })
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
      .finally(() => window.clearTimeout(timer))

    return () => {
      cancelled = true
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [])

  const version = useMemo(() => release?.tag.replace(/^app-v/, '') ?? null, [release])

  return (
    <section className="card download-app" id="unduh" aria-labelledby="unduh-title">
      <h2 className="section-title" id="unduh-title">
        Unduh Aplikasi Offline
      </h2>
      <p>
        Versi aplikasi untuk komputer dan Android berisi seluruh bank soal di dalamnya, sehingga try out dapat
        dikerjakan <strong>tanpa koneksi internet</strong> — tanpa akun dan tanpa iklan. Saat perangkat terhubung,
        aplikasi memeriksa paket soal baru secara otomatis.
      </p>
      <p className="muted download-status">
        {version ? (
          <>
            Versi terbaru: <strong>v{version}</strong>
            {release?.publishedAt ? ` · dirilis ${new Date(release.publishedAt).toLocaleDateString('id-ID')}` : ''}
          </>
        ) : failed ? (
          <>
            Daftar unduhan tidak dapat dimuat saat ini. Buka{' '}
            <a {...externalLinkProps(RELEASES_URL)}>halaman rilis di GitHub</a> untuk mengunduh langsung.
          </>
        ) : (
          'Memuat daftar unduhan…'
        )}
      </p>

      <div className="download-grid">
        {PLATFORMS.map((platform) => {
          const downloads = release ? platform.find(release.assets) : []
          const available = downloads.filter((download) => download.asset)
          return (
            <article className="download-card" key={platform.id}>
              <h3>
                <span aria-hidden="true">{platform.icon}</span> {platform.title}
              </h3>
              <p className="muted download-subtitle">{platform.subtitle}</p>

              <div className="download-links">
                {available.length > 0 ? (
                  available.map((download, index) => (
                    <a
                      key={download.asset!.name}
                      className={`btn btn-block btn-sm ${index === 0 ? 'btn-navy' : 'btn-ghost'}`}
                      {...externalLinkProps(download.asset!.url)}
                      download
                    >
                      {download.label}
                      {download.asset!.size ? (
                        <span className="download-size"> · {formatSize(download.asset!.size)}</span>
                      ) : null}
                    </a>
                  ))
                ) : (
                  <a className="btn btn-ghost btn-block btn-sm" {...externalLinkProps(release?.page ?? RELEASES_URL)}>
                    Buka halaman rilis
                  </a>
                )}
              </div>

              <p className="download-note">{platform.note}</p>
            </article>
          )
        })}
      </div>

      <p className="download-footnote">
        Aplikasi ini <strong>belum bertanda tangan digital berbayar</strong> karena merupakan proyek gratis dan terbuka,
        sehingga sistem operasi menampilkan peringatan saat pertama dipasang — bukan berarti berbahaya.{' '}
        <a {...externalLinkProps(release?.page ?? RELEASES_URL)}>Petunjuk pemasangan langkah demi langkah</a> tersedia
        di catatan rilis, lengkap untuk keempat sistem operasi. Pastikan Anda hanya mengunduh dari{' '}
        <a {...externalLinkProps(REPO_URL)}>github.com/muhammadhabibullah/tbs-lpdp</a>.
      </p>
    </section>
  )
}
