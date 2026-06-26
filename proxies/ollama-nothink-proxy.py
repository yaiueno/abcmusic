#!/usr/bin/env python3
"""Ollama proxy: inject think=false for Cline / OpenAI-compat clients."""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UPSTREAM = os.environ.get("OLLAMA_UPSTREAM", "http://127.0.0.1:11434")
LISTEN_HOST = os.environ.get("OLLAMA_PROXY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("OLLAMA_PROXY_PORT", "11435"))


def inject_nothink(body: bytes, path: str) -> bytes:
    if not body or "/api/chat" not in path and "/api/generate" not in path:
        return body
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body
    if isinstance(data, dict):
        data["think"] = False
        return json.dumps(data, ensure_ascii=False).encode("utf-8")
    return body


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[ollama-nothink-proxy] " + (fmt % args) + "\n")

    def _forward(self, method: str) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        body = inject_nothink(body, self.path)

        headers = {}
        for key in ("Content-Type", "Authorization"):
            if self.headers.get(key):
                headers[key] = self.headers.get(key)

        req = Request(
            UPSTREAM + self.path,
            data=body if method != "GET" else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(req, timeout=600) as resp:
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    lk = key.lower()
                    if lk in ("transfer-encoding", "connection"):
                        continue
                    self.send_header(key, value)
                self.end_headers()
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except HTTPError as e:
            payload = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "text/plain"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except URLError as e:
            msg = f"upstream error: {e.reason}".encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self) -> None:
        self._forward("GET")

    def do_POST(self) -> None:
        self._forward("POST")

    def do_DELETE(self) -> None:
        self._forward("DELETE")


def main() -> None:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print(f"Ollama no-think proxy: http://{LISTEN_HOST}:{LISTEN_PORT} -> {UPSTREAM}", flush=True)
    print("Cline: API Provider=Ollama, Base URL=http://localhost:11435", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    main()
