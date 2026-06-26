#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - FastAPI メインエントリポイント

【開発モード】 (npm run dev + uvicorn を個別起動)
    cd server
    uvicorn main:app --host 127.0.0.1 --port 8000 --reload

【本番ホスティングモード】 (ラズパイ等から LAN でアクセス)
    .\\host.ps1
    → http://PCのIP:8000 でブラウザからアクセス可能
"""

import os
import sys

# Windows環境のUnicodeEncodeError対策
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# server/ ディレクトリを sys.path に追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
# abc_synthesizer.py は 情報科学演習/ ルートにある
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from modules.config import OUTPUT_DIR
from routes.compose import router as compose_router
from routes.harmonize import router as harmonize_router
from routes.midi_convert import router as midi_router
from routes.chat import router as chat_router

# ------------------------------------------------------------------
# アプリケーション設定
# ------------------------------------------------------------------
app = FastAPI(
    title="ABC Music Suite API",
    version="2.0.0",
    description="""
## ABC Music Suite バックエンドAPI

ローカルLLM (Ollama) を使ったABC記法音楽生成システムのバックエンドです。
LAN内のどのデバイス（ラズパイ等）からも `http://PCのIP:8000` でアクセスできます。

### 主な機能
- 🎵 **自動作曲** (`/api/compose`)
- 🎹 **ハーモニー付与** (`/api/harmonize`)
- 🔄 **MIDI変換** (`/api/midi-to-abc`, `/api/abc-to-midi`)
- 💬 **チャット** (`/api/chat`)
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------------------------------------------
# CORS設定 (LAN内からのアクセスを許可)
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN内のどこからでもアクセス可能
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# 静的ファイル配信
# ------------------------------------------------------------------
# 生成されたWAV/ABCファイル → /output/
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# ビルド済みフロントエンド (本番ホスティング時)
DIST_DIR = os.path.join(ROOT_DIR, "web-ui", "dist")
if os.path.isdir(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# ------------------------------------------------------------------
# ルーター登録 (APIルートを先に登録すること)
# ------------------------------------------------------------------
app.include_router(compose_router)
app.include_router(harmonize_router)
app.include_router(midi_router)
app.include_router(chat_router)

# ------------------------------------------------------------------
# SPA フォールバック
# ビルド済み index.html をすべての非APIルートに返す
# ------------------------------------------------------------------
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """
    SPAのフォールバックルート。
    ビルド済みの dist/index.html を返す。
    dist/ が存在しない場合はAPIドキュメントへリダイレクト。
    """
    index_file = os.path.join(DIST_DIR, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# ------------------------------------------------------------------
# 起動時ログ
# ------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    import socket
    from modules.config import get_ollama_base_url, get_midi_server_url

    try:
        lan_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        lan_ip = "不明"

    dist_exists = os.path.isfile(os.path.join(DIST_DIR, "index.html"))
    print("=" * 55)
    print("  ABC Music Suite API v2.0.0")
    print("=" * 55)
    print(f"  Ollama サーバー : {get_ollama_base_url()}")
    print(f"  MIDI サーバー   : {get_midi_server_url()}")
    print(f"  出力ディレクトリ: {OUTPUT_DIR}")
    print(f"  フロントエンド  : {'配信中 ✅' if dist_exists else '⚠️ 未ビルド (host.ps1 を使用してください)'}")
    print(f"  ローカル        : http://localhost:8000")
    print(f"  LAN (ラズパイ等): http://{lan_ip}:8000")
    print(f"  API ドキュメント: http://{lan_ip}:8000/docs")
    print("=" * 55)


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
