/**
 * HTML-escape a string so it is safe to display in the UI.
 * React escapes JSX text nodes automatically, but this is used
 * wherever we need an escaped value outside JSX (e.g. aria labels,
 * test assertions) or want to be explicit about the contract.
 */
export function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

/** Return true if a string contains any HTML special characters. */
export function containsHtml(s: string): boolean {
  return /[&<>"']/.test(s)
}
