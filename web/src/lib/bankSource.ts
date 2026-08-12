import { isTauri } from './appRuntime'
import { ApiError, BANK_UPDATED_EVENT } from './config'
import { BANK_SCHEMA_VERSION, parseManifest, type BankManifest } from './bankSchema'
import type { Bank } from './types'

/**
 * Where the local exam engine gets its questions (AP-2), and how the offline
 * app keeps them current (AP-4, AP-5, NF-30, NF-31).
 *
 * Two implementations:
 *
 * - `devBankSource` — the Vite middleware at `/__mock/bank.json`, dev only.
 * - `offlineBankSource` — the verified cached bank in the app data directory,
 *   else the snapshot bundled into the installer; refreshed from GitHub Pages.
 *
 * Attempts are pinned to an immutable release snapshot taken when they start,
 * so hot-swapping the bank underneath a running or finished attempt is safe.
 */

/** GitHub Pages copy published by `deploy-web.yml` (v6 §4). */
const PUBLISHED_BANK_BASE = 'https://muhammadhabibullah.github.io/tbs-lpdp/bank/'

/** NF-30: a launch check must never hold the UI, so it gives up quickly. */
const MANIFEST_TIMEOUT_MS = 5_000
const DOWNLOAD_TIMEOUT_MS = 60_000

/** Cached bank lives in the app data directory, next to its own manifest. */
const CACHE_DIR = 'bank'
const CACHE_MANIFEST = `${CACHE_DIR}/manifest.json`

export type BankOrigin = 'dev' | 'bundled' | 'cached'

export interface BankStatus {
  /** 12-hex digest of the active bank, or `'dev'` for the middleware source. */
  version: string
  /** When the bank content was last changed in git; null for the dev source. */
  generatedAt: string | null
  origin: BankOrigin
}

export type RefreshResult =
  | { status: 'updated'; version: string }
  | { status: 'current'; version: string }
  | { status: 'offline' }
  /** AP-5: the published bank needs a newer app; the current bank is kept. */
  | { status: 'app-outdated'; minAppVersion: string }
  /** The dev middleware source has nothing to pull from. */
  | { status: 'unsupported' }
  | { status: 'error'; message: string }

export interface BankSource {
  /** Resolves the active bank, loading it on first use. */
  load(): Promise<Bank>
  /** Null until the first successful `load()`. */
  status(): BankStatus | null
  /** AP-4: check the published manifest and swap in a newer bank. */
  refresh(): Promise<RefreshResult>
  /** Notified after a hot swap so the UI can re-read packages. */
  subscribe(listener: () => void): () => void
}

async function fetchJson(url: string, timeoutMs: number): Promise<unknown> {
  const response = await fetchWithTimeout(url, timeoutMs)
  return response.json()
}

async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(url, { signal: controller.signal, cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return response
  } finally {
    clearTimeout(timer)
  }
}

/** NF-31: nothing is trusted until its bytes hash to the advertised digest. */
async function sha256Hex(text: string): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error('Web Crypto tidak tersedia untuk memverifikasi bank soal.')
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

function parseBank(text: string): Bank {
  const parsed = JSON.parse(text) as Partial<Bank>
  if (!Array.isArray(parsed.packages) || typeof parsed.questions !== 'object' || parsed.questions === null) {
    throw new Error('bank file has an unexpected shape')
  }
  return { packages: parsed.packages, questions: parsed.questions }
}

// ---------------------------------------------------------------------------
// Dev source — the Vite middleware, `apply: 'serve'` only.
// ---------------------------------------------------------------------------

export function createDevBankSource(): BankSource {
  let pending: Promise<Bank> | null = null
  let status: BankStatus | null = null

  return {
    load() {
      if (!pending) {
        pending = fetch('/__mock/bank.json')
          .then((response) => {
            if (!response.ok) throw new ApiError('Bank soal mock tidak tersedia (jalankan `npm run dev`).')
            return response.json() as Promise<Bank>
          })
          .then((bank) => {
            status = { version: 'dev', generatedAt: null, origin: 'dev' }
            return bank
          })
          .catch((error) => {
            pending = null
            throw error instanceof ApiError ? error : new ApiError(String(error))
          })
      }
      return pending
    },
    status: () => status,
    refresh: async () => ({ status: 'unsupported' }),
    subscribe: () => () => undefined,
  }
}

// ---------------------------------------------------------------------------
// Offline source — bundled snapshot + verified cache in the app data directory.
// ---------------------------------------------------------------------------

interface CachedBank {
  manifest: BankManifest
  bankJson: string
}

/**
 * Persistence for the downloaded bank. Under Tauri this is the app data
 * directory; in a plain browser (`VITE_OFFLINE=true npm run dev`) nothing is
 * persisted and the app simply falls back to the bundled snapshot each launch.
 */
interface BankStore {
  read(): Promise<CachedBank | null>
  write(manifest: BankManifest, bankJson: string): Promise<void>
}

const memoryStore: BankStore = {
  read: async () => null,
  write: async () => undefined,
}

function createTauriStore(): BankStore {
  // Imported lazily so a dev-mock or web build never pulls the plugin in.
  const plugin = () => import('@tauri-apps/plugin-fs')

  return {
    async read() {
      const fs = await plugin()
      const base = fs.BaseDirectory.AppData
      if (!(await fs.exists(CACHE_MANIFEST, { baseDir: base }))) return null
      const manifest = parseManifest(JSON.parse(await fs.readTextFile(CACHE_MANIFEST, { baseDir: base })))
      if (!manifest) return null
      const bankPath = `${CACHE_DIR}/${manifest.bank.url}`
      if (!(await fs.exists(bankPath, { baseDir: base }))) return null
      return { manifest, bankJson: await fs.readTextFile(bankPath, { baseDir: base }) }
    },

    async write(manifest, bankJson) {
      const fs = await plugin()
      const base = fs.BaseDirectory.AppData
      await fs.mkdir(CACHE_DIR, { baseDir: base, recursive: true })

      // Content-addressed name + manifest written last: a crash mid-update
      // leaves the previous (manifest, bank) pair intact and usable (NF-31).
      const bankPath = `${CACHE_DIR}/${manifest.bank.url}`
      const bankTemp = `${bankPath}.tmp`
      await fs.writeTextFile(bankTemp, bankJson, { baseDir: base })
      await fs.rename(bankTemp, bankPath, { oldPathBaseDir: base, newPathBaseDir: base })

      const manifestTemp = `${CACHE_MANIFEST}.tmp`
      await fs.writeTextFile(manifestTemp, JSON.stringify(manifest, null, 2), { baseDir: base })
      await fs.rename(manifestTemp, CACHE_MANIFEST, { oldPathBaseDir: base, newPathBaseDir: base })

      // Superseded revisions are dead weight; losing one is not an error.
      try {
        for (const entry of await fs.readDir(CACHE_DIR, { baseDir: base })) {
          if (entry.isFile && /^bank-[0-9a-f]{12}\.json(\.tmp)?$/.test(entry.name) && entry.name !== manifest.bank.url) {
            await fs.remove(`${CACHE_DIR}/${entry.name}`, { baseDir: base })
          }
        }
      } catch {
        // Leave the leftovers; the active pair is already committed.
      }
    },
  }
}

export function createOfflineBankSource(store: BankStore = isTauri() ? createTauriStore() : memoryStore): BankSource {
  let pending: Promise<Bank> | null = null
  let active: { bank: Bank; status: BankStatus } | null = null
  const listeners = new Set<() => void>()

  const bundledUrl = (name: string) => `${import.meta.env.BASE_URL}${CACHE_DIR}/${name}`

  async function loadBundled(): Promise<{ bank: Bank; status: BankStatus }> {
    const manifest = parseManifest(await fetchJson(bundledUrl('manifest.json'), DOWNLOAD_TIMEOUT_MS))
    if (!manifest) throw new ApiError('Bank soal bawaan aplikasi tidak dapat dibaca.')
    const response = await fetchWithTimeout(bundledUrl(manifest.bank.url), DOWNLOAD_TIMEOUT_MS)
    // The snapshot ships inside the installer, so its integrity is the app
    // signature's job; re-hashing it on every launch would only cost time.
    return {
      bank: parseBank(await response.text()),
      status: { version: manifest.bank_version, generatedAt: manifest.generated_at, origin: 'bundled' },
    }
  }

  async function loadCached(): Promise<{ bank: Bank; status: BankStatus } | null> {
    try {
      const cached = await store.read()
      if (!cached) return null
      // A-4: a corrupted cache must never take the app down — verify, then drop.
      if ((await sha256Hex(cached.bankJson)) !== cached.manifest.bank.sha256) return null
      return {
        bank: parseBank(cached.bankJson),
        status: {
          version: cached.manifest.bank_version,
          generatedAt: cached.manifest.generated_at,
          origin: 'cached',
        },
      }
    } catch {
      return null
    }
  }

  async function resolve(): Promise<Bank> {
    const loaded = (await loadCached()) ?? (await loadBundled())
    active = loaded
    emit(false)
    return loaded.bank
  }

  function emit(swapped: boolean): void {
    for (const listener of listeners) listener()
    // Anything showing package data — the home page above all — re-reads on
    // this rather than importing the bank plumbing into the web bundle. Only a
    // real swap counts; the first load is what the page was already waiting on.
    if (swapped) window.dispatchEvent(new CustomEvent(BANK_UPDATED_EVENT))
  }

  function load(): Promise<Bank> {
    if (!pending) {
      pending = resolve().catch((error) => {
        pending = null
        throw error instanceof ApiError ? error : new ApiError(String(error))
      })
    }
    return pending
  }

  return {
    load,

    status: () => active?.status ?? null,

    async refresh(): Promise<RefreshResult> {
      // The comparison is against whatever is actually loaded, so a refresh
      // before the first load cannot mistake "bundled" for "up to date".
      try {
        await load()
      } catch (error) {
        return { status: 'error', message: error instanceof Error ? error.message : String(error) }
      }
      const current = active?.status.version ?? null

      let manifest: BankManifest | null
      try {
        const url = `${PUBLISHED_BANK_BASE}manifest.json?t=${Date.now()}`
        manifest = parseManifest(await fetchJson(url, MANIFEST_TIMEOUT_MS))
      } catch {
        // Offline, DNS failure, timeout: indistinguishable and equally benign.
        return { status: 'offline' }
      }
      if (!manifest) return { status: 'error', message: 'Manifest bank soal tidak dikenali.' }

      // AP-5: the only coupling between the bank and app update planes.
      if (manifest.bank_schema_version > BANK_SCHEMA_VERSION) {
        return { status: 'app-outdated', minAppVersion: manifest.min_app_version }
      }
      if (current !== null && manifest.bank_version === current) return { status: 'current', version: current }

      try {
        const response = await fetchWithTimeout(`${PUBLISHED_BANK_BASE}${manifest.bank.url}`, DOWNLOAD_TIMEOUT_MS)
        const bankJson = await response.text()
        if ((await sha256Hex(bankJson)) !== manifest.bank.sha256) {
          return { status: 'error', message: 'Berkas bank soal tidak lolos verifikasi. Bank soal lama tetap dipakai.' }
        }
        const bank = parseBank(bankJson)
        await store.write(manifest, bankJson)
        active = {
          bank,
          status: { version: manifest.bank_version, generatedAt: manifest.generated_at, origin: 'cached' },
        }
        pending = Promise.resolve(bank)
        emit(true)
        return { status: 'updated', version: manifest.bank_version }
      } catch (error) {
        return { status: 'error', message: error instanceof Error ? error.message : String(error) }
      }
    },

    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}

/** Chosen once per page load; `VITE_OFFLINE` is inlined at build time. */
export const bankSource: BankSource =
  import.meta.env.VITE_OFFLINE === 'true' ? createOfflineBankSource() : createDevBankSource()
