#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ラズパイ用 ローカルLLMクライアント（この1ファイルだけで動く）
使い方:
  python3 llm.py test       # 接続テスト
  python3 llm.py chat       # チャット
  python3 llm.py chat qwen2.5-coder:7b
"""

import json
import sys
import urllib.error
import urllib.request

# ===== 設定（PCのIPをここで変更） =====
OLLAMA_HOST = "10.98.145.83"
OLLAMA_PORT = 11434
DEFAULT_MODEL = "qwen3.5:9b"
# =====================================

BASE_URL = "http://{}:{}".format(OLLAMA_HOST, OLLAMA_PORT)


def api_get(path):
    req = urllib.request.Request(BASE_URL + path)
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read())


def api_post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req, timeout=600)


def cmd_test():
    print("接続先: {}".format(BASE_URL))
    try:
        data = api_get("/api/tags")
        models = [m["name"] for m in data.get("models", [])]
        print("接続成功！")
        print("利用可能モデル ({}個):".format(len(models)))
        for name in models:
            print("  - {}".format(name))
        return 0
    except Exception as e:
        print("接続失敗: {}".format(e))
        print("")
        print("確認すること:")
        print("  1. PCが起動していて Ollama が動いている")
        print("  2. ラズパイとPCが同じWi-Fi")
        print("  3. llm.py の OLLAMA_HOST = \"{}\"".format(OLLAMA_HOST))
        return 1


def main():
    if len(sys.argv) < 2:
        print("使い方:")
        print("  python3 llm.py test")
        return 1

    cmd = sys.argv[1].lower()

    if cmd == "test":
        return cmd_test()
    if cmd == "chat":
        print("エラー: ラズパイのCLI経由のチャットアクセスは廃止されました。")
        print("Web UI（ブラウザ経由）からチャット機能をご利用ください。")
        return 1

    print("不明なコマンド: {}".format(sys.argv[1]))
    print("test を指定してください")
    return 1


if __name__ == "__main__":
    sys.exit(main())
