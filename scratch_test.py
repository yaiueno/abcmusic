import urllib.request
import json
import sys

url = "http://127.0.0.1:8000/api/compose"
data = {
    "theme": "テスト用の短いマーチ",
    "key": "C",
    "tempo": 120,
    "model": "qwen2.5-coder:1.5b"
}

body = json.dumps(data).encode("utf-8")
req = urllib.request.Request(
    url,
    data=body,
    headers={"Content-Type": "application/json"}
)

print("Sending request to FastAPI compose API...")
try:
    with urllib.request.urlopen(req, timeout=120) as res:
        response_data = json.loads(res.read())
        print("\n--- Response ---")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error occurred: {e}")
    if hasattr(e, "read"):
        print(e.read().decode("utf-8"))
