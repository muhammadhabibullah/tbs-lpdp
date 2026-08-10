import { syncServerTime } from './clock'
import { ApiError, isSupabaseConfigured } from './config'
import { supabase } from './supabase'
import type {
  AttemptState,
  AttemptSummary,
  ExamApi,
  FinishSectionResult,
  OptionKey,
  Package,
  QuestionReport,
  ReportReason,
  Review,
  StartAttemptResult,
  StartSectionResult,
  Subtest,
} from './types'

type PostgrestErrorish = { message: string; code?: string; details?: string | null } | null

function fail(error: PostgrestErrorish): never {
  throw new ApiError(error?.message ?? 'Permintaan ke server gagal', error?.code)
}

/** Every RPC returns a json object carrying `server_time` (see schema.sql). */
async function rpc<T>(fn: string, args: Record<string, unknown>): Promise<T> {
  const { data, error } = await supabase.rpc(fn, args)
  if (error) fail(error)
  const result = data as T & { server_time?: string }
  syncServerTime(result?.server_time)
  return result
}

function sortSubtests(subtests: Subtest[]): Subtest[] {
  return [...subtests].sort((a, b) => a.position - b.position)
}

async function requireSession(): Promise<void> {
  if (!isSupabaseConfigured) {
    throw new ApiError(
      'Supabase belum dikonfigurasi. Isi VITE_SUPABASE_URL dan VITE_SUPABASE_PUBLISHABLE_KEY (atau jalankan mode mock).',
    )
  }
  const { data } = await supabase.auth.getSession()
  if (data.session) return
  // BE-1: transparent anonymous identity, one per browser.
  const { error } = await supabase.auth.signInAnonymously()
  if (error) fail(error)
}

/**
 * The published catalogue, fetched once per page load. HomePage asks for it
 * while `listAttempts` asks again for its section counts; caching the *promise*
 * collapses those two into one request even when they overlap in flight. A
 * newly published package appears on the next reload — the catalogue only
 * changes when the developer runs the push script.
 */
let packagesPromise: Promise<Package[]> | null = null

export const supabaseApi: ExamApi = {
  init: requireSession,

  async listPackages(): Promise<Package[]> {
    await requireSession()
    if (!packagesPromise) {
      const load = (async () => {
        const { data, error } = await supabase
          .from('packages')
          .select('id,title,description,is_published,created_at,subtests(*)')
          .eq('is_published', true)
          .order('id')
        if (error) fail(error)
        return (data as Package[]).map((pkg) => ({ ...pkg, subtests: sortSubtests(pkg.subtests ?? []) }))
      })()
      // Never cache a rejection: a failed load must be retryable.
      packagesPromise = load.catch((err) => {
        packagesPromise = null
        throw err
      })
    }
    return packagesPromise
  },

  async getPackage(packageId: number): Promise<Package> {
    await requireSession()
    const { data, error } = await supabase
      .from('packages')
      .select('id,title,description,is_published,created_at,subtests(*)')
      .eq('id', packageId)
      .single()
    if (error) fail(error)
    const pkg = data as Package
    return { ...pkg, subtests: sortSubtests(pkg.subtests ?? []) }
  },

  async listAttempts(): Promise<AttemptSummary[]> {
    await requireSession()
    const { data, error } = await supabase
      .from('attempts')
      .select('id,package_id,status,started_at,total_score,packages(title),section_attempts(status)')
      .order('started_at', { ascending: false })
      .limit(25)
    if (error) fail(error)

    const packages = await supabaseApi.listPackages()
    const sectionCount = new Map(packages.map((p) => [p.id, p.subtests.length]))

    type Row = {
      id: string
      package_id: number
      status: 'active' | 'finished'
      started_at: string
      total_score: number | null
      packages: { title: string } | { title: string }[] | null
      section_attempts: { status: string }[] | null
    }

    return (data as Row[]).map((row) => {
      const pkg = Array.isArray(row.packages) ? row.packages[0] : row.packages
      return {
        id: row.id,
        package_id: row.package_id,
        package_title: pkg?.title ?? `Paket ${row.package_id}`,
        status: row.status,
        started_at: row.started_at,
        total_score: row.total_score,
        finished_sections: (row.section_attempts ?? []).filter((s) => s.status === 'finished').length,
        total_sections: sectionCount.get(row.package_id) ?? 3,
      }
    })
  },

  async startAttempt(packageId: number): Promise<StartAttemptResult> {
    await requireSession()
    return rpc<StartAttemptResult>('start_attempt', { p_package_id: packageId })
  },

  async startSection(attemptId: string): Promise<StartSectionResult> {
    await requireSession()
    return rpc<StartSectionResult>('start_section', { p_attempt_id: attemptId })
  },

  async saveAnswer(sectionAttemptId: string, questionId: string, option: OptionKey | null): Promise<void> {
    await rpc('save_answer', {
      p_section_attempt_id: sectionAttemptId,
      p_question_id: questionId,
      p_option: option,
    })
  },

  async toggleDoubt(sectionAttemptId: string, questionId: string, doubtful: boolean): Promise<void> {
    await rpc('toggle_doubt', {
      p_section_attempt_id: sectionAttemptId,
      p_question_id: questionId,
      p_doubtful: doubtful,
    })
  },

  async finishSection(sectionAttemptId: string): Promise<FinishSectionResult> {
    await requireSession()
    return rpc<FinishSectionResult>('finish_section', { p_section_attempt_id: sectionAttemptId })
  },

  async getAttemptState(attemptId: string): Promise<AttemptState> {
    await requireSession()
    return rpc<AttemptState>('get_attempt_state', { p_attempt_id: attemptId })
  },

  async getReview(attemptId: string): Promise<Review> {
    await requireSession()
    return rpc<Review>('get_review', { p_attempt_id: attemptId })
  },

  async reportQuestion(
    questionId: string,
    reason: ReportReason,
    comment: string,
    attemptId: string,
  ): Promise<QuestionReport> {
    await requireSession()
    const result = await rpc<{ report: QuestionReport }>('report_question', {
      p_question_id: questionId,
      p_reason: reason,
      p_comment: comment,
      p_attempt_id: attemptId,
    })
    return result.report
  },

  async deleteQuestionReport(questionId: string): Promise<void> {
    await requireSession()
    await rpc('delete_question_report', { p_question_id: questionId })
  },
}
