import type { MouseEvent } from 'react'
import { REPO_URL, openExternal } from '../lib/appRuntime'
import { IS_OFFLINE_APP } from '../lib/config'

/**
 * The maintainer's address, assembled at runtime: the served HTML is a JS
 * bundle either way, but a plain `mailto:` literal is exactly what address
 * harvesters grep for, and they do not execute the page.
 */
const MAILBOX = 'muhammadhabibullah.id'
const DOMAIN = 'gmail.com'

export const FEEDBACK_EMAIL = `${MAILBOX}@${DOMAIN}`

/**
 * Prefilled so a report arrives with the page it came from already attached.
 * `extraLines` carries whatever context the caller has — the offline app uses
 * it to attach the reported question, which has no server to reach (AP-9).
 */
export function feedbackMailto(subject = 'Masukan — TBS LPDP Try Out', extraLines: string[] = []): string {
  const body = [
    'Tulis masukan Anda di bawah ini:',
    '',
    '',
    '---',
    ...extraLines,
    `Halaman: ${typeof window === 'undefined' ? '-' : window.location.href}`,
    'Perangkat / browser: ',
  ].join('\n')
  return `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

/**
 * Props for a link that leaves the app. A Tauri webview refuses to navigate
 * away on its own, so there the click is handed to the system browser or mail
 * client instead (AP-9). On the web, only http(s) links open in a new tab —
 * a `mailto:` should stay in the current one.
 */
export function externalLinkProps(url: string): {
  href: string
  target?: string
  rel?: string
  onClick?: (event: MouseEvent) => void
} {
  if (IS_OFFLINE_APP) {
    return {
      href: url,
      onClick: (event) => {
        event.preventDefault()
        void openExternal(url)
      },
    }
  }
  return url.startsWith('http') ? { href: url, target: '_blank', rel: 'noopener noreferrer' } : { href: url }
}

export default function FeedbackFooter() {
  return (
    <footer className="site-footer" id="disclaimer">
      {/* Two columns, each carrying a heading block and then a divided one:
          Masukan → Disclaimer on the left, Kontak → Open Source Code on the
          right. Keeping the fine print in the left column is what closes the
          gap the taller right column used to leave under the button. */}
      <div className="site-footer-inner">
        <div className="site-footer-row">
          <div className="site-footer-about">
            <h2>Masukan &amp; Laporan</h2>
            <p>
              Laporkan bug atau usulkan jenis soal yang seharusnya muncul di test LPDP untuk meningkatkan kualitas Try Out LPDP ini.
              Silakan kirimkan masukan Anda ke alamat pada bagian Kontak, atau klik tombol “Kirim Masukan” untuk membuka email baru
              dengan subjek dan isi yang telah disiapkan.
            </p>
            <a className="btn btn-cyan btn-sm site-footer-cta" {...externalLinkProps(feedbackMailto())}>
              Kirim Masukan
            </a>

            <div className="site-footer-notes">
              <h2>Disclaimer</h2>
              <ul>
                <li>Konten dibuat dengan bantuan AI dan diperiksa otomatis. Laporan Anda membantu perbaikan.</li>
                {!IS_OFFLINE_APP && (
                  <li>Riwayat tersimpan selama <strong>10 hari</strong> kemudian dihapus otomatis.</li>
                )}
                <li>Try out gratis dan mandiri — bukan produk resmi LPDP atau PUSMENDIK.</li>
              </ul>
            </div>
          </div>

          <div className="site-footer-contact">
            <h2>Kontak</h2>
            <p className="contact-email">
              <span aria-hidden="true">🇮🇩</span>
              <a {...externalLinkProps(`mailto:${FEEDBACK_EMAIL}`)}>{FEEDBACK_EMAIL}</a>
            </p>
            <p className="contact-name">Muhammad Habibullah</p>
            <p className="contact-role">Calon Penerima Beasiswa LPDP Batch 1 Tahun 2026</p>

            {/* FE-43: shown in both the web build and the app. */}
            <div className="site-footer-source">
              <h2>Open Source Code</h2>
              <p>
                Seluruh kode dan bank soal try out ini terbuka. Silakan tinjau, laporkan masalah, atau berkontribusi.
              </p>
              <p className="contact-email">
                <span aria-hidden="true">💻</span>
                <a {...externalLinkProps(REPO_URL)}>github.com/muhammadhabibullah/tbs-lpdp</a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
