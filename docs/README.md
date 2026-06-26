# ABC Music Suite

> ローカルLLM (Ollama) を使ったABC記法音楽生成・編集・変換統合システム

## 概要

**ABC Music Suite** は、ローカルマシン上のAI（Ollama）を活用して音楽を自動作曲・編集できるシステムです。
外部APIキーは不要で、すべてオフラインで動作します。

| 機能 | 説明 |
|---|---|
| 🌌 自動作曲 | テーマを入力するとAI が ABC記法の楽譜とWAV音源を生成 |
| 🎹 ハーモニー付与 | 単旋律メロディにAIが伴奏コードを重ねる |
| 🔄 MIDI変換 | MIDI↔ABC記法の双方向変換 (abc2midiエンジン使用) |
| 💬 AIチャット | Ollamaとリアルタイムチャット、ABC楽譜を自動検出して表示 |
| 🍓 ラズパイ連携 | Raspberry PiからLANを経由してPCで生成したABC楽譜の自動演奏 |

---

## クイックスタート

### 必要環境

- **Ollama** がインストール済みで、Qwenモデルが1つ以上ダウンロード済み
- **Python 3.10+** (FastAPI用)
- **Node.js 18+** (Vite/Expressサーバー用)

### 依存関係のインストール

```powershell
# Pythonパッケージ
cd C:\情報科学演習\server
pip install fastapi uvicorn pydantic

# MIDIサーバー
cd C:\情報科学演習\midi-server
npm install

# フロントエンド
cd C:\情報科学演習\web-ui
npm install
```

### 起動方法

```powershell
# 全サービスを一括起動 (推奨)
cd C:\情報科学演習
.\start.ps1
```

または個別起動:

```powershell
# ターミナル1: FastAPI
cd C:\情報科学演習\server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# ターミナル2: MIDIサーバー
cd C:\情報科学演習\midi-server
node server.js

# ターミナル3: フロントエンド
cd C:\情報科学演習\web-ui
npm run dev
```

### アクセス

| URL | 説明 |
|---|---|
| http://localhost:5173 | Web UI（ここを開く） |
| http://localhost:8000/docs | FastAPI Swagger ドキュメント |
| http://localhost:3001 | MIDI変換サーバー |

---

## ディレクトリ構成

```
情報科学演習/
├── server/                  # Python FastAPI バックエンド
│   ├── main.py              # エントリポイント
│   ├── modules/
│   │   ├── config.py        # 統合設定ファイル ← IPアドレスはここで変更
│   │   └── llm_client.py    # OllamaClientクラス（疎結合LLM通信）
│   └── routes/
│       ├── compose.py       # 自動作曲API
│       ├── harmonize.py     # ハーモニー付与API
│       ├── midi_convert.py  # MIDI変換API (Node.jsへのプロキシ)
│       └── chat.py          # チャット・モデル・ヘルスチェックAPI
│
├── midi-server/             # Node.js MIDI変換サーバー
│   ├── server.js            # abc2midi ラッパー + MIDI↔ABC変換
│   ├── abc2midi.exe         # abc2midiバイナリ (Windows)
│   └── package.json
│
├── web-ui/                  # Vite + React フロントエンド
│   └── src/
│       ├── App.jsx          # タブナビ・ヘルスインジケーター
│       ├── index.css        # デザインシステム（CSS変数ベース）
│       └── components/
│           ├── ComposeTab.jsx      # 自動作曲タブ
│           ├── HarmonizeTab.jsx    # ハーモニー付与タブ
│           ├── MidiConvertTab.jsx  # MIDI変換タブ
│           └── ChatTab.jsx         # チャットタブ（SSEストリーミング）
│
├── raspberry/               # Raspberry Pi用クライアント
│   ├── config.py            # ラズパイ側の接続設定
│   ├── play_abc.py          # ABC楽譜ファイル演奏
│   ├── abc_synthesizer.py   # ABC→WAV合成ライブラリ
│   └── setup.sh             # ラズパイセットアップスクリプト
│
├── docs/                    # ドキュメント
│   ├── README.md            # このファイル
│   ├── ARCHITECTURE.md      # システム構成図
│   ├── API.md               # APIリファレンス
│   └── RASPBERRY_PI.md      # ラズパイ連携ガイド
│
├── abc_synthesizer.py       # ABC→WAV合成ライブラリ（ルート）
├── output/                  # 生成ファイルの保存先
├── start.ps1                # 全サービス一括起動
└── start.bat                # ダブルクリック起動用
```

---

## 設定変更

### OllamaのIPアドレスを変更する

`server/modules/config.py` の `OLLAMA_HOST` を変更:

```python
OLLAMA_HOST = "192.168.0.136"  # ラズパイから接続する場合
```

または環境変数で上書き:

```powershell
$env:OLLAMA_HOST = "192.168.0.136"
.\start.ps1
```

---

## Raspberry Pi連携

[ラズパイ連携ガイド](./RASPBERRY_PI.md) を参照してください。

---

## APIドキュメント

[APIリファレンス](./API.md) を参照してください。
サーバー起動後は http://localhost:8000/docs でSwagger UIを確認できます。

---

## 免責事項とライセンス

### 保証および免責事項
本システム（ABC Music Suite）は評価・プロトタイプ用製品として「現状のまま（AS IS）」提供されます。開発者（メーカー）は、本ソフトウェアの動作、特定の目的への適合性、あるいは生成されるデータの正確性および第三者の権利非侵害性について、明示的にも黙示的にもいかなる保証も行いません。

本システムの使用から生じるあらゆる直接的・間接的損害（ハードウェアの故障、データの損失、セキュリティインシデント等）に対して、メーカーは一切の責任を負いません。外部アクセス許可（Ollamaを0.0.0.0で公開）を行う際は、セキュリティリスクを理解した上で、自己責任において実行してください。

### ライセンス
本システムは MIT License の下で公開されています。詳細な許諾内容についてはドキュメントのライセンスセクションを参照してください。
