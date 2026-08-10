import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import LaporSoal, { REASON_LABELS } from '../components/LaporSoal'
import Passage from '../components/Passage'
import { api, errorMessage, withRetry } from '../lib/api'
import { formatDateTime } from '../lib/clock'
import { OPTION_KEYS } from '../lib/types'
import type { QuestionReport, ReportReason, Review, ReviewQuestion } from '../lib/types'

const MAX_SCORE = 300
type Filter = 'all' | 'wrong' | 'blank' | 'doubt' | 'reported'

const FILTER_LABELS: Record<Filter, string> = {
  all: 'Semua soal',
  wrong: 'Jawaban salah',
  blank: 'Tidak dijawab',
  doubt: 'Ditandai ragu-ragu',
  reported: 'Dilaporkan',
}

function matches(question: ReviewQuestion, filter: Filter): boolean {
  switch (filter) {
    case 'wrong':
      return question.selected_option !== null && question.selected_option !== question.correct_option
    case 'blank':
      return question.selected_option === null
    case 'doubt':
      return question.is_doubtful
    case 'reported':
      return Boolean(question.my_report)
    default:
      return true
  }
}

/** Server messages are English; the user gets Bahasa Indonesia (v2 §5.1). */
function reportErrorMessage(err: unknown): string {
  switch ((err as { code?: string }).code) {
    case 'P0002':
      return 'Soal ini belum bisa dilaporkan. Selesaikan mata ujinya terlebih dahulu.'
    case 'P0005':
      return 'Terlalu banyak laporan dalam satu jam. Coba lagi nanti.'
    case 'P0006':
      return 'Periksa kembali isian laporan Anda.'
    default:
      return `Laporan gagal dikirim: ${errorMessage(err)}`
  }
}

/** FE-8: score summary + per-question review with all five explanations. */
export default function ReviewPage() {
  const { attemptId = '' } = useParams()
  const [review, setReview] = useState<Review | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeSubtest, setActiveSubtest] = useState<string | null>(null)
  const [filter, setFilter] = useState<Filter>('all')
  // v2: the question whose report dialog is open, plus its in-flight state.
  const [reportingId, setReportingId] = useState<string | null>(null)
  const [reportConfirmDelete, setReportConfirmDelete] = useState(false)
  const [reportBusy, setReportBusy] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [packageTitle, setPackageTitle] = useState('')
  /** True for the one render that feeds the print dialog. */
  const [printing, setPrinting] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        await api.init()
        const data = await api.getReview(attemptId)
        if (cancelled) return
        setReview(data)
        setActiveSubtest(data.sections[0]?.subtest.id ?? null)
        // Only for the heading and the PDF filename, so a failure is ignored;
        // listPackages is cached per page load, so this is usually free.
        api
          .listPackages()
          .then((pkgs) => {
            if (!cancelled) setPackageTitle(pkgs.find((p) => p.id === data.attempt.package_id)?.title ?? '')
          })
          .catch(() => undefined)
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
  }, [attemptId])

  /**
   * FE-20: hand the whole Pembahasan to the browser's own print dialog, which
   * is where "Save as PDF" lives. No new dependency and no server: the print
   * stylesheet does the work, and the expanded render below makes sure the PDF
   * carries every subtest and every question rather than whatever tab and
   * filter happened to be open.
   */
  useEffect(() => {
    if (!printing) return
    const previousTitle = document.title
    // Chrome seeds the PDF filename from the document title.
    document.title = `Pembahasan — ${packageTitle || `Paket ${review?.attempt.package_id ?? ''}`}`
    const done = () => setPrinting(false)
    window.addEventListener('afterprint', done)
    // one frame, so the expanded DOM is committed before the dialog blocks
    const timer = window.setTimeout(() => window.print(), 60)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('afterprint', done)
      document.title = previousTitle
    }
  }, [printing, packageTitle, review])

  const section = useMemo(
    () => review?.sections.find((s) => s.subtest.id === activeSubtest) ?? review?.sections[0] ?? null,
    [review, activeSubtest],
  )

  const visible = useMemo(() => (section ? section.questions.filter((q) => matches(q, filter)) : []), [section, filter])

  const reportingQuestion = useMemo(
    () => review?.sections.flatMap((s) => s.questions).find((q) => q.id === reportingId) ?? null,
    [review, reportingId],
  )

  function openReport(questionId: string, confirmDelete = false): void {
    setReportingId(questionId)
    setReportConfirmDelete(confirmDelete)
    setReportError(null)
  }

  /** Writes the report back into the loaded review, so no refetch is needed. */
  function patchReport(questionId: string, report: QuestionReport | null): void {
    setReview((prev) =>
      prev
        ? {
            ...prev,
            sections: prev.sections.map((s) => ({
              ...s,
              questions: s.questions.map((q) => (q.id === questionId ? { ...q, my_report: report } : q)),
            })),
          }
        : prev,
    )
  }

  // FE-13: on failure the dialog stays open with everything the user typed.
  async function submitReport(reason: ReportReason, comment: string): Promise<void> {
    if (!reportingId) return
    setReportBusy(true)
    setReportError(null)
    try {
      const report = await withRetry(() => api.reportQuestion(reportingId, reason, comment, attemptId))
      patchReport(reportingId, report)
      setReportingId(null)
    } catch (err) {
      setReportError(reportErrorMessage(err))
    } finally {
      setReportBusy(false)
    }
  }

  async function withdrawReport(): Promise<void> {
    if (!reportingId) return
    setReportBusy(true)
    setReportError(null)
    try {
      await withRetry(() => api.deleteQuestionReport(reportingId))
      patchReport(reportingId, null)
      setReportingId(null)
    } catch (err) {
      setReportError(reportErrorMessage(err))
    } finally {
      setReportBusy(false)
    }
  }

  if (loading) {
    return (
      <AppShell>
        <div className="card loading">Memuat hasil…</div>
      </AppShell>
    )
  }

  if (error || !review) {
    return (
      <AppShell>
        <div className="card">
          <div className="notice error">{error ?? 'Hasil tidak ditemukan.'}</div>
          <Link to="/">← Kembali ke daftar paket</Link>
        </div>
      </AppShell>
    )
  }

  if (review.sections.length === 0) {
    return (
      <AppShell>
        <div className="card">
          <p className="empty-state">
            Belum ada mata uji yang diselesaikan pada percobaan ini. Pembahasan terbuka setelah sebuah mata uji
            diakhiri.
          </p>
          <Link className="btn btn-navy" to={`/attempt/${attemptId}`}>
            Lanjutkan tes
          </Link>
        </div>
      </AppShell>
    )
  }

  const totalScore = review.attempt.total_score ?? review.sections.reduce((sum, s) => sum + s.score, 0)
  const finished = review.attempt.status === 'finished'
  const passingTotal = review.sections.reduce((sum, s) => sum + s.subtest.passing_grade, 0)

  return (
    <AppShell>
      {/* Print-only masthead: a PDF with no title is a PDF nobody can file. */}
      <div className="print-header">
        <strong>Pembahasan — {packageTitle || 'TBS LPDP Try Out'}</strong>
        <span>Dikerjakan {formatDateTime(review.attempt.started_at)}</span>
      </div>

      <div className="card">
        <div className="score-hero">
          <div>
            <h1 style={{ margin: '0 0 4px', fontSize: 23 }}>{finished ? 'Hasil Try Out' : 'Hasil Sementara'}</h1>
            {packageTitle ? <p className="muted" style={{ margin: '0 0 4px' }}>{packageTitle}</p> : null}
            <p className="muted" style={{ margin: 0 }}>
              {finished
                ? 'Seluruh mata uji telah selesai. Ambang skor bersifat indikatif — seleksi LPDP berbasis peringkat.'
                : 'Sebagian mata uji sudah selesai. Skor akhir muncul setelah seluruh mata uji dikerjakan.'}
            </p>
          </div>
          <div className="score-total">
            <span className="big">{totalScore}</span>
            <span className="max">/ {MAX_SCORE}</span>
          </div>
        </div>

        <div className="score-cards">
          {review.sections.map((s) => {
            const max = s.questions.length * 5
            const correct = s.questions.filter((q) => q.selected_option === q.correct_option).length
            const passed = s.score >= s.subtest.passing_grade
            return (
              <div className="score-card" key={s.subtest.id}>
                <h4>{s.subtest.name}</h4>
                <div className="val">
                  {s.score}
                  <span className="sub"> / {max}</span>
                </div>
                <div className="meter">
                  <span className={passed ? undefined : 'below'} style={{ width: `${max ? (s.score / max) * 100 : 0}%` }} />
                </div>
                <div className="sub">
                  {correct} benar dari {s.questions.length} · ambang {s.subtest.passing_grade} ·{' '}
                  {passed ? 'terlampaui' : 'belum terlampaui'}
                </div>
              </div>
            )
          })}
        </div>

        <div className="spread" style={{ marginTop: 18 }}>
          <span className="muted">
            Total ambang indikatif untuk mata uji yang selesai: <strong>{passingTotal}</strong>
          </span>
          <Link className="btn btn-ghost btn-sm" to="/">
            Kembali ke beranda
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="spread" style={{ marginBottom: 14 }}>
          <h2 className="section-title" style={{ margin: 0 }}>
            Pembahasan
          </h2>
          <button
            className="btn btn-ghost btn-sm no-print"
            onClick={() => setPrinting(true)}
            disabled={printing}
            title="Membuka dialog cetak — pilih “Save as PDF” untuk mengunduh"
          >
            {printing ? 'Menyiapkan…' : '⤓ Unduh PDF'}
          </button>
        </div>

        <div className="review-filters" style={{ marginBottom: 12 }}>
          {review.sections.map((s) => (
            <button
              key={s.subtest.id}
              className={`chip ${section?.subtest.id === s.subtest.id ? 'active' : ''}`}
              onClick={() => setActiveSubtest(s.subtest.id)}
            >
              {s.subtest.name}
            </button>
          ))}
        </div>

        <div className="review-filters">
          {(Object.keys(FILTER_LABELS) as Filter[]).map((key) => (
            <button key={key} className={`chip ${filter === key ? 'active' : ''}`} onClick={() => setFilter(key)}>
              {FILTER_LABELS[key]}
              {section ? ` (${section.questions.filter((q) => matches(q, key)).length})` : ''}
            </button>
          ))}
        </div>

        <div style={{ marginTop: 16 }}>
          {printing ? (
            // The PDF carries the whole attempt, not the tab and filter that
            // happen to be open — nobody prints a subset on purpose.
            review.sections.map((s) => (
              <section className="print-section" key={s.subtest.id}>
                <h3 className="print-subtest">
                  {s.subtest.name} — {s.score} poin
                </h3>
                {s.questions.map(renderQuestion)}
              </section>
            ))
          ) : visible.length === 0 ? (
            <p className="empty-state">Tidak ada soal pada filter ini.</p>
          ) : (
            visible.map(renderQuestion)
          )}
        </div>
      </div>

      {reportingQuestion ? (
        <LaporSoal
          key={reportingQuestion.id}
          questionNumber={reportingQuestion.number}
          existing={reportingQuestion.my_report}
          initialConfirmDelete={reportConfirmDelete}
          submitting={reportBusy}
          error={reportError}
          onCancel={() => setReportingId(null)}
          onSubmit={(reason, comment) => void submitReport(reason, comment)}
          onDelete={() => void withdrawReport()}
        />
      ) : null}
    </AppShell>
  )

  function renderQuestion(question: ReviewQuestion) {
    const correct = question.selected_option === question.correct_option
    const blank = question.selected_option === null
    return (
              <article className="review-question" key={question.id}>
                  <header>
                    <h4>Soal nomor {question.number}</h4>
                    <span className={`tag ${blank ? 'blank' : correct ? 'correct' : 'wrong'}`}>
                      {blank ? 'Tidak dijawab' : correct ? 'Benar +5' : 'Salah 0'}
                    </span>
                    <span className="tag">{question.qtype.replace(/_/g, ' ')}</span>
                    {question.is_doubtful ? <span className="tag doubt">Ragu-ragu</span> : null}

                    {/* FE-11/FE-13: the only report entry point in the app. */}
                    <span className="report-slot">
                      {question.my_report ? (
                        <>
                          <span className="tag reported" title={REASON_LABELS[question.my_report.reason]}>
                            ✓ Sudah dilaporkan
                          </span>
                          <button className="btn btn-link" onClick={() => openReport(question.id)}>
                            Ubah
                          </button>
                          <button className="btn btn-link-danger" onClick={() => openReport(question.id, true)}>
                            Batalkan laporan
                          </button>
                        </>
                      ) : (
                        <button className="btn btn-ghost btn-sm" onClick={() => openReport(question.id)}>
                          Laporkan soal
                        </button>
                      )}
                    </span>
                  </header>

                  {question.passage ? <Passage text={question.passage} /> : null}
                  <p className="question-text">{question.question_text}</p>
                  {question.image_url ? (
                    <img className="question-image" src={question.image_url} alt={`Gambar soal ${question.number}`} />
                  ) : null}

                  <div>
                    {OPTION_KEYS.map((key) => {
                      const option = question.options.find((o) => o.key === key)
                      if (!option) return null
                      const isCorrect = key === question.correct_option
                      const isPicked = key === question.selected_option
                      return (
                        <div
                          key={key}
                          className={`review-option ${isCorrect ? 'is-correct' : ''} ${isPicked ? 'is-picked' : ''}`}
                        >
                          <span className="key">{key}</span>
                          <span className="text">
                            {option.text}
                            {isPicked ? <strong className="muted"> — jawaban Anda</strong> : null}
                            {isCorrect ? <strong style={{ color: '#1c7a41' }}> — kunci jawaban</strong> : null}
                            <span className="why">{question.explanations[key]}</span>
                          </span>
                        </div>
                      )
                    })}
                  </div>
              </article>
    )
  }
}
