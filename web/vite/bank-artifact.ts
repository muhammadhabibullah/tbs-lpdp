import { createHash } from 'node:crypto'
import { readBank } from './bank-reader.ts'
import { BANK_SCHEMA_VERSION, MANIFEST_SCHEMA_VERSION, MIN_APP_VERSION, type BankManifest } from '../src/lib/bankSchema.ts'

/**
 * Compiles the git bank into the two files that make up the published artifact
 * (AP-3): an immutable, content-addressed `bank-<digest>.json` and the small
 * mutable `manifest.json` that points at it.
 *
 * Everything here is a pure function of the git tree — question versions come
 * from commit history and `generated_at` from the newest bank commit — so two
 * runs over the same tree emit byte-identical files (NF-32).
 */

export interface BankArtifact {
  manifest: BankManifest
  manifestJson: string
  /** `bank-<digest>.json` */
  bankFileName: string
  bankJson: string
  /** Whether git history was available; false means the output is not stable. */
  versionsFromGit: boolean
}

export function buildBankArtifact(bankDir: string): BankArtifact {
  const { bank, versionsFromGit, latestCommitAt } = readBank(bankDir, { images: 'inline' })

  const bankJson = JSON.stringify(bank)
  const sha256 = createHash('sha256').update(bankJson, 'utf8').digest('hex')
  const bankVersion = sha256.slice(0, 12)
  const bankFileName = `bank-${bankVersion}.json`

  const manifest: BankManifest = {
    schema_version: MANIFEST_SCHEMA_VERSION,
    bank_schema_version: BANK_SCHEMA_VERSION,
    min_app_version: MIN_APP_VERSION,
    bank_version: bankVersion,
    // Wall-clock time would make every publish a new manifest; the newest bank
    // commit is the honest answer and keeps the manifest reproducible too.
    generated_at: latestCommitAt ?? new Date(0).toISOString(),
    bank: {
      url: bankFileName,
      sha256,
      bytes: Buffer.byteLength(bankJson, 'utf8'),
    },
  }

  return {
    manifest,
    manifestJson: `${JSON.stringify(manifest, null, 2)}\n`,
    bankFileName,
    bankJson,
    versionsFromGit,
  }
}
