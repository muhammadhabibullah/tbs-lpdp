import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import ExamPage from './ExamPage'
import SectionIntro from './SectionIntro'
import { api, errorMessage } from '../lib/api'
import { remainingMs } from '../lib/clock'
import type { ActiveSection, Subtest } from '../lib/types'

type Phase =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'intro'; subtest: Subtest; position: number; total: number }
  | { kind: 'exam'; section: ActiveSection }

/**
 * Drives one attempt: intro → questions → next section → review (FE-2, FE-7,
 * FE-9). The intro is shown *before* start_section so the reading pause never
 * eats into the server-issued section deadline.
 */
export default function AttemptPage() {
  const { attemptId = '' } = useParams()
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' })
  const [packageTitle, setPackageTitle] = useState('')
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const bootstrapping = useRef(false)

  const bootstrap = useCallback(async () => {
    if (bootstrapping.current) return
    bootstrapping.current = true
    try {
      const state = await api.getAttemptState(attemptId)
      const pkg = await api.getPackage(state.attempt.package_id)
      setPackageTitle(pkg.title)

      const active = state.sections.find((s) => s.section_attempt.status === 'active')
      if (active) {
        if (remainingMs(active.section_attempt.deadline_at) <= 0) {
          // Deadline elapsed while away: close it out, then re-evaluate (FE-9).
          await api.finishSection(active.section_attempt.id)
          bootstrapping.current = false
          return bootstrap()
        }
        const resumed = await api.startSection(attemptId)
        if (resumed.done) {
          navigate(`/attempt/${attemptId}/review`, { replace: true })
          return
        }
        setPhase({ kind: 'exam', section: resumed })
        return
      }

      const started = new Set(state.sections.map((s) => s.section_attempt.subtest_id))
      const next = pkg.subtests.find((st) => !started.has(st.id))
      if (!next) {
        navigate(`/attempt/${attemptId}/review`, { replace: true })
        return
      }
      setPhase({
        kind: 'intro',
        subtest: next,
        position: pkg.subtests.indexOf(next) + 1,
        total: pkg.subtests.length,
      })
    } catch (err) {
      setPhase({ kind: 'error', message: errorMessage(err) })
    } finally {
      bootstrapping.current = false
    }
  }, [attemptId, navigate])

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  async function handleStart() {
    setStarting(true)
    setStartError(null)
    try {
      const result = await api.startSection(attemptId)
      if (result.done) {
        navigate(`/attempt/${attemptId}/review`, { replace: true })
        return
      }
      setPhase({ kind: 'exam', section: result })
    } catch (err) {
      setStartError(errorMessage(err))
    } finally {
      setStarting(false)
    }
  }

  if (phase.kind === 'loading') {
    return (
      <AppShell>
        <div className="card loading">Memuat sesi ujian…</div>
      </AppShell>
    )
  }

  if (phase.kind === 'error') {
    return (
      <AppShell>
        <div className="card">
          <div className="notice error">{phase.message}</div>
          <p style={{ marginBottom: 0 }}>
            <Link to="/">← Kembali ke daftar paket</Link>
          </p>
        </div>
      </AppShell>
    )
  }

  if (phase.kind === 'intro') {
    return (
      <SectionIntro
        subtest={phase.subtest}
        packageTitle={packageTitle}
        position={phase.position}
        total={phase.total}
        starting={starting}
        error={startError}
        onStart={() => void handleStart()}
      />
    )
  }

  return (
    <ExamPage
      key={phase.section.section_attempt.id}
      packageTitle={packageTitle}
      section={phase.section}
      onSectionFinished={() => {
        setPhase({ kind: 'loading' })
        void bootstrap()
      }}
    />
  )
}
