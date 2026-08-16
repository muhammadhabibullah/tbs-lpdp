import { useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import { externalLinkProps, feedbackMailto } from './FeedbackFooter'
import { IS_OFFLINE_APP } from '../lib/config'
import { REPORT_COMMENT_MAX, REPORT_REASONS } from '../lib/types'
import type { QuestionReport, ReportReason } from '../lib/types'

/** v2 §4.1: stable codes, Bahasa Indonesia labels. */
export const REASON_LABELS: Record<ReportReason, string> = {
  wrong_key: 'Kunci jawaban salah',
  ambiguous: 'Soal ambigu / lebih dari satu jawaban benar',
  bad_explanation: 'Pembahasan keliru atau tidak sesuai',
  typo: 'Salah ketik atau kalimat rancu',
  image_issue: 'Gambar tidak tampil atau tidak sesuai',
  other: 'Lainnya',
}

const REASON_HINTS: Partial<Record<ReportReason, string>> = {
  wrong_key: 'Opsi yang ditandai sebagai kunci menurut Anda bukan jawaban yang benar.',
  ambiguous: 'Tidak ada jawaban yang benar, atau lebih dari satu opsi sama-sama benar.',
  bad_explanation: 'Kunci mungkin benar, tetapi pembahasannya salah atau tidak nyambung.',
  other: 'Jelaskan masalahnya pada catatan di bawah.',
}

/**
 * FE-12/FE-15: report dialog for one question, opened from Pembahasan only.
 * The parent owns the async call — this component never closes itself on
 * failure, so a rejected submit keeps everything the user typed (FE-13).
 */
export default function LaporSoal({
  questionNumber,
  questionId,
  packageTitle,
  existing,
  initialConfirmDelete = false,
  submitting,
  error,
  onCancel,
  onSubmit,
  onDelete,
}: {
  questionNumber: number
  /** Identifies the exact bank file in an emailed report (AP-9). */
  questionId: string
  packageTitle: string
  existing: QuestionReport | null
  /** Opens straight into the withdraw confirmation (FE-15). */
  initialConfirmDelete?: boolean
  submitting: boolean
  error: string | null
  onCancel: () => void
  onSubmit: (reason: ReportReason, comment: string) => void
  onDelete: () => void
}) {
  const [reason, setReason] = useState<ReportReason>(existing?.reason ?? 'wrong_key')
  const [comment, setComment] = useState(existing?.comment ?? '')
  const [confirmingDelete, setConfirmingDelete] = useState(initialConfirmDelete)
  const bodyRef = useRef<HTMLDivElement>(null)

  // FE-18: focus lands inside the dialog, on the reason that is already chosen.
  useEffect(() => {
    bodyRef.current?.querySelector<HTMLInputElement>('input[type="radio"]:checked')?.focus()
  }, [])

  const trimmed = comment.trim()
  const tooLong = comment.length > REPORT_COMMENT_MAX
  const missingComment = reason === 'other' && trimmed === ''
  const canSubmit = !submitting && !tooLong && !missingComment

  // AP-9: the app stores no report state — the device mail client is the only
  // way a report reaches the maintainer, so the email draft is the primary
  // action and replaces the web flavor's "Kirim laporan" submit.
  const emailProps = externalLinkProps(
    feedbackMailto(`Laporan soal ${questionId} — TBS LPDP Try Out`, [
      `Paket: ${packageTitle}`,
      `Soal: nomor ${questionNumber} (id ${questionId})`,
      `Alasan: ${REASON_LABELS[reason]}`,
      `Catatan: ${trimmed || '-'}`,
    ]),
  )

  return (
    <Modal
      title={`Laporkan Soal nomor ${questionNumber}`}
      onClose={submitting ? undefined : onCancel}
      footer={
        confirmingDelete ? (
          <>
            <button className="btn btn-ghost" onClick={() => setConfirmingDelete(false)} disabled={submitting}>
              Tidak, kembali
            </button>
            <button className="btn btn-red" onClick={onDelete} disabled={submitting}>
              {submitting ? 'MENGHAPUS…' : 'Ya, batalkan laporan'}
            </button>
          </>
        ) : IS_OFFLINE_APP ? (
          <>
            <button className="btn btn-ghost" onClick={onCancel}>
              Batal
            </button>
            <a
              className="btn btn-cyan btn-lg"
              href={emailProps.href}
              aria-disabled={!canSubmit || undefined}
              onClick={(event) => {
                if (!canSubmit) {
                  event.preventDefault()
                  return
                }
                emailProps.onClick?.(event)
              }}
            >
              Kirim via Email
            </a>
          </>
        ) : (
          <>
            <button className="btn btn-ghost" onClick={onCancel} disabled={submitting}>
              Batal
            </button>
            <button className="btn btn-navy btn-lg" onClick={() => onSubmit(reason, trimmed)} disabled={!canSubmit}>
              {submitting ? 'MENGIRIM…' : existing ? 'Simpan perubahan' : 'Kirim laporan'}
            </button>
          </>
        )
      }
    >
      <div ref={bodyRef}>
        {confirmingDelete ? (
          <p style={{ marginTop: 0 }}>
            Laporan Anda untuk soal nomor <strong>{questionNumber}</strong> akan dihapus. Anda tetap bisa melaporkan
            soal ini lagi nanti.
          </p>
        ) : (
          <>
            <p className="muted" style={{ marginTop: 0 }}>
              {IS_OFFLINE_APP
                ? 'Aplikasi offline tidak menyimpan laporan dan tidak mengirim apa pun ke server — tombol “Kirim via Email” membuka draf email berisi laporan ini pada aplikasi email perangkat Anda.'
                : 'Laporan Anda tersimpan untuk ditinjau penulis soal. Laporan tidak mengubah skor try out Anda.'}
            </p>

            <fieldset className="report-reasons">
              <legend>Apa yang bermasalah?</legend>
              {REPORT_REASONS.map((key) => (
                <label key={key} className={`report-reason ${reason === key ? 'is-selected' : ''}`}>
                  <input
                    type="radio"
                    name="report-reason"
                    value={key}
                    checked={reason === key}
                    onChange={() => setReason(key)}
                    disabled={submitting}
                  />
                  <span>
                    {REASON_LABELS[key]}
                    {REASON_HINTS[key] ? <em>{REASON_HINTS[key]}</em> : null}
                  </span>
                </label>
              ))}
            </fieldset>

            <label className="report-comment">
              <span className="spread">
                <span>Catatan {reason === 'other' ? '(wajib)' : '(opsional)'}</span>
                <span className={tooLong ? 'over' : 'muted'}>
                  {comment.length}/{REPORT_COMMENT_MAX}
                </span>
              </span>
              <textarea
                rows={4}
                value={comment}
                disabled={submitting}
                placeholder="Contoh: menurut saya jawaban yang benar adalah C karena…"
                onChange={(e) => setComment(e.target.value)}
              />
            </label>

            {!IS_OFFLINE_APP && existing ? (
              <button
                className="btn btn-link-danger"
                onClick={() => setConfirmingDelete(true)}
                disabled={submitting}
              >
                Batalkan laporan ini
              </button>
            ) : null}
          </>
        )}

        {error ? (
          <div className="notice error" style={{ marginTop: 12 }} role="alert">
            {error}
          </div>
        ) : null}
      </div>
    </Modal>
  )
}
