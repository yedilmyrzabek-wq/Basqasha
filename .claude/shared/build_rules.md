# Common rules for all BUILD subagents

- Source of truth: `docs/PROJECT_BRIEF.md`. Plan: `docs/PLAN.md`. Research rules: `docs/research/SUMMARY.md` (+ individual research docs).
- Contracts (owned by `architect`): `/schemas/*.schema.json`, `/supabase/migrations/*.sql`, `docs/api/openapi.yaml`, `backend/app/providers/interfaces.py`, `docs/ARCHITECTURE.md`. You MUST conform to them. If a contract is wrong or missing something, STOP and report a change request to the LEAD — do not edit it yourself.
- Edit ONLY your owned folders. Reading anything is fine.
- Non-negotiables (brief §3.3, kickoff rules):
  1. Originality guard: only pipeline steps 1–2 may access the source transcript (`SourceMaterial`). Downstream steps receive brief + chosen angle + facts only. Enforced by separate data models / repositories in code, and covered by a test.
  2. Database = Supabase Postgres via `DATABASE_URL` from `.env`. Media (images, mp3, mp4, poses) ONLY on local disk under `data/` and `library/`; DB stores relative paths. No Supabase Storage.
  3. Secrets only in `.env`; keep `.env.example` updated (via architect). Never commit keys.
  4. No automation of the Google Flow web UI. Images via Gemini API; manual upload is the fallback.
  5. Voice = manual ElevenLabs (copy text → upload mp3). ElevenLabs API provider is a disabled stub.
  6. Every external API call writes a `CostEntry` (provider, model, units, usd).
  7. Language is a parameter (`kk` now, `en` later) — no hard-coded Kazakh outside prompts/fixtures.
  8. Must run on Windows (PowerShell) and macOS/Linux. Use `pathlib`, no shell-specific paths.
- Code style: small modules, type hints / strict TS, no dead code, comments only where non-obvious.
- Tests: add unit tests for your logic under your folder or ask qa-tester for `/tests` coverage. Code must pass lint/typecheck you set up.
- Git: work in the branch/worktree the LEAD gives you; commit with conventional messages; do not merge to main yourself.
- If blocked (missing key, unclear contract, failing dependency) — report the blocker with specifics instead of guessing or stubbing silently.
- Final reply to the LEAD: ≤ 15 lines — what was done, how to run/verify, known issues, change requests.
