import Modal from './Modal'
import { formatMinutes } from '../lib/clock'
import type { Subtest } from '../lib/types'

export default function InformasiSoal({
  subtest,
  packageTitle,
  answeredCount,
  doubtCount,
  onClose,
}: {
  subtest: Subtest
  packageTitle: string
  answeredCount: number
  doubtCount: number
  onClose: () => void
}) {
  return (
    <Modal title="Informasi Soal" onClose={onClose} footer={<button className="btn btn-cyan" onClick={onClose}>Tutup</button>}>
      <ul className="info-list">
        <li>
          <span>Paket</span>
          <strong>{packageTitle}</strong>
        </li>
        <li>
          <span>Mata uji</span>
          <strong>{subtest.name}</strong>
        </li>
        <li>
          <span>Jumlah soal</span>
          <strong>{subtest.question_count} soal</strong>
        </li>
        <li>
          <span>Alokasi waktu</span>
          <strong>{formatMinutes(subtest.duration_seconds)}</strong>
        </li>
        <li>
          <span>Penilaian</span>
          <strong>Benar +5, salah/kosong 0</strong>
        </li>
        <li>
          <span>Sudah dijawab</span>
          <strong>
            {answeredCount} dari {subtest.question_count}
          </strong>
        </li>
        <li>
          <span>Ditandai ragu-ragu</span>
          <strong>{doubtCount} soal</strong>
        </li>
      </ul>
      <p className="muted" style={{ marginTop: 16, fontSize: 13.5 }}>
        Waktu berjalan di server. Menutup atau menyegarkan halaman tidak menghentikan hitungan mundur; jawaban yang
        sudah tersimpan tetap aman.
      </p>
    </Modal>
  )
}
