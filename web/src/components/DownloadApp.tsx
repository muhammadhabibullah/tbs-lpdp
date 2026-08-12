import { useEffect, useMemo, useState } from 'react'
import { LATEST_RELEASE_API, RELEASES_URL, REPO_URL } from '../lib/appRuntime'
import { externalLinkProps } from './FeedbackFooter'

/**
 * FE-42: the download section of the web home page — one button, aimed at the
 * device asking. Links resolve at runtime from the GitHub Releases API —
 * CORS-open and unauthenticated — so a new release needs no site rebuild. If
 * the call fails or is rate-limited, the button falls back to the releases
 * page, which is never wrong, only slower.
 *
 * The source is the Releases API and *not* the updater's `latest.json`: that
 * manifest carries only `{url, signature}` per platform, and its URLs are the
 * update payloads (`.app.tar.gz`, `-setup.nsis.zip`), not the installers a
 * person should double-click. It also has no Android entry and no file sizes.
 *
 * Per-platform install steps live in the release notes, which the footnote
 * links to; four step-lists inline turned this section into a manual.
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

/** Every installer we publish, in the order the "other devices" list shows them. */
const OPTIONS = [
  {
    id: 'windows',
    icon: '🪟',
    /** What the button says once this is the detected device. */
    action: 'Unduh untuk Windows',
    /** What the list says when it is one row among several. */
    label: 'Windows 10/11 (64-bit)',
    find: (assets: ReleaseAsset[]) => pick(assets, (n) => n.endsWith('.exe')),
  },
  {
    id: 'macos-arm',
    icon: '🍎',
    action: 'Unduh untuk Mac (Apple Silicon)',
    label: 'macOS — Apple Silicon (M1 ke atas)',
    find: (assets: ReleaseAsset[]) =>
      pick(assets, (n) => n.endsWith('.dmg') && (n.includes('aarch64') || n.includes('arm64'))),
  },
  {
    id: 'macos-intel',
    icon: '🍎',
    action: 'Unduh untuk Mac (Intel)',
    label: 'macOS — Intel',
    find: (assets: ReleaseAsset[]) =>
      pick(assets, (n) => n.endsWith('.dmg') && (n.includes('x64') || n.includes('x86_64'))),
  },
  {
    id: 'linux-appimage',
    icon: '🐧',
    action: 'Unduh untuk Linux (AppImage)',
    label: 'Linux — AppImage (x86-64)',
    find: (assets: ReleaseAsset[]) => pick(assets, (n) => n.endsWith('.appimage')),
  },
  {
    id: 'linux-deb',
    icon: '🐧',
    action: 'Unduh untuk Linux (.deb)',
    label: 'Linux — Debian/Ubuntu (.deb)',
    find: (assets: ReleaseAsset[]) => pick(assets, (n) => n.endsWith('.deb')),
  },
  {
    id: 'linux-rpm',
    icon: '🐧',
    action: 'Unduh untuk Linux (.rpm)',
    label: 'Linux — Fedora (.rpm)',
    find: (assets: ReleaseAsset[]) => pick(assets, (n) => n.endsWith('.rpm')),
  },
  {
    id: 'android',
    icon: '🤖',
    action: 'Unduh untuk Android',
    label: 'Android 7.0 ke atas (arm64)',
    find: (assets: ReleaseAsset[]) => pick(assets, (n) => n.endsWith('.apk')),
  },
] as const

type OptionId = (typeof OPTIONS)[number]['id']

type Os = 'windows' | 'macos' | 'linux' | 'android' | 'ios' | 'unknown'

/**
 * Order matters: Android's user agent also says "Linux", and an iPad since
 * iPadOS 13 claims to be a Mac — only the touch-point count gives it away.
 */
function detectOs(): Os {
  if (typeof navigator === 'undefined') return 'unknown'
  const ua = navigator.userAgent
  if (/android/i.test(ua)) return 'android'
  if (/iphone|ipod/i.test(ua)) return 'ios'
  if (/mac/i.test(ua)) return navigator.maxTouchPoints > 1 ? 'ios' : 'macos'
  if (/windows|win32|win64/i.test(ua)) return 'windows'
  if (/linux|x11|cros/i.test(ua)) return 'linux'
  return 'unknown'
}

/**
 * Which Mac to offer. Chromium answers this exactly; Safari and Firefox expose
 * nothing usable, and every Mac sold since late 2020 is Apple Silicon, so that
 * is the default — with the Intel build kept one visible click away rather than
 * buried in the list, because guessing wrong hands someone a build that will
 * not launch.
 */
interface UserAgentData {
  getHighEntropyValues?: (hints: string[]) => Promise<{ architecture?: string }>
}

async function detectMacArch(): Promise<'arm' | 'intel'> {
  const uaData = (navigator as Navigator & { userAgentData?: UserAgentData }).userAgentData
  try {
    const values = await uaData?.getHighEntropyValues?.(['architecture'])
    if (values?.architecture) return values.architecture === 'arm' ? 'arm' : 'intel'
  } catch {
    // Chromium can reject the request; fall through to the default.
  }
  return 'arm'
}

function formatSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function DownloadApp() {
  const [release, setRelease] = useState<Release | null>(null)
  const [failed, setFailed] = useState(false)
  const [os] = useState<Os>(detectOs)
  const [macArch, setMacArch] = useState<'arm' | 'intel'>('arm')
  const [showAll, setShowAll] = useState(false)

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

  useEffect(() => {
    if (os !== 'macos') return
    let cancelled = false
    void detectMacArch().then((arch) => {
      if (!cancelled) setMacArch(arch)
    })
    return () => {
      cancelled = true
    }
  }, [os])

  const version = useMemo(() => release?.tag.replace(/^app-v/, '') ?? null, [release])

  /** The one the button offers. `null` on iOS and anything unrecognised. */
  const primaryId: OptionId | null = useMemo(() => {
    switch (os) {
      case 'windows':
        return 'windows'
      case 'macos':
        return macArch === 'intel' ? 'macos-intel' : 'macos-arm'
      case 'linux':
        return 'linux-appimage'
      case 'android':
        return 'android'
      default:
        return null
    }
  }, [os, macArch])

  const primary = OPTIONS.find((option) => option.id === primaryId) ?? null
  const primaryAsset = primary && release ? primary.find(release.assets) : null
  /** Offered beside the button, because a wrong guess here does not launch. */
  const macAlternative = os === 'macos' ? OPTIONS.find((o) => o.id === (macArch === 'intel' ? 'macos-arm' : 'macos-intel')) : null
  const macAlternativeAsset = macAlternative && release ? macAlternative.find(release.assets) : null

  const others = useMemo(
    () =>
      release
        ? OPTIONS.filter((option) => option.id !== primaryId).map((option) => ({
            ...option,
            asset: option.find(release.assets),
          }))
        : [],
    [release, primaryId],
  )

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

      <div className="download-cta">
        {primary && primaryAsset ? (
          <a className="btn btn-navy btn-lg download-primary" {...externalLinkProps(primaryAsset.url)} download>
            <span aria-hidden="true">{primary.icon}</span> {primary.action}
            {primaryAsset.size ? <span className="download-size"> · {formatSize(primaryAsset.size)}</span> : null}
          </a>
        ) : (
          <a className="btn btn-navy btn-lg download-primary" {...externalLinkProps(release?.page ?? RELEASES_URL)}>
            Buka halaman rilis di GitHub
          </a>
        )}

        <p className="muted download-status">
          {failed ? (
            'Daftar unduhan tidak dapat dimuat saat ini — halaman rilis memuat seluruh berkasnya.'
          ) : !release ? (
            'Memuat daftar unduhan…'
          ) : (
            <>
              {version ? (
                <>
                  Versi <strong>v{version}</strong>
                  {release.publishedAt ? ` · ${new Date(release.publishedAt).toLocaleDateString('id-ID')}` : ''}
                </>
              ) : null}
              {os === 'ios' ? ' · Belum tersedia untuk iPhone dan iPad — gunakan versi web.' : null}
              {os === 'unknown' ? ' · Perangkat Anda tidak dikenali; pilih berkas secara manual.' : null}
            </>
          )}
        </p>

        <p className="download-alternatives">
          {macAlternativeAsset ? (
            <>
              <a {...externalLinkProps(macAlternativeAsset.url)} download>
                {macArch === 'intel' ? 'Mac dengan chip Apple Silicon?' : 'Mac dengan prosesor Intel?'}
              </a>
              <span aria-hidden="true"> · </span>
            </>
          ) : null}
          <button type="button" className="btn btn-link" aria-expanded={showAll} onClick={() => setShowAll((v) => !v)}>
            {showAll ? 'Sembunyikan unduhan lain' : 'Unduhan untuk perangkat lain'}
          </button>
        </p>

        {showAll ? (
          <ul className="download-others">
            {others.map((option) => (
              <li key={option.id}>
                <span aria-hidden="true">{option.icon}</span>{' '}
                {option.asset ? (
                  <a {...externalLinkProps(option.asset.url)} download>
                    {option.label}
                  </a>
                ) : (
                  <span className="muted">{option.label}</span>
                )}
                {option.asset?.size ? <span className="download-size"> · {formatSize(option.asset.size)}</span> : null}
              </li>
            ))}
            {others.length === 0 ? (
              <li>
                <a {...externalLinkProps(release?.page ?? RELEASES_URL)}>Lihat seluruh berkas di halaman rilis</a>
              </li>
            ) : null}
          </ul>
        ) : null}
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
