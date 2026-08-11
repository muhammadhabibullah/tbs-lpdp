/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL?: string
  /** New-style public key (`sb_publishable_…`). */
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string
  /** Legacy public key (anon JWT). Used only if the publishable key is unset. */
  readonly VITE_SUPABASE_ANON_KEY?: string
  readonly VITE_USE_MOCK?: string
  /** Development server only; ignored by production builds. */
  readonly VITE_BYPASS_MAINTENANCE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
