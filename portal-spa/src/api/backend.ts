import { api, ApiError } from './client'

export interface AllowedConfig {
  directories: string[]
  operations: OperationDef[]
}

export interface OperationDef {
  name: string
  description: string
}

export interface UploadRequestResponse {
  upload_token: string
  expires_at: string
}

export interface UploadResponse {
  uploaded: boolean
  path: string
}

export interface RunResponse {
  operation: string
  exit_code: number
  output: string
  duration_ms: number
}

export function getAllowedConfig() {
  return api.get<AllowedConfig>('/portal/config')
}

export function requestUpload(directory: string, filename: string) {
  return api.post<UploadRequestResponse>('/upload/request', { directory, filename })
}

export async function uploadFile(
  token: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', `/upload/${token}`)
    xhr.withCredentials = true

    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
      })
    }

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as UploadResponse)
      } else {
        // Extract the server's detail message from the response body if available
        let serverDetail: string | undefined
        try {
          const body = JSON.parse(xhr.responseText)
          if (typeof body?.detail === 'string') serverDetail = body.detail
        } catch { /* ignore */ }
        reject(new ApiError(xhr.status, 'Upload failed', serverDetail))
      }
    })
    xhr.addEventListener('error', () => reject(new ApiError(0, 'Network error')))
    xhr.send(file)
  })
}

export function runOperation(operation_name: string) {
  return api.post<RunResponse>('/operations/run', { operation_name })
}
