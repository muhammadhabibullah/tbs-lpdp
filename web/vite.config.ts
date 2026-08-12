import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { mockBankPlugin } from './vite/mock-bank-plugin.ts'
import { bankAssetPlugin } from './vite/bank-asset-plugin.ts'

// The question bank lives outside `web/`; vite is always run with cwd = web/.
const BANK_DIR = path.resolve(process.cwd(), '../questions/bank')

/**
 * Three build flavors, one codebase (v6 §2). The selector is inlined by Vite, so
 * each bundle contains only its own backend:
 *
 * - web production (default)  → supabaseApi, base /tbs-lpdp/
 * - dev mock (VITE_USE_MOCK)  → local engine + the serve-only bank middleware
 * - offline app (VITE_OFFLINE)→ local engine + the bundled/cached bank, base ./
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const offline = env.VITE_OFFLINE === 'true'
  const mock = env.VITE_USE_MOCK === 'true'
  // Set by the Tauri CLI for both `tauri dev` and `tauri build`.
  const tauri = Boolean(process.env.TAURI_ENV_PLATFORM)

  return {
    /**
     * Both flavor selectors, forced to literals. Vite only inlines env vars it
     * actually has, and an *undefined* `import.meta.env.VITE_OFFLINE` never
     * folds to a constant — without folding, Rollup keeps both backends in
     * every bundle, which is exactly what C-29 (no local engine or answer key
     * on GitHub Pages) and C-31 (no Supabase or Turnstile key in the app)
     * forbid. Defining them here makes the dead branch provably dead.
     */
    define: {
      'import.meta.env.VITE_USE_MOCK': JSON.stringify(String(mock)),
      'import.meta.env.VITE_OFFLINE': JSON.stringify(String(offline)),
    },
    // C-3: GitHub Pages serves this repo from /tbs-lpdp/. A Tauri webview
    // serves the app from its own root, so assets must be relative (AP-1).
    base: tauri ? './' : '/tbs-lpdp/',
    plugins: [react(), mockBankPlugin(BANK_DIR), ...(offline ? [bankAssetPlugin(BANK_DIR)] : [])],
    build: {
      outDir: 'dist',
      sourcemap: false,
      // Tauri ships a current WebView2/WKWebView/WebKitGTK; Android's is at
      // least Chrome 108. Elsewhere keep Vite's own browser baseline.
      ...(tauri ? { target: ['es2022', 'chrome108', 'safari15'] } : {}),
    },
    // Vite's default HMR/websocket setup does not survive the Tauri origin.
    clearScreen: false,
    server: tauri ? { strictPort: true, host: process.env.TAURI_DEV_HOST || false } : undefined,
  }
})
