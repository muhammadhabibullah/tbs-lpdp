import Modal from './Modal'
import type { OptionKey, Question } from '../lib/types'

export interface AnswerMap {
  [questionId: string]: { selected_option: OptionKey | null; is_doubtful: boolean }
}

/**
 * FE-5: navigation grid with the official colour code —
 * hitam = sudah dijawab, biru = soal saat ini, putih = belum dijawab,
 * kuning = ragu-ragu.
 */
export default function DaftarSoal({
  questions,
  answers,
  currentIndex,
  onJump,
  onClose,
}: {
  questions: Question[]
  answers: AnswerMap
  currentIndex: number
  onJump: (index: number) => void
  onClose: () => void
}) {
  return (
    <Modal title="Daftar Soal" onClose={onClose}>
      <div className="daftar-grid">
        {questions.map((question, index) => {
          const answer = answers[question.id]
          const answered = Boolean(answer?.selected_option)
          const doubtful = Boolean(answer?.is_doubtful)
          const current = index === currentIndex
          const state = current ? 'current' : doubtful ? 'doubt' : answered ? 'answered' : 'unanswered'
          return (
            <button
              key={question.id}
              type="button"
              className={`daftar-item ${state}`}
              onClick={() => {
                onJump(index)
                onClose()
              }}
              aria-label={`Soal nomor ${question.number}${answered ? ', sudah dijawab' : ', belum dijawab'}${
                doubtful ? ', ragu-ragu' : ''
              }`}
            >
              {question.number}
              {answered ? <span className="chosen">{answer?.selected_option}</span> : null}
              {answered ? <span className="tick">✓</span> : null}
            </button>
          )
        })}
      </div>

      <div className="legend">
        <div>
          <span className="swatch answered" /> Hitam: peserta sudah menjawab soal tersebut
        </div>
        <div>
          <span className="swatch current" /> Biru: peserta sedang berada di soal tersebut
        </div>
        <div>
          <span className="swatch unanswered" /> Putih: peserta belum menjawab soal tersebut
        </div>
        <div>
          <span className="swatch doubt" /> Kuning: peserta ragu-ragu pada soal tersebut
        </div>
      </div>
    </Modal>
  )
}
