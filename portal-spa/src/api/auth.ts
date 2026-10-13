import { api } from './client'

export interface LoginResponse {
  access_token?: string
  expires_at?: string
  totp_required?: boolean   // server returns this on 200 when password ok but no TOTP yet
}

export interface ValidateResponse {
  valid: boolean
  vendor_id: number
  role: string
  expires_at: string
}

export interface RenewResponse {
  expires_at: string
}

export function login(username: string, password: string, totp_code: string, device_uuid = '') {
  return api.post<LoginResponse>('/auth/login', { username, password, totp_code })
}

export function validate() {
  return api.post<ValidateResponse>('/auth/validate', {})
}

export function renew(totp_code: string) {
  return api.post<RenewResponse>('/auth/renew', { totp_code })
}

export function logout() {
  return api.post<void>('/auth/logout', {})
}
