import logging
import os

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)

from backend.providers.common import build_prompt, normalize_choice, random_choice

LOGGER = logging.getLogger(__name__)


def _extract_text(response: object) -> str:
    output_text = (getattr(response, "output_text", "") or "").strip()
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            content_type = getattr(content, "type", "")
            if content_type in {"output_text", "text"}:
                value = (getattr(content, "text", "") or "").strip()
                if value:
                    chunks.append(value)

    return "\n".join(chunks).strip()


def get_move(model: str, history: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        LOGGER.warning("OPENAI_API_KEY is missing. Falling back to random choice.")
        return random_choice()

    prompt = build_prompt(history)

    try:
        client = OpenAI(api_key=api_key, timeout=8.0, max_retries=0)
        response = client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=32,
            reasoning={"effort": "none"},
        )

        raw_choice = _extract_text(response)
        parsed = normalize_choice(raw_choice)
        if parsed:
            return parsed

        LOGGER.warning("OpenAI returned unparseable move: %r. Falling back to random choice.", raw_choice)
        return random_choice()
    except RateLimitError as exc:
        LOGGER.warning("OpenAI rate-limit/quota error. Falling back to random choice: %s", exc)
    except (APITimeoutError, APIConnectionError, APIStatusError, BadRequestError) as exc:
        LOGGER.warning("OpenAI request failed. Falling back to random choice: %s", exc)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Unexpected OpenAI provider error. Falling back to random choice: %s", exc)

    return random_choice()
