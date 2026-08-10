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
  ServiceStatus,
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

export const supabaseApi: ExamApi = {
  init: requireSession,

  async getServiceStatus(): Promise<ServiceStatus> {
    await requireSession()
    return rpc<ServiceStatus>('get_service_status', {})
  },

  async listPackages(): Promise<Package[]> {
    await requireSession()
    const packages = await rpc<Package[]>('get_package_catalog', {})
    return packages.map((pkg) => ({ ...pkg, subtests: sortSubtests(pkg.subtests ?? []) }))
  },

  async getPackage(packageId: number): Promise<Package> {
    const packages = await supabaseApi.listPackages()
    const pkg = packages.find((item) => item.id === packageId)
    if (!pkg) throw new ApiError('Paket tidak ditemukan.', 'P0002')
    return pkg
  },

  async listAttempts(): Promise<AttemptSummary[]> {
    await requireSession()
    return rpc<AttemptSummary[]>('get_attempt_summaries', {})
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

  async deleteQuestionReport(questionId: string, attemptId: string): Promise<void> {
    await requireSession()
    await rpc('delete_question_report', { p_question_id: questionId, p_attempt_id: attemptId })
  },
}
