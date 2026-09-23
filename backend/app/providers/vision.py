"""VisionProvider abstraction for food-photo analysis.

- GeminiVisionProvider: calls the Gemini REST API (no SDK dependency).
- StubVisionProvider: offline deterministic detection used when GEMINI_API_KEY is
  empty and in tests.

The provider only DETECTS foods and rough quantity estimates. Nutritional values
always come from the Food Database afterwards — never from the vision model.
"""
from __future__ import annotations

import abc
import base64
import json
import re
from dataclasses import dataclass, field

import httpx

from ..settings import get_settings


@dataclass
class DetectedFood:
    name: str
    estimated_grams: float
    confidence: str = "estimated"  # always an estimate from a photo


@dataclass
class VisionResult:
    foods: list[DetectedFood] = field(default_factory=list)
    provider: str = "stub"
    model: str = "stub"
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class VisionProvider(abc.ABC):
    @abc.abstractmethod
    async def detect_foods(self, image_bytes: bytes, mime_type: str, language: str) -> VisionResult: ...


_PROMPT = (
    "You are a food recognition assistant. Look at the photo and list the foods you can see. "
    "For each food give a rough quantity estimate in grams. Quantities from photos are always "
    "approximate — never claim precision. Respond ONLY with JSON: "
    '{"foods": [{"name": "...", "estimated_grams": 150}]}. '
    "Use food names in language: {lang}. If you cannot identify food, return {\"foods\": []}."
)


class GeminiVisionProvider(VisionProvider):
    COST_PER_M_INPUT = 0.10
    COST_PER_M_OUTPUT = 0.40

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def detect_foods(self, image_bytes: bytes, mime_type: str, language: str) -> VisionResult:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        payload = {
            "contents": [{
                "parts": [
                    {"text": _PROMPT.replace("{lang}", language)},
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}},
                ]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500},
        }
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(url, json=payload, headers={"x-goog-api-key": self._api_key})
            resp.raise_for_status()
            data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        in_tok = usage.get("promptTokenCount", 0)
        out_tok = usage.get("candidatesTokenCount", 0)
        foods = _parse_foods_json(text)
        return VisionResult(
            foods=foods,
            provider="gemini",
            model=self._model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=round(in_tok / 1e6 * self.COST_PER_M_INPUT + out_tok / 1e6 * self.COST_PER_M_OUTPUT, 6),
        )


def _parse_foods_json(text: str) -> list[DetectedFood]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    foods = []
    for f in data.get("foods", []):
        name = str(f.get("name", "")).strip()
        grams = f.get("estimated_grams", 0)
        try:
            grams = float(grams)
        except (TypeError, ValueError):
            continue
        if name and 0 < grams <= 5000:
            foods.append(DetectedFood(name=name, estimated_grams=grams))
    return foods


class StubVisionProvider(VisionProvider):
    """Deterministic offline detection for development/tests."""

    async def detect_foods(self, image_bytes: bytes, mime_type: str, language: str) -> VisionResult:
        if not image_bytes:
            return VisionResult(foods=[])
        names = {"ar": ["أرز أبيض مطبوخ", "صدر دجاج مشوي"], "he": ["אורז לבן מבושל", "חזה עוף"],
                 "en": ["cooked white rice", "grilled chicken breast"]}
        picked = names.get(language, names["en"])
        return VisionResult(foods=[
            DetectedFood(name=picked[0], estimated_grams=200.0),
            DetectedFood(name=picked[1], estimated_grams=150.0),
        ])


def get_vision_provider() -> VisionProvider:
    s = get_settings()
    if s.gemini_api_key:
        return GeminiVisionProvider(s.gemini_api_key, s.gemini_vision_model)
    return StubVisionProvider()
