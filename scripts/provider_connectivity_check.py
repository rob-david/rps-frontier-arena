from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROMPT = "What is 2+2? Reply with just the number."
ROOT_DIR = Path(__file__).resolve().parents[1]
MODELS_FILE = ROOT_DIR / "config" / "models.json"


def _load_models() -> dict:
    with MODELS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _check_openai(model: str) -> tuple[bool, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False, "OPENAI_API_KEY is missing"

    headers = {"Authorization": f"Bearer {api_key}"}
    candidates = [model, "gpt-4o-mini", "gpt-4.1-mini"]

    with httpx.Client(timeout=15.0) as client:
        last_error = ""
        for current_model in candidates:
            payload = {
                "model": current_model,
                "input": PROMPT,
                "max_output_tokens": 16,
            }
            response = client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
            if response.status_code >= 400:
                last_error = f"{response.status_code}: {response.text[:200]}"
                continue

            data = response.json()
            text = (data.get("output_text") or "").strip()
            if not text:
                chunks: list[str] = []
                for item in data.get("output", []):
                    for content in item.get("content", []):
                        if content.get("type") in {"output_text", "text"}:
                            value = (content.get("text") or "").strip()
                            if value:
                                chunks.append(value)
                text = "\n".join(chunks).strip()
            if text:
                return True, f"model={current_model}, response='{text}'"
            last_error = f"model={current_model}: empty response text"

    return False, last_error or "request failed"


def _check_anthropic(model: str) -> tuple[bool, str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "ANTHROPIC_API_KEY is missing"

    payload = {
        "model": model,
        "max_tokens": 8,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": PROMPT}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data.get("content", [])
        text_block = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
    text_block = text_block.strip()
    if not text_block:
        return False, "empty response text"
    return True, f"response='{text_block}'"


def _check_xai(model: str) -> tuple[bool, str]:
    api_key = os.getenv("GROK_API_KEY")
    if not api_key:
        return False, "GROK_API_KEY is missing"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 8,
        "reasoning_effort": "none",
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=15.0) as client:
        response = client.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not text:
        return False, "empty response text"
    return True, f"response='{text}'"


def _check_google(model: str) -> tuple[bool, str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return False, "GEMINI_API_KEY is missing"

    versions = ["v1", "v1beta"]
    params = {"key": api_key}
    payload = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {"maxOutputTokens": 16},
    }

    with httpx.Client(timeout=15.0) as client:
        last_error = ""
        for version in versions:
            discovered_models: list[str] = []
            list_url = f"https://generativelanguage.googleapis.com/{version}/models"
            list_response = client.get(list_url, params=params)
            if list_response.status_code < 400:
                list_data = list_response.json()
                for item in list_data.get("models", []):
                    methods = item.get("supportedGenerationMethods", [])
                    name = (item.get("name") or "").replace("models/", "")
                    if "generateContent" in methods and name:
                        discovered_models.append(name)

            candidates = [model, *discovered_models, "gemini-2.5-flash", "gemini-2.0-flash"]
            seen = set()
            deduped = []
            for current_model in candidates:
                if current_model and current_model not in seen:
                    deduped.append(current_model)
                    seen.add(current_model)

            for current_model in deduped:
                url = f"https://generativelanguage.googleapis.com/{version}/models/{current_model}:generateContent"
                response = client.post(url, params=params, json=payload)
                if response.status_code >= 400:
                    last_error = f"{response.status_code}: {response.text[:200]}"
                    continue

                data = response.json()
                text = ""
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        value = (part.get("text") or "").strip()
                        if value:
                            text = value
                            break
                    if text:
                        break
                if text:
                    return True, f"model={current_model}, version={version}, response='{text}'"
                last_error = f"model={current_model}, version={version}: empty response text"

    return False, last_error or "request failed"


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    models = _load_models()

    checks = [
        ("sam", "openai", _check_openai, models["sam"]["model"]),
        ("claude", "anthropic", _check_anthropic, models["claude"]["model"]),
        ("elon", "xai", _check_xai, models["elon"]["model"]),
        ("sergey", "google", _check_google, models["sergey"]["model"]),
    ]

    failed = False
    print("Provider connectivity check")
    for player_id, provider, checker, model in checks:
        try:
            ok, detail = checker(model)
            status = "OK" if ok else "FAIL"
            print(f"[{status}] {player_id} ({provider}, model={model}) -> {detail}")
            failed = failed or (not ok)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {player_id} ({provider}, model={model}) -> {exc}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
