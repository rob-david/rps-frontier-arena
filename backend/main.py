import os
import json
import random
import logging
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.notifications import push
from backend.providers.anthropic_provider import get_move as anthropic_get_move
from backend.providers.google_provider import get_move as google_get_move
from backend.providers.openai_provider import get_move as openai_get_move
from backend.providers.xai_provider import get_move as xai_get_move

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_OUT_DIR = BASE_DIR / "frontend" / "out"
PLACEHOLDER_DIR = BASE_DIR / "backend" / "_placeholder_static"
MODELS_CONFIG_PATH = BASE_DIR / "config" / "models.json"
LOGGER = logging.getLogger(__name__)

load_dotenv(BASE_DIR / ".env")

Choice = Literal["kamen", "nuzky", "papir"]
AIPlayerId = Literal["sam", "claude", "elon", "sergey"]


class AIPlayerConfig(BaseModel):
  provider: str
  model: str


class AIMoveRequest(BaseModel):
  player_id: AIPlayerId
  active_players: list[str]
  history: str


class AIMoveResponse(BaseModel):
  choice: Choice


class NotifyRequest(BaseModel):
  event: Literal["app_opened", "first_round_played"]


class NotifyResponse(BaseModel):
  notified: bool


def _load_models_config() -> dict[str, AIPlayerConfig]:
  with MODELS_CONFIG_PATH.open("r", encoding="utf-8") as handle:
    raw = json.load(handle)

  required = ["sam", "claude", "elon", "sergey"]
  missing = [key for key in required if key not in raw]
  if missing:
    raise RuntimeError(f"Missing model config entries: {', '.join(missing)}")

  return {key: AIPlayerConfig.model_validate(value) for key, value in raw.items()}


MODEL_CONFIG = _load_models_config()
RANDOM_CHOICES: tuple[Choice, Choice, Choice] = ("kamen", "nuzky", "papir")
PROVIDER_TO_GET_MOVE = {
  "openai": openai_get_move,
  "anthropic": anthropic_get_move,
  "xai": xai_get_move,
  "google": google_get_move,
}


def _resolve_static_dir() -> Path:
    if FRONTEND_OUT_DIR.exists():
        return FRONTEND_OUT_DIR

    PLACEHOLDER_DIR.mkdir(parents=True, exist_ok=True)
    placeholder_index = PLACEHOLDER_DIR / "index.html"
    if not placeholder_index.exists():
        placeholder_index.write_text(
            """<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>RPS Frontier Arena</title>
  </head>
  <body style=\"font-family: sans-serif; padding: 2rem;\">
    <h1>RPS Frontier Arena</h1>
    <p>Frontend build not found yet. Run frontend build to populate frontend/out.</p>
  </body>
</html>
""",
            encoding="utf-8",
        )
    return PLACEHOLDER_DIR


app = FastAPI(title="RPS Frontier Arena")


@app.post("/api/ai-move", response_model=AIMoveResponse)
def ai_move(payload: AIMoveRequest) -> AIMoveResponse:
  # Backend remains stateless: every request is resolved only from payload + model config.
  if payload.player_id not in MODEL_CONFIG:
    raise HTTPException(status_code=400, detail="Unknown player_id")

  config = MODEL_CONFIG[payload.player_id]
  provider_key = config.provider.strip().lower()
  get_move = PROVIDER_TO_GET_MOVE.get(provider_key)
  if not get_move:
    LOGGER.warning(
      "Unknown provider '%s' configured for '%s'. Falling back to random choice.",
      config.provider,
      payload.player_id,
    )
    return AIMoveResponse(choice=random.choice(RANDOM_CHOICES))

  choice = get_move(config.model, payload.history)
  if choice not in RANDOM_CHOICES:
    LOGGER.warning("Provider returned invalid choice %r. Falling back to random choice.", choice)
    choice = random.choice(RANDOM_CHOICES)

  return AIMoveResponse(choice=choice)


@app.post("/api/notify", response_model=NotifyResponse)
def notify(payload: NotifyRequest) -> NotifyResponse:
  # Keep notification as a best-effort side effect: never fail the request for env/network issues.
  token = os.getenv("PUSHOVER_TOKEN")
  user = os.getenv("PUSHOVER_USER")
  if not token or not user:
    return NotifyResponse(notified=False)

  messages = {
    "app_opened": "RPS Frontier Arena: someone opened the app",
    "first_round_played": "RPS Frontier Arena: someone started playing",
  }
  push(messages[payload.event])
  return NotifyResponse(notified=True)


app.mount("/", StaticFiles(directory=str(_resolve_static_dir()), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
