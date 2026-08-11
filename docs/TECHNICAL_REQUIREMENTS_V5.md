# Technical Requirements v5 — Robot and AI-Scraper Deterrence

| | |
|---|---|
| Status | v5.0 — implemented; production activation requires operator configuration |
| Date | 2026-08-12 |
| Extends | Core requirements through v4 and v3.1 |
| Scope | Server-verified CAPTCHA for new anonymous identities |

## 1. Goal and limits

The public SPA must make bulk automated use materially harder without requiring
an email account or challenging a returning browser on every visit. New
anonymous identities therefore pass Cloudflare Turnstile before Supabase Auth
creates the user. Existing persisted sessions continue silently.

This control protects the live application and its authenticated Supabase RPCs.
It is not DRM: a person can still copy or screenshot content after verification,
a sophisticated scraper can use human challenge-solving, and question files in
a public source repository remain public.

Primary implementation references:

- [Supabase CAPTCHA protection](https://supabase.com/docs/guides/auth/auth-captcha)
- [Supabase anonymous sign-in abuse prevention](https://supabase.com/docs/guides/auth/auth-anonymous#abuse-prevention-and-rate-limits)
- [Supabase JS `signInAnonymously`](https://supabase.com/docs/reference/javascript/auth-signinanonymously)

## 2. Requirements

### 2.1 Constraints

| ID | Requirement |
|----|-------------|
| C-25 | CAPTCHA verification is enforced by Supabase Auth, not trusted JavaScript. The Cloudflare secret exists only in Supabase; the bundle receives only the public Turnstile site key. |
| C-26 | Bot protection does not weaken C-4: active answer keys remain inaccessible and all application RPCs retain their existing authenticated grants and ownership checks. |
| C-27 | The feature is described as deterrence. UI and documentation must not claim that copying, screenshots, public-repository access, or all automated collection are impossible. |

### 2.2 Frontend

| ID | Requirement |
|----|-------------|
| FE-39 | Before mounting any normal route, the SPA checks for a persisted session. A returning session passes silently; a browser needing a new anonymous identity sees a Bahasa Indonesia Turnstile gate. |
| FE-40 | The challenge script is loaded only when needed, supports retry and expiry, and a failure never falls through to protected routes. Mock mode never loads Turnstile. |
| FE-41 | The token is single-use input to `signInAnonymously({ options: { captchaToken } })`; it is not stored in local storage, application tables, logs, or URLs. |

### 2.3 Backend and operations

| ID | Requirement |
|----|-------------|
| BE-46 | Supabase Authentication enables CAPTCHA protection with Cloudflare Turnstile. Anonymous account creation without a valid token is rejected server-side; existing authenticated sessions and database RPC contracts are unchanged. |
| BE-47 | Supabase's IP-based anonymous-sign-in rate limit remains enabled alongside CAPTCHA. Existing per-user attempt, report, event, capacity, and retention controls remain additive. |
| NF-28 | A returning browser adds no third-party request for bot protection. A new browser loads Turnstile once before its first authenticated content request. |
| NF-29 | Production configuration is fail-closed when `VITE_TURNSTILE_SITE_KEY` is present: protected routes do not mount until session reuse or successful verification. A missing site key preserves the pre-v5 client for staged rollout, while Supabase remains the final authority. |

## 3. Delivered files

| File | Change |
|------|--------|
| `web/src/components/HumanVerificationGate.tsx` | Session-aware pre-route Turnstile gate and retry/error states |
| `web/src/lib/config.ts`, `types.ts`, `api.ts`, `supabaseApi.ts`, `mockApi.ts` | Public site-key config and CAPTCHA-token auth contract |
| `web/src/App.tsx`, `styles.css` | Global placement and responsive presentation |
| `web/.env.example`, `.github/workflows/deploy-web.yml` | Public site-key configuration and deployment wiring |

No SQL migration is needed. Token verification belongs to Supabase Auth's
managed configuration, before a JWT and `auth.uid()` exist.

## 4. Production activation

1. Create a Cloudflare Turnstile widget for the production hostname. Keep its
   secret out of git; copy only its public site key to the frontend.
2. Add repository Actions variable `VITE_TURNSTILE_SITE_KEY` and deploy the SPA.
   At this point the official UI is gated, but direct Auth calls are not yet
   protected.
3. In Supabase Dashboard, open **Authentication → Bot and Abuse Protection**,
   choose Cloudflare Turnstile, enter the Turnstile **secret**, and enable
   CAPTCHA protection. This makes bypassing the SPA insufficient.
4. Confirm a clean/private browser receives the challenge and a returning
   browser with a persisted session does not.

For rollback, disable CAPTCHA in Supabase first, then remove the GitHub variable
and redeploy. This order avoids stranding new browsers with a backend that
requires tokens from a frontend that no longer produces them.

## 5. Acceptance criteria

| # | Check | Expected |
|---|-------|----------|
| A-1 | Returning browser with a valid session | Routes mount without loading the Turnstile script |
| A-2 | New browser with site key configured | Normal routes remain unmounted and the verification card appears |
| A-3 | Valid challenge with Supabase CAPTCHA enabled | Anonymous sign-in succeeds once; package catalogue loads |
| A-4 | Direct anonymous sign-in without token | Supabase Auth rejects account creation |
| A-5 | Expired/failed challenge or blocked script | No content route mounts; the user gets a retryable Bahasa Indonesia error |
| A-6 | Mock mode with a production site key in the environment | Mock routes load; no Turnstile network request occurs |
| A-7 | Token inspection after success | Token is absent from local/session storage, URLs, and application data |
| A-8 | `cd web && npm run build` | Typecheck and production build exit 0 |
