import { bankSource } from './bankSource'
import { ApiError } from './config'
import { REPORT_COMMENT_MAX, REPORT_REASONS } from './types'
import type {
  Attempt,
  AttemptState,
  AttemptSummary,
  Bank,
  BankPackage,
  BankQuestion,
  ExamApi,
  FinishSectionResult,
  MaintenanceStatus,
  OptionKey,
  Package,
  Question,
  QuestionReport,
  ReportReason,
  Review,
  ReviewQuestion,
  ServiceStatus,
  StartAttemptResult,
  StartSectionResult,
  Subtest,
} from './types'

/**
 * The local exam engine: a full reimplementation of the Supabase RPC semantics
 * (immutable release snapshots, attempt pinning, server deadline + 5 s grace,
 * idempotent finish, keys only for finished sections, monotonic statistics)
 * against `localStorage`, with the question bank injected by `bankSource`.
 *
 * Two flavors run it — the dev mock and the offline app (v6 §2). It is the only
 * place answer keys are graded on the client, which is exactly why it can never
 * reach the web production bundle (C-4/C-29).
 */

interface MockRelease {
  id: string
  package: Package
  questions: Record<string, BankQuestion[]>
}

interface MockAttempt extends Attempt {}

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

interface MockStatistics {
  attempts_started_total: number
  attempts_completed_total: number
  score_sum: number
  statistics_sample_total: number
  statistics_score_sum: number
  score_histogram: Record<string, number>
  coverage_started_at: string
  score_statistics_coverage_started_at: string
}

interface MockState {
  attempts: MockAttempt[]
  sections: MockSection[]
  answers: Record<string, Record<string, { selected_option: OptionKey | null; is_doubtful: boolean }>>
  /** `${release_id}:${question_id}` -> the report for that immutable revision. */
  reports: Record<string, QuestionReport>
  releases: Record<string, MockRelease>
  statistics: Record<string, MockStatistics>
}

const STORAGE_KEY = 'tbs-lpdp.mock.v3'
const FULL_KEY = 'tbs-lpdp.mock.full'
/** Dev-only schedule override; see web/README.md. */
const MAINTENANCE_KEY = 'tbs-lpdp.mock.maintenance'
const GRACE_MS = 5_000
const REPORTS_PER_HOUR = 20
const EMPTY: MockState = { attempts: [], sections: [], answers: {}, reports: {}, releases: {}, statistics: {} }

/**
 * The bank can be hot-swapped underneath us (AP-4). That is safe because every
 * attempt reads through the release snapshot it was pinned to, which lives in
 * `state.releases` from the moment the attempt starts.
 */
function loadBank(): Promise<Bank> {
  return bankSource.load()
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
      releases: parsed.releases ?? {},
      statistics: parsed.statistics ?? {},
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

function findBankPackage(bank: Bank, packageId: number): BankPackage {
  const pkg = bank.packages.find((item) => item.id === packageId)
  if (!pkg) throw new ApiError('package not found', 'P0002')
  return pkg
}

function ensureStatistics(state: MockState, packageId: number): MockStatistics {
  const stats = (state.statistics[String(packageId)] ??= {
    attempts_started_total: 0,
    attempts_completed_total: 0,
    score_sum: 0,
    statistics_sample_total: 0,
    statistics_score_sum: 0,
    score_histogram: {},
    coverage_started_at: now(),
    score_statistics_coverage_started_at: now(),
  })
  // Upgrade existing tbs-lpdp.mock.v3 state without pretending its historical
  // all-completion sum satisfies the stricter v3.1 eligibility rule.
  stats.statistics_sample_total ??= 0
  stats.statistics_score_sum ??= 0
  stats.score_histogram ??= {}
  stats.score_statistics_coverage_started_at ??= now()
  return stats
}

function medianScore(stats: MockStatistics): number | null {
  if (stats.statistics_sample_total === 0) return null
  const lowerRank = Math.floor((stats.statistics_sample_total + 1) / 2)
  const upperRank = Math.floor((stats.statistics_sample_total + 2) / 2)
  const entries = Object.entries(stats.score_histogram)
    .map(([score, count]) => [Number(score), count] as const)
    .sort((a, b) => a[0] - b[0])
  let cumulative = 0
  let lower: number | null = null
  let upper: number | null = null
  for (const [score, count] of entries) {
    cumulative += count
    if (lower == null && cumulative >= lowerRank) lower = score
    if (upper == null && cumulative >= upperRank) {
      upper = score
      break
    }
  }
  return lower == null || upper == null ? null : (lower + upper) / 2
}

function withStatistics(pkg: Package, state: MockState): Package {
  const stats = ensureStatistics(state, pkg.id)
  return {
    ...pkg,
    completed_attempts_total: stats.attempts_completed_total,
    statistics_sample_total: stats.statistics_sample_total,
    mean_score: stats.statistics_sample_total === 0
      ? null
      : stats.statistics_score_sum / stats.statistics_sample_total,
    median_score: medianScore(stats),
    statistics_coverage_started_at: stats.coverage_started_at,
    score_statistics_coverage_started_at: stats.score_statistics_coverage_started_at,
  }
}

function ensureCurrentRelease(state: MockState, bank: Bank, packageId: number): MockRelease {
  const current = findBankPackage(bank, packageId)
  const existing = state.releases[current.release_id]
  if (existing) return existing
  const { release_id: id, ...packageData } = current
  const questions: Record<string, BankQuestion[]> = {}
  for (const subtest of current.subtests) {
    questions[subtest.id] = structuredClone(bank.questions[subtest.id] ?? [])
  }
  const release: MockRelease = { id, package: structuredClone(packageData), questions }
  state.releases[id] = release
  return release
}

function releaseForAttempt(state: MockState, attempt: MockAttempt): MockRelease {
  const release = state.releases[attempt.package_release_id]
  if (!release) throw new ApiError('pinned mock release is no longer available', 'P0002')
  return release
}

function findSubtest(release: MockRelease, subtestId: string): Subtest {
  const subtest = release.package.subtests.find((item) => item.id === subtestId)
  if (!subtest) throw new ApiError('subtest not found', 'P0002')
  return subtest
}

function stripKeys(questions: BankQuestion[]): Question[] {
  return questions.map(({ correct_option: _correct, explanations: _explanations, ...question }) => question)
}

function gradeSection(state: MockState, sectionId: string): number {
  const section = state.sections.find((item) => item.id === sectionId)
  if (!section) throw new ApiError('section attempt not found', 'P0002')
  if (section.status === 'finished') return section.score ?? 0
  const attempt = state.attempts.find((item) => item.id === section.attempt_id)
  if (!attempt) throw new ApiError('attempt not found', 'P0002')
  const release = releaseForAttempt(state, attempt)
  const answers = state.answers[sectionId] ?? {}
  const correct = (release.questions[section.subtest_id] ?? [])
    .filter((question) => answers[question.id]?.selected_option === question.correct_option).length

  section.status = 'finished'
  section.finished_at = now()
  section.score = correct * 5

  const done = release.package.subtests.every((subtest) =>
    state.sections.some((item) => item.attempt_id === attempt.id && item.subtest_id === subtest.id && item.status === 'finished'),
  )
  if (done && attempt.status === 'active') {
    attempt.status = 'finished'
    attempt.finished_at = now()
    attempt.total_score = state.sections
      .filter((item) => item.attempt_id === attempt.id)
      .reduce((sum, item) => sum + (item.score ?? 0), 0)
    const stats = ensureStatistics(state, attempt.package_id)
    stats.attempts_completed_total += 1
    stats.score_sum += attempt.total_score
    const answeredBySubtest = release.package.subtests.map((subtest) => {
      const completedSection = state.sections.find(
        (item) => item.attempt_id === attempt.id && item.subtest_id === subtest.id,
      )
      const saved = completedSection ? state.answers[completedSection.id] ?? {} : {}
      return Object.values(saved).filter((answer) => answer.selected_option !== null).length
    })
    const answeredTotal = answeredBySubtest.reduce((sum, count) => sum + count, 0)
    const eligible = answeredTotal >= 48
      && (answeredBySubtest[0] ?? 0) >= 12
      && (answeredBySubtest[1] ?? 0) >= 13
      && (answeredBySubtest[2] ?? 0) >= 6
    if (eligible) {
      stats.statistics_sample_total += 1
      stats.statistics_score_sum += attempt.total_score
      const scoreKey = String(attempt.total_score)
      stats.score_histogram[scoreKey] = (stats.score_histogram[scoreKey] ?? 0) + 1
    }
  }
  return section.score
}

function assertActiveSection(state: MockState, sectionId: string): { section: MockSection; release: MockRelease } {
  const section = state.sections.find((item) => item.id === sectionId)
  if (!section) throw new ApiError('section attempt not found', 'P0002')
  if (section.status === 'finished') throw new ApiError('section already finished', 'P0003')
  const attempt = state.attempts.find((item) => item.id === section.attempt_id)
  if (!attempt) throw new ApiError('attempt not found', 'P0002')
  const release = releaseForAttempt(state, attempt)
  if (Date.now() > Date.parse(section.deadline_at) + GRACE_MS) {
    gradeSection(state, sectionId)
    writeState(state)
    throw new ApiError('section deadline passed', 'P0004')
  }
  return { section, release }
}

function reportKey(state: MockState, questionId: string, attemptId: string): string {
  const attempt = state.attempts.find((item) => item.id === attemptId)
  if (!attempt) throw new ApiError('question not available for reporting', 'P0002')
  const release = releaseForAttempt(state, attempt)
  const allowed = state.sections.some((section) =>
    section.attempt_id === attemptId && section.status === 'finished' &&
    (release.questions[section.subtest_id] ?? []).some((question) => question.id === questionId),
  )
  if (!allowed) throw new ApiError('question not available for reporting', 'P0002')
  return `${release.id}:${questionId}`
}

function summarize(state: MockState): AttemptSummary[] {
  return [...state.attempts]
    .sort((a, b) => b.started_at.localeCompare(a.started_at))
    .slice(0, 25)
    .map((attempt) => {
      const release = releaseForAttempt(state, attempt)
      return {
        id: attempt.id,
        package_id: attempt.package_id,
        package_title: release.package.title,
        package_version: release.package.question_version,
        status: attempt.status,
        started_at: attempt.started_at,
        total_score: attempt.total_score,
        finished_sections: state.sections.filter((item) => item.attempt_id === attempt.id && item.status === 'finished').length,
        total_sections: release.package.subtests.length,
      }
    })
}

export const localApi: ExamApi = {
  async getMaintenanceStatus(): Promise<MaintenanceStatus> {
    const serverTime = now()
    const fallback: MaintenanceStatus = {
      enabled: false,
      starts_at: null,
      ends_at: null,
      message: '',
      phase: 'open',
      server_time: serverTime,
    }

    // Fast visual rehearsal without calculating timestamps: restart Vite with
    // VITE_MOCK_MAINTENANCE_PHASE=warning or =maintenance. This module is
    // excluded from production builds unless VITE_USE_MOCK=true.
    const forcedPhase = import.meta.env.VITE_MOCK_MAINTENANCE_PHASE
    if (forcedPhase === 'warning' || forcedPhase === 'maintenance') {
      const current = Date.now()
      // Anchor to the current hour so polling/reloading keeps the same schedule
      // key and can verify session-scoped banner dismissal.
      const hour = 60 * 60 * 1000
      const anchor = Math.floor(current / hour) * hour
      const startsAt = forcedPhase === 'warning' ? anchor + 2 * hour : anchor - hour
      const endsAt = startsAt + 3 * 60 * 60 * 1000
      return {
        enabled: true,
        starts_at: new Date(startsAt).toISOString(),
        ends_at: new Date(endsAt).toISOString(),
        message: 'Maintenance sistem sedang dilakukan.',
        phase: forcedPhase,
        server_time: serverTime,
      }
    }

    try {
      const raw = localStorage.getItem(MAINTENANCE_KEY)
      if (!raw) return fallback
      const value = JSON.parse(raw) as Partial<MaintenanceStatus>
      if (typeof value.starts_at !== 'string' || typeof value.ends_at !== 'string') return fallback

      const current = Date.now()
      const startsAt = Date.parse(value.starts_at)
      const endsAt = Date.parse(value.ends_at)
      if (!value.enabled || Number.isNaN(startsAt) || Number.isNaN(endsAt) || endsAt <= startsAt) return fallback

      const phase =
        current >= startsAt && current < endsAt
          ? 'maintenance'
          : current >= startsAt - 4 * 60 * 60 * 1000 && current < startsAt
            ? 'warning'
            : 'open'

      return {
        enabled: true,
        starts_at: value.starts_at,
        ends_at: value.ends_at,
        message:
          typeof value.message === 'string' && value.message.trim()
            ? value.message.trim()
            : 'Kami sedang melakukan pemeliharaan terjadwal agar layanan tetap andal.',
        phase,
        server_time: serverTime,
      }
    } catch {
      return fallback
    }
  },

  async init(_captchaToken?: string): Promise<void> {
    await loadBank()
  },

  async getServiceStatus(): Promise<ServiceStatus> {
    const full = localStorage.getItem(FULL_KEY) === 'true'
    return { accepting_attempts: !full, usage_percent: full ? 100 : 3, measured_at: now() }
  },

  async listPackages(): Promise<Package[]> {
    const bank = await loadBank()
    const state = readState()
    const packages = bank.packages.map(({ release_id: _id, ...pkg }) => withStatistics(pkg, state))
    writeState(state)
    return packages
  },

  async getPackage(packageId: number): Promise<Package> {
    const packages = await this.listPackages()
    const pkg = packages.find((item) => item.id === packageId)
    if (!pkg) throw new ApiError('package not found', 'P0002')
    return pkg
  },

  async listAttempts(): Promise<AttemptSummary[]> {
    return summarize(readState())
  },

  async startAttempt(packageId: number): Promise<StartAttemptResult> {
    const bank = await loadBank()
    const state = readState()
    let attempt = state.attempts.find((item) => item.package_id === packageId && item.status === 'active')
    if (!attempt) {
      if (localStorage.getItem(FULL_KEY) === 'true') throw new ApiError('storage capacity reached', 'P0007')
      const hourAgo = Date.now() - 3_600_000
      if (state.attempts.filter((item) => Date.parse(item.started_at) > hourAgo).length >= 10) {
        throw new ApiError('too many attempts', 'P0005')
      }
      const release = ensureCurrentRelease(state, bank, packageId)
      attempt = {
        id: crypto.randomUUID(), package_id: packageId, package_release_id: release.id,
        status: 'active', started_at: now(), finished_at: null, total_score: null,
      }
      state.attempts.push(attempt)
      ensureStatistics(state, packageId).attempts_started_total += 1
    }
    const release = releaseForAttempt(state, attempt)
    writeState(state)
    return { attempt, package: withStatistics(release.package, state), server_time: now() }
  },

  async startSection(attemptId: string): Promise<StartSectionResult> {
    const state = readState()
    const attempt = state.attempts.find((item) => item.id === attemptId)
    if (!attempt) throw new ApiError('attempt not found', 'P0002')
    const release = releaseForAttempt(state, attempt)
    for (const section of state.sections) {
      if (section.attempt_id === attemptId && section.status === 'active' &&
          Date.now() > Date.parse(section.deadline_at) + GRACE_MS) gradeSection(state, section.id)
    }

    let section = state.sections.find((item) => item.attempt_id === attemptId && item.status === 'active')
    if (!section) {
      const next = release.package.subtests.find((subtest) =>
        !state.sections.some((item) => item.attempt_id === attemptId && item.subtest_id === subtest.id))
      if (!next) {
        writeState(state)
        return { done: true, server_time: now() }
      }
      section = {
        id: crypto.randomUUID(), attempt_id: attemptId, subtest_id: next.id,
        status: 'active', started_at: now(),
        deadline_at: new Date(Date.now() + next.duration_seconds * 1000).toISOString(),
        finished_at: null, score: null,
      }
      state.sections.push(section)
    }
    writeState(state)
    const saved = state.answers[section.id] ?? {}
    return {
      done: false,
      section_attempt: section,
      subtest: findSubtest(release, section.subtest_id),
      package: withStatistics(release.package, state),
      questions: stripKeys(release.questions[section.subtest_id] ?? []),
      answers: Object.entries(saved).map(([question_id, value]) => ({ question_id, ...value })),
      server_time: now(),
    }
  },

  async saveAnswer(sectionId: string, questionId: string, option: OptionKey | null): Promise<void> {
    const state = readState()
    const { section, release } = assertActiveSection(state, sectionId)
    if (!(release.questions[section.subtest_id] ?? []).some((question) => question.id === questionId)) {
      throw new ApiError('question not in pinned section', 'P0002')
    }
    const bucket = (state.answers[sectionId] ??= {})
    bucket[questionId] = { selected_option: option, is_doubtful: bucket[questionId]?.is_doubtful ?? false }
    writeState(state)
  },

  async toggleDoubt(sectionId: string, questionId: string, doubtful: boolean): Promise<void> {
    const state = readState()
    const { section, release } = assertActiveSection(state, sectionId)
    if (!(release.questions[section.subtest_id] ?? []).some((question) => question.id === questionId)) {
      throw new ApiError('question not in pinned section', 'P0002')
    }
    const bucket = (state.answers[sectionId] ??= {})
    bucket[questionId] = { selected_option: bucket[questionId]?.selected_option ?? null, is_doubtful: doubtful }
    writeState(state)
  },

  async finishSection(sectionId: string): Promise<FinishSectionResult> {
    const state = readState()
    const score = gradeSection(state, sectionId)
    const section = state.sections.find((item) => item.id === sectionId)!
    const attempt = state.attempts.find((item) => item.id === section.attempt_id)!
    writeState(state)
    return { score, attempt_status: attempt.status, total_score: attempt.total_score, server_time: now() }
  },

  async getAttemptState(attemptId: string): Promise<AttemptState> {
    const state = readState()
    const attempt = state.attempts.find((item) => item.id === attemptId)
    if (!attempt) throw new ApiError('attempt not found', 'P0002')
    const release = releaseForAttempt(state, attempt)
    return {
      attempt,
      package: withStatistics(release.package, state),
      server_time: now(),
      sections: state.sections.filter((item) => item.attempt_id === attemptId)
        .sort((a, b) => a.started_at.localeCompare(b.started_at))
        .map((section) => ({ section_attempt: section, subtest: findSubtest(release, section.subtest_id) })),
    }
  },

  async getReview(attemptId: string): Promise<Review> {
    const state = readState()
    const attempt = state.attempts.find((item) => item.id === attemptId)
    if (!attempt) throw new ApiError('attempt not found', 'P0002')
    const release = releaseForAttempt(state, attempt)
    const sections = state.sections.filter((item) => item.attempt_id === attemptId && item.status === 'finished')
      .map((section) => {
        const saved = state.answers[section.id] ?? {}
        const questions: ReviewQuestion[] = (release.questions[section.subtest_id] ?? []).map((question) => ({
          ...question,
          selected_option: saved[question.id]?.selected_option ?? null,
          is_doubtful: saved[question.id]?.is_doubtful ?? false,
          my_report: state.reports[`${release.id}:${question.id}`] ?? null,
        }))
        return { subtest: findSubtest(release, section.subtest_id), score: section.score ?? 0, questions }
      }).sort((a, b) => a.subtest.position - b.subtest.position)
    return { attempt, package: withStatistics(release.package, state), sections }
  },

  async reportQuestion(questionId: string, reason: ReportReason, comment: string, attemptId: string): Promise<QuestionReport> {
    const state = readState()
    const trimmed = comment.trim()
    if (!REPORT_REASONS.includes(reason)) throw new ApiError('unknown report reason', 'P0006')
    if (trimmed.length > REPORT_COMMENT_MAX) throw new ApiError('comment too long', 'P0006')
    if (reason === 'other' && trimmed === '') throw new ApiError('comment required for reason other', 'P0006')
    const key = reportKey(state, questionId, attemptId)
    const cutoff = Date.now() - 3_600_000
    if (Object.values(state.reports).filter((report) => Date.parse(report.updated_at) > cutoff).length >= REPORTS_PER_HOUR) {
      throw new ApiError('too many reports', 'P0005')
    }
    const existing = state.reports[key]
    const report: QuestionReport = {
      reason, comment: trimmed, status: existing?.status ?? 'open',
      created_at: existing?.created_at ?? now(), updated_at: now(),
    }
    state.reports[key] = report
    writeState(state)
    return report
  },

  async deleteQuestionReport(questionId: string, attemptId: string): Promise<void> {
    const state = readState()
    const key = reportKey(state, questionId, attemptId)
    delete state.reports[key]
    writeState(state)
  },
}
