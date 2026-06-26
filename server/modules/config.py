#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - 統合設定モジュール

このファイルを編集することで、全サービスの設定を一元管理できます。
ラズパイからPCのOllamaに接続する場合は OLLAMA_HOST をPCのIPアドレスに変更してください。
"""

import os

# =============================================================================
# Ollama LLMサーバー設定
# =============================================================================
# ローカルPC上で動かす場合: "127.0.0.1"
# ラズパイなど別マシンから接続する場合: PCのIPアドレス (例: "192.168.0.136")
# 注意: API_HOST (FastAPIが公開するIP) とは別設定です。
OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "127.0.0.1")
if OLLAMA_HOST == "0.0.0.0":
    OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT: int = int(os.environ.get("OLLAMA_PORT", "11434"))

# デフォルトで使用するLLMモデル
# 思考フェーズのない nothink / coder モデルが高速でABC記法出力に最適
DEFAULT_MODEL: str = os.environ.get("DEFAULT_MODEL", "qwen3.5:9b")

# =============================================================================
# APIサーバー設定
# =============================================================================
# FastAPI (Python バックエンド)
API_HOST: str = os.environ.get("API_HOST", "127.0.0.1")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))

# MIDI変換サーバー (Node.js)
MIDI_SERVER_HOST: str = os.environ.get("MIDI_SERVER_HOST", "127.0.0.1")
MIDI_SERVER_PORT: int = int(os.environ.get("MIDI_SERVER_PORT", "3001"))

# =============================================================================
# ファイル出力設定
# =============================================================================
# 生成されたWAV/ABCファイルの保存先ディレクトリ (server/ からの相対パス)
OUTPUT_DIR: str = os.environ.get(
    "OUTPUT_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
)

# =============================================================================
# LLMパラメータ設定
# =============================================================================
# ストリーミングタイムアウト (秒)
STREAM_TIMEOUT: int = int(os.environ.get("STREAM_TIMEOUT", "120"))

# モデル別のデフォルトパラメータ
def get_model_options(model: str) -> dict:
    """モデル名に応じた最適なオプションを返す"""
    if "3.6" in model:
        return {"num_predict": 8192}
    if "3.5" in model or "long" in model:
        return {"num_predict": 16384, "num_ctx": 16384}
    return {}


# =============================================================================
# ヘルパー関数
# =============================================================================
def get_ollama_base_url() -> str:
    """OllamaサーバーのベースURLを返す"""
    return f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"


def get_midi_server_url() -> str:
    """MIDIサーバーのベースURLを返す"""
    return f"http://{MIDI_SERVER_HOST}:{MIDI_SERVER_PORT}"
