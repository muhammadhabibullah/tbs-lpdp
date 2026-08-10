/**
 * The maintainer's address, assembled at runtime: the served HTML is a JS
 * bundle either way, but a plain `mailto:` literal is exactly what address
 * harvesters grep for, and they do not execute the page.
 */
const MAILBOX = 'muhammadhabibullah.id'
const DOMAIN = 'gmail.com'

export const FEEDBACK_EMAIL = `${MAILBOX}@${DOMAIN}`

/** Prefilled so a report arrives with the page it came from already attached. */
export function feedbackMailto(subject = 'Masukan — TBS LPDP Try Out'): string {
  const body = [
    'Tulis masukan Anda di bawah ini:',
    '',
    '',
    '---',
    `Halaman: ${typeof window === 'undefined' ? '-' : window.location.href}`,
    'Perangkat / browser: ',
  ].join('\n')
  return `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

export default function FeedbackFooter() {
  return (
    <footer className="site-footer" id="disclaimer">
      {/* One container for both rows, so the fine print lines up with the
          heading above it instead of being centred on its own. */}
      <div className="site-footer-inner">
        <div className="site-footer-row">
          <div>
            <h2>Masukan &amp; Laporan</h2>
            <p>
              Punya saran atau temukan kesalahan? Kirim email ke{' '}
              <a href={feedbackMailto()}>{FEEDBACK_EMAIL}</a>.
            </p>
            <p className="site-footer-contact">
              <strong>Kontak:</strong> Muhammad Habibullah
              <span>Calon Penerima Beasiswa LPDP Jalur Non-LoA</span>
            </p>
          </div>
          <div className="site-footer-actions">
            <a className="btn btn-cyan btn-sm" href={feedbackMailto()}>
              Kirim Masukan
            </a>
          </div>
        </div>

        <ul className="site-footer-notes">
          <li>Konten dibuat dengan bantuan AI dan diperiksa otomatis. Laporan Anda membantu perbaikan.</li>
          <li>Riwayat tersimpan selama <strong>7 hari</strong> kemudian dihapus otomatis.</li>
          <li>Try out gratis dan mandiri — bukan produk resmi LPDP atau PUSMENDIK.</li>
        </ul>
      </div>
    </footer>
  )
}
