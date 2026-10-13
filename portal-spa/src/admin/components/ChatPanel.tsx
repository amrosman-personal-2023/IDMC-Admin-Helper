import React, { useEffect, useRef, useState } from 'react'
import { LogContext } from '../api/endpoints'
import '../../styles/design.css'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

interface Props {
  context: LogContext | null
  messages: ChatMessage[]
  onSend: (text: string) => void
  onClear: () => void
  streaming: boolean
}

function MarkdownText({ text }: { text: string }) {
  // Very simple rendering: bold **text**, code `text`, line breaks
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('`') && part.endsWith('`'))
          return <code key={i} style={{ background: '#222539', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace', fontSize: 11 }}>{part.slice(1, -1)}</code>
        if (part.startsWith('**') && part.endsWith('**'))
          return <strong key={i}>{part.slice(2, -2)}</strong>
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

export default function ChatPanel({ context, messages, onSend, onClear, streaming }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    onSend(text)
  }

  return (
    <div style={s.root}>
      {/* Context strip */}
      <div style={s.contextStrip}>
        {context ? (
          <>
            <span className="badge badge-green" style={{ fontSize: 10 }}>{context.service}</span>
            <span style={{ fontSize: 11, color: '#5a5e78', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
              …/{context.file_path.split('/').pop()}
            </span>
            <span style={{ fontSize: 11, color: '#5a5e78' }}>{context.lines.toLocaleString()} lines</span>
          </>
        ) : (
          <span style={{ fontSize: 12, color: '#5a5e78' }}>No file loaded</span>
        )}
        {messages.length > 0 && (
          <button style={s.clearBtn} onClick={onClear} title="Clear conversation">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/>
            </svg>
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={s.messages}>
        {messages.length === 0 && !context && (
          <div style={s.empty}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2e3150" strokeWidth="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <p style={{ color: '#5a5e78', fontSize: 13, marginTop: 10, textAlign: 'center' }}>
              Load a log file to start the AI analysis
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 4,
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 12 }}>
            <span style={{ fontSize: 10, color: '#5a5e78', textTransform: 'uppercase', letterSpacing: '.4px' }}>
              {msg.role === 'user' ? 'You' : '✦ AI Analysis'}
            </span>
            <div style={{
              ...s.bubble,
              background: msg.role === 'user' ? 'rgba(79,126,255,.15)' : '#1a1d2e',
              border: `1px solid ${msg.role === 'user' ? 'rgba(79,126,255,.3)' : '#2e3150'}`,
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: msg.role === 'user' ? '85%' : '100%',
            }}>
              {msg.content.split('\n').map((line, j) => (
                <React.Fragment key={j}>
                  <MarkdownText text={line} />
                  {j < msg.content.split('\n').length - 1 && <br />}
                </React.Fragment>
              ))}
              {msg.streaming && <span style={{ opacity: .6 }}>▌</span>}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} style={s.inputRow}>
        <input
          className="input"
          placeholder={context ? 'Ask a question about this log…' : 'Load a file first'}
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={!context || streaming}
          style={{ flex: 1, fontSize: 13 }}
          data-testid="chat-input"
        />
        <button className="btn btn-primary btn-sm" type="submit"
          disabled={!context || streaming || !input.trim()}
          data-testid="chat-send-btn">
          {streaming ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' },
  contextStrip: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid #2e3150', background: '#1a1d2e', flexShrink: 0 },
  clearBtn: { background: 'none', border: 'none', cursor: 'pointer', color: '#5a5e78', padding: 4, borderRadius: 4, display: 'flex', alignItems: 'center' },
  messages: { flex: 1, overflowY: 'auto', padding: '12px 14px' },
  empty: { height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' },
  bubble: { padding: '10px 14px', borderRadius: 10, fontSize: 13, lineHeight: 1.65, color: '#c8ccd8', wordBreak: 'break-word' },
  inputRow: { display: 'flex', gap: 8, padding: '10px 12px', borderTop: '1px solid #2e3150', background: '#1a1d2e', flexShrink: 0 },
}
