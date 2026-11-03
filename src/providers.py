"""Pluggable LLM providers (BYOK). All use plain HTTPS via httpx."""
from typing import Literal, Protocol

import httpx

# Default model ids; confirm against each provider's current docs before release.
PROVIDERS: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "claude": "claude-sonnet-5-5",
    "openai": "gpt-4o-mini",
}

_TIMEOUT = 90.0
_MAX_TOKENS = 8192


class ProviderError(Exception):
    """Provider failure. The message never includes the API key."""

    def __init__(self, message: str, kind: Literal["auth", "rate_limit", "network", "other"]):
        super().__init__(message)
        self.kind = kind


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class _HttpProvider:
    name = ""

    def __init__(self, api_key: str, model: str, transport: httpx.BaseTransport | None = None):
        self._key = api_key
        self.model = model
        self._client = httpx.Client(transport=transport, timeout=_TIMEOUT)

    def _request(self, system: str, user: str) -> tuple[str, dict, dict]:
        raise NotImplementedError

    def _extract(self, data: dict) -> str:
        raise NotImplementedError

    def complete(self, system: str, user: str) -> str:
        url, headers, body = self._request(system, user)
        try:
            resp = self._client.post(url, headers=headers, json=body)
        except httpx.HTTPError:
            raise ProviderError(f"Could not reach {self.name}. Check your connection.", "network") from None
        if resp.status_code in (401, 403):
            raise ProviderError(f"{self.name} rejected the API key (HTTP {resp.status_code}).", "auth")
        if resp.status_code == 429:
            raise ProviderError(f"{self.name} rate limit reached. Wait a moment and try again.", "rate_limit")
        if resp.status_code >= 400:
            raise ProviderError(f"{self.name} returned HTTP {resp.status_code}.", "other")
        try:
            text = self._extract(resp.json())
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError(f"Unexpected response format from {self.name}.", "other") from None
        if not isinstance(text, str):
            raise ProviderError(f"Unexpected response format from {self.name}.", "other")
        return text


class _OpenAICompatible(_HttpProvider):
    base_url = ""

    def _request(self, system, user):
        return (
            f"{self.base_url}/chat/completions",
            {"Authorization": f"Bearer {self._key}"},
            {"model": self.model, "messages": [
                {"role": "system", "content": system}, {"role": "user", "content": user}]},
        )

    def _extract(self, data):
        return data["choices"][0]["message"]["content"]


class OpenAIProvider(_OpenAICompatible):
    name = "OpenAI"
    base_url = "https://api.openai.com/v1"


class GroqProvider(_OpenAICompatible):
    name = "Groq"
    base_url = "https://api.groq.com/openai/v1"


class GeminiProvider(_HttpProvider):
    name = "Gemini"

    def _request(self, system, user):
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": self._key},
            {"systemInstruction": {"parts": [{"text": system}]},
             "contents": [{"role": "user", "parts": [{"text": user}]}]},
        )

    def _extract(self, data):
        return data["candidates"][0]["content"]["parts"][0]["text"]


class ClaudeProvider(_HttpProvider):
    name = "Claude"

    def _request(self, system, user):
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self._key, "anthropic-version": "2023-06-01"},
            {"model": self.model, "max_tokens": _MAX_TOKENS, "system": system,
             "messages": [{"role": "user", "content": user}]},
        )

    def _extract(self, data):
        return data["content"][0]["text"]


_CLASSES = {"gemini": GeminiProvider, "groq": GroqProvider,
            "claude": ClaudeProvider, "openai": OpenAIProvider}


def get_provider(name: str, api_key: str, model: str | None = None,
                 transport: httpx.BaseTransport | None = None) -> LLMProvider:
    if name not in _CLASSES:
        raise ValueError(f"Unknown provider: {name}")
    if not api_key or not api_key.strip():
        raise ValueError("An API key is required.")
    return _CLASSES[name](api_key.strip(), model or PROVIDERS[name], transport)
