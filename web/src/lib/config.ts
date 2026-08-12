/**
 * Build-time config and the shared error type — deliberately free of any
 * `@supabase/supabase-js` import.
 *
 * HomePage needs `isSupabaseConfigured` on first paint, so whatever this module
 * pulls in lands in the eager bundle. Keeping `createClient` out of here is what
 * lets the ~110 kB client library stay in the lazily-imported `supabaseApi`
 * chunk (see lib/api.ts).
 */

/**
 * The offline app (v6): Tauri shell, local exam engine, no account and no
 * network needed to take a try-out. Inlined by Vite, so the branches it guards
 * are eliminated from the other two flavors and vice versa.
 */
export const IS_OFFLINE_APP = import.meta.env.VITE_OFFLINE === 'true'

/**
 * C-31: the app talks to no backend at all, so its bundle must not carry a
 * project URL or key even if one happens to sit in the build environment.
 */
export const SUPABASE_URL = IS_OFFLINE_APP ? undefined : import.meta.env.VITE_SUPABASE_URL

/**
 * The public client key. Supabase's newer projects issue a *publishable* key
 * (`sb_publishable_…`); older ones issue the legacy *anon* JWT. They play the
 * same role — public, RLS-bound, safe in the bundle — so either is accepted.
 */
export const SUPABASE_PUBLIC_KEY = IS_OFFLINE_APP
  ? undefined
  : import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY

/**
 * Public Cloudflare Turnstile site key. The matching secret belongs in
 * Supabase Auth's CAPTCHA settings and must never be added to this repository.
 * There is no anonymous sign-up in the app, so there is nothing to protect.
 */
export const TURNSTILE_SITE_KEY = IS_OFFLINE_APP
  ? undefined
  : import.meta.env.VITE_TURNSTILE_SITE_KEY?.trim() || undefined

/** False until the developer supplies the project URL + public key (C-1). */
export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_PUBLIC_KEY)

export class ApiError extends Error {
  code?: string
  constructor(message: string, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

/** Section expired server-side — the section was auto-graded (BE-2). */
export const DEADLINE_PASSED = 'P0004'
/** Section already finished; writes are rejected. */
export const ALREADY_FINISHED = 'P0003'

/** A new anonymous identity needs a server-verified CAPTCHA token. */
export const HUMAN_VERIFICATION_REQUIRED = 'HUMAN_VERIFICATION_REQUIRED'

/**
 * Fired on `window` after the offline app hot-swaps a newer question bank
 * (AP-4). A DOM event rather than a shared store so pages can listen without
 * importing the bank machinery into the web bundle.
 */
export const BANK_UPDATED_EVENT = 'tbs-lpdp:bank-updated'
