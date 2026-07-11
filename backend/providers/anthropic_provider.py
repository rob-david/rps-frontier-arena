import logging
import os

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Anthropic,
    BadRequestError,
    RateLimitError,
)

from backend.providers.common import build_prompt, normalize_choice, random_choice

LOGGER = logging.getLogger(__name__)


def _extract_text(response: object) -> str:
    chunks: list[str] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", "") == "text":
            value = (getattr(block, "text", "") or "").strip()
            if value:
                chunks.append(value)
    return "\n".join(chunks).strip()


def get_move(model: str, history: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        LOGGER.warning("ANTHROPIC_API_KEY is missing. Falling back to random choice.")
        return random_choice()

    prompt = build_prompt(history)

    try:
        client = Anthropic(api_key=api_key, timeout=8.0, max_retries=0)
        response = client.messages.create(
            model=model,
            max_tokens=32,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )

        raw_choice = _extract_text(response)
        parsed = normalize_choice(raw_choice)
        if parsed:
            return parsed

        LOGGER.warning("Anthropic returned unparseable move: %r. Falling back to random choice.", raw_choice)
        return random_choice()
    except RateLimitError as exc:
        LOGGER.warning("Anthropic rate-limit/quota error. Falling back to random choice: %s", exc)
    except (APITimeoutError, APIConnectionError, APIStatusError, BadRequestError) as exc:
        LOGGER.warning("Anthropic request failed. Falling back to random choice: %s", exc)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Unexpected Anthropic provider error. Falling back to random choice: %s", exc)

    return random_choice()
