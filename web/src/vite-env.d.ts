/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL?: string
  /** New-style public key (`sb_publishable_…`). */
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string
  /** Legacy public key (anon JWT). Used only if the publishable key is unset. */
  readonly VITE_SUPABASE_ANON_KEY?: string
  /** Public Cloudflare Turnstile site key; the secret is configured in Supabase only. */
  readonly VITE_TURNSTILE_SITE_KEY?: string
  readonly VITE_USE_MOCK?: string
  /**
   * Offline app flavor (v6): local exam engine + bundled question bank inside
   * the Tauri shell. The Pages deploy workflow asserts this is unset (C-29).
   */
  readonly VITE_OFFLINE?: string
  /** Development server only; ignored by production builds. */
  readonly VITE_BYPASS_MAINTENANCE?: string
  /** Development server only; forces a maintenance phase in the local engine. */
  readonly VITE_MOCK_MAINTENANCE_PHASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
