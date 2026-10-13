/**
 * Central fetch wrapper.
 * - Always sends credentials: 'include' for HttpOnly cookie forwarding.
 * - Never touches localStorage or sessionStorage.
 * - Returns parsed JSON or throws an ApiError.
 */

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly serverDetail?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const resp = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  if (!resp.ok) {
    // Attempt to extract the server's `detail` field for display
    let serverDetail: string | undefined
    try {
      const body = await resp.json()
      if (typeof body?.detail === 'string') serverDetail = body.detail
    } catch { /* ignore parse errors */ }
    throw new ApiError(resp.status, `Request failed: ${resp.status}`, serverDetail)
  }
  return resp.json() as Promise<T>
}

export const api = {
  post: <T>(url: string, body: unknown) =>
    request<T>(url, { method: 'POST', body: JSON.stringify(body) }),

  get: <T>(url: string) => request<T>(url),
}
