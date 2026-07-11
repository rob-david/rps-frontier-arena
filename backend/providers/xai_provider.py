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


def get_move(model: str, history: str) -> str:
    api_key = os.getenv("GROK_API_KEY")
    if not api_key:
        LOGGER.warning("GROK_API_KEY is missing. Falling back to random choice.")
        return random_choice()

    prompt = build_prompt(history)

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=8.0, max_retries=0)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=32,
            reasoning_effort="none",
        )

        raw_choice = (response.choices[0].message.content or "").strip()
        parsed = normalize_choice(raw_choice)
        if parsed:
            return parsed

        LOGGER.warning("xAI returned unparseable move: %r. Falling back to random choice.", raw_choice)
        return random_choice()
    except RateLimitError as exc:
        LOGGER.warning("xAI rate-limit/quota error. Falling back to random choice: %s", exc)
    except (APITimeoutError, APIConnectionError, APIStatusError, BadRequestError) as exc:
        LOGGER.warning("xAI request failed. Falling back to random choice: %s", exc)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Unexpected xAI provider error. Falling back to random choice: %s", exc)

    return random_choice()
