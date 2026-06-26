# ABC Music Suite - システム構成図

## 全体アーキテクチャ

```mermaid
graph TB
    subgraph Browser["🌐 ブラウザ (localhost:5173)"]
        UI["Vite + React\nABC Music Suite UI"]
        T1["🌌 自動作曲タブ"]
        T2["🎹 ハーモニー付与タブ"]
        T3["🔄 MIDI変換タブ"]
        T4["💬 AIチャットタブ"]
        UI --> T1 & T2 & T3 & T4
    end

    subgraph Python["🐍 FastAPI バックエンド (localhost:8000)"]
        MAIN["main.py\nエントリポイント"]
        R1["routes/compose.py\n自動作曲API"]
        R2["routes/harmonize.py\nハーモニー付与API"]
        R3["routes/midi_convert.py\nMIDI変換プロキシ"]
        R4["routes/chat.py\nチャット・モデル・ヘルス"]
        M1["modules/llm_client.py\nOllamaClient クラス"]
        M2["modules/config.py\n統合設定"]
        ABC["abc_synthesizer.py\nABC→WAV合成ライブラリ"]
        OUT["output/\n生成WAV・ABCファイル"]

        MAIN --> R1 & R2 & R3 & R4
        R1 & R2 --> M1
        R4 --> M1
        M1 --> M2
        R1 & R2 --> ABC
        ABC --> OUT
    end

    subgraph Node["🟢 MIDI サーバー (localhost:3001)"]
        NJS["server.js\nNode.js Express"]
        MIDI_EXE["abc2midi.exe\nバイナリエンジン"]
        NJS --> MIDI_EXE
    end

    subgraph Ollama["🤖 Ollama LLMサーバー (localhost:11434)"]
        OL["Ollama API"]
        QW1["qwen3.5:9b"]
        QW2["その他モデル"]
        OL --> QW1 & QW2
    end

    subgraph RPi["🍓 Raspberry Pi (LAN接続)"]
        PLAY["play_abc.py\nABC演奏"]
        CFG["config.py\n接続設定"]
    end

    T1 & T2 --> |HTTP POST| R1 & R2
    T3 --> |HTTP POST| R3
    T4 --> |SSE ストリーミング| R4
    R3 --> |HTTP プロキシ| NJS
    M1 --> |HTTP REST| OL
    PLAY --> ABC
```

---

## 疎結合の設計原則

```mermaid
graph LR
    subgraph 変更が局所的
        A["フロントエンド変更\n(React → Vue など)"] -.->|影響なし| B
        B["FastAPI ルート\n(API仕様維持)"]
        B -.->|影響なし| C
        C["LLM Client\nOllamaClient クラス"]
        C -.->|影響なし| D
        D["Ollama API\n(LLM プロバイダー変更)"]
    end
```

各レイヤーはHTTP REST APIまたは関数インターフェースでのみ結合しているため：
- **LLMプロバイダーを変える** → `llm_client.py` だけ修正
- **Ollamaのホストを変える** → `config.py` の1行だけ修正
- **フロントエンドを全面刷新** → バックエンドは無変更
- **MIDI変換エンジンを変える** → `midi-server/server.js` だけ修正

---

## データフロー図

### 自動作曲フロー

```mermaid
sequenceDiagram
    participant UI as React UI
    participant API as FastAPI
    participant LLM as OllamaClient
    participant OL as Ollama
    participant SYN as abc_synthesizer

    UI->>API: POST /api/compose {theme, key, tempo, model}
    API->>LLM: client.prompt(model, prompt)
    LLM->>OL: POST /api/chat (ストリーミング)
    OL-->>LLM: トークン列
    LLM-->>API: 完全な回答テキスト
    API->>SYN: extract_abc_blocks(response)
    SYN-->>API: ABCテキスト
    API->>SYN: play_abc_string(abc, wav_path)
    SYN-->>API: output/compose_xxx.wav
    API-->>UI: {abc_content, abc_url, wav_url}
    UI->>UI: <audio> で再生
```

### MIDI変換フロー

```mermaid
sequenceDiagram
    participant UI as React UI
    participant API as FastAPI
    participant NODE as Node.js MIDI Server
    participant EXE as abc2midi.exe

    UI->>API: POST /api/midi-to-abc (MIDIファイル)
    API->>NODE: POST /api/upload-convert (プロキシ)
    NODE-->>API: ABC テキスト
    API-->>UI: {abc_text}

    UI->>API: POST /api/abc-to-midi {abc_text}
    API->>NODE: POST /api/text-to-midi (プロキシ)
    NODE->>EXE: abc2midi.exe input.abc -o output.mid
    EXE-->>NODE: generated_output.mid
    NODE-->>API: {midi_url}
    API-->>UI: {midi_url}
    UI->>UI: ダウンロードリンクを表示
```

---

## ポート一覧

| サービス | ポート | プロトコル | 役割 |
|---|---|---|---|
| Vite Dev Server | 5173 | HTTP | React フロントエンド |
| FastAPI | 8000 | HTTP/SSE | バックエンドAPI |
| MIDI Server | 3001 | HTTP | abc2midi ラッパー |
| Ollama | 11434 | HTTP | LLM推論エンジン |

---

## モジュール依存関係

```mermaid
graph TD
    APP["App.jsx"] --> CT["ComposeTab"]
    APP --> HT["HarmonizeTab"]
    APP --> MT["MidiConvertTab"]
    APP --> CHT["ChatTab"]
    CT & HT --> RP["ResultPanel\n共有コンポーネント"]

    MAIN["main.py"] --> RC["routes/compose.py"]
    MAIN --> RH["routes/harmonize.py"]
    MAIN --> RM["routes/midi_convert.py"]
    MAIN --> RCHT["routes/chat.py"]

    RC & RH & RCHT --> LLC["modules/llm_client.py"]
    LLC --> CFG["modules/config.py"]
    RC & RH --> SYN["abc_synthesizer.py"]
    RM --> NODE["midi-server/server.js"]
```
