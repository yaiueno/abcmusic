#!/usr/bin/env python3
"""Test qwen3.6-long with Ollama web_search (signed-in local server)."""
import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:11434/api/chat"
SEARCH = "http://localhost:11434/api/web_search"


def chat(messages, tools=None):
    body = {
        "model": "qwen3.6-long",
        "messages": messages,
        "stream": False,
        "think": False,
    }
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        BASE,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def web_search(query, max_results=3):
    body = json.dumps({"query": query, "max_results": max_results}).encode()
    req = urllib.request.Request(
        SEARCH,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main():
    messages = [
        {
            "role": "user",
            "content": (
                "Use web_search to find Ollama's latest version as of June 2026. "
                "Answer in one Japanese sentence."
            ),
        }
    ]
    tools = [{"type": "web_search"}]

    print("=== qwen3.6-long + web_search test ===")
    t0 = time.time()

    for step in range(5):
        r = chat(messages, tools)
        msg = r["message"]
        print(f"\n--- step {step + 1} ({time.time() - t0:.1f}s) ---")

        if msg.get("thinking"):
            print("thinking:", msg["thinking"][:200], "...")

        if msg.get("content"):
            print("content:", msg["content"][:500])

        if not msg.get("tool_calls"):
            print("\n=== DONE ===")
            print("Final:", msg.get("content", ""))
            print(f"Total time: {time.time() - t0:.1f}s")
            return

        print("tool_calls:", json.dumps(msg["tool_calls"], ensure_ascii=False))
        messages.append(msg)

        for tc in msg["tool_calls"]:
            fn = tc["function"]
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args)
            query = args.get("query", "")
            try:
                result = web_search(query, args.get("max_results", 3))
                print("search OK:", json.dumps(result, ensure_ascii=False)[:500], "...")
            except urllib.error.HTTPError as e:
                result = {"error": e.read().decode()[:500]}
                print("search HTTP error:", e.code, result)
            except Exception as e:
                result = {"error": str(e)}
                print("search FAIL:", e)

            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False)[:8000],
                    "tool_name": fn["name"],
                }
            )

    print("max steps reached")


if __name__ == "__main__":
    main()
