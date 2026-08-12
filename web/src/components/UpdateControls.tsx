import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { RELEASES_URL, getAppVersion, openExternal } from '../lib/appRuntime'
import { checkForAppUpdate, promptForAppUpdate } from '../lib/appUpdate'
import { bankSource, type BankStatus, type RefreshResult } from '../lib/bankSource'
import { formatDate } from '../lib/clock'

/**
 * The offline app's two update planes, side by side with the versions they
 * move (AP-4, AP-6, AP-7, AP-10). Rendered only under `VITE_OFFLINE`; the web
 * build never imports this module.
 */

const subscribe = (listener: () => void) => bankSource.subscribe(listener)
const readStatus = () => bankSource.status()

/** Reactive view of the active bank, re-read after every hot swap. */
export function useBankStatus(): BankStatus | null {
  return useSyncExternalStore(subscribe, readStatus, readStatus)
}

function bankMessage(result: RefreshResult): { tone: 'ok' | 'warn' | 'error'; text: string } {
  switch (result.status) {
    case 'updated':
      return { tone: 'ok', text: `Bank soal diperbarui (versi ${result.version}).` }
    case 'current':
      return { tone: 'ok', text: 'Bank soal sudah terbaru.' }
    case 'offline':
      return {
        tone: 'warn',
        text: 'Tidak dapat menghubungi server bank soal — periksa koneksi internet Anda. Soal yang sudah tersimpan tetap bisa dikerjakan seperti biasa.',
      }
    case 'app-outdated':
      return {
        tone: 'warn',
        text: `Versi aplikasi terbaru diperlukan untuk soal terbaru (minimal v${result.minAppVersion}). Bank soal saat ini tetap dipakai.`,
      }
    case 'unsupported':
      return { tone: 'warn', text: 'Pembaruan bank soal tidak tersedia pada mode ini.' }
    default:
      return { tone: 'error', text: `Gagal memperbarui bank soal: ${result.message}` }
  }
}

/**
 * AP-10: one line that answers "am I current?" for both planes, next to the
 * buttons that fix it if the answer is no.
 */
export default function UpdateControls() {
  const bank = useBankStatus()
  const [appVersion, setAppVersion] = useState<string | null>(null)
  const [bankBusy, setBankBusy] = useState(false)
  const [appBusy, setAppBusy] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'warn' | 'error'; text: string } | null>(null)

  useEffect(() => {
    let cancelled = false
    void getAppVersion().then((version) => {
      if (!cancelled) setAppVersion(version)
    })
    return () => {
      cancelled = true
    }
  }, [])

  async function refreshBank(): Promise<void> {
    setBankBusy(true)
    setNotice(null)
    const result = await bankSource.refresh()
    setNotice(bankMessage(result))
    setBankBusy(false)
    // AP-5: an outdated app is exactly the case where the app update matters,
    // so offer it straight away instead of leaving the user at a dead end.
    if (result.status === 'app-outdated') await checkApp()
  }

  async function checkApp(): Promise<void> {
    setAppBusy(true)
    setNotice(null)
    const result = await checkForAppUpdate()
    switch (result.status) {
      case 'available': {
        const started = await promptForAppUpdate(result)
        if (!started) setNotice({ tone: 'warn', text: `Versi ${result.version} tersedia. Pembaruan ditunda.` })
        break
      }
      case 'current':
        setNotice({ tone: 'ok', text: `Aplikasi sudah versi terbaru (v${result.version}).` })
        break
      case 'offline':
        setNotice({ tone: 'warn', text: 'Tidak dapat memeriksa pembaruan aplikasi. Anda sedang offline.' })
        break
      case 'unsupported':
        setNotice({ tone: 'warn', text: 'Pembaruan aplikasi hanya tersedia pada aplikasi terpasang.' })
        break
      default:
        setNotice({ tone: 'error', text: `Gagal memeriksa pembaruan aplikasi: ${result.message}` })
    }
    setAppBusy(false)
  }

  return (
    <section className="card update-controls" id="pembaruan" aria-labelledby="pembaruan-title">
      <h2 className="section-title" id="pembaruan-title">
        Versi &amp; Pembaruan
      </h2>
      <p className="update-versions">
        Aplikasi v{appVersion ?? '—'} · Bank soal{' '}
        <code>{bank?.version ?? '—'}</code>
        {bank?.generatedAt ? ` (${formatDate(bank.generatedAt)})` : ''}
      </p>
      <p className="muted update-hint">
        Soal tersimpan di dalam aplikasi, jadi try out tetap bisa dikerjakan tanpa internet. Saat terhubung, aplikasi
        memeriksa paket soal baru secara otomatis.
      </p>
      <div className="stack">
        <button className="btn btn-navy btn-sm" onClick={() => void refreshBank()} disabled={bankBusy}>
          {bankBusy ? 'Memeriksa…' : 'Perbarui Bank Soal'}
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => void checkApp()} disabled={appBusy}>
          {appBusy ? 'Memeriksa…' : 'Periksa Pembaruan Aplikasi'}
        </button>
        <button className="btn btn-link" onClick={() => void openExternal(RELEASES_URL)}>
          Halaman rilis
        </button>
      </div>
      {notice ? (
        <div className={`notice ${notice.tone}`} role="status">
          {notice.text}
        </div>
      ) : null}
    </section>
  )
}

/**
 * NF-30: one check of each plane per launch, in the background, silent when
 * offline. Mounted next to the router so the toast survives navigation.
 */
export function AppUpdateWatcher() {
  const [toast, setToast] = useState<string | null>(null)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true

    void (async () => {
      const result = await bankSource.refresh()
      if (result.status === 'updated') setToast(`Bank soal diperbarui (versi ${result.version}).`)
      // AP-5: the published bank has outrun this binary — say so once, here,
      // rather than silently serving stale questions forever.
      if (result.status === 'app-outdated') {
        setToast(`Versi aplikasi terbaru diperlukan untuk soal terbaru (minimal v${result.minAppVersion}).`)
      }

      const update = await checkForAppUpdate()
      if (update.status === 'available') await promptForAppUpdate(update)
    })()
  }, [])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(null), 9_000)
    return () => window.clearTimeout(timer)
  }, [toast])

  if (!toast) return null
  return (
    <div className="toast app-toast" role="status" aria-live="polite">
      <span>{toast}</span>
      <button type="button" aria-label="Tutup pemberitahuan" onClick={() => setToast(null)}>
        ×
      </button>
    </div>
  )
}
