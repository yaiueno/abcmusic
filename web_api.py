from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import sys

# 同一ディレクトリの prototype_qwen_composition, abc_synthesizer を読み込めるようにパスを設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import prototype_qwen_composition as compo
import abc_synthesizer

app = FastAPI(title="Qwen Auto Composition API", version="1.0.0")

# CORS設定 (Reactフロントエンドからのリクエストを許可)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 疎結合検証のためワイルドカードに設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 生成ファイルの保存ディレクトリ (静的配信)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 静的ファイルの配信設定 (/output/filename.wav でブラウザからアクセス可能にする)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

class ComposeRequest(BaseModel):
    theme: str
    key: str = "C"
    tempo: int = 120
    model: str = "qwen3.5:9b"

class HarmonizeRequest(BaseModel):
    melody_abc: str
    title: str = "harmony_input"
    model: str = "qwen3.5:9b"

@app.get("/api/models")
def get_models():
    try:
        base_url = compo.get_ollama_base_url()
        models = compo.get_available_models(base_url)
        return {"models": models, "base_url": base_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compose")
def compose(req: ComposeRequest):
    try:
        base_url = compo.get_ollama_base_url()
        # 作曲実行し、出力されたファイルパスを取得
        result = compo.process_composition(base_url, req.model, req.theme, req.key, req.tempo)
        if not result:
            raise HTTPException(status_code=500, detail="自動作曲の生成に失敗しました。")
            
        abc_path, wav_path = result
        
        # クライアントに返却するためのURLを生成 (例: /output/file.wav)
        abc_filename = os.path.basename(abc_path)
        wav_filename = os.path.basename(wav_path)
        
        # ABC楽譜のテキスト内容を読み込む
        with open(abc_path, "r", encoding="utf-8") as f:
            abc_content = f.read()
            
        return {
            "title": req.theme,
            "abc_url": f"/output/{abc_filename}",
            "wav_url": f"/output/{wav_filename}",
            "abc_content": abc_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/harmonize")
def harmonize(req: HarmonizeRequest):
    try:
        base_url = compo.get_ollama_base_url()
        result = compo.process_harmony(base_url, req.model, req.melody_abc, req.title)
        if not result:
            raise HTTPException(status_code=500, detail="ハーモニーの付与に失敗しました。")
            
        abc_path, wav_path = result
        abc_filename = os.path.basename(abc_path)
        wav_filename = os.path.basename(wav_path)
        
        with open(abc_path, "r", encoding="utf-8") as f:
            abc_content = f.read()
            
        return {
            "title": req.title,
            "abc_url": f"/output/{abc_filename}",
            "wav_url": f"/output/{wav_filename}",
            "abc_content": abc_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_api:app", host="127.0.0.1", port=8000, reload=True)
