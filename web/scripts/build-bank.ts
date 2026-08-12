/**
 * Emits the published question-bank artifact (v6 §4, AP-3):
 *
 *     <out>/manifest.json          small, mutable, fetched with a cache-buster
 *     <out>/bank-<digest>.json     content-addressed, immutable
 *
 * Used twice in CI: `deploy-web.yml` publishes the output under GitHub Pages at
 * `/tbs-lpdp/bank/`, and `release-app.yml` produces the snapshot bundled into
 * the installers so a fresh install works with zero connectivity.
 *
 *     node scripts/build-bank.ts --out dist/bank
 *
 * Requires Node ≥ 22.18 (native TypeScript type stripping).
 */

import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { parseArgs } from 'node:util'
import { buildBankArtifact } from '../vite/bank-artifact.ts'

const { values } = parseArgs({
  options: {
    out: { type: 'string', default: 'dist/bank' },
    'bank-dir': { type: 'string' },
    /** Escape hatch for local experiments; CI must never pass it. */
    'skip-validate': { type: 'boolean', default: false },
    help: { type: 'boolean', default: false },
  },
})

if (values.help) {
  console.log('usage: node scripts/build-bank.ts [--out <dir>] [--bank-dir <dir>] [--skip-validate]')
  process.exit(0)
}

// Run from web/; the bank and the validator live one level up.
const repoRoot = path.resolve(process.cwd(), '..')
const bankDir = path.resolve(values['bank-dir'] ?? path.join(repoRoot, 'questions/bank'))
const outDir = path.resolve(values.out)

/** validate_bank.py stays the gate: a broken bank never reaches users (§4). */
if (!values['skip-validate']) {
  const validator = path.join(repoRoot, 'questions/generator/validate_bank.py')
  console.log(`build-bank: validating ${path.relative(repoRoot, bankDir)}`)
  const result = spawnSync('python3', [validator], { cwd: repoRoot, stdio: 'inherit' })
  if (result.error) {
    console.error(`build-bank: could not run ${validator}: ${result.error.message}`)
    process.exit(1)
  }
  if (result.status !== 0) {
    console.error('build-bank: validate_bank.py failed; refusing to publish')
    process.exit(result.status ?? 1)
  }
}

const artifact = buildBankArtifact(bankDir)

if (!artifact.versionsFromGit) {
  // Without commit history every question falls back to version 1 + mtime,
  // which is neither meaningful nor reproducible (NF-32). In CI this means
  // actions/checkout ran without `fetch-depth: 0`.
  console.error('build-bank: no git history for the question bank; check out the full history (fetch-depth: 0)')
  process.exit(1)
}

if (artifact.manifest.bank.bytes === 0 || artifact.bankJson === '{"packages":[],"questions":{}}') {
  console.error(`build-bank: compiled an empty bank from ${bankDir}`)
  process.exit(1)
}

fs.mkdirSync(outDir, { recursive: true })
fs.writeFileSync(path.join(outDir, artifact.bankFileName), artifact.bankJson)
fs.writeFileSync(path.join(outDir, 'manifest.json'), artifact.manifestJson)

const megabytes = artifact.manifest.bank.bytes / 1024 / 1024
console.log(`build-bank: ${artifact.bankFileName} (${megabytes.toFixed(2)} MB) + manifest.json → ${outDir}`)
console.log(`build-bank: bank_version=${artifact.manifest.bank_version} generated_at=${artifact.manifest.generated_at}`)
// AP-3 sets ~10 MB as the point to revisit inlining images as data URIs.
if (megabytes > 10) console.warn('build-bank: bank exceeds 10 MB — revisit inlining images (AP-3)')
