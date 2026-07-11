from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import anthropic
import httpx
import openai
from dotenv import load_dotenv
from google.genai import errors as google_errors

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "models.json"
VALID = {"kamen", "nuzky", "papir"}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.providers import anthropic_provider, google_provider, openai_provider, xai_provider
SAMPLE_HISTORY = (
    "Tournament #1\n\n"
    "Round 1\n"
    "You selected Rock.\n"
    "Sam selected Scissors.\n"
    "Sam was eliminated.\n"
    "Champion: You 🏆\n\n"
    "Tournament #2\n\n"
    "Round 1\n"
    "You selected Paper.\n"
    "Claude selected Rock.\n"
    "2 players remain."
)


def _load_models() -> dict[str, dict[str, str]]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@contextmanager
def _patch_attr(module: object, name: str, replacement: object):
    original = getattr(module, name)
    setattr(module, name, replacement)
    try:
        yield
    finally:
        setattr(module, name, original)


def _rate_limit_error_for_openai() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429, request=request)
    return openai.RateLimitError("rate limit", response=response, body=None)


def _rate_limit_error_for_anthropic() -> anthropic.RateLimitError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(429, request=request)
    return anthropic.RateLimitError("rate limit", response=response, body=None)


def test_success_paths(models: dict[str, dict[str, str]]) -> bool:
    checks = [
        ("sam", openai_provider.get_move),
        ("claude", anthropic_provider.get_move),
        ("elon", xai_provider.get_move),
        ("sergey", google_provider.get_move),
    ]

    ok = True
    print("Provider success-path checks")
    for player_id, fn in checks:
        model = models[player_id]["model"]
        choice = fn(model, SAMPLE_HISTORY)
        passed = choice in VALID
        print(f"[{'OK' if passed else 'FAIL'}] {player_id}: choice={choice}")
        ok = ok and passed
    return ok


def test_rate_limit_fallbacks(models: dict[str, dict[str, str]]) -> bool:
    print("Provider forced rate-limit fallback checks")
    ok = True

    class FailingOpenAIResponsesClient:
        def __init__(self, *args, **kwargs):
            self.responses = self

        def create(self, *args, **kwargs):
            raise _rate_limit_error_for_openai()

    with _patch_attr(openai_provider, "OpenAI", FailingOpenAIResponsesClient):
        choice = openai_provider.get_move(models["sam"]["model"], SAMPLE_HISTORY)
        passed = choice in VALID
        print(f"[{'OK' if passed else 'FAIL'}] sam fallback choice={choice}")
        ok = ok and passed

    class FailingAnthropicMessages:
        def create(self, *args, **kwargs):
            raise _rate_limit_error_for_anthropic()

    class FailingAnthropicClient:
        def __init__(self, *args, **kwargs):
            self.messages = FailingAnthropicMessages()

    with _patch_attr(anthropic_provider, "Anthropic", FailingAnthropicClient):
        choice = anthropic_provider.get_move(models["claude"]["model"], SAMPLE_HISTORY)
        passed = choice in VALID
        print(f"[{'OK' if passed else 'FAIL'}] claude fallback choice={choice}")
        ok = ok and passed

    class _FailingChatCompletions:
        def create(self, *args, **kwargs):
            raise _rate_limit_error_for_openai()

    class _FailingChat:
        def __init__(self):
            self.completions = _FailingChatCompletions()

    class FailingXAIClient:
        def __init__(self, *args, **kwargs):
            self.chat = _FailingChat()

    with _patch_attr(xai_provider, "OpenAI", FailingXAIClient):
        choice = xai_provider.get_move(models["elon"]["model"], SAMPLE_HISTORY)
        passed = choice in VALID
        print(f"[{'OK' if passed else 'FAIL'}] elon fallback choice={choice}")
        ok = ok and passed

    class FailingGoogleModels:
        def generate_content(self, *args, **kwargs):
            raise google_errors.ClientError(429, {"error": "rate limit"})

    class FailingGoogleClient:
        def __init__(self, *args, **kwargs):
            self.models = FailingGoogleModels()

    with _patch_attr(google_provider.genai, "Client", FailingGoogleClient):
        choice = google_provider.get_move(models["sergey"]["model"], SAMPLE_HISTORY)
        passed = choice in VALID
        print(f"[{'OK' if passed else 'FAIL'}] sergey fallback choice={choice}")
        ok = ok and passed

    return ok


def main() -> int:
    load_dotenv(ROOT / ".env")

    required_env = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY", "GEMINI_API_KEY"]
    missing = [key for key in required_env if not os.getenv(key)]
    if missing:
        print(f"Missing required env keys: {', '.join(missing)}")
        return 1

    models = _load_models()
    success_ok = test_success_paths(models)
    fallback_ok = test_rate_limit_fallbacks(models)

    return 0 if (success_ok and fallback_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
