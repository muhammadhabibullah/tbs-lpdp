import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { mockBankPlugin } from './vite/mock-bank-plugin'

// The question bank lives outside `web/`; vite is always run with cwd = web/.
const BANK_DIR = path.resolve(process.cwd(), '../questions/bank')

export default defineConfig({
  // C-3: GitHub Pages serves this repo from /tbs-lpdp/.
  base: '/tbs-lpdp/',
  plugins: [react(), mockBankPlugin(BANK_DIR)],
  build: { outDir: 'dist', sourcemap: false },
})
