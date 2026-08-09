import { useState } from 'react'
import Modal from './Modal'
import { formatDurationWords } from '../lib/clock'

/**
 * FE-6: pressing Selesai with time left opens this dialog; the SELESAI button
 * stays disabled until the confirmation checkbox is ticked.
 */
export default function KonfirmasiTes({
  subtestName,
  remainingMs,
  answered,
  total,
  doubtCount,
  submitting,
  onCancel,
  onConfirm,
}: {
  subtestName: string
  remainingMs: number
  answered: number
  total: number
  doubtCount: number
  submitting: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  const [checked, setChecked] = useState(false)
  const unanswered = total - answered

  return (
    <Modal
      title="Konfirmasi Tes"
      onClose={submitting ? undefined : onCancel}
      footer={
        <>
          <button className="btn btn-ghost" onClick={onCancel} disabled={submitting}>
            Kembali ke soal
          </button>
          <button className="btn btn-navy btn-lg" onClick={onConfirm} disabled={!checked || submitting}>
            {submitting ? 'MENGIRIM…' : 'SELESAI'}
          </button>
        </>
      }
    >
      <p style={{ marginTop: 0 }}>
        Anda masih memiliki waktu <strong>{formatDurationWords(remainingMs)}</strong> untuk mata uji{' '}
        <strong>{subtestName}</strong>.
      </p>
      <ul className="info-list">
        <li>
          <span>Sudah dijawab</span>
          <strong>{answered} soal</strong>
        </li>
        <li>
          <span>Belum dijawab</span>
          <strong style={unanswered > 0 ? { color: '#a33540' } : undefined}>{unanswered} soal</strong>
        </li>
        <li>
          <span>Ditandai ragu-ragu</span>
          <strong>{doubtCount} soal</strong>
        </li>
      </ul>
      <label className="confirm-check">
        <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
        <span>
          Saya menyatakan telah selesai mengerjakan mata uji ini dan bersedia melanjutkan ke tahap berikutnya. Mata uji
          yang sudah diakhiri tidak dapat dibuka kembali.
        </span>
      </label>
    </Modal>
  )
}
