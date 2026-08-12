import fs from 'node:fs'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import type { Bank, BankPackage, BankQuestion, OptionKey, QuestionOption, SubtestKey } from '../src/lib/types.ts'

/**
 * Compiles `questions/bank/` — the git source of truth — into the single
 * `{ packages, questions }` structure the local exam engine consumes.
 *
 * Two consumers, one reader:
 *
 * - `vite/mock-bank-plugin.ts` (dev only) serves the result at
 *   `/__mock/bank.json` with images behind a middleware URL.
 * - `scripts/build-bank.ts` emits the published/bundled artifact with images
 *   inlined as data URIs, for the offline app (AP-3).
 *
 * Versions come from git history, never from in-memory counters, so the same
 * tree always compiles to the same bytes and `bank_version` changes if and only
 * if content changed (NF-32).
 */

// Mirrors questions/generator/common.py BLUEPRINT (docs §4).
const BLUEPRINT: Record<SubtestKey, { name: string; position: number; duration_seconds: number; passing_grade: number }> = {
  verbal: { name: 'Penalaran Verbal', position: 1, duration_seconds: 30 * 60, passing_grade: 70 },
  kuantitatif: { name: 'Penalaran Kuantitatif', position: 2, duration_seconds: 40 * 60, passing_grade: 75 },
  pemecahan_masalah: { name: 'Pemecahan Masalah', position: 3, duration_seconds: 20 * 60, passing_grade: 35 },
}

const SUBTEST_KEYS = Object.keys(BLUEPRINT) as SubtestKey[]

const MIME: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
}

/** How `image_url` is rendered for a question that carries a figure. */
export type ImageMode =
  /** `/__mock/image/<package>/<sha256>/<name>`, served by the dev middleware. */
  | 'url'
  /** `data:<mime>;base64,…` — self-contained, for the published bank file. */
  | 'inline'

export interface BankImage {
  bytes: Buffer
  mime: string
}

export interface ReadBankResult {
  bank: Bank
  /** Populated in `'url'` mode only; keyed by the middleware path suffix. */
  images: Map<string, BankImage>
  /** False when git history was unavailable and mtimes had to stand in. */
  versionsFromGit: boolean
  /** Newest bank commit as an ISO timestamp, or null without git history. */
  latestCommitAt: string | null
}

interface Revision {
  /** Number of commits that have touched the path. Starts at 1. */
  version: number
  updatedAt: string
}

interface Commit {
  date: string
  files: Set<string>
}

/**
 * `git log` over the bank directory, newest first. Renames are not followed —
 * bank file ids are derived from their path and are never renamed once pushed
 * (see CLAUDE.md conventions).
 */
function readCommits(bankDir: string): Commit[] | null {
  let stdout: string
  try {
    stdout = execFileSync(
      'git',
      ['-C', bankDir, 'log', '--pretty=format:%x00%aI', '--name-only', '--', '.'],
      { encoding: 'utf8', maxBuffer: 256 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'] },
    )
  } catch {
    // No git, not a repository, or a checkout with no history at all.
    return null
  }

  const commits: Commit[] = []
  for (const line of stdout.split('\n')) {
    if (line.startsWith('\0')) {
      const parsed = Date.parse(line.slice(1))
      commits.push({ date: Number.isNaN(parsed) ? new Date(0).toISOString() : new Date(parsed).toISOString(), files: new Set() })
    } else if (line !== '' && commits.length > 0) {
      commits[commits.length - 1].files.add(line)
    }
  }
  return commits.length > 0 ? commits : null
}

/**
 * Revision of one exact path and of every directory prefix above it, so a
 * package's version counts the commits that touched *any* of its files.
 */
function buildRevisions(commits: Commit[]): Map<string, Revision> {
  const revisions = new Map<string, Revision>()
  // Newest first: the first sighting of a key is its last change.
  for (const commit of commits) {
    const keys = new Set<string>()
    for (const file of commit.files) {
      keys.add(file)
      for (let cut = file.lastIndexOf('/'); cut > 0; cut = file.lastIndexOf('/', cut - 1)) {
        keys.add(file.slice(0, cut))
      }
    }
    for (const key of keys) {
      const existing = revisions.get(key)
      if (existing) existing.version += 1
      else revisions.set(key, { version: 1, updatedAt: commit.date })
    }
  }
  return revisions
}

function fallbackRevision(absolutePath: string): Revision {
  let mtime = 0
  try {
    mtime = fs.statSync(absolutePath).mtimeMs
  } catch {
    // Missing file: the caller is about to fail on it anyway.
  }
  return { version: 1, updatedAt: new Date(mtime).toISOString() }
}

interface RawQuestion {
  id: string
  number: number
  type: string
  question_text: string
  passage?: string | null
  image?: string | null
  difficulty: 'easy' | 'medium' | 'hard'
  options: QuestionOption[]
  correct_option: OptionKey
  explanations: Record<OptionKey, string>
}

interface RawPackage {
  title?: string
  description?: string
  difficulty: 'easy' | 'medium' | 'hard'
  ai_model: string
  ai_company: string
  ai_model_description: string
}

export function readBank(bankDir: string, options: { images?: ImageMode } = {}): ReadBankResult {
  const imageMode = options.images ?? 'url'
  const packages: BankPackage[] = []
  const questions: Record<string, BankQuestion[]> = {}
  const images = new Map<string, BankImage>()

  const commits = readCommits(bankDir)
  const revisions = commits ? buildRevisions(commits) : new Map<string, Revision>()
  const latestCommitAt = commits?.[0]?.date ?? null

  if (!fs.existsSync(bankDir)) {
    return { bank: { packages, questions }, images, versionsFromGit: commits !== null, latestCommitAt }
  }

  // git prints paths relative to the repository root; keys must match.
  let gitPrefix = ''
  if (commits) {
    try {
      const root = execFileSync('git', ['-C', bankDir, 'rev-parse', '--show-toplevel'], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim()
      gitPrefix = path.relative(root, bankDir).split(path.sep).join('/')
    } catch {
      gitPrefix = ''
    }
  }
  const revisionOf = (relativePath: string, absolutePath: string): Revision =>
    revisions.get(gitPrefix ? `${gitPrefix}/${relativePath}` : relativePath) ?? fallbackRevision(absolutePath)

  const packageDirs = fs
    .readdirSync(bankDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d+$/.test(entry.name))
    .sort((a, b) => Number(a.name) - Number(b.name))

  for (const dir of packageDirs) {
    const packageId = Number(dir.name)
    const manifestPath = path.join(bankDir, dir.name, 'package.json')
    if (!fs.existsSync(manifestPath)) continue
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8')) as RawPackage
    // The release digest is content-addressed, so an *uncommitted* edit still
    // produces a new release id and the engine still pins attempts correctly.
    const releaseDigest = createHash('sha256').update(JSON.stringify(manifest))

    const subtests = []
    for (const key of SUBTEST_KEYS) {
      const subtestDir = path.join(bankDir, dir.name, key)
      if (!fs.existsSync(subtestDir)) continue

      const files = fs
        .readdirSync(subtestDir)
        .filter((file) => file.endsWith('.json'))
        .sort()
      if (files.length === 0) continue

      const subtestId = `${packageId}-${key}`
      const compiled: BankQuestion[] = files.map((file) => {
        const absolutePath = path.join(subtestDir, file)
        const raw = JSON.parse(fs.readFileSync(absolutePath, 'utf8')) as RawQuestion
        releaseDigest.update(JSON.stringify(raw))

        let imageUrl: string | null = null
        if (raw.image) {
          const imagePath = path.join(bankDir, dir.name, raw.image)
          const bytes = fs.readFileSync(imagePath)
          const imageSha = createHash('sha256').update(bytes).digest('hex')
          const mime = MIME[path.extname(imagePath).toLowerCase()] ?? 'application/octet-stream'
          if (imageMode === 'inline') {
            imageUrl = `data:${mime};base64,${bytes.toString('base64')}`
          } else {
            const cacheKey = `${packageId}/${imageSha}/${path.basename(raw.image)}`
            images.set(cacheKey, { bytes, mime })
            imageUrl = `/__mock/image/${cacheKey}`
          }
          releaseDigest.update(imageSha)
        }

        const revision = revisionOf(`${dir.name}/${key}/${file}`, absolutePath)
        // Key order is fixed here on purpose: the published bank file must be
        // byte-identical across runs over the same tree (NF-32).
        return {
          id: raw.id,
          number: raw.number,
          qtype: raw.type,
          question_text: raw.question_text,
          passage: raw.passage ?? null,
          image_url: imageUrl,
          difficulty: raw.difficulty,
          options: raw.options,
          correct_option: raw.correct_option,
          explanations: raw.explanations,
          question_version: revision.version,
          question_updated_at: revision.updatedAt,
        }
      })
      compiled.sort((a, b) => a.number - b.number)
      questions[subtestId] = compiled

      const blueprint = BLUEPRINT[key]
      subtests.push({
        id: subtestId,
        package_id: packageId,
        key,
        name: blueprint.name,
        position: blueprint.position,
        // Actual count, not the blueprint count: the bank may still be in progress.
        question_count: compiled.length,
        duration_seconds: blueprint.duration_seconds,
        passing_grade: blueprint.passing_grade,
      })
    }

    if (subtests.length === 0) continue
    const release = revisionOf(dir.name, path.join(bankDir, dir.name))
    packages.push({
      id: packageId,
      title: manifest.title ?? `Paket ${packageId}`,
      description: manifest.description ?? '',
      is_published: true,
      created_at: new Date(0).toISOString(),
      difficulty: manifest.difficulty,
      ai_model: manifest.ai_model,
      ai_company: manifest.ai_company,
      ai_model_description: manifest.ai_model_description,
      question_version: release.version,
      last_updated_at: release.updatedAt,
      completed_attempts_total: 0,
      statistics_sample_total: 0,
      mean_score: null,
      median_score: null,
      statistics_coverage_started_at: release.updatedAt,
      score_statistics_coverage_started_at: release.updatedAt,
      release_id: `${packageId}:${releaseDigest.digest('hex')}`,
      subtests,
    })
  }

  return { bank: { packages, questions }, images, versionsFromGit: commits !== null, latestCommitAt }
}
