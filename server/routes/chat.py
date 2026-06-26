#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - チャットルート

POST /api/chat          : Ollamaとのチャット（ストリーミング）
GET  /api/models        : 利用可能モデル一覧
GET  /api/health        : ヘルスチェック
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.llm_client import get_client, OllamaClient
from modules.config import DEFAULT_MODEL, get_ollama_base_url, get_midi_server_url

router = APIRouter(prefix="/api", tags=["chat"])


# ------------------------------------------------------------------
# リクエスト/レスポンスモデル
# ------------------------------------------------------------------
class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = DEFAULT_MODEL
    system_prompt: Optional[str] = None


# ------------------------------------------------------------------
# エンドポイント
# ------------------------------------------------------------------
@router.get("/health")
def health_check():
    """
    全サービスのヘルスチェック。
    各コンポーネントの接続状態を返します。
    """
    client = get_client()
    ollama_ok = client.is_available()

    # MIDIサーバーの確認
    import urllib.request
    import urllib.error
    midi_ok = False
    try:
        req = urllib.request.Request(f"{get_midi_server_url()}/api/health")
        with urllib.request.urlopen(req, timeout=3):
            midi_ok = True
    except Exception:
        midi_ok = False

    models = []
    if ollama_ok:
        try:
            models = client.list_models()
        except Exception:
            pass

    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": {
            "connected": ollama_ok,
            "url": get_ollama_base_url(),
            "model_count": len(models),
        },
        "midi_server": {
            "connected": midi_ok,
            "url": get_midi_server_url(),
        },
    }


@router.get("/models")
def get_models():
    """
    Ollamaサーバーで利用可能なモデルの一覧を返す。
    """
    client = get_client()
    try:
        models = client.list_models()
        return {"models": models, "base_url": get_ollama_base_url()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
def chat(req: ChatRequest):
    """
    OllamaとのチャットをSSE（Server-Sent Events）でストリーミング返答する。

    - **messages**: 会話履歴（role/contentのリスト）
    - **model**: 使用するOllamaモデル名
    - **system_prompt**: システムプロンプト（省略可）
    """
    client = get_client()

    if not client.is_available():
        raise HTTPException(status_code=503, detail="Ollamaサーバーに接続できません。")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    if req.system_prompt:
        messages = [{"role": "system", "content": req.system_prompt}] + messages

    def event_stream():
        import json
        try:
            for token in client.chat_stream(req.model, messages):
                data = json.dumps({"token": token}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat/simple")
def chat_simple(req: ChatRequest):
    """
    チャット（ストリーミングなし、一括返答）。
    テスト用または短い回答が期待される場合に使用。
    """
    client = get_client()

    if not client.is_available():
        raise HTTPException(status_code=503, detail="Ollamaサーバーに接続できません。")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    reply = client.chat(req.model, messages, system_prompt=req.system_prompt)
    return {"reply": reply}
