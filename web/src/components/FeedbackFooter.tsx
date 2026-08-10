import { useState } from 'react'

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
  const [copied, setCopied] = useState(false)

  async function copyAddress() {
    try {
      await navigator.clipboard.writeText(FEEDBACK_EMAIL)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard blocked (insecure context, permission denied): the address is
      // on screen next to this button, so selecting it by hand still works.
      setCopied(false)
    }
  }

  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div>
          <h2>Masukan &amp; Laporan</h2>
          <p>
            Menemukan soal yang keliru, pembahasan yang salah, atau kendala teknis? Kirim email ke{' '}
            <a href={feedbackMailto()}>{FEEDBACK_EMAIL}</a>. Setiap masukan dibaca dan dipakai untuk memperbaiki bank
            soal.
          </p>
        </div>
        <div className="site-footer-actions">
          <a className="btn btn-cyan btn-sm" href={feedbackMailto()}>
            Kirim Masukan
          </a>
          <button className="btn btn-ghost btn-sm" type="button" onClick={() => void copyAddress()}>
            {copied ? '✓ Alamat tersalin' : 'Salin alamat email'}
          </button>
        </div>
      </div>
      <p className="site-footer-note">
        Try out ini gratis dan dikelola mandiri — bukan produk resmi LPDP maupun PUSMENDIK.
      </p>
    </footer>
  )
}
