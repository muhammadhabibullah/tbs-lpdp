/**
 * NF-3: the countdown must track the server-issued deadline, not the device
 * clock. Every RPC returns `server_time`; we keep the offset and use it for all
 * time math. The client countdown stays cosmetic — the database enforces
 * deadlines regardless.
 */

let skewMs = 0

export function syncServerTime(serverTime: string | null | undefined): void {
  if (!serverTime) return
  const parsed = Date.parse(serverTime)
  if (!Number.isNaN(parsed)) skewMs = parsed - Date.now()
}

export function serverNow(): number {
  return Date.now() + skewMs
}

export function remainingMs(deadlineIso: string): number {
  return Math.max(0, Date.parse(deadlineIso) - serverNow())
}

/** "mm:ss", or "hh:mm:ss" past an hour — matches the CBT "Sisa Waktu" box. */
export function formatClock(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return hours > 0 ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
}

/** "00 jam 20 menit" — the phrasing used in the Konfirmasi Tes dialog. */
export function formatDurationWords(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  return `${String(hours).padStart(2, '0')} jam ${String(minutes).padStart(2, '0')} menit`
}

export function formatMinutes(durationSeconds: number): string {
  return `${Math.round(durationSeconds / 60)} menit`
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('id-ID', {
    timeZone: 'Asia/Jakarta',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('id-ID', {
    timeZone: 'Asia/Jakarta',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
