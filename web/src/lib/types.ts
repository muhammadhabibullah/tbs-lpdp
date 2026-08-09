// Shapes returned by the RPCs in supabase/schema.sql (docs §6–§7).

export type SubtestKey = 'verbal' | 'kuantitatif' | 'pemecahan_masalah'
export type OptionKey = 'A' | 'B' | 'C' | 'D' | 'E'

export const OPTION_KEYS: OptionKey[] = ['A', 'B', 'C', 'D', 'E']

export interface Subtest {
  id: string
  package_id: number
  key: SubtestKey
  name: string
  position: number
  question_count: number
  duration_seconds: number
  passing_grade: number
}

export interface Package {
  id: number
  title: string
  description: string
  is_published: boolean
  created_at: string
  subtests: Subtest[]
}

export interface QuestionOption {
  key: OptionKey
  text: string
}

/** Question as served to an active attempt — never carries the answer key. */
export interface Question {
  id: string
  number: number
  qtype: string
  question_text: string
  passage: string | null
  image_url: string | null
  options: QuestionOption[]
}

export interface AnswerState {
  question_id: string
  selected_option: OptionKey | null
  is_doubtful: boolean
}

export interface Attempt {
  id: string
  package_id: number
  status: 'active' | 'finished'
  started_at: string
  finished_at: string | null
  total_score: number | null
}

export interface SectionAttempt {
  id: string
  attempt_id: string
  subtest_id: string
  status: 'active' | 'finished'
  started_at: string
  deadline_at: string
  finished_at: string | null
  score: number | null
}

export interface StartAttemptResult {
  attempt: Attempt
  server_time: string
}

export type StartSectionResult =
  | { done: true; server_time: string }
  | {
      done?: false
      section_attempt: SectionAttempt
      subtest: Subtest
      questions: Question[]
      answers: AnswerState[]
      server_time: string
    }

/** The "a section is running" branch of StartSectionResult. */
export type ActiveSection = Extract<StartSectionResult, { section_attempt: SectionAttempt }>

export interface FinishSectionResult {
  score: number
  attempt_status: 'active' | 'finished'
  total_score: number | null
  server_time: string
}

export interface AttemptState {
  attempt: Attempt
  server_time: string
  sections: { section_attempt: SectionAttempt; subtest: Subtest }[]
}

/** v2 §4.1 — stable codes; the Bahasa Indonesia labels live in LaporSoal.tsx. */
export type ReportReason = 'wrong_key' | 'ambiguous' | 'bad_explanation' | 'typo' | 'image_issue' | 'other'

export const REPORT_REASONS: ReportReason[] = [
  'wrong_key',
  'ambiguous',
  'bad_explanation',
  'typo',
  'image_issue',
  'other',
]

export const REPORT_COMMENT_MAX = 1000

/** A report as its own author sees it. Never carries another user's data. */
export interface QuestionReport {
  reason: ReportReason
  comment: string
  status: 'open' | 'reviewing' | 'accepted' | 'rejected' | 'duplicate'
  created_at: string
  updated_at: string
}

export interface ReviewQuestion extends Question {
  selected_option: OptionKey | null
  is_doubtful: boolean
  correct_option: OptionKey
  explanations: Record<OptionKey, string>
  /** BE-11: the caller's own report on this question, or null. */
  my_report: QuestionReport | null
}

export interface ReviewSection {
  subtest: Subtest
  score: number
  questions: ReviewQuestion[]
}

export interface Review {
  attempt: Attempt
  sections: ReviewSection[]
}

export interface AttemptSummary {
  id: string
  package_id: number
  package_title: string
  status: 'active' | 'finished'
  started_at: string
  total_score: number | null
  finished_sections: number
  total_sections: number
}

/** The whole backend surface the UI depends on (Supabase or the dev mock). */
export interface ExamApi {
  /** Anonymous sign-in (BE-1). Safe to call repeatedly. */
  init(): Promise<void>
  listPackages(): Promise<Package[]>
  getPackage(packageId: number): Promise<Package>
  listAttempts(): Promise<AttemptSummary[]>
  startAttempt(packageId: number): Promise<StartAttemptResult>
  startSection(attemptId: string): Promise<StartSectionResult>
  saveAnswer(sectionAttemptId: string, questionId: string, option: OptionKey | null): Promise<void>
  toggleDoubt(sectionAttemptId: string, questionId: string, doubtful: boolean): Promise<void>
  finishSection(sectionAttemptId: string): Promise<FinishSectionResult>
  getAttemptState(attemptId: string): Promise<AttemptState>
  getReview(attemptId: string): Promise<Review>
  /** BE-10: report a question from Pembahasan. Re-reporting edits in place. */
  reportQuestion(
    questionId: string,
    reason: ReportReason,
    comment: string,
    attemptId: string,
  ): Promise<QuestionReport>
  /** BE-12: withdraw own report. Idempotent — no error if none exists. */
  deleteQuestionReport(questionId: string): Promise<void>
}
