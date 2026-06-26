import { useState, useEffect } from 'react'

// API_BASE: 開発時は .env.development の値、本番（FastAPIホスティング）時は同一Origin（空文字）
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export default function ComposeTab({ models, selectedModel, onModelChange }) {
  const [theme, setTheme] = useState('')
  const [key, setKey] = useState('C')
  const [tempo, setTempo] = useState(120)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [presets, setPresets] = useState([])

  useEffect(() => {
    fetch(`${API_BASE}/api/compose/presets`)
      .then(r => r.json())
      .then(d => setPresets(d.presets || []))
      .catch(() => {})
  }, [])

  const handleCompose = async (e, presetTheme = null) => {
    if (e) e.preventDefault()
    const finalTheme = presetTheme || theme
    if (!finalTheme.trim()) return
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const res = await fetch(`${API_BASE}/api/compose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: finalTheme, key, tempo: parseInt(tempo), model: selectedModel })
      })
      if (!res.ok) {
        const detail = await res.json()
        throw new Error(detail.detail || '作曲中にエラーが発生しました。')
      }
      setResult(await res.json())
      if (presetTheme) setTheme(presetTheme)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const KEYS = [
    { value: 'C', label: 'C Major (ハ長調)' }, { value: 'Am', label: 'A minor (イ短調)' },
    { value: 'G', label: 'G Major (ト長調)' }, { value: 'Em', label: 'E minor (ホ短調)' },
    { value: 'F', label: 'F Major (ヘ長調)' }, { value: 'Dm', label: 'D minor (ニ短調)' },
    { value: 'D', label: 'D Major (ニ長調)' }, { value: 'Bm', label: 'B minor (ロ短調)' },
  ]

  return (
    <div className="tab-content">
      {/* プリセット */}
      {presets.length > 0 && (
        <div className="preset-grid">
          <p className="preset-label">🎲 プリセットから選ぶ</p>
          <div className="preset-buttons">
            {presets.map(p => (
              <button
                key={p.id}
                className="btn-preset"
                disabled={loading}
                onClick={() => handleCompose(null, p.theme)}
              >
                {p.theme}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="two-col">
        {/* 入力フォーム */}
        <div className="glass-panel p-6">
          <form onSubmit={handleCompose} className="form-stack">
            <div className="field">
              <label>使用するLLMモデル</label>
              <select value={selectedModel} onChange={e => onModelChange(e.target.value)} disabled={loading}>
                {models.map(m => <option key={m} value={m}>{m}</option>)}
                {models.length === 0 && <option value="qwen3.5:9b">qwen3.5:9b（接続待機中...）</option>}
              </select>
            </div>
            <div className="field">
              <label>曲のテーマ・イメージ</label>
              <input
                type="text"
                value={theme}
                onChange={e => setTheme(e.target.value)}
                placeholder="例: 爽やかな朝の森、哀愁漂う雨上がりの街角"
                required
                disabled={loading}
              />
            </div>
            <div className="two-col-sm">
              <div className="field">
                <label>調 (Key)</label>
                <select value={key} onChange={e => setKey(e.target.value)} disabled={loading}>
                  {KEYS.map(k => <option key={k.value} value={k.value}>{k.label}</option>)}
                </select>
              </div>
              <div className="field">
                <label>テンポ (BPM): {tempo}</label>
                <input
                  type="range" min="60" max="200" value={tempo}
                  onChange={e => setTempo(e.target.value)}
                  disabled={loading}
                  className="range-input"
                />
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? <><span className="loader-ring" /> <span>作曲中...</span></> : '🌌 楽譜と音源を自動生成する'}
            </button>
          </form>
        </div>

        {/* 結果表示 */}
        <ResultPanel loading={loading} error={error} result={result} loadingText="AIが音楽理論を考えて作曲しています..." />
      </div>
    </div>
  )
}

// 共通の結果パネル（他のタブでも再利用）
export function ResultPanel({ loading, error, result, loadingText = '処理中...' }) {
  return (
    <div className="result-panel">
      {error && (
        <div className="error-box">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}
      {loading && (
        <div className="glass-panel p-12 flex-center-col gap-4 min-h-72">
          <div className="pulse-bars">
            <div className="pulse-bar" /><div className="pulse-bar" />
            <div className="pulse-bar" /><div className="pulse-bar" />
          </div>
          <div className="loading-text animate-pulse">{loadingText}</div>
        </div>
      )}
      {!loading && !result && !error && (
        <div className="glass-panel p-12 flex-center-col gap-4 min-h-72 border-dashed">
          <span className="text-5xl opacity-40">🎼</span>
          <p className="text-gray-400 font-semibold">生成結果がここに表示されます</p>
          <p className="text-xs text-gray-500">左のフォームからリクエストを入力してください</p>
        </div>
      )}
      {!loading && result && (
        <div className="glass-panel p-6 result-content animate-fadeIn">
          <div className="result-header">
            <div>
              <span className="badge-success">SUCCESS</span>
              <h2 className="result-title">{result.title}</h2>
            </div>
            <a href={`${API_BASE}${result.abc_url}`} download className="btn-ghost">楽譜をDL</a>
          </div>
          <div className="audio-player">
            <div className="audio-header">
              <span className="text-xs text-gray-400">合成されたWAV音源</span>
              <span className="badge-live"><span className="dot-ping" />Ready to play</span>
            </div>
            <audio src={`${API_BASE}${result.wav_url}`} controls className="w-full" />
          </div>
          <div className="field">
            <label className="text-xs text-gray-400">ABC記法楽譜データ</label>
            <pre className="abc-code">{result.abc_content}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
