import httpx
import pytest

from src.providers import PROVIDERS, ProviderError, get_provider

KEY = "sk-SECRET-123"

OK_BODIES = {
    "openai": {"choices": [{"message": {"content": "hello"}}]},
    "groq": {"choices": [{"message": {"content": "hello"}}]},
    "gemini": {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]},
    "claude": {"content": [{"type": "text", "text": "hello"}]},
}


def transport(status=200, body=None, error=None, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if error:
            raise error
        return httpx.Response(status, json=body or {})
    return httpx.MockTransport(handler)


@pytest.mark.parametrize("name", list(OK_BODIES))
def test_success_returns_text(name):
    p = get_provider(name, KEY, transport=transport(200, OK_BODIES[name]))
    assert p.complete("sys", "usr") == "hello"


@pytest.mark.parametrize("name", list(OK_BODIES))
def test_request_carries_system_and_user_text(name):
    seen = []
    p = get_provider(name, KEY, transport=transport(200, OK_BODIES[name], seen=seen))
    p.complete("SYSTEXT", "USERTEXT")
    body = seen[0].content.decode()
    assert "SYSTEXT" in body and "USERTEXT" in body


@pytest.mark.parametrize("name", list(OK_BODIES))
@pytest.mark.parametrize("status,kind", [(401, "auth"), (403, "auth"), (429, "rate_limit"), (500, "other")])
def test_http_errors_map_to_kinds(name, status, kind):
    p = get_provider(name, KEY, transport=transport(status, {"error": {"message": KEY}}))
    with pytest.raises(ProviderError) as exc:
        p.complete("s", "u")
    assert exc.value.kind == kind
    assert KEY not in str(exc.value)


@pytest.mark.parametrize("name", list(OK_BODIES))
def test_network_error(name):
    p = get_provider(name, KEY, transport=transport(error=httpx.ConnectError(f"boom {KEY}")))
    with pytest.raises(ProviderError) as exc:
        p.complete("s", "u")
    assert exc.value.kind == "network"
    assert KEY not in str(exc.value)


@pytest.mark.parametrize("name", list(OK_BODIES))
def test_malformed_success_body_is_provider_error(name):
    p = get_provider(name, KEY, transport=transport(200, {"unexpected": True}))
    with pytest.raises(ProviderError) as exc:
        p.complete("s", "u")
    assert exc.value.kind == "other"


def test_unknown_provider_and_empty_key():
    with pytest.raises(ValueError):
        get_provider("nope", "k")
    with pytest.raises(ValueError):
        get_provider("groq", "")


def test_default_models_defined():
    assert set(PROVIDERS) == {"gemini", "groq", "claude", "openai"}
