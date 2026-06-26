#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen 3.5によるABC記法作曲プロトタイピングスクリプト
"""

import json
import os
import sys
import urllib.error
import re
import datetime

# Windows環境の文字化け・UnicodeEncodeError（Emoji等の出力バグ）対策
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# 同一階層の abc_synthesizer.py をインポートできるように設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    import abc_synthesizer
except ImportError:
    print("エラー: abc_synthesizer.py が同じディレクトリに見つかりません。")
    sys.exit(1)

# Ollama 接続設定
# localhost (127.0.0.1) を優先し、接続に失敗した場合は llm.py 内のホスト設定をフォールバックとして試みます。
DEFAULT_OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
DEFAULT_MODEL = "qwen3.5:9b"

def get_ollama_base_url():
    """
    Ollamaの接続先URLを取得する（localhostがダメなら llm.py から読み込みを試みる）
    """
    # まず localhost で接続テスト
    url = f"http://{DEFAULT_OLLAMA_HOST}:{OLLAMA_PORT}"
    try:
        req = urllib.request.Request(f"{url}/api/tags")
        with urllib.request.urlopen(req, timeout=2) as res:
            return url
    except Exception:
        pass

    # llm.py から OLLAMA_HOST を取得してみる
    try:
        import llm
        url = f"http://{llm.OLLAMA_HOST}:{llm.OLLAMA_PORT}"
        req = urllib.request.Request(f"{url}/api/tags")
        with urllib.request.urlopen(req, timeout=2) as res:
            return url
    except Exception:
        pass

    # どちらもダメな場合は localhost をデフォルトとする
    return f"http://{DEFAULT_OLLAMA_HOST}:{OLLAMA_PORT}"


def get_available_models(base_url):
    """
    Ollamaから利用可能なモデルのリストを取得する
    """
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"[警告] モデルリストの取得に失敗しました: {e}")
        return []


def query_ollama_stream(base_url, model, prompt, system_prompt=None):
    """
    Ollama APIをストリーミングで呼び出し、結果をリアルタイム表示する
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Qwen3.5やlongモデルのコンテキスト制限と出力制限を調整（思考プロセス用にある程度余裕を持たせ4096に設定）
    options = {}
    if "3.5" in model or "long" in model:
        options = {"num_predict": 16384, "num_ctx": 16384}

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "think": False,
    }
    if options:
        payload["options"] = options

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    print(f"\n[AI ({model}) に接続中...]")
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            parts = []
            thinking_started = False
            for line in res:
                chunk = json.loads(line)
                
                # 思考プロセスの表示（グレイスケール/控えめな表記）
                thinking_token = chunk.get("message", {}).get("thinking", "")
                if thinking_token:
                    if not thinking_started:
                        print("\n=== [思考プロセス] ===")
                        thinking_started = True
                    print(thinking_token, end="", flush=True)
                
                # 回答本文の表示
                token = chunk.get("message", {}).get("content", "")
                if token:
                    if thinking_started:
                        print("\n======================\n\n[回答]: ", end="", flush=True)
                        thinking_started = False
                    print(token, end="", flush=True)
                    parts.append(token)
                    
                if chunk.get("done"):
                    break
            print("\n")
            return "".join(parts)
    except Exception as e:
        print(f"\n[エラー] Ollamaとの通信に失敗しました: {e}")
        return ""


def make_composition_prompt(theme, key="C", tempo=120):
    """
    作曲用のプロンプトを作成する
    """
    return f"""あなたはABC記法でメロディを作曲する優秀なAI音楽家です。
以下のテーマに基づいて、美しく、一貫性があり、音楽として成立する短いメロディをABC記法で作曲してください。

【テーマ】: {theme}

【作曲のルール】:
1. ABC記法の標準ヘッダー（X, T, M, L, Q, K）を必ず含めてください。
   - X: 1 (曲番号)
   - T: {theme} (曲のタイトル)
   - M: 4/4 または 3/4 など (拍子)
   - L: 1/8 または 1/16 など (基準音長)
   - Q: {tempo} (テンポ BPM)
   - K: {key} (調号、例: C, G, Am, Em, F, Dm など)
2. 音符は以下の範囲のものをシンプルに使用してください：
   - 中音域: C D E F G A B
   - 高音域: c d e f g a b
   - 低音域: C, D, E, F, G, A, B,
   - シャープ(^), フラット(_), ナチュラル(=)
   - 休符: z
   - 音の長さの倍数（例: C2, C4, C/2, C3/2 など）
   - 小節区切り: |
3. 複雑な複数パート(V:)や、コードシンボル（"C", "G7"など）はパーサーのエラーを防ぐため、今回は出力しないでください。単一のメロディライン（単旋律）のみにしてください。
4. 楽譜ブロックは、必ず ```abc と ``` のマークダウンブロックで囲んで出力してください。
5. 楽譜ブロックの下に、日本語で曲の構成や雰囲気、作曲の意図などの解説を2〜3行で記述してください。
6. ABC記法の仕様解釈やリズムの定義について過剰に長考することは避け、要点だけを思考（thinking）して、迅速に楽譜を出力してください。
7. 単調な音階（スケール）の上昇・下降だけを繰り返すような退屈なメロディは避けてください。
8. 同じ長さの音符（例：8分音符だけ）を並べるのではなく、4分音符、8分音符、休符(z)などを組み合わせて、リズムに変化をつけてください。
9. 音が隣り合う階段状の動きだけでなく、時には音がジャンプする進行（3度や5度、オクターブなどの跳躍進行）を取り入れ、歌うような抑揚のあるメロディにしてください。
10. メロディにフレーズとしてのまとまり（「問いと答え」や「リピートと変化」）を持たせてください。
11. **【音楽理論・コード進行のルール】**:
    - 指定された調（Key={key}）の主要和音（主和音: Tonic [T]、下属和音: Subdominant [S]、属和音: Dominant [D]）を意識してメロディの骨格を作ってください。
    - フレーズをカデンツ進行（T → S → D → T など）のコード進行の流れに沿って構成してください。
    - フレーズの前半（問い）の終わりは属和音（Dominant）の音で緊張感を持たせ、後半（答え）の終わりは主和音（Tonic）的着地（解決）させてください。
    - 各小節の強拍（1拍目、3拍目など）にはコードの構成音（和声音）を主に配置し、その間をスケール音（経過音や刺繍音）で滑らかに繋いでください。

【ABC記法の出力例】:
```abc
X:1
T:Sample Melody
M:4/4
L:1/8
Q:120
K:C
|: E2 G2 c2 d2 | e3 d c4 | d2 B2 G3 A | B2 A2 G4 |
|  E2 G2 c2 d2 | e3 d c4 | d2 B2 G2 AB | c4 c4 :|
```
**解説:**
Cメジャーのトニック（C: ドミソ）から始まり、3〜4小節目でドミナント（G: ソシレ）に向かって緊張する「問い」のフレーズを作り、後半でトニックのC（ド）の主音に力強く解決する「答え」の構造を持たせました。強拍（1拍目・3拍目）にはド・ミ・ソ・シなどの和声音を配置し、8分音符で滑らかに装飾しています。
"""


def save_and_play_abc(abc_text, original_title, file_prefix="qwen_compo"):
    """
    抽出されたABC記法楽譜をファイルに保存し、WAV波形を合成して再生する共通処理
    （出力ファイルは自動作成される output/ ディレクトリ以下に格納されます）
    """
    # outputディレクトリの自動作成
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # タイムスタンプの生成
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存ファイル名の生成
    safe_title = re.sub(r'[\\/*?:"<>| ]', '_', original_title)
    wav_filename = os.path.join(output_dir, f"{file_prefix}_{safe_title}_{timestamp}.wav")
    abc_filename = os.path.join(output_dir, f"{file_prefix}_{safe_title}_{timestamp}.abc")

    # ABC楽譜のテキスト保存
    try:
        with open(abc_filename, "w", encoding="utf-8") as f:
            f.write(abc_text)
        print(f"[システム] 楽譜をテキストとして保存しました: {abc_filename}")
    except Exception as e:
        print(f"[警告] 楽譜テキストの保存に失敗しました: {e}")

    # 合成と再生
    print("\n[システム] WAV波形の合成と自動再生を開始します...")
    try:
        success = abc_synthesizer.play_abc_string(abc_text, wav_filename)
        if success:
            print(f"[システム] 演奏が正常に終了しました。保存されたWAV: {wav_filename}")
        else:
            print("[エラー] 楽譜の解析または合成に失敗しました。")
    except Exception as e:
        print(f"[エラー] 演奏中に例外が発生しました: {e}")

    return abc_filename, wav_filename


def process_composition(base_url, model, theme, key, tempo):
    """
    作曲を実行し、再生と保存を行う
    """
    prompt = make_composition_prompt(theme, key, tempo)
    response = query_ollama_stream(base_url, model, prompt)

    if not response:
        return

    # ABCブロックの抽出
    abc_blocks = abc_synthesizer.extract_abc_blocks(response)
    
    if not abc_blocks:
        print("[エラー] 生成されたテキストからABC記法の楽譜を検出できませんでした。")
        return

    abc_text = abc_blocks[0]
    print("=" * 60)
    print("【抽出されたABC記法楽譜】")
    print(abc_text)
    print("=" * 60)

    # 共通関数を呼び出してファイル保存・演奏を行う
    return save_and_play_abc(abc_text, theme, file_prefix="qwen_compo")


def make_harmony_prompt(melody_abc):
    """
    既存のメロディにハーモニー（和音伴奏）を付与するためのプロンプトを作成する
    """
    return f"""あなたはABC記法でメロディにハーモニー（和音伴奏）を付与する優秀なAI音楽家です。
以下の入力されたメロディ（単旋律）を解析し、そのメロディラインを活かしつつ、美しい和音（コード伴奏）を重ねたABC記法楽譜を作成してください。

【入力されたメロディ】:
```abc
{melody_abc.strip()}
```

【ハーモニー付与のルール】:
1. 元のメロディの音符やリズム、調（Key）を完全に維持してください。
2. ハーモニー（伴奏）は、ABC記法の和音ブロック `[音符1音符2]` を使って表現してください。
   - 例: メロディ音 `c` に対してオクターブ下のベース音 `C,` を重ねる場合、スペースを一切入れずに `[C,c]` のように記述します。
3. **【重要・文法エラーの禁止】**:
   - **ブラケットの入れ子（例: `[C[EG]]`）は絶対にしないでください。**
   - **二重のブラケット（例: `[[C]]`）は絶対に避けてください。**
   - **和音ブロック `[...]` 内の音符数は、メロディ音を含めて「常に2音だけ（メロディ音＋1オクターブ下のベース音の計2音）」に制限してください。** 3声以上の和音は絶対に避けてください。
   - **ブラケットの内部には、半角スペースやカンマなどの区切り文字を絶対に含めないでください。スペースが入ると楽譜の解析でエラーが発生します。** (例: `[C, G, c]` や `[C, C]` はNG。必ず `[C,C]` や `[G,G]` のように詰めて記述してください)。
   - 臨時記号（`^` や `_`）は1音につき1つだけにし、`##` や `^^` などの重複した記号は入れないでください。
4. 複雑な複数パート(V:)や、コードシンボル（"C", "G7"など）はパーサーのエラーを防ぐため、出力しないでください。必ず単一のメロディライン内に和音ブロック `[...]` を埋め込む形式にしてください。
5. **出力する楽譜ブロック（```abc）は、必ず1つだけにしてください。** 修正版や複数のバージョンを出力しないでください。
6. 楽譜ブロックの下に、日本語でどのようなコード進行を付与したか、ハーモニーの意図を2〜3行で記述してください。
7. **【音楽理論・コード進行のルール】**:
   - 入力されたメロディの小節頭や強拍を解析し、その調に適合するコード進行（主和音: Tonic [T]、下属和音: Subdominant [S]、属和音: Dominant [D] などのカデンツ進行）を想定してください。
   - メロディ音（ソプラノ）の下に、1オクターブ下またはそれ以下のルート音（ベース音）を重ねて2音の和音ブロック `[...]` を構成してください。
   - フレーズの終わり（カデンツの終止部）では、属和音（Dominant）から主和音（Tonic）へ解決する進行（例: G7からCへの移行など）を意識したベース音を付与してください。
   - すべての音符に和音を重ねる必要はありません。小節の1拍目や3拍目などの強拍に伴奏音を重ね、弱拍や経過音は元のメロディの単音のままにすると、音楽的なメリハリが生まれます。

【ABC記法でのハーモニー付与例】:
入力:
```abc
X:1
T:Twinkle Twinkle Little Star
M:4/4
L:1/4
Q:120
K:C
C C G G | A A G2 | F F E E | D D C2 |
```
出力:
```abc
X:1
T:Twinkle Twinkle Little Star with Harmony
M:4/4
L:1/4
Q:120
K:C
[C,C] C [G,G] G | [A,A] A [G,2G2] | [F,F] F [C,E] E | [G,D] D [C,2C2] |
```
"""


def process_harmony(base_url, model, melody_abc, original_title="harmony_input"):
    """
    既存のメロディにハーモニーを重ねる処理
    """
    prompt = make_harmony_prompt(melody_abc)
    response = query_ollama_stream(base_url, model, prompt)

    if not response:
        return

    # ABCブロックの抽出
    abc_blocks = abc_synthesizer.extract_abc_blocks(response)
    
    if not abc_blocks:
        print("[エラー] 生成されたテキストからABC記法の楽譜を検出できませんでした。")
        return

    abc_text = abc_blocks[0]
    print("=" * 60)
    print("【抽出されたハーモニー付きABC記法楽譜】")
    print(abc_text)
    print("=" * 60)

    # 共通関数を呼び出してファイル保存・演奏を行う
    return save_and_play_abc(abc_text, original_title, file_prefix="qwen_harmony")


def main():
    print("=" * 60)
    print("   Qwen 3.5 ABC記法 作曲プロトタイプ (PCローカル検証)")
    print("=" * 60)

    base_url = get_ollama_base_url()
    print(f"Ollamaサーバー接続先: {base_url}")

    models = get_available_models(base_url)
    if not models:
        print("[エラー] Ollamaサーバーに接続できないか、モデルが登録されていません。")
        print("Ollamaが起動していること、および 'ollama list' でモデルが表示されることを確認してください。")
        sys.exit(1)

    # Qwenモデルのフィルタリングと選択
    qwen_models = [m for m in models if "qwen" in m.lower()]
    
    selected_model = DEFAULT_MODEL
    # 高速かつ正確にABC記法を出力するため、思考プロセスのない qwen2.5-coder や nothink モデルを最優先に選択します
    coder_models = [m for m in qwen_models if "coder" in m.lower()]
    nothink_models = [m for m in qwen_models if "nothink" in m.lower()]
    
    if coder_models:
        selected_model = coder_models[0]
    elif nothink_models:
        selected_model = nothink_models[0]
    elif qwen_models:
        matched_default = [m for m in qwen_models if DEFAULT_MODEL in m]
        if matched_default:
            selected_model = matched_default[0]
        else:
            selected_model = qwen_models[0]
    else:
        print("[警告] Qwen系のモデルがOllamaに見つかりません。")
        if models:
            selected_model = models[0]
            print(f"代わりに最初のモデル '{selected_model}' を使用します。")
        else:
            sys.exit(1)

    print(f"使用予定のLLMモデル: {selected_model}")
    print("  ※ 思考フェーズのある qwen3.5:9b-long 等はプロンプト処理が非常に重いため、")
    print("    思考フェーズのない qwen2.5-coder や nothink モデルの使用を推奨します。")
    print(f"検出されたすべてのQwenモデル: {', '.join(qwen_models) if qwen_models else 'なし'}")

    presets = [
        {"theme": "明るく楽しい子供向けのマーチ (C Major)", "key": "C", "tempo": 120},
        {"theme": "哀愁漂う雨の日のバイオリンソロ (A Minor)", "key": "Am", "tempo": 80},
        {"theme": "森の妖精が踊る軽快なワルツ (G Major, 3/4拍子)", "key": "G", "tempo": 140},
        {"theme": "荒野を進むカウボーイの力強い唄 (E Minor)", "key": "Em", "tempo": 100},
    ]

    while True:
        print("\n" + "-" * 50)
        print(f"【現在のモデル: {selected_model}】")
        print("メニューを選択してください:")
        for idx, preset in enumerate(presets):
            print(f"  {idx + 1}. プリセット作曲: {preset['theme']}")
        print("  5. 自由なテーマで作曲 (プロンプト入力)")
        print("  6. 使用するLLMモデルを変更する")
        print("  7. 既存のメロディにハーモニー（和音伴奏）を付与する")
        print("  8. 終了")
        print("-" * 50)

        try:
            choice = input("選択 (1-8): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n終了します。")
            break

        if choice in ("1", "2", "3", "4"):
            preset = presets[int(choice) - 1]
            # 3番目の妖精のワルツなら3/4拍子にするため、テーマ情報を調整
            theme = preset["theme"]
            process_composition(base_url, selected_model, theme, preset["key"], preset["tempo"])

        elif choice == "5":
            try:
                theme = input("どのような曲を作りたいですか？ (例: 爽やかな朝の目覚め): ").strip()
                if not theme:
                    print("テーマが空です。キャンセルします。")
                    continue
                key = input("調号を指定してください (デフォルト: C. 他に Am, G, Em, F, Dm など): ").strip()
                if not key:
                    key = "C"
                tempo_str = input("テンポ(BPM)を指定してください (デフォルト: 120): ").strip()
                tempo = 120
                if tempo_str.isdigit():
                    tempo = int(tempo_str)
                process_composition(base_url, selected_model, theme, key, tempo)
            except Exception as e:
                print(f"入力処理エラー: {e}")

        elif choice == "6":
            print("\n利用可能なモデル一覧:")
            for idx, m in enumerate(models):
                print(f"  {idx + 1}. {m}")
            try:
                model_idx = input(f"使用するモデルの番号を選択してください (1-{len(models)}): ").strip()
                if model_idx.isdigit() and 1 <= int(model_idx) <= len(models):
                    selected_model = models[int(model_idx) - 1]
                    print(f"モデルを '{selected_model}' に変更しました。")
                else:
                    print("無効な入力です。")
            except Exception as e:
                print(f"入力処理エラー: {e}")

        elif choice == "7":
            try:
                print("\nメロディの入力方法を選択してください:")
                print("  1. ABC記法のテキストを直接入力する (貼り付け)")
                print("  2. ローカルの .abc ファイルから読み込む")
                method = input("選択 (1-2, デフォルト 1): ").strip()
                
                melody_abc = ""
                original_title = "harmony_result"
                
                if method == "2":
                    filepath = input("読み込む .abc ファイルのパスを入力してください: ").strip()
                    if os.path.exists(filepath):
                        with open(filepath, "r", encoding="utf-8") as f:
                            melody_abc = f.read()
                        original_title = os.path.splitext(os.path.basename(filepath))[0] + "_harmony"
                    else:
                        print(f"[エラー] ファイルが見つかりません: {filepath}")
                        continue
                else:
                    print("\nABC記法の楽譜テキストを入力してください。")
                    print("入力終了時は、空行を連続で入力するか、最後の行のあとに Ctrl+Z + Enter (Windows) / Ctrl+D (Unix) を入力してください。")
                    print("-" * 50)
                    lines = []
                    while True:
                        try:
                            line = input()
                            if line.strip() == "" and len(lines) > 0 and lines[-1].strip() == "":
                                break
                            lines.append(line)
                        except (EOFError, KeyboardInterrupt):
                            break
                    melody_abc = "\n".join(lines)
                    print("-" * 50)
                    
                    title_input = input("曲のタイトル/識別名を入力してください (デフォルト: harmony_input): ").strip()
                    if title_input:
                        original_title = title_input
                
                if melody_abc.strip():
                    process_harmony(base_url, selected_model, melody_abc, original_title)
                else:
                    print("[エラー] メロディテキストが入力されていません。")
            except Exception as e:
                print(f"入力処理エラー: {e}")

        elif choice == "8":
            print("プログラムを終了します。")
            break
        else:
            print("1から8の間で入力してください。")


if __name__ == "__main__":
    main()
