/**
 * The contract between the published question-bank artifact and the offline app
 * (v6 §4). Deliberately dependency-free: `scripts/build-bank.ts` runs this file
 * under plain Node, and the app imports it in the browser.
 */

/** Shape of `manifest.json` itself. Bump only if these fields change. */
export const MANIFEST_SCHEMA_VERSION = 1

/**
 * Shape of the bank payload the local engine consumes. An app whose
 * `BANK_SCHEMA_VERSION` is lower than a manifest's refuses the download and
 * asks the user to update the app instead (AP-5).
 */
export const BANK_SCHEMA_VERSION = 1

/** Oldest app release that can read a bank at `BANK_SCHEMA_VERSION`. */
export const MIN_APP_VERSION = '0.1.0'

export interface BankManifest {
  schema_version: number
  bank_schema_version: number
  min_app_version: string
  /** First 12 hex characters of the bank file's SHA-256. */
  bank_version: string
  generated_at: string
  bank: {
    /** Relative to the manifest's own URL. */
    url: string
    sha256: string
    bytes: number
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/** Structural validation only — the SHA-256 is checked against the payload. */
export function parseManifest(value: unknown): BankManifest | null {
  if (!isRecord(value) || !isRecord(value.bank)) return null
  const bank = value.bank
  if (
    typeof value.schema_version !== 'number' ||
    typeof value.bank_schema_version !== 'number' ||
    typeof value.min_app_version !== 'string' ||
    typeof value.bank_version !== 'string' ||
    typeof value.generated_at !== 'string' ||
    typeof bank.url !== 'string' ||
    typeof bank.sha256 !== 'string' ||
    typeof bank.bytes !== 'number'
  ) {
    return null
  }
  if (!/^[0-9a-f]{64}$/.test(bank.sha256) || !/^[0-9a-f]{12}$/.test(value.bank_version)) return null
  // The manifest names the file to fetch; keep it a plain sibling name so a
  // hostile or corrupted manifest cannot redirect the download elsewhere.
  if (!/^bank-[0-9a-f]{12}\.json$/.test(bank.url)) return null
  return {
    schema_version: value.schema_version,
    bank_schema_version: value.bank_schema_version,
    min_app_version: value.min_app_version,
    bank_version: value.bank_version,
    generated_at: value.generated_at,
    bank: { url: bank.url, sha256: bank.sha256, bytes: bank.bytes },
  }
}

/** Compares dotted numeric versions; suffixes such as `-beta` are ignored. */
export function compareVersions(a: string, b: string): number {
  const parse = (value: string) =>
    value
      .split('-')[0]
      .split('.')
      .map((part) => Number.parseInt(part, 10) || 0)
  const left = parse(a)
  const right = parse(b)
  for (let i = 0; i < Math.max(left.length, right.length); i++) {
    const diff = (left[i] ?? 0) - (right[i] ?? 0)
    if (diff !== 0) return diff < 0 ? -1 : 1
  }
  return 0
}
