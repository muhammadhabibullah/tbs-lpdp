import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import DownloadApp from '../components/DownloadApp'
import InfoTooltip from '../components/InfoTooltip'
import { scrollToSection } from '../components/MenuBar'
import PackageStatisticsPopover from '../components/PackageStatisticsPopover'
import UpdateControls from '../components/UpdateControls'
import { USE_MOCK, api, errorMessage } from '../lib/api'
import { formatDate, formatDateTime, formatMinutes } from '../lib/clock'
import { BANK_UPDATED_EVENT, IS_OFFLINE_APP, isSupabaseConfigured } from '../lib/config'
import type { AttemptSummary, Package, ServiceStatus } from '../lib/types'

const MAX_SCORE = 300
/** Packages per page. Two full rows of the grid on a desktop. */
const PAGE_SIZE = 6
const DIFFICULTY_LABEL = { easy: 'Easy', medium: 'Medium', hard: 'Hard' } as const
const DIFFICULTY_HELP = {
  easy: 'Indeks kesulitan paket di bawah 1,90 berdasarkan komposisi 60 soal.',
  medium: 'Indeks kesulitan paket 1,90–2,19 berdasarkan komposisi 60 soal.',
  hard: 'Indeks kesulitan paket minimal 2,20 berdasarkan komposisi 60 soal.',
} as const

/** FE-19: shown wherever a new attempt is refused for lack of storage. */
const CAPACITY_MESSAGE =
  'Kuota penyimpanan gratis sedang penuh, jadi try out baru dihentikan sementara. Try out yang sedang berjalan tetap bisa dilanjutkan dan pembahasan lama tetap terbuka. Riwayat lama terhapus otomatis setelah 7 hari, jadi kuota biasanya tersedia lagi dalam beberapa hari.'

/** Server messages are English; the user gets Bahasa Indonesia. */
function startErrorMessage(err: unknown): string {
  switch ((err as { code?: string }).code) {
    // BE-18: capacity ran out between the page load and the click.
    case 'P0007':
      return CAPACITY_MESSAGE
    // BE-16: the hourly cap on creating attempts.
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
  const location = useLocation()
  const [packages, setPackages] = useState<Package[]>([])
  const [attempts, setAttempts] = useState<AttemptSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startingId, setStartingId] = useState<number | null>(null)
  const [status, setStatus] = useState<ServiceStatus | null>(null)
  const [page, setPage] = useState(1)
  const [openStatsPackageId, setOpenStatsPackageId] = useState<number | null>(null)
  /** AP-4: bumped when the app hot-swaps a newer bank, to re-read the catalogue. */
  const [bankRevision, setBankRevision] = useState(0)

  useEffect(() => {
    if (!IS_OFFLINE_APP) return
    const onBankUpdated = () => setBankRevision((value) => value + 1)
    window.addEventListener(BANK_UPDATED_EVENT, onBankUpdated)
    return () => window.removeEventListener(BANK_UPDATED_EVENT, onBankUpdated)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        await api.init()
        const [pkgs, history, service] = await Promise.all([
          api.listPackages(),
          api.listAttempts(),
          // Never let the capacity probe take the page down with it: a project
          // running an older schema has no get_service_status, and "unknown"
          // has to mean "open" or nobody could start anything.
          api.getServiceStatus().catch(() => null),
        ])
        if (cancelled) return
        setPackages(pkgs)
        setAttempts(history)
        setStatus(service)
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
  }, [bankRevision])

  // The menu bar routes here with the wanted anchor in the location state; the
  // sections only exist once the fetch has resolved, hence the `loading` gate.
  useEffect(() => {
    const target = (location.state as { scrollTo?: string } | null)?.scrollTo
    if (!target || loading) return
    scrollToSection(target)
  }, [location.state, loading])

  /** BE-18: null status (probe failed / old schema) is treated as accepting. */
  const atCapacity = status !== null && !status.accepting_attempts

  const pageCount = Math.max(1, Math.ceil(packages.length / PAGE_SIZE))
  const current = Math.min(page, pageCount)
  const visiblePackages = useMemo(
    () => packages.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE),
    [packages, current],
  )

  function goToPage(next: number): void {
    setPage(Math.min(Math.max(1, next), pageCount))
    scrollToSection('paket')
  }

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

      {!USE_MOCK && !IS_OFFLINE_APP && !isSupabaseConfigured ? (
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

      {/* FE-19: say it once, above the disabled buttons, rather than repeating
          the explanation on every package card. */}
      {atCapacity && error !== CAPACITY_MESSAGE ? (
        <div className="card">
          <div className="notice warn">{CAPACITY_MESSAGE}</div>
        </div>
      ) : null}

      <div className="card" id="paket">
        <div className="spread">
          <h2 className="section-title" style={{ margin: 0 }}>
            Paket Try Out
          </h2>
          {packages.length > PAGE_SIZE ? (
            <span className="muted" style={{ fontSize: 13 }}>
              Menampilkan {(current - 1) * PAGE_SIZE + 1}–{Math.min(current * PAGE_SIZE, packages.length)} dari{' '}
              {packages.length} paket
            </span>
          ) : null}
        </div>
        {loading ? (
          <div className="loading">Memuat paket…</div>
        ) : packages.length === 0 ? (
          <p className="empty-state">
            {IS_OFFLINE_APP ? (
              <>
                Bank soal belum tersedia di aplikasi ini. Sambungkan perangkat ke internet, lalu tekan{' '}
                <strong>Perbarui Bank Soal</strong> di bagian Versi &amp; Pembaruan.
              </>
            ) : (
              <>
                Belum ada paket yang dipublikasikan. Jalankan <code>push_to_supabase.py --package 1 --publish</code>{' '}
                setelah bank soal siap.
              </>
            )}
          </p>
        ) : (
          <div className="package-grid">
            {visiblePackages.map((pkg) => {
              const totalQuestions = pkg.subtests.reduce((sum, s) => sum + s.question_count, 0)
              const totalSeconds = pkg.subtests.reduce((sum, s) => sum + s.duration_seconds, 0)
              return (
                <article className="package-card" key={pkg.id}>
                  <PackageStatisticsPopover
                    pkg={pkg}
                    open={openStatsPackageId === pkg.id}
                    onOpenChange={(open) => setOpenStatsPackageId(open ? pkg.id : null)}
                  />
                  <h3>{pkg.title}</h3>
                  <div className="package-meta" aria-label="Metadata paket soal">
                    <InfoTooltip
                      className={`difficulty-${pkg.difficulty}`}
                      label={DIFFICULTY_LABEL[pkg.difficulty]}
                    >
                      <strong>{DIFFICULTY_LABEL[pkg.difficulty]}.</strong> {DIFFICULTY_HELP[pkg.difficulty]} Label ini
                      menggambarkan komposisi paket, bukan prediksi skor setiap peserta.
                    </InfoTooltip>
                    <InfoTooltip label={`AI: ${pkg.ai_model}`}>
                      <strong>Dikembangkan oleh {pkg.ai_company}.</strong> {pkg.ai_model_description} Label model bukan
                      jaminan tingkat kesulitan; soal tetap divalidasi dan ditinjau sebelum dipublikasikan.
                    </InfoTooltip>
                    <span className="package-badge">
                      Versi {pkg.question_version} · diperbarui {formatDate(pkg.last_updated_at)}
                    </span>
                  </div>
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
                    disabled={startingId !== null || atCapacity}
                    title={atCapacity ? CAPACITY_MESSAGE : undefined}
                  >
                    {atCapacity ? 'Kuota Penuh' : startingId === pkg.id ? 'Menyiapkan…' : 'Mulai Try Out'}
                  </button>
                </article>
              )
            })}
          </div>
        )}

        {pageCount > 1 ? (
          <nav className="pagination" aria-label="Halaman paket try out">
            <button className="btn btn-ghost btn-sm" onClick={() => goToPage(current - 1)} disabled={current === 1}>
              ◀ Sebelumnya
            </button>
            <span className="pagination-pages">
              {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  className={`page-dot ${n === current ? 'active' : ''}`}
                  onClick={() => goToPage(n)}
                  aria-current={n === current ? 'page' : undefined}
                  aria-label={`Halaman ${n}`}
                >
                  {n}
                </button>
              ))}
            </span>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => goToPage(current + 1)}
              disabled={current === pageCount}
            >
              Selanjutnya ▶
            </button>
          </nav>
        ) : null}
      </div>

      <div className="card" id="riwayat">
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
                    <td>
                      {attempt.package_title}
                      <span className="history-version">Versi {attempt.package_version}</span>
                    </td>
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

      {/* FE-42 on the web, AP-10 in the app — never both. */}
      {IS_OFFLINE_APP ? <UpdateControls /> : <DownloadApp />}

      <section className="card seo-overview" id="tentang" aria-labelledby="tentang-title">
        <h2 className="section-title" id="tentang-title">
          Tentang Try Out TBS LPDP
        </h2>
        <p>
          Tes Bakat Skolastik (TBS) LPDP menguji tiga kemampuan: penalaran verbal, penalaran kuantitatif, dan
          pemecahan masalah. Try out gratis ini membantu Anda berlatih dalam alur tes yang terukur sebelum menghadapi
          seleksi sebenarnya.
        </p>
        <div className="seo-facts" aria-label="Ringkasan simulasi TBS LPDP">
          <div>
            <strong>60 soal</strong>
            <span>tiga mata uji berurutan</span>
          </div>
          <div>
            <strong>90 menit</strong>
            <span>waktu simulasi penuh</span>
          </div>
          <div>
            <strong>Skor &amp; pembahasan</strong>
            <span>tersedia setelah tes selesai</span>
          </div>
        </div>

        <h3>Pertanyaan umum</h3>
        <div className="seo-faq">
          <details>
            <summary>Apa itu TBS LPDP?</summary>
            <p>
              TBS LPDP adalah Tes Bakat Skolastik yang mengukur penalaran verbal, penalaran kuantitatif, dan
              pemecahan masalah.
            </p>
          </details>
          <details>
            <summary>Apakah try out TBS LPDP ini gratis?</summary>
            <p>Ya. Seluruh paket try out, skor otomatis, dan pembahasan dapat digunakan tanpa biaya.</p>
          </details>
          <details>
            <summary>Berapa jumlah soal dan durasi try out?</summary>
            <p>Satu paket berisi 60 soal dalam tiga mata uji berurutan dengan total waktu 90 menit.</p>
          </details>
          <details>
            <summary>Apakah situs ini merupakan layanan resmi LPDP?</summary>
            <p>Bukan. Situs ini adalah sarana latihan gratis dan mandiri, bukan produk resmi LPDP atau PUSMENDIK.</p>
          </details>
        </div>
      </section>
    </AppShell>
  )
}
