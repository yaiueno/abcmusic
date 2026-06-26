# ABC Music Suite - APIリファレンス

ベースURL: `http://localhost:8000`

Swagger UIで対話的に確認: http://localhost:8000/docs

---

## システム系

### `GET /api/health`
全サービスのヘルスチェック。

**レスポンス例:**
```json
{
  "status": "ok",
  "ollama": {
    "connected": true,
    "url": "http://127.0.0.1:11434",
    "model_count": 3
  },
  "midi_server": {
    "connected": true,
    "url": "http://127.0.0.1:3001"
  }
}
```

### `GET /api/models`
Ollamaで利用可能なモデルの一覧を返す。

**レスポンス例:**
```json
{
  "models": ["qwen3.5:9b", "qwen2.5-coder:7b"],
  "base_url": "http://127.0.0.1:11434"
}
```

---

## 自動作曲

### `GET /api/compose/presets`
プリセット作曲テーマの一覧を返す。

**レスポンス例:**
```json
{
  "presets": [
    {"id": 1, "theme": "明るく楽しい子供向けのマーチ", "key": "C", "tempo": 120},
    {"id": 2, "theme": "哀愁漂う雨の日のバイオリンソロ", "key": "Am", "tempo": 80}
  ]
}
```

### `POST /api/compose`
テーマを受け取り、LLMでABC楽譜とWAVを生成する。

**リクエスト:**
```json
{
  "theme": "爽やかな朝の森",
  "key": "C",
  "tempo": 120,
  "model": "qwen3.5:9b"
}
```

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `theme` | string | 必須 | 曲のテーマ・イメージ |
| `key` | string | `"C"` | 調号 (C, G, Am, Em, F, Dm など) |
| `tempo` | int | `120` | テンポ BPM (60〜200) |
| `model` | string | `"qwen3.5:9b"` | 使用するOllamaモデル |

**レスポンス:**
```json
{
  "title": "爽やかな朝の森",
  "abc_content": "X:1\nT:爽やかな朝の森\n...",
  "abc_url": "/output/compose_xxx.abc",
  "wav_url": "/output/compose_xxx.wav"
}
```

---

## ハーモニー付与

### `POST /api/harmonize`
単旋律メロディにAI生成ハーモニーを付与する。

**リクエスト:**
```json
{
  "melody_abc": "X:1\nT:Test\nM:4/4\nL:1/4\nQ:120\nK:C\nC C G G | A A G2 |",
  "title": "twinkle_harmony",
  "model": "qwen3.5:9b"
}
```

**レスポンス:** `/api/compose` と同じ形式。

---

## MIDI変換

### `POST /api/midi-to-abc`
MIDIファイルをABC記法に変換する（multipart/form-data）。

**リクエスト:** `multipart/form-data` で `midiFile` フィールドにMIDIファイルを添付。

**レスポンス:**
```json
{
  "status": "success",
  "abc_text": "X:1\nT:Converted MIDI\n...",
  "message": "MIDI→ABC変換成功！"
}
```

### `POST /api/abc-to-midi`
ABC記法テキストをMIDIに変換する。

**リクエスト:**
```json
{
  "abc_text": "X:1\nT:Test\nM:4/4\nL:1/4\nK:C\nC D E F |"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "abc2midiによるMIDI変換に成功！",
  "midi_url": "/generated_output.mid"
}
```
> ⚠️ MIDI変換にはMIDIサーバー (ポート3001) の起動が必要です。

### `POST /api/ai-edit`
ABC記法テキストをOllamaで編集する。

**リクエスト:**
```json
{
  "abc_text": "X:1\nT:Test\n...",
  "edit_type": "harmony",
  "model": "qwen3.5:9b"
}
```

| `edit_type` | 説明 |
|---|---|
| `"harmony"` | ハーモニーパートを追加 |
| `"chord"` | コード記号を追加 |

**レスポンス:**
```json
{
  "status": "success",
  "abc_text": "X:1\nT:Test with Harmony\n..."
}
```

---

## チャット

### `POST /api/chat` (SSEストリーミング)
OllamaとのチャットをServer-Sent Events形式でストリーミングする。

**リクエスト:**
```json
{
  "messages": [
    {"role": "user", "content": "Cメジャーで明るいメロディを作って"}
  ],
  "model": "qwen3.5:9b",
  "system_prompt": "あなたは音楽家AIです。"
}
```

**レスポンス:** `text/event-stream` 形式。
```
data: {"token": "X"}
data: {"token": ":1\n"}
...
data: [DONE]
```

### `POST /api/chat/simple`
チャット（ストリーミングなし、一括返答）。

**レスポンス:**
```json
{
  "reply": "X:1\nT:明るいメロディ\n..."
}
```

---

## 静的ファイル配信

| パス | 説明 |
|---|---|
| `GET /output/{filename}.wav` | 生成されたWAVファイルのダウンロード |
| `GET /output/{filename}.abc` | 生成されたABCファイルのダウンロード |

---

## MIDIサーバー直接API (ポート3001)

> 通常はFastAPI経由でアクセスします。直接アクセスは開発・デバッグ用。

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/api/health` | GET | ヘルスチェック |
| `/api/upload-convert` | POST | MIDI→ABCファイル変換 |
| `/api/text-to-midi` | POST | ABC→MIDI変換 |
| `/result.abc` | GET | 最後に変換されたABCテキスト |
| `/generated_output.mid` | GET | 最後に生成されたMIDIファイル |
