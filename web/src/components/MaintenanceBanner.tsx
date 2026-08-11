import { useMaintenance } from '../contexts/MaintenanceContext'
import { formatMaintenanceDateTime } from '../lib/maintenance'

export default function MaintenanceBanner() {
  const { status, phase, warningDismissed, dismissWarning } = useMaintenance()

  if (phase !== 'warning' || warningDismissed || !status?.starts_at || !status.ends_at) return null

  return (
    <aside className="maintenance-banner" role="status" aria-label="Pemberitahuan pemeliharaan terjadwal">
      <div className="maintenance-banner-inner">
        <span className="maintenance-banner-icon" aria-hidden="true">
          🛠
        </span>
        <div className="maintenance-banner-copy">
          <strong>Pemeliharaan terjadwal</strong>
          <span>
            Situs akan ditutup sementara pada {formatMaintenanceDateTime(status.starts_at)} hingga{' '}
            {formatMaintenanceDateTime(status.ends_at)}. {status.message}
          </span>
        </div>
        <button
          type="button"
          className="maintenance-banner-close"
          onClick={dismissWarning}
          aria-label="Tutup pemberitahuan pemeliharaan"
          title="Tutup"
        >
          ×
        </button>
      </div>
    </aside>
  )
}
