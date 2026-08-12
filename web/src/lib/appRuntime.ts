/**
 * The thin seam between the SPA and the Tauri shell (v6 §2). Every Tauri import
 * here is dynamic, so the web and dev-mock builds never pull a plugin chunk,
 * and every entry point degrades to a plain-browser equivalent — which is what
 * makes `VITE_OFFLINE=true npm run dev` usable in an ordinary browser.
 */

export const REPO_URL = 'https://github.com/muhammadhabibullah/tbs-lpdp'
export const RELEASES_URL = `${REPO_URL}/releases`
export const LATEST_RELEASE_API = 'https://api.github.com/repos/muhammadhabibullah/tbs-lpdp/releases/latest'

/** Tauri's IPC bridge only exists inside the app shell. */
export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
}

/**
 * AP-7: the updater plugin has no Android implementation, so the app checks
 * versions itself there. The webview user agent is the cheapest reliable
 * signal and saves shipping `tauri-plugin-os` for one boolean.
 */
export function isAndroidApp(): boolean {
  return isTauri() && typeof navigator !== 'undefined' && /android/i.test(navigator.userAgent)
}

/**
 * Opens a link in the user's own browser. A Tauri webview refuses `target`
 * navigation, so the opener plugin — scoped to github.com and mailto: in
 * `capabilities/default.json` (C-31) — has to do it.
 */
export async function openExternal(url: string): Promise<void> {
  if (isTauri()) {
    const { openUrl } = await import('@tauri-apps/plugin-opener')
    await openUrl(url)
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

/** The installed app's semver (AP-10). Null outside the app shell. */
export async function getAppVersion(): Promise<string | null> {
  if (!isTauri()) return null
  try {
    const { getVersion } = await import('@tauri-apps/api/app')
    return await getVersion()
  } catch {
    return null
  }
}
