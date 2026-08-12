import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { LATEST_RELEASE_API, RELEASES_URL, REPO_URL } from '../lib/appRuntime'
import { externalLinkProps } from './FeedbackFooter'

/**
 * FE-42: the download section of the web home page. Links resolve at runtime
 * from the GitHub Releases API — CORS-open and unauthenticated — so a new
 * release needs no site rebuild. If the call fails or is rate-limited, every
 * card falls back to the releases page, which is never wrong, only slower.
 *
 * v6 §6 is the source for the install steps: they exist because the installers
 * are unsigned, and a non-technical user meeting Gatekeeper or SmartScreen with
 * no explanation simply gives up.
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
  steps: ReactNode[]
}

const PLATFORMS: PlatformCard[] = [
  {
    id: 'windows',
    icon: '🪟',
    title: 'Windows',
    subtitle: 'Windows 10 atau 11, 64-bit',
    find: (assets) => [{ label: 'Unduh pemasang (.exe)', asset: pick(assets, (n) => n.endsWith('.exe')) }],
    steps: [
      <>
        Unduh berkas <code>…-setup.exe</code>, lalu klik dua kali berkas hasil unduhan.
      </>,
      <>
        Jika muncul layar biru <strong>“Windows protected your PC”</strong>, klik <strong>More info</strong> lalu{' '}
        <strong>Run anyway</strong>. Aplikasi ini belum memiliki sertifikat berbayar dari Microsoft — bukan berarti
        berbahaya; kode sumbernya terbuka dan dapat Anda periksa sendiri.
      </>,
      <>Ikuti langkah pemasang sampai selesai.</>,
      <>
        Aplikasi muncul di <strong>Start Menu</strong> dengan nama <strong>TBS LPDP Try Out</strong>.
      </>,
    ],
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
    steps: [
      <>
        Unduh berkas <code>.dmg</code> sesuai jenis prosesor Mac Anda (menu  → About This Mac).
      </>,
      <>
        Buka berkas tersebut, lalu seret ikon aplikasi ke folder <strong>Applications</strong>.
      </>,
      <>
        Saat pertama dibuka, macOS menahan aplikasi yang tidak bersertifikat berbayar Apple. Buka{' '}
        <strong>System Settings → Privacy &amp; Security</strong>, gulir ke bawah, lalu klik{' '}
        <strong>Open Anyway</strong>. Pada macOS 14 ke bawah, klik kanan ikon aplikasi →{' '}
        <strong>Open</strong> juga bisa.
      </>,
      <>
        Jika muncul pesan <strong>“… is damaged and can’t be opened”</strong>, itu penanda karantina
        unduhan — berkasnya tidak rusak. Buka <strong>Terminal</strong>, jalankan{' '}
        <code>xattr -cr &quot;/Applications/TBS LPDP Try Out.app&quot;</code>, lalu buka lagi aplikasinya.
      </>,
    ],
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
    steps: [
      <>
        Unduh berkas <code>.AppImage</code>.
      </>,
      <>
        Klik kanan berkas → <strong>Properties</strong> → centang <strong>Executable</strong> (atau jalankan{' '}
        <code>chmod +x nama-berkas.AppImage</code> di terminal).
      </>,
      <>Klik dua kali berkas tersebut untuk menjalankan aplikasi.</>,
      <>
        Pengguna Debian/Ubuntu dapat memakai berkas <code>.deb</code>, dan Fedora <code>.rpm</code>. Perlu dicatat:{' '}
        <strong>pembaruan otomatis hanya tersedia pada AppImage</strong>; paket .deb/.rpm harus diperbarui manual.
      </>,
    ],
  },
  {
    id: 'android',
    icon: '🤖',
    title: 'Android',
    subtitle: 'Android 7.0 ke atas, 64-bit (arm64)',
    find: (assets) => [{ label: 'Unduh .apk', asset: pick(assets, (n) => n.endsWith('.apk')) }],
    steps: [
      <>
        Unduh berkas <code>.apk</code> langsung di perangkat Android Anda.
      </>,
      <>Buka berkas hasil unduhan (dari notifikasi unduhan atau aplikasi Files).</>,
      <>
        Saat diminta, izinkan <strong>“Install unknown apps”</strong> / <strong>“Instal dari sumber tidak dikenal”</strong>{' '}
        untuk browser yang Anda pakai, lalu kembali dan tekan <strong>Install</strong>.
      </>,
      <>
        Pembaruan cukup dengan memasang APK versi baru di atas yang lama — riwayat dan jawaban Anda tetap tersimpan.
      </>,
    ],
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

              <h4>Cara memasang</h4>
              <ol className="download-steps">
                {platform.steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>

              <p className="download-disclaimer">
                Aplikasi ini <strong>belum bertanda tangan digital berbayar</strong> karena merupakan proyek gratis dan
                terbuka, sehingga sistem operasi dapat menampilkan peringatan. Pastikan Anda hanya mengunduh dari{' '}
                <a {...externalLinkProps(REPO_URL)}>github.com/muhammadhabibullah/tbs-lpdp</a>.
              </p>
            </article>
          )
        })}
      </div>
    </section>
  )
}
