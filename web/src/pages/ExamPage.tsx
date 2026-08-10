import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import AppShell from '../components/AppShell'
import DaftarSoal from '../components/DaftarSoal'
import type { AnswerMap } from '../components/DaftarSoal'
import InformasiSoal from '../components/InformasiSoal'
import KonfirmasiTes from '../components/KonfirmasiTes'
import Passage from '../components/Passage'
import SisaWaktu from '../components/SisaWaktu'
import { api, errorMessage, withRetry } from '../lib/api'
import { remainingMs } from '../lib/clock'
import type { ActiveSection, OptionKey } from '../lib/types'

const FONT_SCALES = [0.9, 1, 1.18]
const FONT_STEP_KEY = 'tbs-lpdp.font-step'
/** Long enough to collapse a burst of corrections, short enough to lose nothing. */
const SAVE_DEBOUNCE_MS = 400

export default function ExamPage({
  packageTitle,
  section,
  onSectionFinished,
}: {
  packageTitle: string
  section: ActiveSection
  onSectionFinished: () => void
}) {
  const { section_attempt: sectionAttempt, subtest, questions } = section

  const [answers, setAnswers] = useState<AnswerMap>(() =>
    Object.fromEntries(
      section.answers.map((a) => [a.question_id, { selected_option: a.selected_option, is_doubtful: a.is_doubtful }]),
    ),
  )
  const [index, setIndex] = useState(0)
  const [fontStep, setFontStep] = useState(() => {
    const raw = localStorage.getItem(FONT_STEP_KEY)
    const stored = raw === null ? Number.NaN : Number(raw)
    return Number.isInteger(stored) && stored >= 0 && stored < FONT_SCALES.length ? stored : 1
  })
  const [showDaftar, setShowDaftar] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [warning, setWarning] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [finishing, setFinishing] = useState(false)
  const finishedRef = useRef(false)
  const cardRef = useRef<HTMLDivElement>(null)
  const mountedRef = useRef(false)
  /** question_id → option waiting to be written; drained by flushSaves(). */
  const pendingSaves = useRef(new Map<string, OptionKey | null>())
  const saveTimer = useRef<number | null>(null)

  const question = questions[index]
  const isLast = index === questions.length - 1
  const current = question ? answers[question.id] : undefined
  const answeredCount = useMemo(
    () => questions.filter((q) => answers[q.id]?.selected_option).length,
    [questions, answers],
  )
  const doubtCount = useMemo(() => questions.filter((q) => answers[q.id]?.is_doubtful).length, [questions, answers])

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 1800)
    return () => clearTimeout(id)
  }, [toast])

  // On a phone the card is taller than the screen, so moving to another
  // question would otherwise leave the user parked at the previous answer.
  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true
      return
    }
    const card = cardRef.current
    if (!card) return
    window.scrollTo({ top: Math.max(0, card.getBoundingClientRect().top + window.scrollY) })
  }, [index])

  /** Section is over server-side: leave the screen, the grade is already stored. */
  const leaveSection = useCallback(() => {
    if (finishedRef.current) return
    finishedRef.current = true
    onSectionFinished()
  }, [onSectionFinished])

  const handleWriteError = useCallback(
    (err: unknown) => {
      const code = (err as { code?: string }).code
      if (code === 'P0004' || code === 'P0003') {
        leaveSection()
        return
      }
      setWarning(`Jawaban terakhir belum tersimpan di server (${errorMessage(err)}). Coba pilih ulang jawabannya.`)
    },
    [leaveSection],
  )

  /**
   * Write every queued answer now and return whether all of them landed.
   * Safe to call at any time: with nothing queued it is a no-op.
   */
  const flushSaves = useCallback(async (): Promise<boolean> => {
    if (saveTimer.current !== null) {
      clearTimeout(saveTimer.current)
      saveTimer.current = null
    }
    const queued = [...pendingSaves.current.entries()]
    if (queued.length === 0) return true
    pendingSaves.current.clear()

    const results = await Promise.all(
      queued.map(([questionId, option]) =>
        withRetry(() => api.saveAnswer(sectionAttempt.id, questionId, option))
          .then(() => true)
          .catch((err) => {
            handleWriteError(err)
            return false
          }),
      ),
    )
    const ok = results.every(Boolean)
    if (ok) setWarning(null)
    return ok
  }, [handleWriteError, sectionAttempt.id])

  // Leaving the question — or the screen — settles whatever is still queued.
  useEffect(() => () => void flushSaves(), [index, flushSaves])

  // A phone switching apps mid-exam must not strand the last answer in the
  // debounce window; `pagehide` also covers Safari's back-forward cache.
  useEffect(() => {
    const settle = () => void flushSaves()
    const onVisibility = () => {
      if (document.hidden) settle()
    }
    window.addEventListener('pagehide', settle)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      window.removeEventListener('pagehide', settle)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [flushSaves])

  const finish = useCallback(
    async (auto: boolean) => {
      if (finishedRef.current || finishing) return
      setFinishing(true)
      // Never grade a section while an answer is still sitting in the queue.
      await flushSaves()
      // A rejected flush past the deadline already left the section (P0004).
      if (finishedRef.current) return
      try {
        await withRetry(() => api.finishSection(sectionAttempt.id))
      } catch (err) {
        const code = (err as { code?: string }).code
        // Past the deadline the server has already graded this section.
        if (!auto && code !== 'P0003') {
          setFinishing(false)
          setWarning(`Gagal mengakhiri mata uji: ${errorMessage(err)}. Silakan coba lagi.`)
          return
        }
      }
      finishedRef.current = true
      onSectionFinished()
    },
    [finishing, flushSaves, onSectionFinished, sectionAttempt.id],
  )

  // FE-7: at 0 the section auto-submits with whatever has been saved.
  const handleExpire = useCallback(() => {
    if (!finishedRef.current) void finish(true)
  }, [finish])

  function selectOption(option: OptionKey) {
    if (!question || finishedRef.current) return
    setAnswers((prev) => ({
      ...prev,
      [question.id]: { selected_option: option, is_doubtful: prev[question.id]?.is_doubtful ?? false },
    }))
    // NF-2: optimistic UI, RPC in the background — debounced, so correcting an
    // answer twice in a row costs one write (and one event row) instead of three.
    pendingSaves.current.set(question.id, option)
    if (saveTimer.current !== null) clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => void flushSaves(), SAVE_DEBOUNCE_MS)
  }

  function saveNow() {
    if (!question) return
    // A queued option is the newest intent — newer than `answers`, which this
    // closure may have captured before the last click re-rendered the page.
    const option = pendingSaves.current.get(question.id) ?? answers[question.id]?.selected_option ?? null
    if (!option) {
      setToast('Pilih salah satu jawaban terlebih dahulu')
      return
    }
    // Explicit save: skip the debounce and only claim success if it landed.
    pendingSaves.current.set(question.id, option)
    void flushSaves().then((ok) => {
      if (ok) setToast('Jawaban tersimpan')
    })
  }

  function toggleDoubt() {
    if (!question || finishedRef.current) return
    const next = !(answers[question.id]?.is_doubtful ?? false)
    setAnswers((prev) => ({
      ...prev,
      [question.id]: { selected_option: prev[question.id]?.selected_option ?? null, is_doubtful: next },
    }))
    withRetry(() => api.toggleDoubt(sectionAttempt.id, question.id, next))
      .then(() => setWarning(null))
      .catch(handleWriteError)
  }

  function changeFont(step: number) {
    setFontStep(step)
    localStorage.setItem(FONT_STEP_KEY, String(step))
  }

  if (!question) {
    return (
      <AppShell hideFeedback>
        <div className="card">
          <p className="empty-state">
            Mata uji <strong>{subtest.name}</strong> belum memiliki soal di bank. Jalankan generator soal terlebih
            dahulu.
          </p>
          <button className="btn btn-navy" onClick={() => void finish(false)}>
            Lewati mata uji ini
          </button>
        </div>
      </AppShell>
    )
  }

  const frameStyle = { '--font-scale': String(FONT_SCALES[fontStep]) } as CSSProperties

  return (
    <AppShell hideFeedback>
      <div className="card exam-card" ref={cardRef}>
        <div className="exam-head">
          <div className="exam-title">
            <h1>Soal nomor {question.number}</h1>
            <span className="package-label">
              {/* The package name is dropped on phones to keep the sticky
                  header to two rows; it stays in Informasi Soal. */}
              <span className="package-label-pkg">{packageTitle} — </span>
              {subtest.name}
            </span>
          </div>
          <div className="exam-tools">
            <SisaWaktu deadlineAt={sectionAttempt.deadline_at} onExpire={handleExpire} />
            {/* `display: contents` on desktop, so the buttons sit inline next to
                the timer; on a phone it becomes the header's second row. */}
            <div className="exam-tool-buttons">
              <button className="btn btn-cyan" onClick={() => setShowInfo(true)}>
                <span className="btn-badge">i</span> Informasi Soal
              </button>
              <button className="btn btn-cyan" onClick={() => setShowDaftar(true)}>
                <span className="btn-badge">▦</span> Daftar Soal
              </button>
            </div>
          </div>
        </div>

        <div className="font-control">
          <span>Ukuran font soal:</span>
          {FONT_SCALES.map((_, step) => (
            <button
              key={step}
              type="button"
              className={fontStep === step ? 'active' : ''}
              onClick={() => changeFont(step)}
              aria-label={['Perkecil font', 'Font normal', 'Perbesar font'][step]}
            >
              A
            </button>
          ))}
        </div>

        <hr className="exam-divider" />

        <div className="question-frame" style={frameStyle}>
          {question.passage ? <Passage text={question.passage} /> : null}
          <p className="question-text">{question.question_text}</p>
          {question.image_url ? (
            <img className="question-image" src={question.image_url} alt={`Gambar untuk soal nomor ${question.number}`} />
          ) : null}
          <div className="options">
            {question.options.map((option) => (
              <button
                key={option.key}
                type="button"
                className={`option ${current?.selected_option === option.key ? 'selected' : ''}`}
                onClick={() => selectOption(option.key)}
                aria-pressed={current?.selected_option === option.key}
              >
                <span className="option-key">{option.key}</span>
                <span>{option.text}</span>
              </button>
            ))}
          </div>
        </div>

        {warning ? <div className="notice warn">{warning}</div> : null}

        {/* The act-* classes only drive the phone layout, where this bar becomes
            a sticky 2×2 grid ordered mark/save first, navigation second. */}
        <div className="action-bar">
          <button
            className="btn btn-red act-prev"
            onClick={() => setIndex((i) => Math.max(0, i - 1))}
            disabled={index === 0}
          >
            ◀ Soal Sebelumnya
          </button>
          <button className="btn btn-orange act-doubt" onClick={toggleDoubt} aria-pressed={Boolean(current?.is_doubtful)}>
            <span className="btn-square" style={current?.is_doubtful ? { background: '#8a5b09' } : undefined} />
            Ragu — Ragu
          </button>
          <button className="btn btn-green act-save" onClick={saveNow}>
            Simpan Jawaban
          </button>
          {isLast ? (
            <button className="btn btn-navy act-next" onClick={() => setShowConfirm(true)} disabled={finishing}>
              Selesai
            </button>
          ) : (
            <button
              className="btn btn-cyan act-next"
              onClick={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}
            >
              Soal Selanjutnya ▶
            </button>
          )}
        </div>
      </div>

      {showDaftar ? (
        <DaftarSoal
          questions={questions}
          answers={answers}
          currentIndex={index}
          onJump={setIndex}
          onClose={() => setShowDaftar(false)}
        />
      ) : null}

      {showInfo ? (
        <InformasiSoal
          subtest={subtest}
          packageTitle={packageTitle}
          answeredCount={answeredCount}
          doubtCount={doubtCount}
          onClose={() => setShowInfo(false)}
        />
      ) : null}

      {showConfirm ? (
        /* The remaining time is snapshotted when the dialog opens: it quotes
           whole minutes and is answered in seconds, so it need not tick. */
        <KonfirmasiTes
          subtestName={subtest.name}
          remainingMs={remainingMs(sectionAttempt.deadline_at)}
          answered={answeredCount}
          total={questions.length}
          doubtCount={doubtCount}
          submitting={finishing}
          onCancel={() => setShowConfirm(false)}
          onConfirm={() => void finish(false)}
        />
      ) : null}

      {toast ? <div className="toast">{toast}</div> : null}
    </AppShell>
  )
}
