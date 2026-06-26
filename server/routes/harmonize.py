#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - ハーモニー付与ルート

POST /api/harmonize : メロディABCを受け取り、ハーモニー付きABCとWAVを返す
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.llm_client import get_client
from modules.config import DEFAULT_MODEL
from modules import abc_validator
import abc_synthesizer
from routes.compose import _save_and_render

router = APIRouter(prefix="/api", tags=["harmonize"])


# ------------------------------------------------------------------
# リクエスト/レスポンスモデル
# ------------------------------------------------------------------
class HarmonizeRequest(BaseModel):
    melody_abc: str
    title: str = "harmony_input"
    model: str = DEFAULT_MODEL


class HarmonizeResponse(BaseModel):
    title: str
    abc_content: str
    abc_url: str
    wav_url: str


# ------------------------------------------------------------------
# プロンプト生成
# ------------------------------------------------------------------
def _make_harmony_prompt(melody_abc: str) -> str:
    return f"""あなたはABC記法でメロディにハーモニー（和音伴奏）を付与する優秀なAI音楽家です。
以下の単旋律メロディを解析し、美しい和音を重ねたABC記法楽譜を作成してください。

【入力メロディ】:
```abc
{melody_abc.strip()}
```

【ハーモニー付与のルール】:
1. 元のメロディの音符・リズム・調（Key）を完全に維持してください。
2. ハーモニーはABC記法の和音ブロック `[音符1音符2]` で表現してください。
   - 例: メロディ音 `c` にベース音 `C,` を重ねる場合 → `[C,c]`
3. 【重要・文法エラーの禁止】:
   - ブラケットの入れ子（`[C[EG]]`）は絶対にしないこと。
   - 和音ブロック内は常に「メロディ音＋1音のベース音」の2音のみ。
   - ブラケット内にスペースやカンマ区切りを入れないこと。
4. 複数パート(V:)やコードシンボルは出力しないこと。
5. 出力する楽譜ブロック（```abc）は1つだけにすること。
6. 楽譜の下にコード進行の意図を日本語で2〜3行記述してください。
7. すべての音符に和音を重ねる必要はない。強拍（1・3拍目）に重点を置くこと。

【ABC記法でのハーモニー付与例】:
入力:
```abc
X:1
T:Twinkle
M:4/4
L:1/4
Q:120
K:C
C C G G | A A G2 |
```
出力:
```abc
X:1
T:Twinkle with Harmony
M:4/4
L:1/4
Q:120
K:C
[C,C] C [G,G] G | [A,A] A [G,2G2] |
```
"""


# ------------------------------------------------------------------
# エンドポイント
# ------------------------------------------------------------------
@router.post("/harmonize", response_model=HarmonizeResponse)
def harmonize(req: HarmonizeRequest):
    """
    単旋律メロディにAI生成ハーモニーを付与し、ABC楽譜とWAVを返す。

    - **melody_abc**: 入力メロディのABC記法テキスト
    - **title**: 識別用タイトル（ファイル名に使用）
    - **model**: 使用するOllamaモデル名
    """
    client = get_client()

    if not client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollamaサーバーに接続できません。"
        )

    prompt = _make_harmony_prompt(req.melody_abc)
    messages = [{"role": "user", "content": prompt}]

    abc_text = ""
    error_message = ""
    success = False
    MAX_RETRY = 20

    print(f"\n伴奏（ハーモニー）付与開始 (タイトル: '{req.title}', モデル: '{req.model}')")
    for attempt in range(MAX_RETRY):
        print(f"\n[リトライ {attempt+1}/{MAX_RETRY}] LLMへ推論リクエスト送信中 ({req.model})...")
        response = client.chat(req.model, messages)
        if not response:
            error_message = "LLMからの応答を取得できませんでした。"
            print(f"[{attempt+1}/{MAX_RETRY}] 伴奏付与失敗: 応答がありません。")
            continue

        abc_blocks = abc_synthesizer.extract_abc_blocks(response)
        if not abc_blocks:
            error_message = "楽譜ブロック（```abc ... ```）が検出されませんでした。"
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": "上記の応答にはABC記法の楽譜ブロック（```abc ... ```）が含まれていません。楽譜部分を必ず ```abc と ``` で囲んで再出力してください。"
            })
            print(f"[{attempt+1}/{MAX_RETRY}] 伴奏付与失敗: 楽譜ブロック未検出。")
            print(f"LLMの応答:\n{response}\n" + "="*40)
            continue

        temp_abc = abc_blocks[0]
        print(f"[{attempt+1}/{MAX_RETRY}] 抽出された楽譜:\n{temp_abc}\n" + "-"*40)

        # フィルターによる全体チェック
        ok, msg = abc_validator.check_all(temp_abc)
        if ok:
            abc_text = temp_abc
            success = True
            print(f"[{attempt+1}/{MAX_RETRY}] 伴奏付与成功！楽譜検証パス。")
            break
        else:
            error_message = msg
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": (
                    f"生成された楽譜には以下のエラーがあります：\n"
                    f"【エラー内容】: {msg}\n\n"
                    f"このエラーを修正し、正しいABC記法の楽譜を ```abc ... ``` で囲んで再出力してください。"
                )
            })
            print(f"[{attempt+1}/{MAX_RETRY}] 伴奏付与失敗: {msg}。修正指示を送信します。")

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"ハーモニーの自動付与に失敗しました（リトライ上限 {MAX_RETRY} 回に達しました）。最後のエラー: {error_message}"
        )

    try:
        abc_path, wav_path = _save_and_render(abc_text, req.title, "harmony")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return HarmonizeResponse(
        title=req.title,
        abc_content=abc_text,
        abc_url=f"/output/{os.path.basename(abc_path)}",
        wav_url=f"/output/{os.path.basename(wav_path)}",
    )
