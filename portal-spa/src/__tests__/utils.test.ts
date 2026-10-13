import { describe, it, expect } from 'vitest'
import { escapeHtml, containsHtml } from '../utils/escape'
import { isSafeRedirect, safeRedirectTarget } from '../utils/redirect'

describe('escapeHtml', () => {
  it('escapes & < > " \'', () => {
    expect(escapeHtml('a&b')).toBe('a&amp;b')
    expect(escapeHtml('<script>')).toBe('&lt;script&gt;')
    expect(escapeHtml('"quoted"')).toBe('&quot;quoted&quot;')
    expect(escapeHtml("it's")).toBe("it&#x27;s")
  })

  it('leaves safe strings unchanged', () => {
    expect(escapeHtml('hello world')).toBe('hello world')
    expect(escapeHtml('file.py')).toBe('file.py')
  })
})

describe('containsHtml', () => {
  it('detects HTML characters', () => {
    expect(containsHtml('<script>')).toBe(true)
    expect(containsHtml('safe')).toBe(false)
  })
})

describe('isSafeRedirect', () => {
  it('allows internal paths', () => {
    expect(isSafeRedirect('/')).toBe(false)  // / is the landing page, not a valid post-login target
    expect(isSafeRedirect('/portal')).toBe(true)
    expect(isSafeRedirect('/upload')).toBe(true)
    expect(isSafeRedirect('/portal/files')).toBe(true)
  })

  it('rejects external URLs', () => {
    expect(isSafeRedirect('https://evil.com')).toBe(false)
    expect(isSafeRedirect('http://evil.com')).toBe(false)
    expect(isSafeRedirect('//evil.com')).toBe(false)
    expect(isSafeRedirect('javascript:alert(1)')).toBe(false)
  })

  it('rejects empty string and null-ish values', () => {
    expect(isSafeRedirect('')).toBe(false)
  })

  it('rejects paths not in allowlist', () => {
    expect(isSafeRedirect('/admin')).toBe(false)
    expect(isSafeRedirect('/etc/passwd')).toBe(false)
  })
})

describe('safeRedirectTarget', () => {
  it('returns safe path as-is', () => {
    expect(safeRedirectTarget('/portal')).toBe('/portal')
  })

  it('returns "/" for unsafe input', () => {
    expect(safeRedirectTarget('https://evil.com')).toBe('/portal')
    expect(safeRedirectTarget(null)).toBe('/portal')
    expect(safeRedirectTarget('')).toBe('/portal')
  })
})
