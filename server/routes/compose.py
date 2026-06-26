#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - 自動作曲ルート

POST /api/compose  : テーマを受け取りABC記法楽譜とWAVを生成
GET  /api/compose/presets : プリセット一覧を返す
"""

import os
import re
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# モジュールのインポート（server/ ルートから起動されることを前提）
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.llm_client import get_client
from modules.config import DEFAULT_MODEL, OUTPUT_DIR
from modules import abc_validator
import abc_synthesizer

router = APIRouter(prefix="/api", tags=["compose"])

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ------------------------------------------------------------------
# リクエスト/レスポンスモデル
# ------------------------------------------------------------------
class ComposeRequest(BaseModel):
    theme: str
    key: str = "C"
    tempo: int = 120
    model: str = DEFAULT_MODEL


class ComposeResponse(BaseModel):
    title: str
    abc_content: str
    abc_url: str
    wav_url: str


# ------------------------------------------------------------------
# プリセット定義
# ------------------------------------------------------------------
PRESETS = [
    {"id": 1, "theme": "明るく楽しい子供向けのマーチ", "key": "C", "tempo": 120},
    {"id": 2, "theme": "哀愁漂う雨の日のバイオリンソロ", "key": "Am", "tempo": 80},
    {"id": 3, "theme": "森の妖精が踊る軽快なワルツ", "key": "G", "tempo": 140},
    {"id": 4, "theme": "荒野を進むカウボーイの力強い唄", "key": "Em", "tempo": 100},
]


# ------------------------------------------------------------------
# プロンプト生成
# ------------------------------------------------------------------
def _make_compose_prompt(theme: str, key: str = "C", tempo: int = 120) -> str:
    return f"""あなたはABC記法でメロディを作曲する優秀なAI音楽家です。
以下のテーマに基づいて、美しく一貫性のある短いメロディをABC記法で作曲してください。

【テーマ】: {theme}

【作曲のルール】:
1. ABC記法の標準ヘッダー（X, T, M, L, Q, K）を必ず含めてください。
   - X: 1 / T: {theme} / M: 4/4 または 3/4 / L: 1/8 / Q: {tempo} / K: {key}
2. 使用する音符: C〜B（中音域）, c〜b（高音域）, C,〜B,（低音域）
   - 臨時記号: ^（シャープ）_（フラット）=（ナチュラル）
   - 休符: z
3. 複雑な複数パート(V:)やコードシンボルは出力しないでください（単旋律のみ）。
4. 楽譜ブロックは必ず ```abc と ``` で囲んでください。
5. 楽譜の下に日本語で作曲意図の解説を2〜3行記述してください。
6. リズムに変化をつけ（4分音符・8分音符・休符を混在）、跳躍進行も取り入れること。
7. カデンツ進行（T→S→D→T）を意識し、フレーズ終わりは主和音に解決させること。

【出力例】:
```abc
X:1
T:Sample Melody
M:4/4
L:1/8
Q:120
K:C
|: E2 G2 c2 d2 | e3 d c4 | d2 B2 G3 A | B2 A2 G4 :|
```
**解説:** Cメジャーのトニックから始まり、ドミナントで緊張し主音に解決する構造です。
"""


# ------------------------------------------------------------------
# 共通: ABC保存・WAV合成
# ------------------------------------------------------------------
def _save_and_render(abc_text: str, title: str, prefix: str) -> tuple[str, str]:
    """ABC楽譜をファイル保存し、WAVに合成する。(abc_path, wav_path) を返す。"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r'[\\/*?:"<>| ]', "_", title)[:40]

    abc_path = os.path.join(OUTPUT_DIR, f"{prefix}_{safe_title}_{timestamp}.abc")
    wav_path = os.path.join(OUTPUT_DIR, f"{prefix}_{safe_title}_{timestamp}.wav")

    with open(abc_path, "w", encoding="utf-8") as f:
        f.write(abc_text)

    success = abc_synthesizer.play_abc_string(abc_text, wav_path)
    if not success:
        raise ValueError("WAV合成に失敗しました。ABCの構文を確認してください。")

    return abc_path, wav_path


# ------------------------------------------------------------------
# エンドポイント
# ------------------------------------------------------------------
@router.get("/compose/presets")
def get_presets():
    """プリセット作曲テーマ一覧を返す"""
    return {"presets": PRESETS}


@router.post("/compose", response_model=ComposeResponse)
def compose(req: ComposeRequest):
    """
    テーマを受け取り、LLMで作曲してABC楽譜とWAVを返す。

    - **theme**: 曲のテーマ・イメージ（例: 爽やかな朝の森）
    - **key**: 調号（C, Am, G, Em など）
    - **tempo**: テンポ BPM（60〜200）
    - **model**: 使用するOllamaモデル名
    """
    client = get_client()

    if not client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollamaサーバーに接続できません。サーバーが起動しているか確認してください。"
        )

    prompt = _make_compose_prompt(req.theme, req.key, req.tempo)
    messages = [{"role": "user", "content": prompt}]

    abc_text = ""
    error_message = ""
    success = False
    MAX_RETRY = 5

    for attempt in range(MAX_RETRY):
        response = client.chat(req.model, messages)
        if not response:
            error_message = "LLMからの応答を取得できませんでした。"
            print(f"[{attempt+1}/{MAX_RETRY}] 作曲失敗: 応答がありません。")
            continue

        abc_blocks = abc_synthesizer.extract_abc_blocks(response)
        if not abc_blocks:
            error_message = "楽譜ブロック（```abc ... ```）が検出されませんでした。"
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": "上記の応答にはABC記法の楽譜ブロック（```abc ... ```）が含まれていません。楽譜部分を必ず ```abc と ``` で囲んで再出力してください。"
            })
            print(f"[{attempt+1}/{MAX_RETRY}] 作曲失敗: 楽譜ブロック未検出。再生成指示を送信します。")
            continue

        temp_abc = abc_blocks[0]

        # フィルターによる全体チェック
        ok, msg = abc_validator.check_all(temp_abc)
        if ok:
            abc_text = temp_abc
            success = True
            print(f"[{attempt+1}/{MAX_RETRY}] 作曲成功！楽譜検証パス。")
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
            print(f"[{attempt+1}/{MAX_RETRY}] 作曲失敗: {msg}。修正指示を送信します。")

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"楽譜の自動生成に失敗しました（リトライ上限 {MAX_RETRY} 回に達しました）。最後のエラー: {error_message}"
        )

    try:
        abc_path, wav_path = _save_and_render(abc_text, req.theme, "compose")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ComposeResponse(
        title=req.theme,
        abc_content=abc_text,
        abc_url=f"/output/{os.path.basename(abc_path)}",
        wav_url=f"/output/{os.path.basename(wav_path)}",
    )
