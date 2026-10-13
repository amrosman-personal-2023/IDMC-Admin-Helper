import React from 'react'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import FileUploadView from '../components/FileUploadView'

const DIRS = ['pm_scripts', 'source_files', 'parameter_files']

beforeEach(() => vi.restoreAllMocks())

function makeFile(name: string, sizeBytes: number) {
  const file = new File([new Uint8Array(sizeBytes)], name, { type: 'text/plain' })
  return file
}

// ── Directory selector ─────────────────────────────────────────────────────

describe('directory selector', () => {
  it('shows only permitted directories', () => {
    render(<FileUploadView directories={['pm_scripts', 'source_files']} />)
    expect(screen.getByRole('option', { name: 'pm_scripts' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'source_files' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'target_files' })).not.toBeInTheDocument()
  })

  it('does not show target_files for standard role dirs', () => {
    render(<FileUploadView directories={DIRS} />)
    expect(screen.queryByRole('option', { name: 'target_files' })).not.toBeInTheDocument()
  })
})

// ── File size validation ───────────────────────────────────────────────────

describe('client-side file size validation', () => {
  it('rejects file over 500 MB before any fetch call', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    render(<FileUploadView directories={DIRS} />)
    const input = document.getElementById('file-input') as HTMLInputElement

    const bigFile = makeFile('huge.csv', 501 * 1024 * 1024)
    fireEvent.change(input, { target: { files: [bigFile] } })

    await waitFor(() =>
      expect(screen.getByTestId('upload-error')).toHaveTextContent('500 MB')
    )
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('accepts file under 500 MB', async () => {
    render(<FileUploadView directories={DIRS} />)
    const input = document.getElementById('file-input') as HTMLInputElement
    const smallFile = makeFile('small.py', 100)
    fireEvent.change(input, { target: { files: [smallFile] } })
    await waitFor(() => expect(screen.getByTestId('selected-filename')).toHaveTextContent('small.py'))
  })
})

// ── Upload flow ────────────────────────────────────────────────────────────

describe('upload flow', () => {
  it('shows progress and then success with filename only (not full path)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ upload_token: 'tok123', expires_at: '2026-01-01T13:00:00' }),
    } as Response)

    // Mock XHR for the PUT step
    const xhrMock = {
      open: vi.fn(),
      send: vi.fn(),
      withCredentials: false,
      upload: { addEventListener: vi.fn() },
      addEventListener: vi.fn((event: string, cb: () => void) => {
        if (event === 'load') {
          // Simulate immediate load with success
          setTimeout(() => {
            Object.defineProperty(xhrMock, 'status', { value: 200, configurable: true })
            Object.defineProperty(xhrMock, 'responseText', {
              value: JSON.stringify({ uploaded: true, path: 'script.py' }),
              configurable: true,
            })
            cb()
          }, 0)
        }
      }),
    }
    vi.spyOn(globalThis, 'XMLHttpRequest').mockImplementation(() => xhrMock as any)

    const user = userEvent.setup()
    render(<FileUploadView directories={DIRS} />)
    const input = document.getElementById('file-input') as HTMLInputElement
    fireEvent.change(input, { target: { files: [makeFile('script.py', 100)] } })

    await waitFor(() => screen.getByTestId('selected-filename'))
    await user.click(screen.getByTestId('upload-button'))

    await waitFor(() => {
      const success = screen.getByTestId('upload-success')
      expect(success).toBeInTheDocument()
      // Must show filename only — not a full path
      expect(success.textContent).toContain('script.py')
      expect(success.textContent).not.toContain('/opt/idmc')
      expect(success.textContent).not.toContain('\\')
    })
  })

  it('shows server detail message when present', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false, status: 400,
      json: () => Promise.resolve({
        detail: "File type '.exe' is not permitted. Allowed extensions: .csv, .py, .sh"
      }),
    } as Response)

    render(<FileUploadView directories={DIRS} />)
    const input = document.getElementById('file-input') as HTMLInputElement
    fireEvent.change(input, { target: { files: [makeFile('virus.exe', 10)] } })
    await waitFor(() => screen.getByTestId('selected-filename'))
    await userEvent.click(screen.getByTestId('upload-button'))

    await waitFor(() => {
      const err = screen.getByTestId('upload-error')
      expect(err).toBeInTheDocument()
      // Server detail is shown so vendor knows what extensions are allowed
      expect(err.textContent).toContain('.exe')
      expect(err.textContent).toContain('Allowed extensions')
      // Internal details never leak
      expect(err.textContent).not.toContain('Traceback')
    })
  })

  it('shows fallback message when server returns no detail', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false, status: 500,
      json: () => Promise.resolve({}),
    } as Response)

    render(<FileUploadView directories={DIRS} />)
    const input = document.getElementById('file-input') as HTMLInputElement
    fireEvent.change(input, { target: { files: [makeFile('file.py', 10)] } })
    await waitFor(() => screen.getByTestId('selected-filename'))
    await userEvent.click(screen.getByTestId('upload-button'))

    await waitFor(() => {
      const err = screen.getByTestId('upload-error')
      expect(err).toBeInTheDocument()
      expect(err.textContent).toContain('Upload failed')
      expect(err.textContent).not.toContain('Traceback')
    })
  })
})

// ── XSS: filename rendering ────────────────────────────────────────────────

describe('XSS protection', () => {
  it('renders filename with script tag as plain text — not executed', async () => {
    render(<FileUploadView directories={DIRS} />)
    const input = document.getElementById('file-input') as HTMLInputElement
    const xssFile = makeFile('<script>alert(1)</script>.py', 10)
    fireEvent.change(input, { target: { files: [xssFile] } })

    await waitFor(() => {
      const el = screen.getByTestId('selected-filename')
      // Text content must contain the literal angle brackets (React-escaped)
      expect(el.textContent).toContain('<script>')
      // But the DOM must NOT contain an actual <script> element
      expect(document.querySelector('script[src]')).toBeNull()
      // innerHTML must be escaped
      expect(el.innerHTML).not.toContain('<script>')
    })
  })
})
