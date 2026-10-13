/**
 * Admin API client — completely separate from the vendor api/client.ts.
 * All requests use credentials:'include' so the admin_session HttpOnly
 * cookie is forwarded automatically. Nothing is ever stored in
 * localStorage or sessionStorage.
 */

export class AdminApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'AdminApiError'
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const resp = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
  })
  if (!resp.ok) throw new AdminApiError(resp.status, `Admin request failed: ${resp.status}`)
  // 204 No Content — return empty object
  if (resp.status === 204) return {} as T
  return resp.json() as Promise<T>
}

export const adminApi = {
  post: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  get: <T>(url: string) => request<T>(url),
  getRaw: (url: string, headers?: Record<string, string>) =>
    fetch(url, { credentials: 'include', headers: headers ?? {} }),
}
