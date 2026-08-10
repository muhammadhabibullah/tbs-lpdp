import { createClient } from '@supabase/supabase-js'
import { SUPABASE_PUBLIC_KEY, SUPABASE_URL } from './config'

/**
 * The Supabase client. Import this module ONLY from code that is behind the
 * dynamic import in lib/api.ts — it drags the whole client library with it.
 * Config flags and `ApiError` live in ./config for that reason.
 */
export const supabase = createClient(
  SUPABASE_URL ?? 'https://placeholder.supabase.co',
  SUPABASE_PUBLIC_KEY ?? 'placeholder-key',
  { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } },
)
