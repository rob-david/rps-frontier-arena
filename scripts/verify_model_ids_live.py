from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "models.json"


def _load_models() -> dict[str, dict[str, str]]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_openai(model: str) -> tuple[bool, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False, "OPENAI_API_KEY missing"
    client = OpenAI(api_key=api_key, timeout=8.0, max_retries=0)
    result = client.models.retrieve(model)
    return True, f"resolved id={result.id}"


def verify_anthropic(model: str) -> tuple[bool, str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "ANTHROPIC_API_KEY missing"
    client = Anthropic(api_key=api_key, timeout=8.0, max_retries=0)
    result = client.models.retrieve(model)
    return True, f"resolved id={result.id}"


def verify_xai(model: str) -> tuple[bool, str]:
    api_key = os.getenv("GROK_API_KEY")
    if not api_key:
        return False, "GROK_API_KEY missing"
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=8.0, max_retries=0)
    result = client.models.retrieve(model)
    return True, f"resolved id={result.id}"


def verify_google(model: str) -> tuple[bool, str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return False, "GEMINI_API_KEY missing"

    client = genai.Client(api_key=api_key)
    candidates = [model, f"models/{model}"]
    last_error = ""
    for candidate in candidates:
        try:
            result = client.models.get(model=candidate)
            return True, f"resolved name={result.name}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
    return False, last_error or "model lookup failed"


def main() -> int:
    load_dotenv(ROOT / ".env")
    models = _load_models()

    checks = [
        ("sam", "openai", verify_openai),
        ("claude", "anthropic", verify_anthropic),
        ("elon", "xai", verify_xai),
        ("sergey", "google", verify_google),
    ]

    has_failure = False
    print("Live model ID verification")
    for player_id, provider, verifier in checks:
        model = models[player_id]["model"]
        try:
            ok, detail = verifier(model)
        except Exception as exc:  # noqa: BLE001
            ok = False
            detail = str(exc)

        status = "OK" if ok else "FAIL"
        print(f"[{status}] {player_id} ({provider}) model={model} -> {detail}")
        has_failure = has_failure or (not ok)

    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
