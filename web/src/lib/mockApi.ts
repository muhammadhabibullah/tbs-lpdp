import { ApiError } from './supabase'
import { REPORT_COMMENT_MAX, REPORT_REASONS } from './types'
import type {
  AttemptState,
  AttemptSummary,
  ExamApi,
  FinishSectionResult,
  OptionKey,
  Package,
  Question,
  QuestionReport,
  ReportReason,
  Review,
  ReviewQuestion,
  StartAttemptResult,
  StartSectionResult,
  Subtest,
} from './types'

/**
 * Dev-only in-browser stand-in for Supabase, backed by the git question bank
 * served at /__mock/bank.json by vite/mock-bank-plugin.ts. It reproduces the
 * semantics of supabase/schema.sql (deadline enforcement + grace, idempotent
 * finish, keys revealed only for finished sections) so the UI can be built and
 * demoed before a Supabase project exists. Never reachable in a prod build.
 */

interface BankQuestion extends Question {
  correct_option: OptionKey
  explanations: Record<OptionKey, string>
}

interface Bank {
  packages: Package[]
  questions: Record<string, BankQuestion[]>
}

interface MockAttempt {
  id: string
  package_id: number
  status: 'active' | 'finished'
  started_at: string
  finished_at: string | null
  total_score: number | null
}

interface MockSection {
  id: string
  attempt_id: string
  subtest_id: string
  status: 'active' | 'finished'
  started_at: string
  deadline_at: string
  finished_at: string | null
  score: number | null
}

interface MockState {
  attempts: MockAttempt[]
  sections: MockSection[]
  answers: Record<string, Record<string, { selected_option: OptionKey | null; is_doubtful: boolean }>>
  /** v2: question_id → report. One mock browser = one anonymous user, so the
   *  `(user_id, question_id)` unique key of question_reports collapses to this. */
  reports: Record<string, QuestionReport>
}

const STORAGE_KEY = 'tbs-lpdp.mock.v1'
const GRACE_MS = 5_000
const REPORTS_PER_HOUR = 20
const EMPTY: MockState = { attempts: [], sections: [], answers: {}, reports: {} }

let bankPromise: Promise<Bank> | null = null

async function loadBank(): Promise<Bank> {
  if (!bankPromise) {
    bankPromise = fetch('/__mock/bank.json')
      .then((res) => {
        if (!res.ok) throw new ApiError('Bank soal mock tidak tersedia (jalankan `npm run dev`).')
        return res.json() as Promise<Bank>
      })
      .catch((err) => {
        bankPromise = null
        throw err instanceof ApiError ? err : new ApiError(String(err))
      })
  }
  return bankPromise
}

function readState(): MockState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return structuredClone(EMPTY)
    const parsed = JSON.parse(raw) as Partial<MockState>
    return {
      attempts: parsed.attempts ?? [],
      sections: parsed.sections ?? [],
      answers: parsed.answers ?? {},
      reports: parsed.reports ?? {},
    }
  } catch {
    return structuredClone(EMPTY)
  }
}

function writeState(state: MockState): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

function now(): string {
  return new Date().toISOString()
}

function subtestsOf(bank: Bank, packageId: number): Subtest[] {
  const pkg = bank.packages.find((p) => p.id === packageId)
  if (!pkg) throw new ApiError('package not found', 'P0002')
  return [...pkg.subtests].sort((a, b) => a.position - b.position)
}

function findSubtest(bank: Bank, subtestId: string): Subtest {
  for (const pkg of bank.packages) {
    const found = pkg.subtests.find((s) => s.id === subtestId)
    if (found) return found
  }
  throw new ApiError('subtest not found', 'P0002')
}

function stripKeys(questions: BankQuestion[]): Question[] {
  return questions.map(({ correct_option: _c, explanations: _e, ...rest }) => rest)
}

/** Mirrors public._grade_section. Idempotent. */
function gradeSection(state: MockState, bank: Bank, sectionId: string): number {
  const section = state.sections.find((s) => s.id === sectionId)
  if (!section) throw new ApiError('section attempt not found', 'P0002')
  if (section.status === 'finished') return section.score ?? 0

  const questions = bank.questions[section.subtest_id] ?? []
  const answers = state.answers[sectionId] ?? {}
  const correct = questions.filter((q) => answers[q.id]?.selected_option === q.correct_option).length

  section.status = 'finished'
  section.finished_at = now()
  section.score = correct * 5

  const attempt = state.attempts.find((a) => a.id === section.attempt_id)
  if (attempt) {
    const required = subtestsOf(bank, attempt.package_id)
    const done = required.every((st) =>
      state.sections.some((s) => s.attempt_id === attempt.id && s.subtest_id === st.id && s.status === 'finished'),
    )
    if (done && attempt.status === 'active') {
      attempt.status = 'finished'
      attempt.finished_at = now()
      attempt.total_score = state.sections
        .filter((s) => s.attempt_id === attempt.id)
        .reduce((sum, s) => sum + (s.score ?? 0), 0)
    }
  }
  return section.score
}

/** Mirrors public._assert_active_section. */
function assertActiveSection(state: MockState, bank: Bank, sectionId: string): MockSection {
  const section = state.sections.find((s) => s.id === sectionId)
  if (!section) throw new ApiError('section attempt not found', 'P0002')
  if (section.status === 'finished') throw new ApiError('section already finished', 'P0003')
  if (Date.now() > Date.parse(section.deadline_at) + GRACE_MS) {
    gradeSection(state, bank, sectionId)
    writeState(state)
    throw new ApiError('section deadline passed', 'P0004')
  }
  return section
}

/**
 * Mirrors the report gate in public.report_question: the caller must own a
 * FINISHED section containing the question. `attemptId` only narrows it.
 */
function assertReportable(state: MockState, bank: Bank, questionId: string, attemptId: string): void {
  const reportable = state.sections.some(
    (section) =>
      section.status === 'finished' &&
      (!attemptId || section.attempt_id === attemptId) &&
      (bank.questions[section.subtest_id] ?? []).some((q) => q.id === questionId),
  )
  if (!reportable) throw new ApiError('question not available for reporting', 'P0002')
}

function summarize(state: MockState, bank: Bank): AttemptSummary[] {
  return [...state.attempts]
    .sort((a, b) => b.started_at.localeCompare(a.started_at))
    .map((attempt) => ({
      id: attempt.id,
      package_id: attempt.package_id,
      package_title: bank.packages.find((p) => p.id === attempt.package_id)?.title ?? `Paket ${attempt.package_id}`,
      status: attempt.status,
      started_at: attempt.started_at,
      total_score: attempt.total_score,
      finished_sections: state.sections.filter((s) => s.attempt_id === attempt.id && s.status === 'finished').length,
      total_sections: subtestsOf(bank, attempt.package_id).length,
    }))
}

export const mockApi: ExamApi = {
  async init(): Promise<void> {
    await loadBank()
  },

  async listPackages(): Promise<Package[]> {
    const bank = await loadBank()
    return bank.packages
  },

  async getPackage(packageId: number): Promise<Package> {
    const bank = await loadBank()
    const pkg = bank.packages.find((p) => p.id === packageId)
    if (!pkg) throw new ApiError('package not found', 'P0002')
    return pkg
  },

  async listAttempts(): Promise<AttemptSummary[]> {
    const bank = await loadBank()
    return summarize(readState(), bank)
  },

  async startAttempt(packageId: number): Promise<StartAttemptResult> {
    const bank = await loadBank()
    const state = readState()
    subtestsOf(bank, packageId) // validates the package exists
    let attempt = state.attempts.find((a) => a.package_id === packageId && a.status === 'active')
    if (!attempt) {
      attempt = {
        id: crypto.randomUUID(),
        package_id: packageId,
        status: 'active',
        started_at: now(),
        finished_at: null,
        total_score: null,
      }
      state.attempts.push(attempt)
      writeState(state)
    }
    return { attempt, server_time: now() }
  },

  async startSection(attemptId: string): Promise<StartSectionResult> {
    const bank = await loadBank()
    const state = readState()
    const attempt = state.attempts.find((a) => a.id === attemptId)
    if (!attempt) throw new ApiError('attempt not found', 'P0002')

    for (const section of state.sections) {
      if (
        section.attempt_id === attemptId &&
        section.status === 'active' &&
        Date.now() > Date.parse(section.deadline_at) + GRACE_MS
      ) {
        gradeSection(state, bank, section.id)
      }
    }

    let section = state.sections.find((s) => s.attempt_id === attemptId && s.status === 'active')
    if (!section) {
      const next = subtestsOf(bank, attempt.package_id).find(
        (st) => !state.sections.some((s) => s.attempt_id === attemptId && s.subtest_id === st.id),
      )
      if (!next) {
        writeState(state)
        return { done: true, server_time: now() }
      }
      section = {
        id: crypto.randomUUID(),
        attempt_id: attemptId,
        subtest_id: next.id,
        status: 'active',
        started_at: now(),
        deadline_at: new Date(Date.now() + next.duration_seconds * 1000).toISOString(),
        finished_at: null,
        score: null,
      }
      state.sections.push(section)
    }
    writeState(state)

    const subtest = findSubtest(bank, section.subtest_id)
    const saved = state.answers[section.id] ?? {}
    return {
      done: false,
      section_attempt: section,
      subtest,
      questions: stripKeys(bank.questions[section.subtest_id] ?? []),
      answers: Object.entries(saved).map(([question_id, value]) => ({ question_id, ...value })),
      server_time: now(),
    }
  },

  async saveAnswer(sectionAttemptId: string, questionId: string, option: OptionKey | null): Promise<void> {
    const bank = await loadBank()
    const state = readState()
    assertActiveSection(state, bank, sectionAttemptId)
    const bucket = (state.answers[sectionAttemptId] ??= {})
    bucket[questionId] = { selected_option: option, is_doubtful: bucket[questionId]?.is_doubtful ?? false }
    writeState(state)
  },

  async toggleDoubt(sectionAttemptId: string, questionId: string, doubtful: boolean): Promise<void> {
    const bank = await loadBank()
    const state = readState()
    assertActiveSection(state, bank, sectionAttemptId)
    const bucket = (state.answers[sectionAttemptId] ??= {})
    bucket[questionId] = { selected_option: bucket[questionId]?.selected_option ?? null, is_doubtful: doubtful }
    writeState(state)
  },

  async finishSection(sectionAttemptId: string): Promise<FinishSectionResult> {
    const bank = await loadBank()
    const state = readState()
    const score = gradeSection(state, bank, sectionAttemptId)
    writeState(state)
    const section = state.sections.find((s) => s.id === sectionAttemptId)!
    const attempt = state.attempts.find((a) => a.id === section.attempt_id)!
    return { score, attempt_status: attempt.status, total_score: attempt.total_score, server_time: now() }
  },

  async getAttemptState(attemptId: string): Promise<AttemptState> {
    const bank = await loadBank()
    const state = readState()
    const attempt = state.attempts.find((a) => a.id === attemptId)
    if (!attempt) throw new ApiError('attempt not found', 'P0002')
    return {
      attempt,
      server_time: now(),
      sections: state.sections
        .filter((s) => s.attempt_id === attemptId)
        .sort((a, b) => a.started_at.localeCompare(b.started_at))
        .map((section) => ({ section_attempt: section, subtest: findSubtest(bank, section.subtest_id) })),
    }
  },

  async getReview(attemptId: string): Promise<Review> {
    const bank = await loadBank()
    const state = readState()
    const attempt = state.attempts.find((a) => a.id === attemptId)
    if (!attempt) throw new ApiError('attempt not found', 'P0002')

    const sections = state.sections
      .filter((s) => s.attempt_id === attemptId && s.status === 'finished')
      .map((section) => {
        const subtest = findSubtest(bank, section.subtest_id)
        const saved = state.answers[section.id] ?? {}
        const questions: ReviewQuestion[] = (bank.questions[section.subtest_id] ?? []).map((q) => ({
          ...q,
          selected_option: saved[q.id]?.selected_option ?? null,
          is_doubtful: saved[q.id]?.is_doubtful ?? false,
          my_report: state.reports[q.id] ?? null,
        }))
        return { subtest, score: section.score ?? 0, questions }
      })
      .sort((a, b) => a.subtest.position - b.subtest.position)

    return { attempt, sections }
  },

  async reportQuestion(
    questionId: string,
    reason: ReportReason,
    comment: string,
    attemptId: string,
  ): Promise<QuestionReport> {
    const bank = await loadBank()
    const state = readState()
    const trimmed = comment.trim()

    if (!REPORT_REASONS.includes(reason)) throw new ApiError('unknown report reason', 'P0006')
    if (trimmed.length > REPORT_COMMENT_MAX) throw new ApiError('comment too long', 'P0006')
    if (reason === 'other' && trimmed === '') throw new ApiError('comment required for reason other', 'P0006')

    assertReportable(state, bank, questionId, attemptId)

    const cutoff = Date.now() - 3_600_000
    const recent = Object.values(state.reports).filter((r) => Date.parse(r.updated_at) > cutoff).length
    if (recent >= REPORTS_PER_HOUR) throw new ApiError('too many reports', 'P0005')

    // Re-reporting edits in place; status is the developer's field, never reset.
    const existing = state.reports[questionId]
    const report: QuestionReport = {
      reason,
      comment: trimmed,
      status: existing?.status ?? 'open',
      created_at: existing?.created_at ?? now(),
      updated_at: now(),
    }
    state.reports[questionId] = report
    writeState(state)
    return report
  },

  async deleteQuestionReport(questionId: string): Promise<void> {
    const state = readState()
    if (!state.reports[questionId]) return // idempotent, like the RPC
    delete state.reports[questionId]
    writeState(state)
  },
}
