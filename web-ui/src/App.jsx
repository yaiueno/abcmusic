import { useState, useEffect } from 'react'
import ComposeTab from './components/ComposeTab'
import HarmonizeTab from './components/HarmonizeTab'
import MidiConvertTab from './components/MidiConvertTab'
import ChatTab from './components/ChatTab'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

const TABS = [
  { id: 'compose',   icon: '🌌', label: '自動作曲',      color: 'cyan'   },
  { id: 'harmonize', icon: '🎹', label: 'ハーモニー付与', color: 'purple' },
  { id: 'midi',      icon: '🔄', label: 'MIDI変換',       color: 'green'  },
  { id: 'chat',      icon: '💬', label: 'AIチャット',     color: 'blue'   },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('compose')
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')
  const [health, setHealth] = useState(null)
  const [healthChecked, setHealthChecked] = useState(false)

  // ヘルスチェックとモデルの再読み込み
  const checkSystemStatus = () => {
    setHealthChecked(false)
    fetch(`${API_BASE}/api/health`)
      .then(r => r.json())
      .then(d => { setHealth(d); setHealthChecked(true) })
      .catch(() => setHealthChecked(true))

    fetch(`${API_BASE}/api/models`)
      .then(r => r.json())
      .then(d => {
        const ms = d.models || []
        setModels(ms)
        if (ms.length > 0) {
          setSelectedModel(curr => {
            if (ms.includes(curr)) return curr
            return ms.find(m => m.includes('coder') || m.includes('nothink')) || ms[0] || 'qwen3.5:9b'
          })
        }
      })
      .catch(() => {})
  }

  // 起動時: モデル一覧とヘルスチェック
  useEffect(() => {
    checkSystemStatus()
  }, [])

  const tabProps = { models, selectedModel, onModelChange: setSelectedModel }

  return (
    <div className="app-root">
      {/* ヘッダー */}
      <header className="app-header">
        <div className="header-inner">
          <div className="header-brand">
            <span className="brand-icon">♪</span>
            <h1 className="brand-title">
              <span className="gradient-text">ABC Music Suite</span>
            </h1>
            <span className="brand-sub">ローカルLLM × 音楽生成システム</span>
          </div>

          {/* ヘルスインジケーター */}
          <div className="header-status-area">
            {healthChecked && (
              <div className="health-badges">
                <div className={`health-badge ${health?.ollama?.connected ? 'badge-ok' : 'badge-ng'}`}>
                  <span className={`dot ${health?.ollama?.connected ? 'dot-ok' : 'dot-ng'}`} />
                  Ollama {health?.ollama?.connected ? `(${health.ollama.model_count}モデル)` : 'オフライン'}
                </div>
                <div className={`health-badge ${health?.midi_server?.connected ? 'badge-ok' : 'badge-warn'}`}>
                  <span className={`dot ${health?.midi_server?.connected ? 'dot-ok' : 'dot-warn'}`} />
                  MIDIサーバー {health?.midi_server?.connected ? 'OK' : '未起動'}
                </div>
                <button className="status-reset-btn" onClick={checkSystemStatus} title="接続ステータスを再チェック">
                  🔄 再チェック
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* タブナビ */}
      <nav className="tab-nav">
        {TABS.map(tab => (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            className={`tab-btn tab-btn-${tab.color} ${activeTab === tab.id ? 'tab-btn-active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* タブコンテンツ */}
      <main className="app-main">
        {activeTab === 'compose'   && <ComposeTab   {...tabProps} />}
        {activeTab === 'harmonize' && <HarmonizeTab {...tabProps} />}
        {activeTab === 'midi'      && <MidiConvertTab {...tabProps} />}
        {activeTab === 'chat'      && <ChatTab      {...tabProps} />}
      </main>

      {/* フッター */}
      <footer className="app-footer">
        <p>ABC Music Suite v2.0 &nbsp;|&nbsp; Powered by Ollama (ローカルLLM) &nbsp;|&nbsp;
          <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer" className="footer-link">API Docs</a>
        </p>
      </footer>
    </div>
  )
}
