import os
import json
import random
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_OUT_DIR = BASE_DIR / "frontend" / "out"
PLACEHOLDER_DIR = BASE_DIR / "backend" / "_placeholder_static"
MODELS_CONFIG_PATH = BASE_DIR / "config" / "models.json"

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
  # Part 4: keep provider plumbing in place while still returning random choices.
  if payload.player_id not in MODEL_CONFIG:
    raise HTTPException(status_code=400, detail="Unknown player_id")

  _config = MODEL_CONFIG[payload.player_id]
  _ = _config.provider, _config.model, payload.active_players, payload.history
  return AIMoveResponse(choice=random.choice(RANDOM_CHOICES))


app.mount("/", StaticFiles(directory=str(_resolve_static_dir()), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
