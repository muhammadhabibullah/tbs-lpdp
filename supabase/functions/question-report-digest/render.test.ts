import assert from 'node:assert/strict'
import test from 'node:test'
import { escapeHtml, renderDigest, type DigestPayload } from './render.ts'

const EMPTY: DigestPayload = {
  window_start: '2026-08-10T01:00:00.000Z',
  window_end: '2026-08-11T01:00:00.000Z',
  activity_count: 0,
  open_backlog_count: 2,
  truncated_count: 0,
  reason_summary: {},
  reports: [],
}

test('escapes all HTML-significant report characters', () => {
  assert.equal(escapeHtml(`<script a="b">x & 'y'</script>`), '&lt;script a=&quot;b&quot;&gt;x &amp; &#39;y&#39;&lt;/script&gt;')
})

test('renders a zero-report heartbeat', () => {
  const rendered = renderDigest(EMPTY)
  assert.match(rendered.subject, /0 laporan soal/)
  assert.match(rendered.text, /Otomasi berjalan normal/)
  assert.match(rendered.html, /Tidak ada laporan baru/)
})

test('renders revision details and never interpolates raw HTML', () => {
  const payload: DigestPayload = {
    ...EMPTY,
    activity_count: 1,
    reason_summary: { wrong_key: 1 },
    reports: [{
      question_id: '1-verbal-001', package_id: 1, subtest: 'verbal', number: 1,
      question_version: 2, is_current_revision: false, reason: 'wrong_key', status: 'open',
      selected_option: 'A', comment: '<img src=x onerror=alert(1)>',
      created_at: '2026-08-10T02:00:00.000Z', updated_at: '2026-08-10T03:00:00.000Z',
    }],
  }
  const rendered = renderDigest(payload)
  assert.match(rendered.text, /v2, versi lama/)
  assert.doesNotMatch(rendered.html, /<img src=x/)
  assert.match(rendered.html, /&lt;img src=x onerror=alert\(1\)&gt;/)
})
