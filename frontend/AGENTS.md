# Frontend Implementation Log

- Part 2: Scaffolded Next.js App Router frontend and configured static export in `next.config.js`.
- Part 3: Ported `docs/index.html` UI and game flow into React state/components, including `frontend/lib/game.ts` logic and full-session history text generation.
- Part 3 fix: Resolved duplicate tournament creation on opponent toggle by removing side effects from React state updater callbacks in `frontend/app/page.tsx`.
- Part 4: Replaced local AI random move generation with parallel `fetch('/api/ai-move')` calls and kept round resolution logic unchanged.
- Part 6: Re-verified opponent-checkbox routing in browser automation: when only one opponent is checked, only that provider is called each round.
- Part 6: Re-verified user-eliminated flow and long-session behavior: AI rounds continue after user elimination, and session history growth across many tournaments remains responsive without adding a history cutoff.
- Part 8: Verified containerized app UI/gameplay on `http://localhost:8001` including multi-tournament history persistence and reset-on-reload behavior.
- Follow-up: Ported the fixed single last-played-round row into React with `lastRoundChoices` state reset on new tournaments and opponent-toggle resets, and verified in both Next.js dev and FastAPI-served production flow that the row updates in place (no accumulation), applies elimination tint, and maintains stable table height.
- Follow-up: Added a real `isThinking` round-resolution state and a generation guard in `app/page.tsx` so `Play Round` becomes `Thinking...` immediately, human choice/opponent toggles are locked while AI requests are in flight, and stale async results are discarded if a tournament reset occurs before completion.
- Follow-up: Synced `resolveRound` with the corrected rules from `docs/index.html` by removing majority-counting for 3-symbol rounds so any `kamen`/`nuzky`/`papir` mix always ties, and validated forced uneven 3-symbol, 1-symbol tie, 2-symbol elimination, and even 3-way split cases via direct TypeScript execution.
- Follow-up: Added a mount-time fire-and-forget `POST /api/notify` call for `event: "app_opened"` and guarded it with a module-level flag so React Strict Mode remount behavior in `npm run dev` does not double-send within one page load.
- Follow-up: Added a one-time `first_round_played` notification trigger in `handlePlayRound` using a ref guard so it fires only on the first actual round-play click per page load, never blocks round resolution, and does not refire on later rounds or after `New Tournament`.
- Follow-up: Added per-tournament `tournament_champion` notification trigger in `handlePlayRound` so every completed tournament sends a fire-and-forget push with `champion_id`, without waiting and without delaying champion UI state updates.
