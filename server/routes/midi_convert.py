#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - MIDI変換ルート

POST /api/midi-to-abc : MIDIファイルをABC記法に変換 (Node.js MIDIサーバーへプロキシ)
POST /api/abc-to-midi : ABC記法テキストをMIDIに変換 (Node.js MIDIサーバーへプロキシ)
POST /api/ai-edit     : AI (Ollama) でABCを編集 (ハーモニー追加 / コード進行追加)
"""

import os
import json
import urllib.request
import urllib.error
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Literal

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.config import get_midi_server_url
from modules.llm_client import get_client
from modules.config import DEFAULT_MODEL

router = APIRouter(prefix="/api", tags=["midi"])

MIDI_SERVER = get_midi_server_url()


# ------------------------------------------------------------------
# リクエスト/レスポンスモデル
# ------------------------------------------------------------------
class AbcToMidiRequest(BaseModel):
    abc_text: str


class AiEditRequest(BaseModel):
    abc_text: str
    edit_type: Literal["harmony", "chord"]
    model: str = DEFAULT_MODEL


# ------------------------------------------------------------------
# MIDIサーバーへのプロキシヘルパー
# ------------------------------------------------------------------
def _proxy_post_json(path: str, data: dict) -> dict:
    """Node.js MIDIサーバーにJSONをPOSTしてレスポンスを返す"""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{MIDI_SERVER}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=e.code, detail=body)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"MIDIサーバーに接続できません ({MIDI_SERVER}): {e}"
        )


# ------------------------------------------------------------------
# AIプロンプト定義
# ------------------------------------------------------------------
AI_PROMPTS = {
    "harmony": """あなたは音楽理論の専門家です。
以下のABC記法の楽譜を確認し、元のメロディはそのままに、音楽的に自然なハーモニーパートを追加してください。
ハーモニーは元の旋律と3度・6度の音程を使って和音ブロック [音符1音符2] で追記してください。
【重要】ブラケットの入れ子や3音以上の和音は絶対にしないこと。
ABC記法のテキストのみを返してください。説明は一切不要です。""",

    "chord": """あなたは音楽理論の専門家です。
以下のABC記法の楽譜に合うコード進行を追加してください。
小節ごとに適切なコードを "Am" のようなギターコード記号としてABC記法のダブルクォートで記述してください。
各小節の先頭に "コード名" の形式で追記してください。
ABC記法のテキストのみを返してください。説明は一切不要です。""",
}


# ------------------------------------------------------------------
# エンドポイント
# ------------------------------------------------------------------
@router.post("/midi-to-abc")
async def midi_to_abc(midi_file: UploadFile = File(...)):
    """
    MIDIファイルをABC記法テキストに変換する。

    Node.js MIDIサーバー (ポート3001) の `/api/upload-convert` にプロキシします。
    MIDIサーバーが起動していない場合は503エラーを返します。
    """
    import urllib.request
    import io

    # マルチパートフォームデータをMIDIサーバーに転送
    file_data = await midi_file.read()

    # Node.jsサーバーへのマルチパートリクエスト作成
    boundary = "----PythonBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="midiFile"; filename="{midi_file.filename}"\r\n'
        f"Content-Type: audio/midi\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{MIDI_SERVER}/api/upload-convert",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            result = json.loads(res.read())

        # 変換結果のABCテキストを取得
        abc_req = urllib.request.Request(f"{MIDI_SERVER}/result.abc")
        with urllib.request.urlopen(abc_req, timeout=10) as abc_res:
            abc_text = abc_res.read().decode("utf-8")

        return {"status": "success", "abc_text": abc_text, "message": result.get("message", "")}
    except urllib.error.URLError as e:
        raise HTTPException(
            status_code=503,
            detail=f"MIDIサーバーに接続できません ({MIDI_SERVER}): {e}"
        )


@router.post("/abc-to-midi")
def abc_to_midi(req: AbcToMidiRequest):
    """
    ABC記法テキストをMIDIファイルに変換する。

    Node.js MIDIサーバー (ポート3001) の `/api/text-to-midi` にプロキシします。
    変換されたMIDIは `/midi-output/generated_output.mid` からダウンロードできます。
    """
    return _proxy_post_json("/api/text-to-midi", {"abcText": req.abc_text})


@router.post("/ai-edit")
def ai_edit(req: AiEditRequest):
    """
    ABC記法テキストをOllama (ローカルLLM) で編集する。

    - **edit_type**: "harmony"（ハーモニー追加）または "chord"（コード進行追加）
    - **abc_text**: 編集対象のABC記法テキスト
    - **model**: 使用するOllamaモデル名
    """
    if req.edit_type not in AI_PROMPTS:
        raise HTTPException(status_code=400, detail=f"不明なedit_type: {req.edit_type}")

    client = get_client()
    if not client.is_available():
        raise HTTPException(status_code=503, detail="Ollamaサーバーに接続できません。")

    system_prompt = AI_PROMPTS[req.edit_type]
    full_prompt = f"{system_prompt}\n\n---\n{req.abc_text}"

    response = client.prompt(req.model, full_prompt)
    if not response:
        raise HTTPException(status_code=500, detail="LLMから応答を取得できませんでした。")

    # マークダウンコードブロックを除去して純粋なABCテキストを返す
    import re
    fence_match = re.search(r"```(?:abc)?\s*([\s\S]*?)```", response, re.IGNORECASE)
    clean_abc = fence_match.group(1).strip() if fence_match else response.strip()

    return {"status": "success", "abc_text": clean_abc}
