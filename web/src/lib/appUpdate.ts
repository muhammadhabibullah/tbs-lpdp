import { compareVersions } from './bankSchema'
import { LATEST_RELEASE_API, RELEASES_URL, getAppVersion, isAndroidApp, isTauri, openExternal } from './appRuntime'

/**
 * Application updates (AP-6 desktop, AP-7 Android).
 *
 * Desktop installs update in place through `tauri-plugin-updater`, verifying
 * the project's minisign signature over `latest.json`. Android has no updater
 * implementation, so the app compares its own version against the latest
 * release and hands the APK to the system browser; installing over the existing
 * app works because every APK is signed with the same release keystore (C-30).
 */

/** Release tags are `app-vX.Y.Z`; the app itself only knows `X.Y.Z`. */
const TAG_PREFIX = 'app-v'

export type AppUpdateCheck =
  | { status: 'current'; version: string }
  | {
      status: 'available'
      version: string
      notes: string | null
      /** Installs and relaunches (desktop) or opens the APK download (Android). */
      apply: () => Promise<void>
      /** Desktop installs that cannot self-update (deb/rpm) fall back to this. */
      manualUrl: string
    }
  | { status: 'offline' }
  | { status: 'unsupported' }
  | { status: 'error'; message: string }

interface GithubRelease {
  tag_name?: string
  html_url?: string
  body?: string
  assets?: { name?: string; browser_download_url?: string }[]
}

async function checkAndroid(current: string): Promise<AppUpdateCheck> {
  let release: GithubRelease
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 8_000)
    try {
      const response = await fetch(LATEST_RELEASE_API, { signal: controller.signal, cache: 'no-store' })
      // A repository with no published release yet answers 404, not an error.
      if (response.status === 404) return { status: 'current', version: current }
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      release = (await response.json()) as GithubRelease
    } finally {
      clearTimeout(timer)
    }
  } catch {
    return { status: 'offline' }
  }

  const tag = typeof release.tag_name === 'string' ? release.tag_name : ''
  const latest = tag.startsWith(TAG_PREFIX) ? tag.slice(TAG_PREFIX.length) : tag.replace(/^v/, '')
  if (!latest || compareVersions(latest, current) <= 0) return { status: 'current', version: current }

  const apk = release.assets?.find((asset) => asset.name?.toLowerCase().endsWith('.apk'))?.browser_download_url
  const target = apk ?? release.html_url ?? RELEASES_URL
  return {
    status: 'available',
    version: latest,
    notes: release.body?.trim() || null,
    apply: () => openExternal(target),
    manualUrl: release.html_url ?? RELEASES_URL,
  }
}

async function checkDesktop(current: string): Promise<AppUpdateCheck> {
  const { check } = await import('@tauri-apps/plugin-updater')
  let update: Awaited<ReturnType<typeof check>>
  try {
    update = await check({ timeout: 10_000 })
  } catch (error) {
    // `check` cannot tell "no network" from "endpoint unreachable"; both are
    // silent non-events on launch (NF-30).
    const message = error instanceof Error ? error.message : String(error)
    return /network|request|timeout|dns|connect|resolve/i.test(message)
      ? { status: 'offline' }
      : { status: 'error', message }
  }
  if (!update) return { status: 'current', version: current }

  return {
    status: 'available',
    version: update.version,
    notes: update.body?.trim() || null,
    manualUrl: RELEASES_URL,
    async apply() {
      // deb/rpm installs are managed by the system package manager and cannot
      // replace themselves; the release page is the honest fallback (AP-6).
      await update.downloadAndInstall()
      const { relaunch } = await import('@tauri-apps/plugin-process')
      await relaunch()
    },
  }
}

export async function checkForAppUpdate(): Promise<AppUpdateCheck> {
  if (!isTauri()) return { status: 'unsupported' }
  const current = (await getAppVersion()) ?? '0.0.0'
  try {
    return isAndroidApp() ? await checkAndroid(current) : await checkDesktop(current)
  } catch (error) {
    return { status: 'error', message: error instanceof Error ? error.message : String(error) }
  }
}

/**
 * The update conversation itself, in Bahasa Indonesia, through the platform's
 * own dialogs (AP-6). Returns true when an install was started.
 */
export async function promptForAppUpdate(update: Extract<AppUpdateCheck, { status: 'available' }>): Promise<boolean> {
  const { ask, message } = await import('@tauri-apps/plugin-dialog')
  const android = isAndroidApp()
  const accepted = await ask(
    [
      `Versi ${update.version} tersedia.`,
      update.notes ? `\n${update.notes.slice(0, 400)}` : '',
      android
        ? '\n\nBerkas APK akan diunduh melalui browser. Pasang di atas aplikasi yang ada — data Anda tetap tersimpan.'
        : '\n\nAplikasi akan mengunduh pembaruan lalu memulai ulang.',
    ].join(''),
    {
      title: 'Pembaruan Aplikasi',
      kind: 'info',
      okLabel: android ? 'Unduh' : 'Perbarui sekarang',
      cancelLabel: 'Nanti saja',
    },
  )
  if (!accepted) return false

  try {
    await update.apply()
    return true
  } catch (error) {
    await message(
      [
        'Pembaruan otomatis tidak dapat dijalankan untuk cara pemasangan ini',
        ' (paket .deb/.rpm dikelola oleh sistem). Halaman rilis akan dibuka agar Anda',
        ' dapat mengunduh versi terbaru secara manual.',
        `\n\n${error instanceof Error ? error.message : String(error)}`,
      ].join(''),
      { title: 'Pembaruan Aplikasi', kind: 'warning' },
    )
    await openExternal(update.manualUrl)
    return false
  }
}
