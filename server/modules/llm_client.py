#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - OllamaLLMクライアントモジュール

Ollamaとの通信を一元管理するクラスを提供します。
このモジュールを通じてLLMと通信することで、接続先やモデルの変更を
config.py の修正だけで全体に反映できます。
"""

import json
import urllib.error
import urllib.request
from typing import Generator, Optional

# 上位ディレクトリの config を読み込む
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    get_ollama_base_url,
    get_model_options,
    DEFAULT_MODEL,
    STREAM_TIMEOUT,
)


class OllamaClient:
    """
    Ollama APIとの通信を担当するクライアントクラス。

    使い方:
        client = OllamaClient()
        models = client.list_models()
        for token in client.chat_stream("qwen3.5:9b", messages):
            print(token, end="", flush=True)
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or get_ollama_base_url()

    # ------------------------------------------------------------------
    # 接続確認
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Ollamaサーバーが応答するか確認する"""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """利用可能なモデル名のリストを取得する"""
        req = urllib.request.Request(f"{self.base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read())
            return [m["name"] for m in data.get("models", [])]

    # ------------------------------------------------------------------
    # チャット（ストリーミング）
    # ------------------------------------------------------------------
    def chat_stream(
        self,
        model: str,
        messages: list[dict],
        think: bool = False,
        options: Optional[dict] = None,
    ) -> Generator[str, None, None]:
        """
        Ollamaのチャットエンドポイントをストリーミングで呼び出し、
        生成されたトークンをgeneratorとして返す。

        Args:
            model:    使用するモデル名
            messages: [{"role": "user"/"assistant"/"system", "content": "..."}]
            think:    思考プロセスを有効にするか (True にすると遅くなる)
            options:  Ollamaへのオプション (num_ctx, num_predict など)

        Yields:
            str: 生成されたトークン（content の断片）
        """
        merged_options = get_model_options(model)
        if options:
            merged_options.update(options)

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": think,
        }
        if merged_options:
            payload["options"] = merged_options

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=STREAM_TIMEOUT) as res:
            for line in res:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break

    # ------------------------------------------------------------------
    # チャット（一括取得: Web API向け）
    # ------------------------------------------------------------------
    def chat(
        self,
        model: str,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        think: bool = False,
        options: Optional[dict] = None,
    ) -> str:
        """
        ストリーミングで全トークンを収集し、完全な回答文字列を返す。
        サーバー上でLLMを呼び出す際（WebAPI経由）に使用する。

        Args:
            model:         使用するモデル名
            messages:      会話履歴
            system_prompt: システムプロンプト（Noneなら付与しない）
            think:         思考プロセスを有効にするか
            options:       Ollamaオプション

        Returns:
            str: LLMが生成した完全な回答テキスト
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        parts = []
        for token in self.chat_stream(model, full_messages, think=think, options=options):
            parts.append(token)

        return "".join(parts)

    # ------------------------------------------------------------------
    # 単一プロンプト呼び出し（便利メソッド）
    # ------------------------------------------------------------------
    def prompt(
        self,
        model: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        think: bool = False,
        options: Optional[dict] = None,
    ) -> str:
        """
        単一のユーザーメッセージを送信して回答を得る便利メソッド。

        Args:
            model:         使用するモデル名
            user_message:  ユーザーの入力テキスト
            system_prompt: システムプロンプト
            think:         思考プロセスを有効にするか
            options:       Ollamaオプション

        Returns:
            str: LLMの回答テキスト
        """
        messages = [{"role": "user", "content": user_message}]
        return self.chat(model, messages, system_prompt=system_prompt, think=think, options=options)


# ------------------------------------------------------------------
# モジュールレベルのデフォルトインスタンス（シングルトン的に使用可能）
# ------------------------------------------------------------------
_default_client: Optional[OllamaClient] = None


def get_client() -> OllamaClient:
    """デフォルトのOllamaClientインスタンスを返す（初回のみ生成）"""
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient()
    return _default_client
