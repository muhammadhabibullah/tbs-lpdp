import type { Plugin } from 'vite'
import { readBank, type BankImage } from './bank-reader.ts'

/**
 * Dev-only backend fixture. Serves the git question bank (including answer
 * keys) at /__mock/bank.json so the SPA can run the full exam flow without a
 * Supabase project. `apply: 'serve'` guarantees none of this — and no answer
 * key — can ever end up in a *web* production bundle (C-4).
 *
 * The offline app reaches the same compiled bank a different way: a snapshot
 * built by `scripts/build-bank.ts` and bundled into the installer (AP-2/AP-3).
 */

/**
 * Bytes are kept across re-reads and keyed by hash, so a mock attempt that was
 * pinned to an older release keeps rendering its figures after the file on disk
 * is edited.
 */
const imageCache = new Map<string, BankImage>()

export function mockBankPlugin(bankDir: string): Plugin {
  return {
    name: 'tbs-mock-bank',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__mock/bank.json', (_req, res) => {
        try {
          const { bank, images } = readBank(bankDir, { images: 'url' })
          for (const [key, image] of images) imageCache.set(key, image)
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Cache-Control', 'no-store')
          res.end(JSON.stringify(bank))
        } catch (err) {
          res.statusCode = 500
          res.end(JSON.stringify({ error: String(err) }))
        }
      })

      server.middlewares.use('/__mock/image/', (req, res, next) => {
        // req.url: /<package>/<sha256>/<file>
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
