import React, { useState, useEffect, useRef } from 'react'
import { runOperation, OperationDef } from '../api/backend'
import { ApiError } from '../api/client'

interface Props {
  operations: OperationDef[]
}

interface RunState {
  status: 'idle' | 'running' | 'done' | 'timeout' | 'error'
  elapsed?: number
  exitCode?: number
  output?: string
  duration?: number
  error?: string
}

export default function ScriptOperationsView({ operations }: Props) {
  const [states, setStates] = useState<Record<string, RunState>>(() =>
    Object.fromEntries(operations.map((op) => [op.name, { status: 'idle' }]))
  )

  function setState(name: string, s: RunState) {
    setStates((prev) => ({ ...prev, [name]: s }))
  }

  async function handleRun(op: OperationDef) {
    setState(op.name, { status: 'running', elapsed: 0 })

    // Start elapsed-time ticker
    const start = Date.now()
    const ticker = setInterval(() => {
      setState(op.name, { status: 'running', elapsed: Math.floor((Date.now() - start) / 1000) })
    }, 1000)

    try {
      const result = await runOperation(op.name)
      clearInterval(ticker)
      setState(op.name, {
        status: 'done',
        exitCode: result.exit_code,
        output: result.output.slice(0, 2000),
        duration: result.duration_ms,
      })
    } catch (err) {
      clearInterval(ticker)
      if (err instanceof ApiError && err.status === 504) {
        setState(op.name, { status: 'timeout' })
      } else {
        setState(op.name, { status: 'error', error: 'Operation failed. Please try again.' })
      }
    }
  }

  return (
    <section aria-labelledby="ops-heading">
      <h2 id="ops-heading">Script Operations</h2>
      {operations.length === 0 && <p>No operations available for your role.</p>}
      {operations.map((op) => {
        const s = states[op.name] ?? { status: 'idle' }
        const running = s.status === 'running'
        return (
          <div key={op.name} data-testid={`op-${op.name}`}>
            <h3>{op.name}</h3>
            <p>{op.description}</p>
            <button
              onClick={() => handleRun(op)}
              disabled={running}
              data-testid={`run-btn-${op.name}`}
              aria-busy={running}
            >
              {running ? 'Running…' : 'Run'}
            </button>

            {running && (
              <span role="status" data-testid={`elapsed-${op.name}`}>
                Elapsed: {s.elapsed ?? 0}s
              </span>
            )}

            {s.status === 'done' && (
              <div data-testid={`result-${op.name}`}>
                <p>Exit code: {s.exitCode}</p>
                <p>Duration: {s.duration}ms</p>
                {/* output is plain text from the server — rendered as text node, not HTML */}
                <pre data-testid={`output-${op.name}`}>{s.output}</pre>
              </div>
            )}

            {s.status === 'timeout' && (
              <p role="alert" data-testid={`timeout-${op.name}`}>
                Operation timed out after 120 seconds.
              </p>
            )}

            {s.status === 'error' && (
              <p role="alert" data-testid={`error-${op.name}`}>{s.error}</p>
            )}
          </div>
        )
      })}
    </section>
  )
}
