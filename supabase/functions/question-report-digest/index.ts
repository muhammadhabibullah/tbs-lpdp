import { createClient } from 'npm:@supabase/supabase-js@2'
import { renderDigest, type DigestPayload } from './render.ts'

interface DigestRun {
  id: string
  status: 'pending' | 'sending' | 'sent' | 'failed' | 'manual_attention'
  email_payload: DigestPayload
}

function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status, headers: { 'Cache-Control': 'no-store' } })
}

function configuredKeys(): { automationKey: string; adminKey: string } {
  let named: Record<string, string> = {}
  try {
    named = JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS') ?? '{}')
  } catch {
    // A malformed platform variable is a configuration error below.
  }
  const automationKey = named.automations ?? Deno.env.get('AUTOMATIONS_API_KEY') ?? ''
  const adminKey = named.default ?? Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? automationKey
  if (!automationKey || !adminKey) throw new Error('Supabase automation/admin secret is not configured')
  return { automationKey, adminKey }
}

Deno.serve(async (request) => {
  if (request.method !== 'POST') return jsonResponse({ error: 'Method not allowed' }, 405)

  let keys: { automationKey: string; adminKey: string }
  try {
    keys = configuredKeys()
  } catch {
    return jsonResponse({ error: 'Function is not configured' }, 500)
  }
  if (request.headers.get('apikey') !== keys.automationKey) {
    return jsonResponse({ error: 'Unauthorized' }, 401)
  }

  let runId = ''
  try {
    const body = await request.json() as { run_id?: unknown }
    runId = typeof body.run_id === 'string' ? body.run_id : ''
  } catch {
    return jsonResponse({ error: 'Invalid JSON' }, 400)
  }
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(runId)) {
    return jsonResponse({ error: 'Invalid run_id' }, 400)
  }

  const url = Deno.env.get('SUPABASE_URL') ?? ''
  const resendKey = Deno.env.get('RESEND_API_KEY') ?? ''
  const recipient = Deno.env.get('REPORT_DIGEST_TO') ?? ''
  const sender = Deno.env.get('REPORT_DIGEST_FROM') ?? ''
  if (!url || !resendKey || !recipient || !sender) {
    return jsonResponse({ error: 'Email delivery is not configured' }, 500)
  }
  const admin = createClient(url, keys.adminKey, { auth: { persistSession: false } })

  const { data: claim, error: claimError } = await admin.rpc('claim_question_report_digest', {
    p_run_id: runId,
  })
  if (claimError) return jsonResponse({ error: 'Unable to claim digest run' }, 409)
  const run = claim?.run as DigestRun | undefined
  if (!run) return jsonResponse({ error: 'Digest run not found' }, 404)
  if (run.status === 'sent') return jsonResponse({ ok: true, already_sent: true })
  if (run.status !== 'sending') {
    return jsonResponse({ error: `Digest run is ${run.status}` }, 409)
  }

  const rendered = renderDigest(run.email_payload)
  let providerResponse: Response
  try {
    providerResponse = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${resendKey}`,
        'Content-Type': 'application/json',
        'Idempotency-Key': `tbs-report-digest/${runId}`,
      },
      body: JSON.stringify({
        from: sender,
        to: [recipient],
        subject: rendered.subject,
        text: rendered.text,
        html: rendered.html,
      }),
    })
  } catch {
    await admin.rpc('fail_question_report_digest', {
      p_run_id: runId,
      p_error: 'Network error while contacting email provider',
    })
    return jsonResponse({ error: 'Email provider unavailable' }, 502)
  }

  let providerData: { id?: string; message?: string; name?: string } = {}
  try {
    providerData = await providerResponse.json()
  } catch {
    // The status code remains sufficient for a redacted operational error.
  }
  if (!providerResponse.ok || !providerData.id) {
    const providerError = `Resend HTTP ${providerResponse.status}: ${providerData.name ?? providerData.message ?? 'request failed'}`
    await admin.rpc('fail_question_report_digest', { p_run_id: runId, p_error: providerError })
    return jsonResponse({ error: 'Email delivery failed' }, 502)
  }

  const { error: completeError } = await admin.rpc('complete_question_report_digest', {
    p_run_id: runId,
    p_provider_message_id: providerData.id,
  })
  if (completeError) {
    // Resend will deduplicate the same frozen payload/run ID during retry.
    return jsonResponse({ error: 'Email sent but delivery state was not recorded' }, 500)
  }
  return jsonResponse({ ok: true, provider_message_id: providerData.id })
})
