/**
 * Build-time config and the shared error type — deliberately free of any
 * `@supabase/supabase-js` import.
 *
 * HomePage needs `isSupabaseConfigured` on first paint, so whatever this module
 * pulls in lands in the eager bundle. Keeping `createClient` out of here is what
 * lets the ~110 kB client library stay in the lazily-imported `supabaseApi`
 * chunk (see lib/api.ts).
 */

export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

/**
 * The public client key. Supabase's newer projects issue a *publishable* key
 * (`sb_publishable_…`); older ones issue the legacy *anon* JWT. They play the
 * same role — public, RLS-bound, safe in the bundle — so either is accepted.
 */
export const SUPABASE_PUBLIC_KEY =
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY

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
