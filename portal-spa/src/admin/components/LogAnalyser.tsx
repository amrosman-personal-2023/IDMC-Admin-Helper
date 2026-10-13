import React, { useState, useCallback } from 'react'
import { getLogFile, LogFile, LogContext } from '../api/endpoints'
import FileTree from './FileTree'
import LogViewer from './LogViewer'
import ChatPanel, { ChatMessage } from './ChatPanel'
import '../../styles/design.css'

export default function LogAnalyser() {
  const [file, setFile] = useState<LogFile | null>(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [selectedPath, setSelectedPath] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [sensitivityConfirmed, setSensitivityConfirmed] = useState(false)

  const context: LogContext | null = file
    ? { file_path: file.path, content: file.content, service: file.service,
        directory: file.directory, lines: file.lines, size_bytes: file.size_bytes }
    : null

  const handleFileSelect = useCallback(async (path: string) => {
    setSelectedPath(path)
    setFileLoading(true)
    setMessages([])
    setSensitivityConfirmed(false)
    try {
      const data = await getLogFile(path)
      setFile(data)
      // Auto-analyse if not sensitive (or sensitivity already confirmed)
      if (!data.sensitive) {
        triggerAnalysis(data)
      }
    } catch (err: any) {
      setFile(null)
    } finally {
      setFileLoading(false)
    }
  }, [])

  function triggerAnalysis(fileData?: LogFile) {
    const f = fileData ?? file
    if (!f) return
    streamLlm('/admin/logs/analyse', {
      file_path: f.path, content: f.content, service: f.service,
      directory: f.directory, lines: f.lines, size_bytes: f.size_bytes,
    })
  }

  function handleSendChat(text: string) {
    if (!context) return
    const newMessages: ChatMessage[] = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    streamLlm('/admin/logs/chat', {
      messages: newMessages.map(m => ({ role: m.role, content: m.content })),
      context,
    })
  }

  async function streamLlm(url: string, body: object) {
    setStreaming(true)
    const assistantIdx = messages.length + (url.includes('chat') ? 1 : 0)
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    try {
      const resp = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop() ?? ''
        for (const part of parts) {
          if (!part.startsWith('data:')) continue
          try {
            const json = JSON.parse(part.slice(5).trim())
            if (json.done) break
            if (json.delta) {
              setMessages(prev => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'assistant') {
                  next[next.length - 1] = { ...last, content: last.content + json.delta }
                }
                return next
              })
            }
          } catch { /* partial JSON */ }
        }
      }
    } catch (err: any) {
      setMessages(prev => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last?.role === 'assistant') {
          next[next.length - 1] = { ...last, content: `Error: ${err.message}`, streaming: false }
        }
        return next
      })
    } finally {
      setMessages(prev => prev.map((m, i) =>
        i === prev.length - 1 ? { ...m, streaming: false } : m
      ))
      setStreaming(false)
    }
  }

  return (
    <div style={s.root}>
      {/* File browser */}
      <div style={s.panel1}>
        <FileTree onFileSelect={handleFileSelect} selectedPath={selectedPath} />
      </div>

      {/* Divider */}
      <div style={s.divider} />

      {/* Log viewer */}
      <div style={s.panel2}>
        <LogViewer
          file={file}
          loading={fileLoading}
          onAnalyse={() => triggerAnalysis()}
          analysing={streaming}
          sensitivityConfirmed={sensitivityConfirmed}
          onConfirmSensitivity={() => { setSensitivityConfirmed(true); triggerAnalysis() }}
        />
      </div>

      {/* Divider */}
      <div style={s.divider} />

      {/* Chat */}
      <div style={s.panel3}>
        <ChatPanel
          context={context}
          messages={messages}
          onSend={handleSendChat}
          onClear={() => setMessages([])}
          streaming={streaming}
        />
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', height: '100%', overflow: 'hidden', gap: 0 },
  panel1: { width: 220, flexShrink: 0, background: '#1a1d2e', borderRight: '1px solid #2e3150', overflow: 'hidden' },
  panel2: { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  panel3: { width: 360, flexShrink: 0, background: '#0f1117', borderLeft: '1px solid #2e3150', overflow: 'hidden' },
  divider: { width: 1, background: '#2e3150', flexShrink: 0 },
}
