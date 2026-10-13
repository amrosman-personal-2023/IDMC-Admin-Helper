import React, { useState, useRef, useCallback } from 'react'
import { requestUpload, uploadFile } from '../api/backend'
import { ApiError } from '../api/client'

const MAX_FILE_BYTES = 500 * 1024 * 1024  // 500 MB

function resolveUploadError(err: unknown): string {
  if (!(err instanceof ApiError)) return 'Upload failed. Please try again.'
  // Always show the server's detail message when present — it includes
  // actionable information (e.g. which extensions are allowed).
  if (err.serverDetail) return err.serverDetail
  // Fallback readable messages for cases where there is no detail body
  if (err.status === 401) return 'Your session has expired. Please log in again.'
  if (err.status === 403) return 'You do not have permission to upload to this directory.'
  if (err.status === 413) return 'File exceeds the maximum allowed size (500 MB).'
  if (err.status === 503) return 'Service temporarily unavailable. Please try again shortly.'
  return 'Upload failed. Please try again.'
}

interface Props {
  directories: string[]
}

type UploadState =
  | { status: 'idle' }
  | { status: 'uploading'; progress: number }
  | { status: 'success'; filename: string; timestamp: string }
  | { status: 'error'; message: string }

export default function FileUploadView({ directories }: Props) {
  const [directory, setDirectory] = useState(directories[0] ?? '')
  const [file, setFile] = useState<File | null>(null)
  const [uploadState, setUploadState] = useState<UploadState>({ status: 'idle' })
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function selectFile(f: File | null) {
    if (!f) return
    if (f.size > MAX_FILE_BYTES) {
      setUploadState({ status: 'error', message: 'File exceeds the 500 MB limit.' })
      return
    }
    setFile(f)
    setUploadState({ status: 'idle' })
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) selectFile(dropped)
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setUploadState({ status: 'uploading', progress: 0 })

    try {
      const { upload_token } = await requestUpload(directory, file.name)
      const result = await uploadFile(upload_token, file, (pct) =>
        setUploadState({ status: 'uploading', progress: pct })
      )
      setUploadState({
        status: 'success',
        // result.path is filename only — never the full path
        filename: result.path,
        timestamp: new Date().toLocaleString(),
      })
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } catch (err) {
      const msg = resolveUploadError(err)
      setUploadState({ status: 'error', message: msg })
    }
  }

  const uploading = uploadState.status === 'uploading'

  return (
    <section aria-labelledby="upload-heading">
      <h2 id="upload-heading">File Upload</h2>

      <form onSubmit={handleSubmit} aria-label="File upload form">
        <div>
          <label htmlFor="directory-select">Target directory</label>
          <select
            id="directory-select"
            value={directory}
            onChange={(e) => setDirectory(e.target.value)}
            disabled={uploading}
          >
            {directories.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          data-testid="drop-zone"
          aria-label="Drop a file here or click to select"
          style={{ border: `2px dashed ${dragOver ? '#0070c0' : '#ccc'}`, padding: 24 }}
        >
          {file ? (
            /* React renders text nodes as plain text — no XSS possible via file.name */
            <span data-testid="selected-filename">{file.name}</span>
          ) : (
            <span>Drag and drop a file here, or click to select</span>
          )}
          <input
            ref={inputRef}
            type="file"
            style={{ display: 'none' }}
            id="file-input"
            onChange={(e) => selectFile(e.target.files?.[0] ?? null)}
            disabled={uploading}
          />
          <label htmlFor="file-input" style={{ cursor: 'pointer', marginLeft: 8 }}>
            Browse
          </label>
        </div>

        {uploadState.status === 'uploading' && (
          <div role="progressbar"
               aria-valuenow={uploadState.progress}
               aria-valuemin={0}
               aria-valuemax={100}
               data-testid="progress-bar">
            Uploading… {uploadState.progress}%
          </div>
        )}

        {uploadState.status === 'success' && (
          <p role="status" data-testid="upload-success">
            {/* file.name displayed via React text node — auto-escaped */}
            Uploaded: {uploadState.filename} at {uploadState.timestamp}
          </p>
        )}

        {uploadState.status === 'error' && (
          <p role="alert" data-testid="upload-error">{uploadState.message}</p>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          data-testid="upload-button"
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
      </form>
    </section>
  )
}
