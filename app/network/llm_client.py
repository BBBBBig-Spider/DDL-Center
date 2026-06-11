"""Minimal OpenAI-compatible chat client used for DeepSeek integration."""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import requests

from app.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, AI_REQUEST_TIMEOUT
from app.network.network_errors import ConnectionError, ParseError


class LLMClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEEPSEEK_BASE_URL,
        model: str = DEEPSEEK_MODEL,
        timeout: int = AI_REQUEST_TIMEOUT,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key cannot be empty")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict],
        *,
        stream: bool = False,
        max_tokens: int = 2048,
    ) -> tuple[str, int]:
        if stream:
            text = "".join(self.chat_stream(messages, max_tokens=max_tokens))
            return text, self._estimate_tokens(messages, text)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ConnectionError(f"LLM request failed: {exc}") from exc

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ParseError("LLM response is not OpenAI-compatible JSON") from exc

        usage = data.get("usage") or {}
        tokens = usage.get("total_tokens")
        if not isinstance(tokens, int):
            tokens = self._estimate_tokens(messages, content)
        return content, tokens

    def chat_stream(self, messages: list[dict], *, max_tokens: int = 2048) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
        }
        try:
            with requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
                stream=True,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    chunk = line.removeprefix("data: ").strip()
                    if chunk == "[DONE]":
                        break
                    piece = self._parse_stream_chunk(chunk)
                    if piece:
                        yield piece
        except requests.RequestException as exc:
            raise ConnectionError(f"LLM stream request failed: {exc}") from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _parse_stream_chunk(chunk: str) -> str:
        try:
            data: dict[str, Any] = json.loads(chunk)
            return data["choices"][0].get("delta", {}).get("content", "")
        except (ValueError, KeyError, IndexError, TypeError):
            return ""

    @staticmethod
    def _estimate_tokens(messages: list[dict], response: str = "") -> int:
        text = response + "".join(str(msg.get("content", "")) for msg in messages)
        return max(1, len(text) // 4)
