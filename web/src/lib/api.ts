import type { ExamApi } from './types'

/**
 * Picks the backend once, lazily. `import.meta.env.VITE_USE_MOCK` is inlined at
 * build time, so a production bundle drops the mock branch entirely.
 */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

let implPromise: Promise<ExamApi> | null = null

function impl(): Promise<ExamApi> {
  if (!implPromise) {
    implPromise = USE_MOCK
      ? import('./mockApi').then((m) => m.mockApi)
      : import('./supabaseApi').then((m) => m.supabaseApi)
  }
  return implPromise
}

export const api: ExamApi = {
  init: () => impl().then((a) => a.init()),
  getServiceStatus: () => impl().then((a) => a.getServiceStatus()),
  listPackages: () => impl().then((a) => a.listPackages()),
  getPackage: (packageId) => impl().then((a) => a.getPackage(packageId)),
  listAttempts: () => impl().then((a) => a.listAttempts()),
  startAttempt: (packageId) => impl().then((a) => a.startAttempt(packageId)),
  startSection: (attemptId) => impl().then((a) => a.startSection(attemptId)),
  saveAnswer: (sectionId, questionId, option) => impl().then((a) => a.saveAnswer(sectionId, questionId, option)),
  toggleDoubt: (sectionId, questionId, doubtful) => impl().then((a) => a.toggleDoubt(sectionId, questionId, doubtful)),
  finishSection: (sectionId) => impl().then((a) => a.finishSection(sectionId)),
  getAttemptState: (attemptId) => impl().then((a) => a.getAttemptState(attemptId)),
  getReview: (attemptId) => impl().then((a) => a.getReview(attemptId)),
  reportQuestion: (questionId, reason, comment, attemptId) =>
    impl().then((a) => a.reportQuestion(questionId, reason, comment, attemptId)),
  deleteQuestionReport: (questionId) => impl().then((a) => a.deleteQuestionReport(questionId)),
}

/** NF-2: background writes retry a few times before surfacing a warning. */
export async function withRetry<T>(fn: () => Promise<T>, attempts = 3): Promise<T> {
  let lastError: unknown
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      const code = (err as { code?: string }).code
      // Terminal states: retrying cannot help (P0005 rate limit, P0006 bad
      // input, P0007 storage capacity — a retry a second later is still full).
      if (
        code === 'P0002' ||
        code === 'P0003' ||
        code === 'P0004' ||
        code === 'P0005' ||
        code === 'P0006' ||
        code === 'P0007'
      ) {
        throw err
      }
      await new Promise((resolve) => setTimeout(resolve, 300 * 2 ** i))
    }
  }
  throw lastError
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  return String(err)
}
