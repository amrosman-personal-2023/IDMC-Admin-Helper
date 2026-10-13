import React, { useEffect, useState } from 'react'
import { getLlmSettings, updateLlmSettings, testLlmConnection, LlmSettings } from '../api/endpoints'
import '../../styles/design.css'

const PROVIDERS = [
  { value: 'anthropic',    label: 'Anthropic Claude',  placeholder: 'claude-opus-4-8' },
  { value: 'openai',       label: 'OpenAI',             placeholder: 'gpt-4o' },
  { value: 'azure_openai', label: 'Azure OpenAI',       placeholder: 'gpt-4o' },
  { value: 'gemini',       label: 'Google Gemini',      placeholder: 'gemini-2.0-flash' },
]

export default function LlmSettingsPage() {
  const [settings, setSettings] = useState<LlmSettings | null>(null)
  const [provider, setProvider] = useState('anthropic')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [maxTokens, setMaxTokens] = useState(80000)
  const [azureEndpoint, setAzureEndpoint] = useState('')
  const [azureDeployment, setAzureDeployment] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [saveErr, setSaveErr] = useState('')
  const [testResult, setTestResult] = useState<{ success: boolean; latency_ms: number; error?: string } | null>(null)

  useEffect(() => {
    getLlmSettings().then(s => {
      setSettings(s)
      setProvider(s.provider)
      setModel(s.model)
      setMaxTokens(s.max_context_tokens)
      setAzureEndpoint(s.azure_endpoint)
      setAzureDeployment(s.azure_deployment)
      // Leave apiKey blank — user must re-enter to change
    }).catch(() => setSaveErr('Failed to load settings'))
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true); setSaveMsg(''); setSaveErr(''); setTestResult(null)
    try {
      const updated = await updateLlmSettings({
        provider, model, api_key: apiKey || '__keep__',
        max_context_tokens: maxTokens,
        azure_endpoint: azureEndpoint,
        azure_deployment: azureDeployment,
      })
      setSettings(updated)
      setApiKey('')
      setSaveMsg('Settings saved successfully')
    } catch (err: any) {
      setSaveErr(err?.message ?? 'Failed to save settings')
    } finally { setSaving(false) }
  }

  async function handleTest() {
    setTesting(true); setTestResult(null); setSaveMsg(''); setSaveErr('')
    try {
      const result = await testLlmConnection()
      setTestResult(result)
    } catch { setTestResult({ success: false, latency_ms: 0, error: 'Request failed' }) }
    finally { setTesting(false) }
  }

  const currentProvider = PROVIDERS.find(p => p.value === provider) ?? PROVIDERS[0]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 640 }}>
      <div>
        <h2>LLM Settings</h2>
        <p style={{ color: '#8b8fa8', fontSize: 13, marginTop: 4 }}>
          Configure the AI provider used by the Log Analyser. Changes take effect immediately.
        </p>
      </div>

      {saveMsg && <p className="alert alert-success" role="status">{saveMsg}</p>}
      {saveErr && <p className="alert alert-error" role="alert">{saveErr}</p>}

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Provider */}
        <div style={s.card}>
          <h3 style={{ marginBottom: 16 }}>Provider</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10 }}>
            {PROVIDERS.map(p => (
              <button key={p.value} type="button"
                onClick={() => setProvider(p.value)}
                style={{
                  padding: '12px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'center',
                  border: `1px solid ${provider === p.value ? '#4f7eff' : '#2e3150'}`,
                  background: provider === p.value ? 'rgba(79,126,255,.1)' : '#222539',
                  color: provider === p.value ? '#4f7eff' : '#8b8fa8', fontSize: 13, fontWeight: 500,
                }}>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Model + key + tokens */}
        <div style={s.card}>
          <h3 style={{ marginBottom: 16 }}>Model & Authentication</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            <div className="field">
              <label>Model</label>
              <input className="input" value={model} onChange={e => setModel(e.target.value)}
                placeholder={currentProvider.placeholder} data-testid="model-input" />
            </div>

            <div className="field">
              <label>API Key</label>
              <input className="input" type="password" value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder={settings?.api_key_masked ?? 'Enter API key'}
                data-testid="api-key-input" />
              <span style={{ fontSize: 11, color: '#5a5e78' }}>
                Leave blank to keep the existing key ({settings?.api_key_masked ?? '—'}).
              </span>
            </div>

            <div className="field">
              <label>Max context tokens</label>
              <input className="input" type="number" min={1000} max={200000}
                value={maxTokens} onChange={e => setMaxTokens(Number(e.target.value))}
                data-testid="max-tokens-input" />
              <span style={{ fontSize: 11, color: '#5a5e78' }}>
                Log files larger than this will be trimmed (most recent lines kept). Range: 1,000 – 200,000.
              </span>
            </div>

            {provider === 'azure_openai' && (
              <>
                <div className="field">
                  <label>Azure endpoint</label>
                  <input className="input" value={azureEndpoint} onChange={e => setAzureEndpoint(e.target.value)}
                    placeholder="https://your-resource.openai.azure.com/" />
                </div>
                <div className="field">
                  <label>Azure deployment name</label>
                  <input className="input" value={azureDeployment} onChange={e => setAzureDeployment(e.target.value)}
                    placeholder="gpt-4o-deployment" />
                </div>
              </>
            )}
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button className="btn btn-primary" type="submit" disabled={saving} data-testid="save-llm-btn">
            {saving ? 'Saving…' : 'Save changes'}
          </button>
          <button className="btn btn-ghost" type="button" onClick={handleTest} disabled={testing}
            data-testid="test-llm-btn">
            {testing ? 'Testing…' : 'Test connection'}
          </button>

          {testResult && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 13,
              color: testResult.success ? '#3ecf8e' : '#e05252',
            }} data-testid="test-result">
              {testResult.success
                ? `✓ Connected (${testResult.latency_ms}ms)`
                : `✗ ${testResult.error}`}
            </div>
          )}
        </div>
      </form>

      {/* Info */}
      <div style={{ background: 'rgba(79,126,255,.06)', border: '1px solid rgba(79,126,255,.2)', borderRadius: 10, padding: '14px 18px', fontSize: 13, color: '#8b8fa8', lineHeight: 1.7 }}>
        <strong style={{ color: '#4f7eff' }}>Note:</strong> The API key is stored encrypted on disk
        at <code style={{ background: '#222539', padding: '1px 6px', borderRadius: 4, color: '#e8eaf6' }}>LLM_SETTINGS_PATH</code>.
        It is never returned in plaintext after saving. Log file content is sent to the external LLM
        provider when you use the Log Analyser — ensure your organisation's data policy permits this.
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: { background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 12, padding: 24 },
}
