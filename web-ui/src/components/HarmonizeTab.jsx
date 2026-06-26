import { useState } from 'react'
import { ResultPanel } from './ComposeTab'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export default function HarmonizeTab({ models, selectedModel, onModelChange }) {
  const [melodyAbc, setMelodyAbc] = useState('')
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const handleHarmonize = async (e) => {
    e.preventDefault()
    if (!melodyAbc.trim()) return
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const res = await fetch(`${API_BASE}/api/harmonize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          melody_abc: melodyAbc,
          title: title || 'harmony_result',
          model: selectedModel
        })
      })
      if (!res.ok) {
        const detail = await res.json()
        throw new Error(detail.detail || 'ハーモニー生成中にエラーが発生しました。')
      }
      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const EXAMPLE_ABC = `X:1
T:Twinkle Twinkle Little Star
M:4/4
L:1/4
Q:120
K:C
C C G G | A A G2 | F F E E | D D C2 |`

  return (
    <div className="tab-content">
      <div className="two-col">
        <div className="glass-panel p-6">
          <form onSubmit={handleHarmonize} className="form-stack">
            <div className="field">
              <label>使用するLLMモデル</label>
              <select value={selectedModel} onChange={e => onModelChange(e.target.value)} disabled={loading}>
                {models.map(m => <option key={m} value={m}>{m}</option>)}
                {models.length === 0 && <option value="qwen3.5:9b">qwen3.5:9b（接続待機中...）</option>}
              </select>
            </div>
            <div className="field">
              <label>元のメロディ（ABC記法）</label>
              <textarea
                rows={10}
                value={melodyAbc}
                onChange={e => setMelodyAbc(e.target.value)}
                placeholder={EXAMPLE_ABC}
                required
                disabled={loading}
                className="font-mono text-xs text-green-400"
              />
              <button
                type="button"
                className="btn-ghost text-xs mt-1"
                onClick={() => setMelodyAbc(EXAMPLE_ABC)}
              >
                サンプルを入力
              </button>
            </div>
            <div className="field">
              <label>曲のタイトル / 識別名</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="例: twinkle_harmony"
                disabled={loading}
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading
                ? <><span className="loader-ring" /><span>伴奏合成中...</span></>
                : '🎹 ハーモニーを重ねる（2声伴奏）'
              }
            </button>
          </form>
        </div>
        <ResultPanel
          loading={loading}
          error={error}
          result={result}
          loadingText="AIが音楽理論を分析してハーモニーを作成しています..."
        />
      </div>
    </div>
  )
}
