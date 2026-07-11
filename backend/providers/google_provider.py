import logging
import os

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from backend.providers.common import build_prompt, normalize_choice, random_choice

LOGGER = logging.getLogger(__name__)


def _extract_text(response: object) -> str:
    text = (getattr(response, "text", "") or "").strip()
    if text:
        return text

    chunks: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            value = (getattr(part, "text", "") or "").strip()
            if value:
                chunks.append(value)
    return "\n".join(chunks).strip()


def get_move(model: str, history: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        LOGGER.warning("GEMINI_API_KEY is missing. Falling back to random choice.")
        return random_choice()

    prompt = build_prompt(history)

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(clientArgs={"timeout": 8.0}),
        )
        configs = [
            types.GenerateContentConfig(
                maxOutputTokens=256,
                responseMimeType="text/plain",
                thinkingConfig=types.ThinkingConfig(
                    includeThoughts=False,
                    thinkingLevel=types.ThinkingLevel.MINIMAL,
                ),
            ),
            types.GenerateContentConfig(
                maxOutputTokens=256,
                responseMimeType="text/plain",
                thinkingConfig=types.ThinkingConfig(
                    includeThoughts=False,
                    thinkingLevel=types.ThinkingLevel.LOW,
                ),
            ),
            types.GenerateContentConfig(
                maxOutputTokens=256,
                responseMimeType="text/plain",
            ),
        ]

        last_raw_choice = ""
        for config in configs:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
            except genai_errors.ClientError as exc:
                message = str(exc)
                if exc.code == 400 and "Thinking level" in message and "not supported" in message:
                    continue
                raise

            raw_choice = _extract_text(response)
            parsed = normalize_choice(raw_choice)
            if parsed:
                return parsed
            last_raw_choice = raw_choice

        LOGGER.warning(
            "Google returned unparseable move after all thinking attempts: %r. Falling back to random choice.",
            last_raw_choice,
        )
        return random_choice()
    except genai_errors.ClientError as exc:
        if getattr(exc, "code", None) == 429:
            LOGGER.warning("Google rate-limit/quota error. Falling back to random choice: %s", exc)
        else:
            LOGGER.warning("Google client error. Falling back to random choice: %s", exc)
    except genai_errors.ServerError as exc:
        LOGGER.warning("Google server error. Falling back to random choice: %s", exc)
    except TimeoutError as exc:
        LOGGER.warning("Google timeout. Falling back to random choice: %s", exc)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Unexpected Google provider error. Falling back to random choice: %s", exc)

    return random_choice()
