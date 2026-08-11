import { useEffect, useId, useRef } from 'react'
import { formatDate } from '../lib/clock'
import type { Package } from '../lib/types'

const MAX_SCORE = 300

function formatScore(score: number | null): string {
  return score == null
    ? 'Belum ada hasil'
    : `${score.toLocaleString('id-ID', { maximumFractionDigits: 1 })} / ${MAX_SCORE}`
}

export default function PackageStatisticsPopover({
  pkg,
  open,
  onOpenChange,
}: {
  pkg: Package
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const popoverId = useId()
  const headingId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) onOpenChange(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      onOpenChange(false)
      triggerRef.current?.focus()
    }
    document.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [onOpenChange, open])

  return (
    <div className="package-statistics-control" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="package-statistics-trigger"
        aria-label={`Lihat statistik ${pkg.title}`}
        aria-expanded={open}
        aria-controls={popoverId}
        aria-haspopup="dialog"
        onClick={() => onOpenChange(!open)}
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path d="M4 19V10M10 19V5M16 19v-7M22 19H2" />
        </svg>
      </button>
      {open ? (
        <section
          className="package-statistics-popover"
          id={popoverId}
          role="dialog"
          aria-labelledby={headingId}
        >
          <h4 id={headingId}>Statistik semua versi</h4>
          <dl className="package-statistics-grid">
            <div>
              <dt>Percobaan selesai</dt>
              <dd>{pkg.completed_attempts_total.toLocaleString('id-ID')}</dd>
            </div>
            <div>
              <dt>Sampel statistik</dt>
              <dd>{pkg.statistics_sample_total.toLocaleString('id-ID')}</dd>
            </div>
            <div>
              <dt>Rata-rata skor</dt>
              <dd>{formatScore(pkg.mean_score)}</dd>
            </div>
            <div>
              <dt>Median skor</dt>
              <dd>{formatScore(pkg.median_score)}</dd>
            </div>
          </dl>
          <p className="package-statistics-rule">
            Rata-rata dan median hanya memakai try out yang selesai, menjawab minimal 48 dari 60 soal, dan menjawab
            minimal separuh soal di setiap mata uji.
          </p>
          <p className="package-statistics-coverage">
            Percobaan tercatat sejak {formatDate(pkg.statistics_coverage_started_at)}. Statistik skor tercatat sejak{' '}
            {formatDate(pkg.score_statistics_coverage_started_at)}.
          </p>
        </section>
      ) : null}
    </div>
  )
}
