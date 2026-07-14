import logging
import os

import httpx

LOGGER = logging.getLogger(__name__)
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def push(text: str) -> None:
  token = os.getenv("PUSHOVER_TOKEN")
  user = os.getenv("PUSHOVER_USER")

  if not token or not user:
    LOGGER.info("Pushover credentials missing. Notification skipped.")
    return

  payload = {
    "token": token,
    "user": user,
    "message": text,
  }

  try:
    response = httpx.post(PUSHOVER_URL, data=payload, timeout=10.0)
    response.raise_for_status()
    request_id = response.json().get("request")
    LOGGER.info("Pushover notification accepted. request=%s", request_id)
  except Exception as exc:
    LOGGER.warning("Pushover notification failed and was ignored: %s", exc)
