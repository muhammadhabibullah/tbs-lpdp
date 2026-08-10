import { useEffect } from 'react'
import useTick from '../hooks/useTick'
import { formatClock, remainingMs } from '../lib/clock'

/** Under a minute left: the box turns red (matches the CBT chrome). */
const URGENT_MS = 60_000

/**
 * The "Sisa Waktu" box, and the only thing that ticks.
 *
 * NF-3 wants the display within ±1 s of the server deadline, which means
 * re-rendering four times a second — but that used to re-render the whole exam
 * page (question, passage, five options) with it. Owning the tick here keeps
 * the cost to this box; the page above re-renders only when something actually
 * changes. `onExpire` fires once the deadline passes so the parent can
 * auto-submit (FE-7).
 */
export default function SisaWaktu({ deadlineAt, onExpire }: { deadlineAt: string; onExpire: () => void }) {
  useTick(250)
  const remaining = remainingMs(deadlineAt)

  useEffect(() => {
    if (remaining <= 0) onExpire()
  }, [remaining, onExpire])

  return (
    <div className={`timer-box ${remaining <= URGENT_MS ? 'urgent' : ''}`}>
      <span className="label">Sisa Waktu:</span>
      <span className="value">{formatClock(remaining)}</span>
    </div>
  )
}
