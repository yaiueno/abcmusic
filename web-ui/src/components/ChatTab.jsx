import { useState, useRef, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export default function ChatTab({ models, selectedModel, onModelChange }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState(
    'あなたはABC記法で音楽を作曲できる音楽家AIアシスタントです。' +
    'ユーザーが曲を頼んだ際は、必ず ```abc ``` ブロックに囲んだABC記法の楽譜を出力してください。'
  )
  const [showSystem, setShowSystem] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    // AIメッセージのプレースホルダー
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
          model: selectedModel,
          system_prompt: systemPrompt || null,
        })
      })

      if (!res.body) throw new Error('ストリーミング非対応のレスポンス')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '))
        for (const line of lines) {
          const dataStr = line.slice(6)
          if (dataStr === '[DONE]') break
          try {
            const data = JSON.parse(dataStr)
            if (data.token) {
              accumulated += data.token
              setMessages(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = { role: 'assistant', content: accumulated, streaming: true }
                return updated
              })
            }
          } catch { /* ignore parse error */ }
        }
      }

      // ストリーミング完了
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: accumulated, streaming: false }
        return updated
      })

    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: `❌ エラー: ${err.message}`, streaming: false, error: true }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const clearChat = () => setMessages([])

  // ABCブロックの検出・ハイライト
  const renderContent = (content) => {
    const parts = content.split(/(```abc[\s\S]*?```)/g)
    return parts.map((part, i) => {
      const abcMatch = part.match(/```abc\n?([\s\S]*?)```/)
      if (abcMatch) {
        return (
          <div key={i} className="abc-block">
            <div className="abc-block-header">
              <span>🎵 ABC楽譜</span>
            </div>
            <pre className="abc-code">{abcMatch[1].trim()}</pre>
          </div>
        )
      }
      return <span key={i} style={{ whiteSpace: 'pre-wrap' }}>{part}</span>
    })
  }

  return (
    <div className="chat-container">
      {/* ヘッダー */}
      <div className="chat-header">
        <div className="field flex-1">
          <select value={selectedModel} onChange={e => onModelChange(e.target.value)} className="text-sm">
            {models.map(m => <option key={m} value={m}>{m}</option>)}
            {models.length === 0 && <option value="qwen3.5:9b">qwen3.5:9b</option>}
          </select>
        </div>
        <button className="btn-ghost text-xs" onClick={() => setShowSystem(!showSystem)}>
          {showSystem ? '▲' : '▼'} システムプロンプト
        </button>
        <button className="btn-ghost text-xs" onClick={clearChat}>クリア</button>
      </div>

      {/* システムプロンプト（折りたたみ） */}
      {showSystem && (
        <div className="glass-panel p-3 mb-2">
          <label className="text-xs text-gray-400 mb-1 block">システムプロンプト</label>
          <textarea
            rows={3}
            value={systemPrompt}
            onChange={e => setSystemPrompt(e.target.value)}
            className="w-full text-xs font-mono"
          />
        </div>
      )}

      {/* メッセージ一覧 */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <span className="text-4xl">💬</span>
            <p>Ollamaとチャットを始めましょう</p>
            <p className="text-xs text-gray-500">曲のリクエストをすると、ABC記法の楽譜を生成します</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
            <div className="chat-role">{msg.role === 'user' ? 'あなた' : 'AI'}</div>
            <div className="chat-text">
              {renderContent(msg.content)}
              {msg.streaming && <span className="cursor-blink">▌</span>}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* 入力エリア */}
      <div className="chat-input-area">
        <textarea
          rows={2}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="メッセージを入力... (Enter で送信、Shift+Enter で改行)"
          disabled={loading}
          className="chat-input"
        />
        <button
          className="btn-primary"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          {loading ? <span className="loader-ring" /> : '送信'}
        </button>
      </div>
    </div>
  )
}
