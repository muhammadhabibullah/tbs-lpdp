import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL

/**
 * The public client key. Supabase's newer projects issue a *publishable* key
 * (`sb_publishable_…`); older ones issue the legacy *anon* JWT. They play the
 * same role — public, RLS-bound, safe in the bundle — so either is accepted.
 */
const publicKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY

/** False until the developer supplies the project URL + public key (C-1). */
export const isSupabaseConfigured = Boolean(url && publicKey)

export const supabase = createClient(url ?? 'https://placeholder.supabase.co', publicKey ?? 'placeholder-key', {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
})

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
