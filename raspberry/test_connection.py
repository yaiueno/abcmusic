#!/usr/bin/env python3
"""PC上のOllamaサーバーへの接続テスト"""

import json
import os
import sys
import urllib.request

OLLAMA_HOST = "10.98.145.83"
OLLAMA_PORT = 11434

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    from config import OLLAMA_HOST, OLLAMA_PORT
except ImportError:
    pass

url = "http://{}:{}/api/tags".format(OLLAMA_HOST, OLLAMA_PORT)
print("接続先: {}".format(url))

try:
    with urllib.request.urlopen(url, timeout=5) as res:
        data = json.loads(res.read())
        models = [m["name"] for m in data.get("models", [])]
        print("接続成功!")
        print("利用可能モデル ({}個):".format(len(models)))
        for name in models:
            print("  - {}".format(name))
except Exception as e:
    print("接続失敗: {}".format(e))
    print("PCのIPアドレス・Ollama起動・同一LAN接続を確認してください")
