# ABC Music Suite - Raspberry Pi 連携ガイド

## 概要

Raspberry Pi から LAN 経由で PC の Ollama に接続してABC演奏ができます。

```
[Raspberry Pi] ──Wi-Fi/LAN──> [PC: Ollama (RTX 4060)]
   play_abc.py
```

---

## セットアップ手順

### 1. ファイルをラズパイにコピー

PC の PowerShell から:

```powershell
# copy-to-pi.ps1 を使用
cd C:\情報科学演習
.\copy-to-pi.ps1
```

または手動でコピー:
```powershell
scp C:\情報科学演習\raspberry\* pi@<ラズパイのIP>:~/llm-client/
```

### 2. セットアップスクリプトを実行

ラズパイの bash で:

```bash
cd ~/llm-client
bash setup.sh
source ~/.bashrc
```

### 3. PCのIPアドレスを設定

ラズパイの `config.py` を編集:

```python
# ~/llm-client/config.py
OLLAMA_HOST = "192.168.0.136"  # ← PCのIPに変更
OLLAMA_PORT = 11434
DEFAULT_MODEL = "qwen3.5:9b"
```

PCのIPアドレス確認:
```powershell
# WindowsのPowerShellで
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -ne "Loopback*"}).IPAddress
```

### 4. Ollamaをネットワーク公開

PC側で Ollama がラズパイからの接続を受け付けるよう設定:

```powershell
# 環境変数を設定してOllamaを再起動
$env:OLLAMA_HOST = "0.0.0.0"
ollama serve
```

---

## 使い方

### 接続テスト

```bash
# ラズパイ側
python3 ~/llm-client/test_connection.py
```

成功時の出力例:
```
接続先: http://192.168.0.136:11434/api/tags
接続成功!
利用可能モデル (3個):
  - qwen3.5:9b
  - qwen2.5-coder:7b
  - ...
```

### ABC楽譜を演奏する

```bash
# ファイルから演奏
python3 ~/llm-client/play_abc.py /path/to/score.abc

# テキストを直接渡す
python3 ~/llm-client/play_abc.py "X:1
T:Test
M:4/4
L:1/4
K:C
C D E F | G A B c |"
```

---

## ファイル構成 (ラズパイ側)

```
~/llm-client/
├── config.py           ← PC の IP アドレスをここで設定
├── play_abc.py         ← ABC楽譜演奏スクリプト
├── abc_synthesizer.py  ← ABC→WAV合成ライブラリ
├── test_connection.py  ← 接続確認スクリプト
└── setup.sh            ← セットアップスクリプト
```

---

## トラブルシューティング

### 接続できない

1. **PCとラズパイが同じWi-Fiに接続されているか確認**
2. **PCのWindowsファイアウォール**でポート 11434 を許可:
   ```powershell
   New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow
   ```
3. **Ollamaが `0.0.0.0` でListenしているか確認**:
   ```powershell
   netstat -an | Select-String "11434"
   # 0.0.0.0:11434 で LISTEN していること
   ```

### 音が出ない (ラズパイ)

```bash
# aplay が入っているか確認
which aplay
# なければインストール
sudo apt-get install alsa-utils
```

### `abc_synthesizer.py` が見つからない

```bash
# setup.sh を再実行
cd ~/llm-client
bash setup.sh
```

---

## エイリアス一覧

`setup.sh` 実行後に `~/.bashrc` に追加されるエイリアス:

| コマンド | 説明 |
|---|---|
| `llm-test` | 接続テスト |
| `play-abc` | ABC楽譜演奏 |
