/**
 * Validate a post-login redirect target against an allowlist of
 * internal paths.  Rejects anything with a scheme, host, or
 * path that starts outside the known-safe prefixes.
 */

const ALLOWED_PREFIXES = ['/portal', '/upload', '/operations']

export function isSafeRedirect(target: string): boolean {
  if (!target) return false
  // Reject anything that looks like a URL with a scheme or protocol-relative
  if (/^[a-zA-Z][a-zA-Z0-9+\-.]*:/.test(target)) return false
  if (target.startsWith('//')) return false
  // Must start with /
  if (!target.startsWith('/')) return false
  // Must match one of the allowed prefixes
  return ALLOWED_PREFIXES.some(
    (p) => target === p || target.startsWith(p + '/') || target.startsWith(p + '?')
  )
}

export function safeRedirectTarget(target: string | null): string {
  if (target && isSafeRedirect(target)) return target
  return '/portal'
}
