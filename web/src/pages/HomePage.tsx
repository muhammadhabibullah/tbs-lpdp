import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { USE_MOCK, api, errorMessage } from '../lib/api'
import { formatDateTime, formatMinutes } from '../lib/clock'
import { isSupabaseConfigured } from '../lib/config'
import type { AttemptSummary, Package } from '../lib/types'

const MAX_SCORE = 300

/** Server messages are English; the user gets Bahasa Indonesia. */
function startErrorMessage(err: unknown): string {
  switch ((err as { code?: string }).code) {
    // BE-15: the hourly cap on creating attempts.
    case 'P0005':
      return 'Terlalu banyak try out dibuka dalam satu jam. Coba lagi nanti, atau lanjutkan try out yang masih berjalan di bawah.'
    case 'P0002':
      return 'Paket ini sedang tidak tersedia. Muat ulang halaman dan coba lagi.'
    default:
      return `Gagal memulai try out: ${errorMessage(err)}`
  }
}

export default function HomePage() {
  const navigate = useNavigate()
  const [packages, setPackages] = useState<Package[]>([])
  const [attempts, setAttempts] = useState<AttemptSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startingId, setStartingId] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        await api.init()
        const [pkgs, history] = await Promise.all([api.listPackages(), api.listAttempts()])
        if (cancelled) return
        setPackages(pkgs)
        setAttempts(history)
      } catch (err) {
        if (!cancelled) setError(errorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  async function start(packageId: number) {
    setStartingId(packageId)
    setError(null)
    try {
      const { attempt } = await api.startAttempt(packageId)
      navigate(`/attempt/${attempt.id}`)
    } catch (err) {
      setError(startErrorMessage(err))
      setStartingId(null)
    }
  }

  return (
    <AppShell>
      <div className="card home-hero">
        <h1>Try Out Tes Bakat Skolastik LPDP</h1>
        <p>
          Simulasi gratis dengan format dan tampilan menyerupai aplikasi CBT resmi: tiga mata uji berurutan, total 60
          soal dalam 90 menit. Nilai dan pembahasan lengkap tersedia segera setelah tes selesai.
        </p>
      </div>

      {!USE_MOCK && !isSupabaseConfigured ? (
        <div className="card">
          <div className="notice error">
            Backend belum dikonfigurasi. Set <code>VITE_SUPABASE_URL</code> dan{' '}
            <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> (lihat <code>web/.env.example</code>), atau jalankan mode mock
            dengan <code>VITE_USE_MOCK=true</code>.
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="card">
          <div className="notice error">{error}</div>
        </div>
      ) : null}

      <div className="card">
        <h2 className="section-title">Paket Try Out</h2>
        {loading ? (
          <div className="loading">Memuat paket…</div>
        ) : packages.length === 0 ? (
          <p className="empty-state">
            Belum ada paket yang dipublikasikan. Jalankan <code>push_to_supabase.py --package 1 --publish</code> setelah
            bank soal siap.
          </p>
        ) : (
          <div className="package-grid">
            {packages.map((pkg) => {
              const totalQuestions = pkg.subtests.reduce((sum, s) => sum + s.question_count, 0)
              const totalSeconds = pkg.subtests.reduce((sum, s) => sum + s.duration_seconds, 0)
              return (
                <article className="package-card" key={pkg.id}>
                  <h3>{pkg.title}</h3>
                  <p>{pkg.description}</p>
                  <ul className="subtest-list">
                    {pkg.subtests.map((subtest) => (
                      <li key={subtest.id}>
                        <span>
                          {subtest.position}. {subtest.name}
                        </span>
                        <span>
                          {subtest.question_count} soal · {formatMinutes(subtest.duration_seconds)}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <div className="total-row">
                    <span>Total</span>
                    <span>
                      {totalQuestions} soal · {formatMinutes(totalSeconds)}
                    </span>
                  </div>
                  <button
                    className="btn btn-navy btn-block btn-lg"
                    onClick={() => void start(pkg.id)}
                    disabled={startingId !== null}
                  >
                    {startingId === pkg.id ? 'Menyiapkan…' : 'Mulai Try Out'}
                  </button>
                </article>
              )
            })}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="section-title">Riwayat Pengerjaan</h2>
        {loading ? (
          <div className="loading">Memuat riwayat…</div>
        ) : attempts.length === 0 ? (
          <p className="empty-state">Belum ada riwayat. Mulai try out pertama Anda di atas.</p>
        ) : (
          <div className="table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Paket</th>
                  <th>Mulai</th>
                  <th>Status</th>
                  <th>Skor</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {attempts.map((attempt) => (
                  <tr key={attempt.id}>
                    <td>{attempt.package_title}</td>
                    <td className="muted">{formatDateTime(attempt.started_at)}</td>
                    <td>
                      <span className={`pill ${attempt.status}`}>
                        {attempt.status === 'finished'
                          ? 'Selesai'
                          : `Berjalan · ${attempt.finished_sections}/${attempt.total_sections} mata uji`}
                      </span>
                    </td>
                    <td>
                      {attempt.total_score === null ? (
                        <span className="muted">—</span>
                      ) : (
                        <strong>
                          {attempt.total_score}
                          <span className="muted"> / {MAX_SCORE}</span>
                        </strong>
                      )}
                    </td>
                    <td>
                      <div className="stack">
                        {attempt.status === 'active' ? (
                          <Link className="btn btn-cyan btn-sm" to={`/attempt/${attempt.id}`}>
                            Lanjutkan
                          </Link>
                        ) : null}
                        {attempt.finished_sections > 0 ? (
                          <Link className="btn btn-ghost btn-sm" to={`/attempt/${attempt.id}/review`}>
                            Pembahasan
                          </Link>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  )
}
