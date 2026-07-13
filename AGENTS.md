# RPS Frontier Arena

## Business Requirements

This project is a Rock-Paper-Scissors tournament web app. Key features:
- One human player competes against up to 4 AI opponents, each backed by a different real LLM provider
- Player names and their backing models:
  - Sam -> OpenAI -> GPT-5.4
  - Claude -> Anthropic -> Claude Sonnet 5
  - Elon -> xAI -> Grok 4.3
  - Sergey -> Google -> Gemini 3.1 Pro (Preview)
- The human can check/uncheck which of the 4 AI opponents play in a given tournament (minimum 1 must stay checked)
- Elimination tournament format across multiple rounds:
  - All active players choose rock/paper/scissors simultaneously each round
  - If everyone picks the same symbol: tie, round replays, nobody eliminated
  - If exactly 2 distinct symbols are chosen: standard RPS rule applies, the losing symbol's players are eliminated
  - If all 3 symbols are chosen: nobody can be declared a fair winner (no symbol beats both of the others at once), so it's always a tie regardless of how the votes split — nobody is eliminated and the round replays
  - Tournament ends when 1 player remains (the Champion)
- Before choosing its move each round, every AI opponent is given the **complete history of the current browser session** — every round from every tournament played so far, not just the current tournament. Starting a "New Tournament" does NOT clear this context; it only resets the active player pool and the elimination state for the new bracket. Only a full page reload clears everything
- A scoreboard that persists across tournaments within the current browser session: +1 point per round survived (including ties, where everyone survives), +2 bonus points for winning a tournament. "New Tournament" keeps the scoreboard; a full page reload does not (see Limitations)
- The main table shows player columns side by side, always in a row (never stacked, even on mobile), and stays a single fixed row — the live/current round only (interactive choice for the human, "?" waiting badge for AI). It never grows with more rounds or tournaments, so the "Play Round" button always stays directly beneath it, fully visible without scrolling
- A separate sidebar panel (fixed height, its own internal scroll) shows the full session history as readable commentary text, grouped by tournament heading, newest tournament on top. This is the only place round-by-round history is displayed — it keeps growing across tournaments and is never cleared until reload

## Limitations

For the MVP, deliberately:
- **No database. No persistence of any kind.** Everything (scoreboard, tournament state, full session history across all tournaments) lives only in the browser's in-memory state for the current session. This is a deliberate decision — this app has no accounts and nothing worth persisting across visits, so a database would be pure overhead
- Reloading the page always starts completely from scratch: score 0 for everyone, Tournament #1, Round 1, empty history — there is nothing to migrate or preserve
- Starting a "New Tournament" resets the bracket (all players active again, Round 1) but explicitly does NOT clear the scoreboard or the accumulated history — both keep growing until the page is reloaded
- The backend is stateless between requests. It does not remember past rounds or past tournaments itself — the frontend sends the full accumulated session history along with every AI-move request, since it's the only thing tracking state. The backend's only job is: take a game state snapshot, ask the right provider, return a move
- No user accounts or authentication
- Single human player per running instance; no multiplayer, no concurrent session isolation needed beyond what naturally happens per browser tab

## What Already Exists When You Start

The project owner has manually created the following before handing this off. **Do not recreate, move, or restructure any of these** — they are the fixed starting point:

```
rps-frontier-arena/
├── AGENTS.md          # this file
├── README.md          # public-facing GitHub README — portfolio framing, partially complete
├── .env                # 4 AI provider keys, already filled in, gitignored
├── .gitignore          # may already exist
├── assets/
│   └── screenshot.png   # used by README.md, keep as-is
└── docs/
    ├── PLAN.md          # the plan you are executing
    └── index.html       # the reference mockup — already in its final location
```

`README.md` already has its presentation-facing sections written (title, screenshot, live demo link, feature summary, tech stack table, development-process narrative). It is deliberately incomplete on the technical/setup side — see `docs/PLAN.md` Part 7 for exactly what to add, and do not touch the sections that are already there.

Everything else in "Project Structure" below — `backend/`, `frontend/` (including their own `AGENTS.md` implementation logs, see "Working Documentation"), `config/`, `scripts/`, `pyproject.toml`, `Dockerfile`, `docs/.env.example` — does not exist yet and is what you build over the course of `docs/PLAN.md`. `docs/index.html` in particular is already exactly where it needs to be; there is no "move it into docs/" step anywhere in the plan, because it's already there.

## Starting Point — READ THIS BEFORE WRITING ANY FRONTEND CODE

`docs/index.html` (provided alongside this document) is the **single source of truth** for both the visual design and the game logic. It is a fully working, already-approved, already-tested single-file mockup, refined over many iterations. It is not a rough draft — it is the finished product, design-wise and logic-wise. It lives in `docs/` (next to this file and `PLAN.md`) as a reference artifact, not as the shipped frontend itself — the shipped frontend is the NextJS app described below, converted from it.

`docs/index.html` already implements, exactly as it must continue to behave after conversion to NextJS:
- The full 5-column player table (You / Sam / Claude / Elon / Sergey) — a single fixed live row only, always side by side even on mobile, with a constant/predictable height regardless of round or tournament number, so the "Play Round" button beneath it never moves and is always visible without scrolling
- The opponent checkbox panel (minimum 1 opponent enforced)
- The scoreboard (persists across tournaments, resets only on reload)
- The elimination logic described above, exactly as coded in its `resolveRound()` function
- The sportscast-style history sidebar, grouped by tournament, newest tournament on top, **never cleared by "New Tournament"**
- A `getFullSessionHistoryText()` helper function that returns the entire session's history (every tournament, every round, chronological order) as plain text — this output format matters a lot: it is what gets sent to the backend as AI context later, so the NextJS reimplementation of this function must produce functionally identical text output (same structure, same wording, same chronological ordering), not just "similar-looking" text
- AI moves currently generated via `Math.random()` in the mockup — in the real app this becomes a `fetch()` call to `/api/ai-move`, everything else about the app's behavior stays the same

**How to treat the conversion:** `docs/index.html` is vanilla JS with direct DOM manipulation (`document.getElementById(...).innerHTML = ...`). The NextJS version will necessarily rewrite this as React state and JSX (`useState`, conditional rendering, etc.) — that part is a genuine reimplementation, not a copy-paste. But everything else must be preserved as closely to exactly as possible:
- Every CSS custom property, color value, font, spacing value, breakpoint, and animation — copy the values verbatim, don't reinterpret them
- Every rule of game logic (`resolveRound`, `beats`, scoring, elimination, tournament/round numbering) — port the exact algorithm, don't "improve" it
- The exact plain-text output shape of `getFullSessionHistoryText()`
- Every user-facing string and label

If something in `docs/index.html` looks odd or inefficient, leave the *behavior* exactly as-is when porting it to React — it has already been through many rounds of design review.

**If this document and `docs/index.html` ever appear to conflict:** treat `docs/index.html` as the authoritative source for UI behavior and visuals, and this document (`AGENTS.md`) as the authoritative source for architecture and implementation (tech stack, API contract, project structure, fallback rules, etc.). Don't guess — if a conflict seems significant, stop and ask the user rather than picking one silently.

## Technical Decisions

This project uses the following stack: NextJS frontend, Python FastAPI backend serving the static site, Docker packaging, `uv` as the Python package manager. The frontend isn't designed from a blank page — it's a faithful React port of the already-approved `docs/index.html`, and there is no database (see Limitations).

- **Frontend: NextJS (App Router), Node.js, npm.** Configured for static export (`output: 'export'` in `next.config.js`), since this is a single interactive client-side page with no server-rendered data — `next build` produces a static `frontend/out/` directory
- **Backend: Python, FastAPI, package-managed with `uv`**
- FastAPI serves the built static NextJS export (`frontend/out/`) at `/` (via `StaticFiles`) and exposes the API under `/api`
- Keep the component split simple and proportional to the app's actual size — one main page component holding the game state via hooks, plus a handful of presentational components (scoreboard, opponents panel, players table, history panel) is enough; do not over-engineer the component tree
- Game logic (the port of `resolveRound`, `beats`, scoring, `getFullSessionHistoryText`, etc.) lives in a plain TypeScript module (e.g. `frontend/lib/game.ts`), not scattered across components, so it stays easy to diff against the original `docs/index.html` logic
- Backend adds exactly one new endpoint: `POST /api/ai-move` — see "API Contract" below for the exact request/response shape
- Each provider gets its own small wrapper module in `backend/providers/` (`openai_provider.py`, `anthropic_provider.py`, `xai_provider.py`, `google_provider.py`), each exposing a single function: `get_move(model: str, history: str) -> str` returning `"kamen"`, `"nuzky"`, or `"papir"`. Use each provider's official Python SDK (`openai`, `anthropic`, `google-genai`; xAI's API is OpenAI-compatible, so the `openai` SDK pointed at xAI's base URL is fine)
- If any provider call fails, for any reason at all, fall back to a random choice for that player that round — the game must never crash or stall because of an API hiccup. See "Fallback Behavior" below for the full, explicit rule
- Use `reasoning_effort`/thinking set to minimum on all 4 providers where supported — this is a fast decision task, no reasoning budget needed, even with history included. **Claude Sonnet 5 specifically:** unlike older Claude models, adaptive thinking is *on by default* the moment the `thinking` field is omitted — pass `thinking={"type": "disabled"}` explicitly in `anthropic_provider.py`, or responses may come back as a `thinking` block with no `text` block at all if `max_tokens` gets consumed entirely by reasoning. Verify this against Anthropic's current docs before implementing, since this is exactly the kind of provider-specific default that changes between model versions
- Because history accumulates across multiple tournaments in one session, watch for prompt size growing large in long sessions — trim or summarize older tournaments if needed
- **Final packaging: Docker**, matching the original template's approach — the app runs in a container locally as the last polish step, done only after everything works without Docker. This is local packaging, not a commitment to any specific hosting platform; where (or whether) this gets deployed anywhere is a separate decision, made later, outside this plan.
  - A multi-stage `Dockerfile`: a Node stage that runs `npm install && npm run build` to produce `frontend/out/`, and a Python stage that installs dependencies via `uv` and runs the FastAPI app with `uvicorn`, copying in the built static output from the Node stage
  - The server listens on a configurable `PORT` env var, default `8000`
- Start/stop convenience scripts in `scripts/` for local dev: `start.sh`/`stop.sh` (Mac/Linux, or Git Bash/WSL on Windows) **and** `start.ps1`/`stop.ps1` (native Windows PowerShell) — functionally identical, both just build the frontend once and run FastAPI on top of it. Local dev builds the static export once and serves it through FastAPI, the same flow as the Docker packaging step — this avoids running two dev servers (NextJS dev server + FastAPI) with a proxy between them, which would add complexity for no real benefit on an app this size

## Provider API Keys (`.env`)

One key per provider, standard/official variable name for each SDK — do not invent different names:

| Player | Provider | Env variable |
|---|---|---|
| Sam | OpenAI | `OPENAI_API_KEY` |
| Claude | Anthropic | `ANTHROPIC_API_KEY` |
| Elon | xAI | `GROK_API_KEY` |
| Sergey | Google | `GEMINI_API_KEY` |

Notes:
- `GEMINI_API_KEY` is Google's own recommended variable name for the `google-genai` SDK. The SDK also accepts `GOOGLE_API_KEY`, but Google's docs explicitly recommend `GEMINI_API_KEY` and warn that `GOOGLE_API_KEY` silently takes precedence if both happen to be set (e.g. leftover from an unrelated Google Cloud tool on the machine) — use only `GEMINI_API_KEY` to avoid that trap
- xAI's API is OpenAI-compatible; when constructing the `openai` SDK client for Elon's provider wrapper, point `base_url` at xAI's endpoint and pass `GROK_API_KEY` as the API key
- These 4 variables go in `.env` locally (never committed) — read via `os.environ`

## Model Configuration — kept OUT of Python code

Model IDs are a known moving target (deprecations happen with little notice — confirmed already with `grok-3-mini` being retired). To change which model any player uses, nobody should have to touch Python code — they should only need to edit one config file.

- [ ] Create `config/models.json` at the project root, structured like this:
  ```json
  {
    "sam":     { "provider": "openai",    "model": "gpt-5.4" },
    "claude":  { "provider": "anthropic", "model": "claude-sonnet-5" },
    "elon":    { "provider": "xai",       "model": "grok-4.3" },
    "sergey":  { "provider": "google",    "model": "gemini-3.1-pro-preview" }
  }
  ```
- [ ] Confirm each exact model ID string against that provider's live docs before first real run — do not assume from training data
- [ ] The backend loads this file once at startup (not hardcoded constants in any `.py` file) and looks up the right `provider` + `model` for a given player id when routing a request to the correct wrapper function in `backend/providers/`
- [ ] To change a model later (e.g. when one gets deprecated), the only required change is editing `config/models.json` and restarting the app — no Python file should ever need to change for a model swap

## API Contract — `POST /api/ai-move`

This is the only endpoint the frontend calls. The frontend calls it once per active AI opponent per round, in parallel.

**Request body:**
```json
{
  "player_id": "sam",
  "active_players": ["user", "sam", "claude", "elon"],
  "history": "Tournament #1\n\nRound 1\nYou selected Rock.\nSam selected Scissors.\n...\n\nTournament #2\n\nRound 1\n..."
}
```
- `player_id`: one of `"sam"`, `"claude"`, `"elon"`, `"sergey"` — used to look up provider + model from `config/models.json`
- `active_players`: ids of every player still active this round (informational context for the prompt, e.g. so the model knows who else is still in it)
- `history`: the exact, unmodified output of the frontend's `getFullSessionHistoryText()` at the moment of the request — every tournament, every round, played so far this session

**Success response (HTTP 200):**
```json
{ "choice": "papir" }
```
`choice` is always exactly one of `"kamen"`, `"nuzky"`, `"papir"` — this is the same vocabulary already used throughout `docs/index.html`'s logic, no translation layer needed on the frontend.

**No other endpoints exist.** No auth, no session id, no state stored server-side between calls.

## Fallback Behavior — read this carefully, it applies to all 4 providers equally

Each of the 4 providers runs on a small prepaid/capped budget (~$5). Hitting that cap, getting rate-limited, or any other kind of provider failure is a realistic thing to expect during normal use, not just a theoretical edge case — especially if the app ever sees real traffic from multiple people.

The rule is simple and absolute: **any error of any kind, from any provider, for any reason, results in a random fallback choice for that one player only.** Never an unhandled exception, never an HTTP error returned to the frontend, never a crashed round, never a visible error state in the UI. From the human player's point of view, a failing model must be completely indistinguishable from a model that just happened to make a fast, simple choice — the round proceeds exactly as normal either way.

Concretely:
- `/api/ai-move` must never return a non-200 response because of a provider-side failure. It only returns non-200 for a genuinely malformed request (e.g. missing `player_id`)
- Each `get_move()` provider wrapper function must wrap its entire body so that literally any exception — a specific rate-limit/quota exception, a timeout, a network error, an unparseable response, or anything unexpected — is caught inside that function and results in a random valid choice being returned instead. No exception should ever propagate out of `get_move()`
- This must be true independently for all 4 providers. One provider running out of budget must never affect the other 3, and must never crash the round or the app
- Prefer catching specific, known exception types (e.g. `openai.RateLimitError`, `anthropic.RateLimitError`) where practical, so the common failure modes are handled deliberately — but always back that with a final catch-all so nothing can slip through

## Project Structure

```
rps-frontier-arena/
├── AGENTS.md                   # [already exists]
├── .env                         # [already exists]
├── .gitignore                   # [already exists, or create if missing]
├── README.md                    # [already exists — partially complete, you fill in the technical sections]
├── pyproject.toml               # [you create]
├── uv.lock                      # [you create]
├── Dockerfile                   # [you create]
│
├── assets/
│   └── screenshot.png           # [already exists]
│
├── docs/
│   ├── PLAN.md                  # [already exists]
│   ├── index.html               # [already exists — the approved reference mockup]
│   └── .env.example             # [you create — safe template matching .env's keys]
│
├── config/                      # [you create]
│   └── models.json
│
├── backend/                     # [you create]
│   ├── AGENTS.md                # [you create] running implementation log for backend/
│   ├── main.py                  # FastAPI app: serves frontend/out/, exposes /api/ai-move
│   └── providers/
│       ├── openai_provider.py
│       ├── anthropic_provider.py
│       ├── xai_provider.py
│       └── google_provider.py
│
├── frontend/                    # [you create] NextJS app (Node.js, npm)
│   ├── AGENTS.md                # [you create] running implementation log for frontend/
│   ├── package.json
│   ├── next.config.js          # output: 'export'
│   ├── app/
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── Scoreboard.tsx
│   │   ├── OpponentsPanel.tsx
│   │   ├── PlayersTable.tsx
│   │   └── HistoryPanel.tsx
│   ├── lib/
│   │   └── game.ts             # resolveRound, beats, getFullSessionHistoryText, etc.
│   ├── public/
│   └── out/                    # generated by `npm run build`, gitignored — what FastAPI serves
│
└── scripts/                     # [you create]
    ├── start.sh                # builds frontend, then starts FastAPI (Mac/Linux)
    ├── stop.sh
    ├── start.ps1                # same, for native Windows PowerShell
    └── stop.ps1
```

## Color Scheme & Design Tokens

These are already correct in `docs/index.html`'s `:root` CSS variables — copy them exactly into the NextJS global stylesheet, do not invent new values:
- Background: `#12142B`, panels `#1B1E3F` / `#20244A`
- Player (You): `#46E0D0`
- Sam / OpenAI: `#FF5C8A`
- Claude / Anthropic: `#FFB454`
- Elon / xAI: `#9B7CFF`
- Sergey / Google: gradient text `#4C8DFF -> #EA4335 -> #FBBC05 -> #34A853`
- Fonts: Chakra Petch (headings), Inter (body), JetBrains Mono (labels/status text)

## Coding Standards

1. Use current, idiomatic patterns for both stacks: NextJS App Router + React hooks on the frontend, FastAPI + `uv` on the backend (`uv add`, `uv sync`, `uv run` — never call `pip` directly; `npm install` / `npm run build` on the frontend side)
2. Keep it simple — never over-engineer, no unnecessary abstraction layers or component splitting beyond what's proportional to this app's size, no defensive code for cases that can't happen, and no database or caching layer of any kind
3. Be concise. No emojis anywhere in code, commit messages, or README
4. When something breaks, find the root cause before attempting a fix — no guessing
5. Never redesign or "clean up" anything already working in `docs/index.html` — see Starting Point above; port its behavior faithfully into React, don't reinterpret it
6. Never hardcode a model ID in Python — always read it from `config/models.json`
7. Never change `docs/index.html` during implementation unless the user explicitly instructs you to. Treat it as the frozen design specification — if the app doesn't match it, fix the app, not the mockup
8. Local development happens on Windows 11. Windows PowerShell support is not optional: every convenience script in `scripts/` needs both a `.sh` version (Mac/Linux) and a functionally identical `.ps1` version (Windows), and both must be kept in sync whenever either one changes
9. Test thoroughly, always. The `Test:`/`Success criteria:` lines in each `docs/PLAN.md` part are the minimum bar, not a ceiling — they call out the cases that must not be missed, but they don't excuse skipping other reasonable edge cases that come up while building (e.g. an empty state, a boundary value, an unusual but valid sequence of user actions). Don't check off a part on a shallow pass just because the explicitly listed test happened to succeed once

## Working Documentation

All planning and execution tracking for this project lives in `docs/`. Review `docs/PLAN.md` before starting any implementation work, and check off each item as it's completed and tested. `docs/PLAN.md` was enriched into its current detailed, checklist-based form as a one-time task, before implementation began — treat it as fixed from here on. Don't restructure it, rewrite it, or add new parts/substeps to it while building; if the plan itself needs to change, stop and ask the user. Implementation notes belong in `backend/AGENTS.md` / `frontend/AGENTS.md` instead (see below).

In addition, keep a running implementation log in each major part of the codebase:
- When you create the `backend/` directory (Part 2), also create an empty `backend/AGENTS.md`. From that point on, after each step in `docs/PLAN.md` that touches the backend, append a short note to `backend/AGENTS.md` describing what was built or changed and why (e.g. "Part 4: added `/api/ai-move` route, returns random choice for now" / "Part 5: added `openai_provider.py`, catches `RateLimitError` and falls back to random"). Keep entries brief — this is a log, not a rewrite of `AGENTS.md`
- When you create the `frontend/` directory (Part 2), do the same with `frontend/AGENTS.md`
- These two files are for anyone (human or agent) picking up backend-only or frontend-only work later, without needing the full project history — they should never contradict the root `AGENTS.md` or `docs/index.html`; if anything here conflicts with those, the root `AGENTS.md` and `docs/index.html` still win (see "If this document and `docs/index.html` ever appear to conflict" above)
