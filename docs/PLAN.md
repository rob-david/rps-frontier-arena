# PLAN — RPS Frontier Arena: from static mockup to real AI opponents

## Part 0: Understand before touching anything

- [x] Read `AGENTS.md` in full
- [x] Read `docs/index.html` in full
- [x] **Do not write any code, create any files, or run any commands in this step**
- [x] Explain back your understanding of the project to the user: what it is, how the game works, what the tech stack is, and what's already fixed versus what you're expected to build
- [x] Wait for the user's explicit approval before proceeding to Part 1

**Success criteria:** the user has confirmed your understanding is correct. Nothing has been created, modified, or run yet.

---

## Part 1: Plan

- [x] Confirm the starting structure described in `AGENTS.md` "What Already Exists When You Start" is actually present: `AGENTS.md`, `.env` in the project root, and `docs/PLAN.md` + `docs/index.html`. Do not create or move any of these — if one is missing, stop and ask the user rather than guessing
- [x] Walk through this plan (`docs/PLAN.md`) part by part and confirm you understand each phase's scope and success criteria
- [x] Present the plan to the user and get explicit approval before starting Part 2
- [x] From this point on, treat `docs/PLAN.md` as fixed: check off items as they're completed and tested, but do not restructure, rewrite, or add new parts/substeps to it. If you discover the plan needs to change, stop and ask the user rather than editing it yourself. Implementation notes and decisions made along the way belong in `backend/AGENTS.md` / `frontend/AGENTS.md` (see root `AGENTS.md` "Working Documentation"), not in `docs/PLAN.md` itself

**Success criteria:** user has confirmed the plan; no code written yet.

---

## Part 2: Scaffolding

- [x] Create the new directories/files described in `AGENTS.md` "Project Structure" that don't already exist:
  ```
  /backend
  /frontend
  /config
  /scripts
  ```
  (`docs/` and its contents already exist — do not touch `docs/PLAN.md` or `docs/index.html` in this step)
- [x] Backend: initialize the Python project with `uv init` / `uv add fastapi uvicorn python-dotenv`
- [x] Create `backend/AGENTS.md` (empty except for a one-line title) — from this point on, every later part that touches the backend appends a short note to it (see `AGENTS.md` "Working Documentation" for the format)
- [x] Frontend: scaffold a NextJS app in `frontend/` (App Router), configure `next.config.js` with `output: 'export'`
- [x] Create `frontend/AGENTS.md` (empty except for a one-line title) — same idea, for the frontend side
- [x] Create `config/models.json` exactly as specified in `AGENTS.md` ("Model Configuration")
- [x] Set up FastAPI in `backend/main.py` — for now, mount a placeholder static directory at `/` (the real `frontend/out/` won't exist until Part 3's first build)
- [x] Server listens on `PORT` env var, default `8000`
- [x] Read the variable names already used in the existing `.env` and create `docs/.env.example` as a safe template with the same 4 variable names (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROK_API_KEY`, `GEMINI_API_KEY`) but placeholder values — never read or print the real values from `.env`
- [x] Write `scripts/start.sh` (builds the frontend if needed, then runs `uv run uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}`) and `scripts/stop.sh` for Mac/Linux, plus `scripts/start.ps1` and `scripts/stop.ps1` doing the same thing for native Windows PowerShell — keep both pairs in sync, they must do exactly the same thing
- [x] Write a one-off connectivity check script (a throwaway script, not part of `backend/providers/` — that gets built properly in Part 5) that sends a trivial prompt (e.g. "What is 2+2? Reply with just the number.") to each of the 4 providers using the keys from `.env`, and prints whether each one succeeded. Use plain HTTP requests (`requests` or `httpx`) for this, not the official SDKs — those get added properly per-provider in Part 5, no need to install them twice. This is a fast sanity check that all 4 API keys and network paths actually work, run once now — before any real feature code depends on them — rather than discovering a bad key deep inside Part 5's more complex tests

**Test:** `scripts/start.sh` (or `scripts/start.ps1` on Windows) boots the server locally; visiting `/` shows something (even a placeholder). The matching stop script cleanly stops it. The connectivity check script reports success for all 4 providers.
**Success criteria:** both the Node and Python halves of the project are independently runnable; no database, no persistence anywhere in the scaffold; `uv.lock` and `frontend/package-lock.json` are both committed; `config/models.json` exists and is valid JSON; `backend/AGENTS.md` and `frontend/AGENTS.md` exist (empty logs, ready for future entries); all 4 API keys are confirmed working via the connectivity check; `docs/index.html` and `docs/PLAN.md` are untouched from their starting state.

---

## Part 3: Convert `docs/index.html` into the NextJS app

This is a faithful React port, not a redesign — see `AGENTS.md` "Starting Point" for the exact rules on what must be preserved verbatim (CSS values, game logic, text output formats) versus what necessarily changes (DOM manipulation becomes React state/JSX).

- [x] Port all CSS custom properties, fonts, and styles from `docs/index.html`'s `<style>` block into `frontend/app/globals.css`, preserving every value exactly
- [x] Create `frontend/lib/game.ts`: port the pure logic functions from `docs/index.html` with no behavior changes — `beats()`, `resolveRound()`, the scoring rules, tournament/round counters, and `getFullSessionHistoryText()` (its plain-text output format must match exactly, since the backend will depend on this shape later)
- [x] Build the main page (`frontend/app/page.tsx`) holding game state via `useState`/`useReducer`: players, tournament number, round number, selected choice, game-over/champion state, scores, checked opponents
- [x] Build presentational components matching the mockup's sections: `Scoreboard.tsx`, `OpponentsPanel.tsx`, `PlayersTable.tsx` (the 5-column single live row — fixed height, no per-round history rows), `HistoryPanel.tsx` (the sidebar, the only place round-by-round history is shown). Keep this component split proportional to the app's size — don't invent more components than these
- [x] AI opponents still use `Math.random()` at this stage (in `game.ts` or the page component) — do not build the backend call yet
- [x] Run `npm run build` to produce `frontend/out/`, point FastAPI's `StaticFiles` mount at it

**Test:** run the NextJS dev server (`npm run dev`) and manually compare every screen, interaction, and edge case against `docs/index.html` opened directly in a second browser tab, side by side:
- Player columns always stay in a row, never stack, even on narrow viewports
- The players table is a single fixed-height row — it never grows with more rounds or tournaments, and the "Play Round" button stays directly beneath it, visible without scrolling, no matter how long the session gets
- Opponent checkboxes behave identically (minimum 1 enforced)
- Scoreboard math matches exactly (+1 survive, +2 champion bonus)
- "New Tournament" appends a new heading to the sidebar history and does NOT clear previous tournaments' rounds
- `getFullSessionHistoryText()` (call it from the browser console, or temporarily log it) returns all tournaments in correct chronological order (oldest tournament first, oldest round first within each), in the exact same text shape as the original
- Reloading the page fully resets everything (score 0, Tournament #1, empty history)
- Then run `npm run build`, serve the static export through FastAPI, and repeat the same comparison against the production build

**Success criteria:** the NextJS app is visually and behaviorally indistinguishable from `docs/index.html`, both in dev mode and in the built static export served by FastAPI.

---

## Part 4: Backend AI-move endpoint skeleton (still fake)

- [ ] Add `POST /api/ai-move` to `backend/main.py` (or a `backend/routes.py` it includes), using the exact request/response shape defined in `AGENTS.md` under "API Contract" — a Pydantic model for the request (`player_id`, `active_players`, `history`) and for the response (`choice`)
- [ ] The route reads `config/models.json` to know which provider a given `player_id` maps to, but for now still returns a random choice regardless — ignore `history` content at this stage, just wire the plumbing and the config lookup
- [ ] Before wiring the frontend to it, smoke-test `/api/ai-move` in isolation with a plain `curl` (or equivalent) request and confirm the response matches the API Contract exactly — this isolates "does the backend endpoint work at all" from "does the whole game work", so a failure here is easy to tell apart from a frontend bug later
- [ ] Update `frontend/lib/game.ts` (or wherever the AI-move logic lives) so it calls this endpoint via `fetch('/api/ai-move', ...)` (once per active AI player, in parallel with `Promise.all`) instead of calling `Math.random()` locally. Leave everything else about the game logic and UI untouched
- [ ] Rebuild the static export (`npm run build`) after this change and re-verify through FastAPI
- [ ] Confirm the backend does not persist or cache anything it receives between requests

**Test:** first, the standalone `curl` smoke test above should succeed on its own. Then play across two tournaments; moves still come from the backend but are effectively random. Confirm the network tab shows real requests to `/api/ai-move` matching the documented contract exactly, each carrying the growing history text. Add an artificial 300ms delay to confirm the waiting "?" state renders correctly during the round-trip.
**Success criteria:** the isolated `curl` smoke test succeeds; round-trip frontend -> backend -> frontend works reliably and matches the API Contract exactly; backend is verifiably stateless; the rest of the app is unchanged from Part 3.

---

## Part 5: Real provider integration, one at a time

For each provider below, implement its wrapper in `backend/providers/` using its official Python SDK (`uv add` each one as needed), wire it into `/api/ai-move` only for that specific player id, and leave the other 3 players on the Part 4 fake logic until their own turn comes up. Test each in isolation before moving to the next. Every wrapper reads its model ID from `config/models.json` — never hardcode a model string in these files.

- [ ] **Sam / OpenAI GPT-5.4** (`backend/providers/openai_provider.py`, `uv add openai`, reads `OPENAI_API_KEY`)
- [ ] **Claude / Anthropic Claude Sonnet 5** (`backend/providers/anthropic_provider.py`, `uv add anthropic`, reads `ANTHROPIC_API_KEY`)
- [ ] **Elon / xAI Grok 4.3** (`backend/providers/xai_provider.py`, reads `GROK_API_KEY`, `reasoning_effort: "none"` — xAI's API is OpenAI-compatible, so this can reuse the `openai` SDK pointed at xAI's base URL)
- [ ] **Sergey / Google Gemini 3.1 Pro** (`backend/providers/google_provider.py`, `uv add google-genai`, reads `GEMINI_API_KEY` only — do not also set or fall back to `GOOGLE_API_KEY`, see `AGENTS.md` note on precedence)

For each provider:
- [ ] Confirm the exact current model ID string in `config/models.json` against that provider's live docs (do not assume from training data — verify, since IDs get deprecated)
- [ ] Write a prompt that includes the full `history` string passed in from the frontend, plus a clear instruction to respond with a single word (`kamen`/`nuzky`/`papir`) reflecting its actual strategic choice given that history
- [ ] Parse the response defensively: lowercase, trim, map common variants (e.g. "rock" / "kámen" / "🪨") to the 3 valid values; if unparseable, fall back to random for that call only and log a warning
- [ ] Add a request timeout (e.g. 8s) with fallback to random on timeout
- [ ] Explicitly catch that SDK's rate-limit/quota exception type (not just a generic `except Exception`) and fall back to random on it, since each provider runs on a small capped budget (~$5) and will realistically hit this during testing or real use
- [ ] Wrap the entire `get_move()` body so that literally any exception — expected or not, from the SDK, from parsing, from anything — is caught and results in a random fallback choice. This function must never let an exception propagate up to the route handler. See `AGENTS.md` "Fallback Behavior" for the full rule

**Test per provider:** write a small standalone test script (or pytest test) that calls `get_move(model, history)` directly with a fabricated multi-tournament sample history and confirms a valid, context-aware-looking move comes back. Also test the failure path directly: mock or force a rate-limit/quota exception from that provider's SDK and confirm `get_move()` still returns a valid fallback choice instead of raising. Then play across two tournaments with only that provider checked as the opponent.
**Success criteria:** all 4 providers individually return valid, timely moves that visibly take the full multi-tournament history into account (not just uniformly random); a simulated rate-limit/quota failure on each of the 4 providers individually degrades gracefully to random without crashing the round or raising an exception; per the API Contract, the endpoint still returns HTTP 200 with a valid `choice` even when a provider call fails for any reason.

---

## Part 6: Full integration, resilience, and history size

- [ ] Remove all remaining fake/random logic from `/api/ai-move` — every active AI player now calls its real provider (via `config/models.json` lookup) with full history context
- [ ] Confirm the opponent checkboxes correctly control which providers get called each round (unchecked opponents are never called)
- [ ] Confirm parallel calls keep round latency reasonable even with all 4 active (use `asyncio.gather` on the backend if the provider SDK calls are async, or run them concurrently via a thread pool if not)
- [ ] Simulate a provider outage (invalid API key) and confirm that player falls back to random moves instead of breaking the round
- [ ] Simulate a rate-limit/quota-exhausted response individually for **each of the 4 providers** (not just one) and confirm each one independently falls back to random without crashing the round or affecting the other 3 providers — this matters because each provider has a small capped budget and running out mid-session is realistic, especially if the app sees real traffic
- [ ] Play an extended session: multiple tournaments back to back, enough rounds that the accumulated history text grows substantial. Confirm requests don't blow past reasonable prompt-size or latency limits — if they do, trim to e.g. the last N tournaments' full detail plus a short summary line for older ones, and document the cutoff chosen in `AGENTS.md`
- [ ] Confirm behavior when the human player is eliminated but AI players continue
- [ ] Confirm behavior when only 1 opponent is checked
- [ ] Edit `config/models.json` to a deliberately wrong model ID for one provider, confirm the app still runs and that player falls back to random — then revert the edit

**Test:** deliberately break one provider's API key, replay a tournament, confirm it completes anyway. Separately, deliberately trigger a rate-limit/quota error for each of the 4 providers, one at a time, and confirm a complete tournament still finishes normally each time. Separately, play a long multi-tournament session and confirm response times stay reasonable throughout.
**Success criteria:** a complete multi-tournament session runs end to end using only real API calls with full history context, no manual intervention, no crashes, no persistence surviving a reload, no runaway prompt growth, a model can be swapped by editing only `config/models.json`, and every one of the 4 providers has been individually verified to degrade gracefully to random on both a bad key and a rate-limit/quota failure.

---

## Part 7: Documentation

- [ ] `README.md` already exists at the project root with its presentation-facing sections written (title, screenshot, live demo link, features, tech stack, development-process narrative). Do not rewrite, restructure, or remove any of that — only add the technical/setup content below, in a way that fits naturally alongside what's already there
- [ ] Add: setup steps, all 4 required `.env` keys and where to get them, how to run locally (`scripts/start.sh` on Mac/Linux, `scripts/start.ps1` on Windows), how to stop, and how to change a model (edit `config/models.json`, restart)
- [ ] Add a note that provider model IDs should be periodically re-verified, since providers deprecate/rename models with little notice
- [ ] Document the history-size cutoff strategy decided in Part 6, if any was needed
- [ ] Add a note that `docs/index.html` is the permanent design/logic reference and should stay in sync in spirit with the live app — if the app's behavior ever needs to change, consider updating `docs/index.html` first and re-porting, to keep it trustworthy as a reference
- [ ] No emojis anywhere in docs or code, per `AGENTS.md` coding standards — this includes the sections you add to `README.md`, even though the existing presentation sections may already have a different tone

**Success criteria:** a new developer can clone the repo, fill in all 4 keys in `.env`, run `uv sync`, `npm install` (in `frontend/`), and `scripts/start.sh` (or `scripts/start.ps1` on Windows), and have a fully working game against real AI opponents within a few minutes, entirely locally, looking and behaving exactly like `docs/index.html`. `README.md` reads as one coherent document, not as two mismatched halves.

---

## Part 8: Dockerize (final local packaging step, only after everything above works locally)

This mirrors the original template's scope: the app gets packaged into a Docker container as the last piece of polish, run and verified locally. Where (or whether) this gets hosted anywhere public is a separate decision, made later, outside this plan — this step does not deploy anywhere.

- [ ] Write a **multi-stage** `Dockerfile` at the project root:
  - Stage 1 (Node): install frontend dependencies (`npm install`) and build the static export (`npm run build`), producing `frontend/out/`
  - Stage 2 (Python): install dependencies via `uv sync`, copy in `backend/`, `config/`, and the built `frontend/out/` from Stage 1, expose the configured port, run via `uvicorn`
- [ ] Build and run the Docker image locally, confirm the app works identically to the non-Docker local run (using a local `.env` mounted or passed with `--env-file`)
- [ ] Play a full multi-tournament session against the containerized app end to end

**Test:** a multi-tournament session against real AI opponents works identically running inside the Docker container as it did outside it, including history persisting across tournaments and resetting only on reload.
**Success criteria:** the Docker image builds and runs cleanly from a fresh clone (given a filled-in `.env`); the containerized app is visually and behaviorally identical to `docs/index.html`; no secrets are baked into the image itself (they're passed in at runtime via `.env`/`--env-file`).
