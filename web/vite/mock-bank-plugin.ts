import fs from 'node:fs'
import path from 'node:path'
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
        const q = JSON.parse(fs.readFileSync(path.join(subtestDir, file), 'utf8'))
        return {
          id: q.id,
          number: q.number,
          qtype: q.type,
          question_text: q.question_text,
          passage: q.passage ?? null,
          image_url: q.image ? `/__mock/image/${packageId}/${path.basename(q.image)}` : null,
          options: q.options,
          correct_option: q.correct_option,
          explanations: q.explanations,
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
    packages.push({
      id: packageId,
      title: manifest.title ?? `Paket ${packageId}`,
      description: manifest.description ?? '',
      is_published: true,
      created_at: new Date(0).toISOString(),
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
        // req.url here is the path after the mount point: /<package>/<file>
        const match = /^\/(\d+)\/([\w.-]+)$/.exec((req.url ?? '').split('?')[0])
        if (!match) return next()
        const file = path.join(bankDir, match[1], 'images', match[2])
        if (!file.startsWith(path.join(bankDir, match[1])) || !fs.existsSync(file)) return next()
        res.setHeader('Content-Type', MIME[path.extname(file).toLowerCase()] ?? 'application/octet-stream')
        res.end(fs.readFileSync(file))
      })
    },
  }
}
