import fs from 'node:fs'
import path from 'node:path'
import { createHash } from 'node:crypto'
import type { Plugin } from 'vite'

/**
 * Dev-only backend fixture. Serves the git question bank (including answer
 * keys) at /__mock/bank.json so the SPA can run the full exam flow without a
 * Supabase project. `apply: 'serve'` guarantees none of this — and no answer
 * key — can ever end up in a production bundle (C-4).
 */

// Mirrors questions/generator/common.py BLUEPRINT (docs §4).
const BLUEPRINT: Record<string, { name: string; position: number; duration_seconds: number; passing_grade: number }> = {
  verbal: { name: 'Penalaran Verbal', position: 1, duration_seconds: 30 * 60, passing_grade: 70 },
  kuantitatif: { name: 'Penalaran Kuantitatif', position: 2, duration_seconds: 40 * 60, passing_grade: 75 },
  pemecahan_masalah: { name: 'Pemecahan Masalah', position: 3, duration_seconds: 20 * 60, passing_grade: 35 },
}

const MIME: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
}

const releaseHistory = new Map<number, { hash: string; version: number; updatedAt: string }>()
const questionHistory = new Map<string, { hash: string; version: number; updatedAt: string }>()
const imageCache = new Map<string, { bytes: Buffer; mime: string }>()

function readBank(bankDir: string) {
  const packages: unknown[] = []
  const questions: Record<string, unknown[]> = {}
  if (!fs.existsSync(bankDir)) return { packages, questions }

  const packageDirs = fs
    .readdirSync(bankDir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && /^\d+$/.test(e.name))
    .sort((a, b) => Number(a.name) - Number(b.name))

  for (const dir of packageDirs) {
    const packageId = Number(dir.name)
    const manifestPath = path.join(bankDir, dir.name, 'package.json')
    if (!fs.existsSync(manifestPath)) continue
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
    const releaseDigest = createHash('sha256').update(JSON.stringify(manifest))

    const subtests: unknown[] = []
    for (const key of Object.keys(BLUEPRINT)) {
      const subtestDir = path.join(bankDir, dir.name, key)
      if (!fs.existsSync(subtestDir)) continue

      const files = fs
        .readdirSync(subtestDir)
        .filter((f) => f.endsWith('.json'))
        .sort()
      if (files.length === 0) continue

      const subtestId = `${packageId}-${key}`
      questions[subtestId] = files.map((file) => {
        const raw = fs.readFileSync(path.join(subtestDir, file), 'utf8')
        const q = JSON.parse(raw)
        const normalizedQuestion = JSON.stringify(q)
        releaseDigest.update(normalizedQuestion)
        const questionDigest = createHash('sha256').update(normalizedQuestion)
        let imageUrl: string | null = null
        if (q.image) {
          const imagePath = path.join(bankDir, dir.name, q.image)
          const bytes = fs.readFileSync(imagePath)
          const imageSha = createHash('sha256').update(bytes).digest('hex')
          const imageName = path.basename(q.image)
          const cacheKey = `${packageId}/${imageSha}/${imageName}`
          imageCache.set(cacheKey, {
            bytes,
            mime: MIME[path.extname(imagePath).toLowerCase()] ?? 'application/octet-stream',
          })
          imageUrl = `/__mock/image/${cacheKey}`
          releaseDigest.update(imageSha)
          questionDigest.update(imageSha)
        }
        const questionHash = questionDigest.digest('hex')
        const previousQuestion = questionHistory.get(q.id)
        const revision = previousQuestion?.hash === questionHash
          ? previousQuestion
          : {
              hash: questionHash,
              version: (previousQuestion?.version ?? 0) + 1,
              updatedAt: new Date().toISOString(),
            }
        questionHistory.set(q.id, revision)
        return {
          id: q.id,
          number: q.number,
          qtype: q.type,
          question_text: q.question_text,
          passage: q.passage ?? null,
          image_url: imageUrl,
          difficulty: q.difficulty,
          options: q.options,
          correct_option: q.correct_option,
          explanations: q.explanations,
          question_version: revision.version,
          question_updated_at: revision.updatedAt,
        }
      })
      questions[subtestId].sort((a, b) => (a as { number: number }).number - (b as { number: number }).number)

      const blueprint = BLUEPRINT[key]
      subtests.push({
        id: subtestId,
        package_id: packageId,
        key,
        name: blueprint.name,
        position: blueprint.position,
        // Actual count, not the blueprint count: the bank may still be in progress.
        question_count: questions[subtestId].length,
        duration_seconds: blueprint.duration_seconds,
        passing_grade: blueprint.passing_grade,
      })
    }

    if (subtests.length === 0) continue
    const hash = releaseDigest.digest('hex')
    const previous = releaseHistory.get(packageId)
    const release = previous?.hash === hash
      ? previous
      : { hash, version: (previous?.version ?? 0) + 1, updatedAt: new Date().toISOString() }
    releaseHistory.set(packageId, release)
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
      release_id: `${packageId}:${release.hash}`,
      subtests,
    })
  }

  return { packages, questions }
}

export function mockBankPlugin(bankDir: string): Plugin {
  return {
    name: 'tbs-mock-bank',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__mock/bank.json', (_req, res) => {
        try {
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Cache-Control', 'no-store')
          res.end(JSON.stringify(readBank(bankDir)))
        } catch (err) {
          res.statusCode = 500
          res.end(JSON.stringify({ error: String(err) }))
        }
      })

      server.middlewares.use('/__mock/image/', (req, res, next) => {
        // req.url: /<package>/<sha256>/<file>; bytes stay in memory by hash so
        // an already-pinned mock attempt survives an edited image.
        const match = /^\/(\d+)\/([0-9a-f]{64})\/([\w.-]+)$/.exec((req.url ?? '').split('?')[0])
        if (!match) return next()
        const cached = imageCache.get(`${match[1]}/${match[2]}/${match[3]}`)
        if (!cached) return next()
        res.setHeader('Content-Type', cached.mime)
        res.setHeader('Cache-Control', 'public, max-age=31536000, immutable')
        res.end(cached.bytes)
      })
    },
  }
}
