# Backend Implementation Log

- Part 2: Initialized FastAPI scaffold in `backend/main.py` with static mount that serves `frontend/out` when available and a placeholder page otherwise.
- Part 4: Added `POST /api/ai-move` with request/response validation, startup model-config lookup from `config/models.json`, and temporary random-choice response plumbing.
- Part 5: Added provider wrappers (`openai_provider.py`, `anthropic_provider.py`, `xai_provider.py`, `google_provider.py`) with full-history prompts, normalization, per-provider rate-limit handling, request timeout, and catch-all random fallback.
- Part 5: Wired `/api/ai-move` to dispatch by provider from `config/models.json`; endpoint still returns HTTP 200 with a valid choice even on provider failures.
- Part 6: Validated per-provider resilience through `/api/ai-move` for invalid-key outages and simulated rate-limit errors (one provider at a time), confirming each target provider falls back without breaking other providers.
- Part 6: Validated wrong-model-id config fallback by temporarily setting an invalid OpenAI model in `config/models.json`, confirming endpoint HTTP 200 + valid fallback choice, then restoring config.
- Part 8: Added multi-stage Docker packaging (`Dockerfile`) and verified containerized `/api/ai-move` runtime works with keys supplied through `--env-file`.
- Part 8: Confirmed no secrets are baked into the image (no `/app/.env` in container and image env contains only non-secret defaults such as `PORT`).
- Part 8: Loaded root `.env` in `backend/main.py` so local `scripts/start.sh` and `scripts/start.ps1` runs receive provider keys without manual shell export.
- Follow-up: Empirically re-tested Google wrapper behavior with a single `ThinkingLevel.MINIMAL` call to `gemini-3.1-pro-preview`; it returned `400 INVALID_ARGUMENT` ("Thinking level MINIMAL is not supported for this model"), confirming the existing multi-config retry fallback is necessary.
- Follow-up: Added best-effort push notifications scaffolding for `app_opened` only: new `backend/notifications.py` helper posts to Pushover and swallows/logs failures, and new `POST /api/notify` endpoint accepts only `event: "app_opened"` for now, skips push when Pushover env vars are missing, and still returns success.
- Follow-up: Extended `POST /api/notify` to accept `event: "first_round_played"` alongside `"app_opened"` and compose a distinct server-owned message text for each event while keeping the same best-effort, never-fail response behavior.
