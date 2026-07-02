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
    return f"""あなたはABC記法で作曲する優秀なAI音楽家です。
以下のテーマに基づいて、美しく響きのある豊かな楽曲（メロディとハーモニー）をABC記法で作曲してください。

【テーマ】: {theme}

【楽曲の要件】:
1. 構成と長さ:
   - 単調さを避け、ストーリー性や展開を感じられるようにしてください。
   - 長さは「8小節以上16小節以下」とし、A-B-A-C や A-A'-B-A' などの明確なフレーズ構成（構成感）を持たせてください。
2. ハーモニー（和音・コード）の追加:
   - メロディライン単体ではなく、小節の頭や拍の節目などで和音（コード）を重ねて、ある程度のハーモニーをつけてください。
   - ABC記法で和音を表す際は、`[CEG]2` や `[FAc]4` のように `[...]` で複数の音を囲み、直後に長さを表す数値を記述する形式にしてください。
   - 読みやすさのために、小節の頭に `"C"` や `"F"` などのコードシンボル（ダブルクォーテーションで囲む）を付与してください。
     例: `"C" [CEG]4 E2 G2 |`

【出力形式・構文に関する絶対ルール】:
1. キーの指定（K:）:
   - 調（K:）には、必ず指定されたキーである `{key}` を正確に指定してください（例: `K:{key}`）。`Cmaj7` や `Am7` などのコード名を指定してはいけません。
2. シンプルな三和音の使用:
   - ギターコードシンボル（ダブルクォート内）およびブラケット和音 `[...]` には、シンプルな三和音のみを使用してください（例: `"C"` `"Dm"` `"Em"` `"F"` `"G"` `"Am"` `"G7"` など）。
   - 分数コード（`F/C` など）や複雑なテンションコード（`Bm7b5`, `ACEGB` など）は絶対に使用しないでください。和音内の音は3音以下にしてください。
3. 拍数の完全な一致（極めて重要）:
   - 各小節の音符・和音・休符の長さの合計が、指定された拍子（M:4/4, L:1/8 の場合、1小節あたり合計「8」拍分（例えば `4 + 2 + 2 = 8` や `2 + 2 + 2 + 2 = 8` 等））と完全に一致するように、極めて正確に計算してください。

【作曲のルール】:
1. ABC記法の標準ヘッダー（X, T, M, L, Q, K）を必ず含めてください。
   - X: 1 / T: {theme} / M: 4/4 または 3/4 / L: 1/8 / Q: {tempo} / K: {key}
2. 使用する音符: C〜B（中音域）, c〜b（高音域）, C,〜B,（低音域）
   - 臨時記号: ^（シャープ）_（フラット）=（ナチュラル）
   - 休符: z
3. 複雑な複数パート(V:)は使用せず、単一のパートの中にメロディと和音（`[...]`）を混在させて記述してください。
4. 楽譜ブロックは必ず ```abc と ``` で囲んでください。
5. 楽譜の下に日本語で作曲意図と楽曲構成（フレーズ展開）の解説を2〜3行記述してください。
6. リズムに変化をつけ（4分音符・8分音符・休符を混在）、跳躍進行も取り入れること。
7. フレーズ終わりは主和音に解決させること。

【出力例】:
```abc
X:1
T:Sample Harmonies
M:4/4
L:1/8
Q:120
K:C
|: "C" [CEG]4 E2 G2 | "F" [FAc]4 A2 c2 | "G" [GBd]3 d B2 G2 | "C" [cEG]8 |
   "Am" [Ace]4 c2 e2 | "Dm" [DFA]4 F2 A2 | "G" [GBd]2 B2 G2 d2 | "C" [cEG]8 :|
```
**解説:** A-B構成の8小節の楽曲です。前半はC-F-G-Cのカデンツで安定した進行、後半はAmから始まり少し寂しげなニュアンスを加えた後、Gで盛り上げて主音(C)に力強く解決します。小節頭に和音を配置し、響きを豊かにしています。
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
    MAX_RETRY = 20

    print(f"\n自動作曲開始 (テーマ: '{req.theme}', キー: '{req.key}', テンポ: {req.tempo} BPM)")
    for attempt in range(MAX_RETRY):
        print(f"\n[リトライ {attempt+1}/{MAX_RETRY}] LLMへ推論リクエスト送信中 ({req.model})...")
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
            print(f"[{attempt+1}/{MAX_RETRY}] 作曲失敗: 楽譜ブロック未検出。")
            print(f"LLMの応答:\n{response}\n" + "="*40)
            continue

        temp_abc = abc_blocks[0]
        print(f"[{attempt+1}/{MAX_RETRY}] 抽出された楽譜:\n{temp_abc}\n" + "-"*40)

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
