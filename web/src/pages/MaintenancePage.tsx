import AppShell from '../components/AppShell'
import { useMaintenance } from '../contexts/MaintenanceContext'
import { formatMaintenanceDateTime } from '../lib/maintenance'

export default function MaintenancePage() {
  const { status, refresh, refreshing } = useMaintenance()

  return (
    <AppShell hideChrome>
      <section className="card maintenance-card" aria-labelledby="maintenance-title">
        <div className="maintenance-card-icon" aria-hidden="true">
          🛠
        </div>
        <p className="maintenance-eyebrow">Pemeliharaan terjadwal</p>
        <h1 id="maintenance-title">Situs sedang dalam pemeliharaan</h1>
        <p className="maintenance-message">
          {status?.message || 'Kami sedang melakukan pemeliharaan terjadwal agar layanan tetap andal.'}
        </p>
        {status?.ends_at ? (
          <p className="maintenance-until">
            Layanan dijadwalkan kembali tersedia pada <strong>{formatMaintenanceDateTime(status.ends_at)}</strong>.
          </p>
        ) : null}
        <p className="muted">Halaman ini akan terbuka kembali secara otomatis setelah pemeliharaan selesai.</p>
        <button type="button" className="btn btn-navy" onClick={refresh} disabled={refreshing}>
          {refreshing ? 'Memeriksa…' : 'Periksa lagi'}
        </button>
      </section>
    </AppShell>
  )
}
