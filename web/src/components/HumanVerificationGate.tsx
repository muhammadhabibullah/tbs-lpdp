import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { USE_MOCK, api, errorMessage } from '../lib/api'
import {
  HUMAN_VERIFICATION_REQUIRED,
  TURNSTILE_SITE_KEY,
} from '../lib/config'

const TURNSTILE_SCRIPT_ID = 'cloudflare-turnstile-script'
const TURNSTILE_SCRIPT_URL = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'

interface TurnstileOptions {
  sitekey: string
  callback: (token: string) => void
  'error-callback': () => void
  'expired-callback': () => void
  action: string
  appearance: 'always' | 'execute' | 'interaction-only'
  language: string
  theme: 'auto' | 'light' | 'dark'
}

interface TurnstileApi {
  render(container: HTMLElement, options: TurnstileOptions): string
  remove(widgetId: string): void
  reset(widgetId: string): void
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
  }
}

let scriptPromise: Promise<TurnstileApi> | null = null

function loadTurnstile(): Promise<TurnstileApi> {
  if (window.turnstile) return Promise.resolve(window.turnstile)
  if (scriptPromise) return scriptPromise

  const pending = new Promise<TurnstileApi>((resolve, reject) => {
    const existing = document.getElementById(TURNSTILE_SCRIPT_ID) as HTMLScriptElement | null
    const script = existing ?? document.createElement('script')

    const onLoad = () => {
      if (window.turnstile) resolve(window.turnstile)
      else reject(new Error('Turnstile tidak tersedia setelah skrip dimuat.'))
    }
    const onError = () => reject(new Error('Skrip verifikasi tidak dapat dimuat.'))

    script.addEventListener('load', onLoad, { once: true })
    script.addEventListener('error', onError, { once: true })
    if (!existing) {
      script.id = TURNSTILE_SCRIPT_ID
      script.src = TURNSTILE_SCRIPT_URL
      script.async = true
      script.defer = true
      document.head.appendChild(script)
    }
  }).catch((error) => {
    // A privacy extension or transient network failure may block the script.
    // Let the visible retry action make one fresh attempt.
    document.getElementById(TURNSTILE_SCRIPT_ID)?.remove()
    scriptPromise = null
    throw error
  })
  scriptPromise = pending

  return pending
}

type Phase = 'checking' | 'challenge' | 'verified' | 'error'

/**
 * FE-39: authenticates before mounting any content route. Existing sessions
 * pass silently; only creation of a new anonymous identity shows Turnstile.
 */
export default function HumanVerificationGate({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>('checking')
  const [message, setMessage] = useState('')
  const challengeRef = useRef<HTMLDivElement>(null)
  const widgetIdRef = useRef<string | null>(null)
  const mountedRef = useRef(true)
  const authenticatingRef = useRef(false)

  const authenticate = useCallback(async (captchaToken?: string) => {
    if (authenticatingRef.current) return
    authenticatingRef.current = true
    if (mountedRef.current) {
      setPhase('checking')
      setMessage('')
    }
    try {
      await api.init(captchaToken)
      if (mountedRef.current) setPhase('verified')
    } catch (error) {
      if (!mountedRef.current) return
      const code = (error as { code?: string }).code
      if (code === HUMAN_VERIFICATION_REQUIRED && TURNSTILE_SITE_KEY) {
        setPhase('challenge')
      } else {
        setMessage(errorMessage(error))
        setPhase('error')
      }
    } finally {
      authenticatingRef.current = false
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    void authenticate()
    return () => {
      mountedRef.current = false
    }
  }, [authenticate])

  useEffect(() => {
    const siteKey = TURNSTILE_SITE_KEY
    if (phase !== 'challenge' || !siteKey || !challengeRef.current) return
    let cancelled = false
    let renderedWidgetId: string | null = null

    void loadTurnstile()
      .then((turnstile) => {
        if (cancelled || !challengeRef.current) return
        renderedWidgetId = turnstile.render(challengeRef.current, {
          sitekey: siteKey,
          action: 'anonymous-sign-in',
          appearance: 'always',
          language: 'id',
          theme: 'auto',
          callback: (token) => void authenticate(token),
          'expired-callback': () => {
            if (renderedWidgetId) turnstile.reset(renderedWidgetId)
          },
          'error-callback': () => {
            if (!cancelled) setMessage('Verifikasi gagal dimuat. Periksa koneksi, lalu coba lagi.')
          },
        })
        widgetIdRef.current = renderedWidgetId
      })
      .catch((error) => {
        if (!cancelled) {
          setMessage(errorMessage(error))
          setPhase('error')
        }
      })

    return () => {
      cancelled = true
      if (renderedWidgetId && window.turnstile) window.turnstile.remove(renderedWidgetId)
      if (widgetIdRef.current === renderedWidgetId) widgetIdRef.current = null
    }
  }, [authenticate, phase])

  // Mock mode never loads a third-party challenge, even if a developer keeps
  // the production site key in their local environment.
  if (USE_MOCK || phase === 'verified') return <>{children}</>

  return (
    <main className="human-verification-page">
      <section className="card human-verification-card" aria-labelledby="human-verification-title">
        <div className="human-verification-icon" aria-hidden="true">✓</div>
        <p className="human-verification-eyebrow">Perlindungan robot</p>
        <h1 id="human-verification-title">Verifikasi akses</h1>
        {phase === 'challenge' ? (
          <>
            <p>Selesaikan pemeriksaan singkat ini untuk membuka paket try out.</p>
            <div className="turnstile-widget" ref={challengeRef} />
            {message ? (
              <>
                <div className="notice error" role="alert">{message}</div>
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={() => {
                    setMessage('')
                    if (widgetIdRef.current && window.turnstile) window.turnstile.reset(widgetIdRef.current)
                  }}
                >
                  Coba lagi
                </button>
              </>
            ) : null}
          </>
        ) : phase === 'error' ? (
          <>
            <p className="notice error" role="alert">{message || 'Verifikasi tidak dapat diselesaikan.'}</p>
            <button className="btn btn-primary" type="button" onClick={() => void authenticate()}>
              Coba lagi
            </button>
          </>
        ) : (
          <div className="loading" role="status">Memeriksa sesi aman…</div>
        )}
        <p className="human-verification-note">
          Pemeriksaan oleh Cloudflare Turnstile ini membantu mencegah pengambilan soal otomatis dan penyalahgunaan
          layanan.
        </p>
      </section>
    </main>
  )
}
