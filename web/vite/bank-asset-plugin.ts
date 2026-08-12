import type { Plugin } from 'vite'
import { buildBankArtifact } from './bank-artifact.ts'

/**
 * Bundles the compiled question bank into the offline app (AP-2): the same
 * `manifest.json` + `bank-<digest>.json` pair that GitHub Pages publishes, but
 * emitted into the app's own assets so a fresh install works with zero
 * connectivity.
 *
 * Only ever installed for the `VITE_OFFLINE` flavor, so a web build carries no
 * answer keys (C-29).
 */
export function bankAssetPlugin(bankDir: string): Plugin {
  let base = '/'

  return {
    name: 'tbs-bundled-bank',

    configResolved(config) {
      base = config.base
    },

    generateBundle() {
      const artifact = buildBankArtifact(bankDir)
      if (!artifact.versionsFromGit) {
        this.warn('bundled bank has no git history; question versions fall back to 1 (check out with fetch-depth: 0)')
      }
      this.emitFile({ type: 'asset', fileName: 'bank/manifest.json', source: artifact.manifestJson })
      this.emitFile({ type: 'asset', fileName: `bank/${artifact.bankFileName}`, source: artifact.bankJson })
    },

    configureServer(server) {
      // `tauri dev` runs this server with base './', so the app's
      // `BASE_URL + 'bank/…'` resolves to /bank/… here. `npm run dev:app` in a
      // plain browser keeps the Pages base, hence the second mount — dropped
      // when `base` is relative and the two collapse into one.
      const mounts = new Set(['/bank', `${base.replace(/\/$/, '')}/bank`].filter((path) => path.startsWith('/')))
      for (const mount of mounts) {
        server.middlewares.use(mount, (req, res, next) => {
          const name = (req.url ?? '').split('?')[0].replace(/^\//, '')
          if (name !== 'manifest.json' && !/^bank-[0-9a-f]{12}\.json$/.test(name)) return next()
          try {
            const artifact = buildBankArtifact(bankDir)
            const body = name === 'manifest.json' ? artifact.manifestJson : artifact.bankJson
            if (name !== 'manifest.json' && name !== artifact.bankFileName) return next()
            res.setHeader('Content-Type', 'application/json')
            res.setHeader('Cache-Control', 'no-store')
            res.end(body)
          } catch (err) {
            res.statusCode = 500
            res.end(JSON.stringify({ error: String(err) }))
          }
        })
      }
    },
  }
}
