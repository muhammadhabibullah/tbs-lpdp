---
kind: external_dependency
name: Cloudflare Turnstile — server-side bot protection for anonymous sign-in
slug: cloudflare-turnstile
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
source_files:
    - web/src/components/HumanVerificationGate.tsx
---

### Identity & role
- Cloudflare Turnstile is used to protect anonymous identity creation on the web frontend, acting as a captcha-like challenge before a new anonymous Supabase session is minted.

### Integration point
- Frontend gate component `HumanVerificationGate.tsx` renders the Turnstile widget; successful challenges are validated server-side before `start_attempt` proceeds.

### Durable usage model
- Only applied to new anonymous identities; returning users reuse their persisted session. This is a deterrence layer, not a full auth provider.

### Verify exact API/params against official docs
- Confirm site key / secret placement and the server-side validation endpoint used by the Supabase edge function or RPC that guards anonymous sign-in.