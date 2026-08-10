export interface DigestReport {
  question_id: string
  package_id: number
  subtest: string
  number: number
  question_version: number | null
  is_current_revision: boolean
  reason: string
  status: string
  selected_option: string | null
  comment: string
  created_at: string
  updated_at: string
}

export interface DigestPayload {
  window_start: string
  window_end: string
  activity_count: number
  open_backlog_count: number
  truncated_count: number
  reason_summary: Record<string, number>
  reports: DigestReport[]
}

const REASONS: Record<string, string> = {
  wrong_key: 'Kunci jawaban salah',
  ambiguous: 'Soal ambigu',
  bad_explanation: 'Pembahasan keliru',
  typo: 'Salah ketik/kalimat rancu',
  image_issue: 'Masalah gambar',
  other: 'Lainnya',
}

const SUBTESTS: Record<string, string> = {
  verbal: 'Penalaran Verbal',
  kuantitatif: 'Penalaran Kuantitatif',
  pemecahan_masalah: 'Pemecahan Masalah',
}

export function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function formatDate(iso: string, withTime = false): string {
  return new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}),
  }).format(new Date(iso))
}

function reportTitle(report: DigestReport): string {
  const version = report.question_version == null ? 'versi legacy' : `v${report.question_version}`
  const current = report.is_current_revision ? 'versi aktif' : 'versi lama'
  return `Paket ${report.package_id} · ${SUBTESTS[report.subtest] ?? report.subtest} · Soal ${report.number} (${version}, ${current})`
}

export function renderDigest(payload: DigestPayload): { subject: string; text: string; html: string } {
  const endDate = new Date(Date.parse(payload.window_end) - 1)
  const subjectDate = new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta', day: 'numeric', month: 'short', year: 'numeric',
  }).format(endDate)
  const subject = `[TBS LPDP] ${payload.activity_count} laporan soal — ${subjectDate}`
  const period = `${formatDate(payload.window_start, true)} WIB – ${formatDate(payload.window_end, true)} WIB`
  const summary = Object.entries(payload.reason_summary)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([reason, count]) => `${REASONS[reason] ?? reason}: ${count}`)
    .join(' · ')

  const textLines = [
    'Ringkasan laporan soal TBS LPDP',
    `Periode: ${period}`,
    `Baru/diperbarui: ${payload.activity_count}`,
    `Backlog terbuka: ${payload.open_backlog_count}`,
    summary ? `Alasan: ${summary}` : 'Alasan: tidak ada laporan baru',
    '',
  ]
  if (payload.reports.length === 0) {
    textLines.push('Tidak ada laporan baru pada periode ini. Otomasi berjalan normal.')
  } else {
    for (const report of payload.reports) {
      textLines.push(reportTitle(report))
      textLines.push(`ID: ${report.question_id}`)
      textLines.push(`Alasan: ${REASONS[report.reason] ?? report.reason} · Status: ${report.status}`)
      textLines.push(`Jawaban pengguna: ${report.selected_option ?? 'kosong'}`)
      textLines.push(`Diperbarui: ${formatDate(report.updated_at, true)} WIB`)
      textLines.push(`Catatan: ${report.comment || '(tanpa catatan)'}`, '')
    }
    if (payload.truncated_count > 0) {
      textLines.push(`${payload.truncated_count} laporan lain diringkas karena batas 200 detail.`)
    }
  }

  const details = payload.reports.length === 0
    ? '<p><strong>Tidak ada laporan baru.</strong> Otomasi berjalan normal.</p>'
    : payload.reports.map((report) => `
      <section style="border-top:1px solid #ddd;padding:12px 0">
        <h3 style="margin:0 0 6px;font-size:15px">${escapeHtml(reportTitle(report))}</h3>
        <p style="margin:3px 0"><code>${escapeHtml(report.question_id)}</code></p>
        <p style="margin:3px 0"><strong>Alasan:</strong> ${escapeHtml(REASONS[report.reason] ?? report.reason)} · <strong>Status:</strong> ${escapeHtml(report.status)}</p>
        <p style="margin:3px 0"><strong>Jawaban pengguna:</strong> ${escapeHtml(report.selected_option ?? 'kosong')}</p>
        <p style="margin:3px 0"><strong>Diperbarui:</strong> ${escapeHtml(formatDate(report.updated_at, true))} WIB</p>
        <p style="margin:7px 0 0;white-space:pre-wrap"><strong>Catatan:</strong> ${escapeHtml(report.comment || '(tanpa catatan)')}</p>
      </section>`).join('')

  const html = `<!doctype html><html><body style="font-family:system-ui,sans-serif;color:#30343b;line-height:1.45">
    <h2 style="margin-bottom:6px">Ringkasan laporan soal TBS LPDP</h2>
    <p style="margin-top:0;color:#666">${escapeHtml(period)}</p>
    <ul>
      <li>Baru/diperbarui: <strong>${payload.activity_count}</strong></li>
      <li>Backlog terbuka: <strong>${payload.open_backlog_count}</strong></li>
      <li>Alasan: ${escapeHtml(summary || 'tidak ada laporan baru')}</li>
    </ul>
    ${details}
    ${payload.truncated_count > 0 ? `<p><strong>${payload.truncated_count}</strong> laporan lain diringkas karena batas 200 detail.</p>` : ''}
  </body></html>`

  return { subject, text: textLines.join('\n'), html }
}
