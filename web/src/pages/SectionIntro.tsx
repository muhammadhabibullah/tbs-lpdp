import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import { formatMinutes } from '../lib/clock'
import type { Subtest } from '../lib/types'

/** Reading time before the section clock starts (screenshot 4: "Mulai [50]"). */
export const INTRO_WAIT_SECONDS = 10

export default function SectionIntro({
  subtest,
  packageTitle,
  position,
  total,
  starting,
  error,
  onStart,
}: {
  subtest: Subtest
  packageTitle: string
  position: number
  total: number
  starting: boolean
  error: string | null
  onStart: () => void
}) {
  const [wait, setWait] = useState(INTRO_WAIT_SECONDS)

  useEffect(() => {
    setWait(INTRO_WAIT_SECONDS)
    const id = setInterval(() => setWait((w) => (w <= 1 ? 0 : w - 1)), 1000)
    return () => clearInterval(id)
  }, [subtest.id])

  return (
    <AppShell>
      <div className="card intro-card">
        <span className="eyebrow">
          {packageTitle} · Mata uji {position} dari {total}
        </span>
        <h1>{subtest.name}</h1>

        <div className="intro-meta">
          <div>
            <span className="num">{subtest.question_count}</span>
            <span className="lbl">Soal</span>
          </div>
          <div>
            <span className="num">{Math.round(subtest.duration_seconds / 60)}</span>
            <span className="lbl">Menit</span>
          </div>
          <div>
            <span className="num">{subtest.passing_grade}</span>
            <span className="lbl">Ambang skor</span>
          </div>
        </div>

        <ol className="intro-instructions">
          <li>
            Waktu pengerjaan {formatMinutes(subtest.duration_seconds)} dihitung sejak tombol <strong>Mulai</strong>{' '}
            ditekan dan terus berjalan meskipun halaman ditutup.
          </li>
          <li>Setiap soal memiliki lima pilihan jawaban A–E dengan tepat satu jawaban benar.</li>
          <li>Jawaban benar bernilai +5, jawaban salah maupun kosong bernilai 0 (tidak ada pengurangan nilai).</li>
          <li>
            Gunakan tombol <strong>Ragu — Ragu</strong> untuk menandai soal yang ingin ditinjau kembali, lalu buka{' '}
            <strong>Daftar Soal</strong> untuk berpindah antarsoal.
          </li>
          <li>Mata uji yang sudah diakhiri tidak dapat dibuka kembali.</li>
        </ol>

        {error ? <div className="notice error">{error}</div> : null}

        <button className="btn btn-red btn-lg btn-block" onClick={onStart} disabled={wait > 0 || starting}>
          {starting ? 'Menyiapkan soal…' : wait > 0 ? `Mulai [${wait}]` : 'Mulai'}
        </button>
        {wait > 0 ? <p className="muted" style={{ fontSize: 13, marginBottom: 0 }}>Waktu tunggu untuk membaca petunjuk pengerjaan.</p> : null}
      </div>
    </AppShell>
  )
}
