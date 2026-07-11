import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_OUT_DIR = BASE_DIR / "frontend" / "out"
PLACEHOLDER_DIR = BASE_DIR / "backend" / "_placeholder_static"


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
app.mount("/", StaticFiles(directory=str(_resolve_static_dir()), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
