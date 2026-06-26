import { useState, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export default function MidiConvertTab({ models, selectedModel, onModelChange }) {
  const [abcText, setAbcText] = useState('')
  const [status, setStatus] = useState('待機中...')
  const [statusType, setStatusType] = useState('idle') // 'idle' | 'success' | 'error' | 'loading'
  const [midiUrl, setMidiUrl] = useState(null)
  const [aiStatus, setAiStatus] = useState('')
  const fileInputRef = useRef(null)

  // ステータス更新ヘルパー
  const setMsg = (msg, type = 'idle') => { setStatus(msg); setStatusType(type) }

  // ------------------------------------------------------------------
  // 1. MIDI → ABC
  // ------------------------------------------------------------------
  const handleMidiToAbc = async () => {
    const file = fileInputRef.current?.files?.[0]
    if (!file) { setMsg('エラー: MIDIファイルを選択してください。', 'error'); return }
    setMsg('MIDIをABCに変換中...', 'loading')
    setMidiUrl(null)

    try {
      const formData = new FormData()
      formData.append('midiFile', file)
      const res = await fetch(`${API_BASE}/api/midi-to-abc`, { method: 'POST', body: formData })
      const data = await res.json()
      if (data.abc_text) {
        setAbcText(data.abc_text)
        setMsg('✅ MIDI→ABC変換成功！テキストエリアを確認してください。', 'success')
      } else {
        throw new Error(data.detail || data.message || '変換に失敗しました')
      }
    } catch (err) {
      setMsg(`❌ エラー: ${err.message}`, 'error')
    }
  }

  // ------------------------------------------------------------------
  // 2. ABC → MIDI
  // ------------------------------------------------------------------
  const handleAbcToMidi = async () => {
    if (!abcText.trim()) { setMsg('エラー: ABCテキストを入力してください。', 'error'); return }
    setMsg('ABC→MIDIに変換中...', 'loading')
    setMidiUrl(null)

    try {
      const res = await fetch(`${API_BASE}/api/abc-to-midi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ abc_text: abcText })
      })
      const data = await res.json()
      if (data.status === 'success') {
        // FastAPI の /output/ 経由でMIDIを配信（localhost固定を避ける）
        setMidiUrl(`${API_BASE}/output/generated_output.mid`)
        setMsg('✅ ABC→MIDI変換成功！MIDIをダウンロードしてください。', 'success')
      } else {
        throw new Error(data.detail || data.message || '変換に失敗しました')
      }
    } catch (err) {
      setMsg(`❌ エラー: ${err.message}`, 'error')
    }
  }

  // ------------------------------------------------------------------
  // 3. AI編集 (Ollama)
  // ------------------------------------------------------------------
  const handleAiEdit = async (editType) => {
    if (!abcText.trim()) { setAiStatus('エラー: まずABCテキストを入力またはMIDI変換してください。'); return }
    setAiStatus(`AI処理中 (${editType})...`)

    try {
      const res = await fetch(`${API_BASE}/api/ai-edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ abc_text: abcText, edit_type: editType, model: selectedModel })
      })
      const data = await res.json()
      if (data.status === 'success') {
        setAbcText(data.abc_text)
        setAiStatus('✅ AI編集完了！')
        setMsg('AI編集完了', 'success')
      } else {
        throw new Error(data.detail || data.message || 'AI編集に失敗しました')
      }
    } catch (err) {
      setAiStatus(`❌ エラー: ${err.message}`)
    }
  }

  // テキストダウンロード
  const handleDownloadTxt = () => {
    const blob = new Blob([abcText], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'score.abc'
    a.click()
  }

  const statusColors = { idle: 'text-gray-400', success: 'text-cyan-400', error: 'text-red-400', loading: 'text-yellow-400' }

  return (
    <div className="tab-content">
      {/* ステータス */}
      <div className={`text-center text-sm font-bold mb-4 ${statusColors[statusType]}`}>{status}</div>

      <div className="midi-grid">
        {/* 左列: MIDI操作 */}
        <div className="flex flex-col gap-4">
          {/* MIDI → ABC */}
          <div className="glass-panel p-5">
            <h3 className="section-title">① MIDI → テキスト変換</h3>
            <input
              ref={fileInputRef}
              type="file"
              accept=".mid,.midi"
              className="file-input"
            />
            <div className="btn-row mt-3">
              <button className="btn-cyan" onClick={handleMidiToAbc}>MIDIをABCに変換</button>
              {abcText && <button className="btn-green" onClick={handleDownloadTxt}>.abcとして保存</button>}
            </div>
          </div>

          {/* ABC → MIDI */}
          <div className="glass-panel p-5">
            <h3 className="section-title">② テキスト → MIDI逆変換</h3>
            <p className="text-xs text-gray-500 mb-3">下のABCテキストエリアの内容をabc2midiエンジンでMIDIに変換します。</p>
            <div className="btn-row">
              <button className="btn-green" onClick={handleAbcToMidi}>テキストをMIDIに変換</button>
              {midiUrl && (
                <a href={midiUrl} download="generated.mid">
                  <button className="btn-green">MIDIをダウンロード</button>
                </a>
              )}
            </div>
          </div>

          {/* AI編集 */}
          <div className="glass-panel p-5">
            <h3 className="section-title">③ AI編集 <span className="badge-ollama">Ollama</span></h3>
            <div className="field mb-2">
              <label>使用モデル</label>
              <select value={selectedModel} onChange={e => onModelChange(e.target.value)} className="text-sm">
                {models.map(m => <option key={m} value={m}>{m}</option>)}
                {models.length === 0 && <option value="qwen3.5:9b">qwen3.5:9b</option>}
              </select>
            </div>
            <div className="ai-btn-row">
              <button className="btn-harmony" onClick={() => handleAiEdit('harmony')}>🎵 ハモリを追加</button>
              <button className="btn-chord" onClick={() => handleAiEdit('chord')}>🎸 コード進行を追加</button>
            </div>
            {aiStatus && <p className="text-xs text-purple-300 mt-2 text-center">{aiStatus}</p>}
          </div>
        </div>

        {/* 右列: ABCテキストエリア */}
        <div className="glass-panel p-5 flex flex-col">
          <div className="flex justify-between items-center mb-2">
            <h3 className="section-title mb-0">ABCテキストエディタ</h3>
            <button className="btn-ghost text-xs" onClick={() => setAbcText('')}>クリア</button>
          </div>
          <textarea
            value={abcText}
            onChange={e => setAbcText(e.target.value)}
            placeholder={`X:1\nT:Test\nM:4/4\nL:1/4\nK:C\nC D E F | [CEG] z G2 |`}
            className="abc-textarea flex-1"
            style={{ minHeight: '380px' }}
          />
        </div>
      </div>
    </div>
  )
}
