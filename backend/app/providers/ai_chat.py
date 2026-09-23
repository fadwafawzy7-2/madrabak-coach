"""AiChatProvider abstraction. Business logic never touches a vendor SDK directly.

Implementations:
- GroqChatProvider: calls Groq's OpenAI-compatible API via httpx.
- StubChatProvider: deterministic offline responses (used when GROQ_API_KEY is empty
  and in tests). The interface and configuration path are identical, so activating
  Groq only requires setting the environment variable.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

import httpx

from ..settings import get_settings


@dataclass
class ChatResult:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class AiChatProvider(abc.ABC):
    @abc.abstractmethod
    async def chat(self, system: str, messages: list[dict], max_tokens: int = 800) -> ChatResult:
        """messages: [{'role': 'user'|'assistant', 'content': str}, ...]"""


class GroqChatProvider(AiChatProvider):
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    # provisional cost estimate per 1M tokens (configurable-in-code, used for tracking only)
    COST_PER_M_INPUT = 0.59
    COST_PER_M_OUTPUT = 0.79

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def chat(self, system: str, messages: list[dict], max_tokens: int = 800) -> ChatResult:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, *messages],
            "max_tokens": max_tokens,
            "temperature": 0.6,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.BASE_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        cost = in_tok / 1e6 * self.COST_PER_M_INPUT + out_tok / 1e6 * self.COST_PER_M_OUTPUT
        return ChatResult(
            text=data["choices"][0]["message"]["content"],
            provider="groq",
            model=self._model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=round(cost, 6),
        )


class StubChatProvider(AiChatProvider):
    """Offline deterministic provider. Clearly marked as a stub; replies echo intent
    without inventing nutrition numbers (numbers come from the context we were given)."""

    async def chat(self, system: str, messages: list[dict], max_tokens: int = 800) -> ChatResult:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        text = (
            "[وضع التطوير — لم يتم تفعيل مزوّد الذكاء الاصطناعي بعد]\n"
            "تم استلام رسالتك: «" + last_user[:200] + "»\n"
            "عند تفعيل GROQ_API_KEY سيرد المدرب الذكي هنا بالاعتماد على أرقامك "
            "المحسوبة من محرك التغذية (وليس على تخمينات)."
        )
        return ChatResult(
            text=text, provider="stub", model="stub", input_tokens=0, output_tokens=0, estimated_cost_usd=0.0
        )


def get_chat_provider() -> AiChatProvider:
    s = get_settings()
    if s.groq_api_key:
        return GroqChatProvider(s.groq_api_key, s.groq_model)
    return StubChatProvider()
