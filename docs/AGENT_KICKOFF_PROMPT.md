# Промпт для Claude Code: команда субагентов

**Как использовать:**
1. В пустую папку положите `PROJECT_BRIEF.md` и `costco_project_example.zip`.
2. Запустите `claude` и вставьте текст из блока ниже.
3. Агент создаст команду субагентов (`.claude/agents/*.md`) и будет координировать их работу сам.

Перед этим подключите MCP:
- `claude mcp add playwright npx @playwright/mcp@latest` — нужен тестировщику;
- vidIQ MCP — по желанию, для исследователей тем;
- Supabase MCP — по желанию, чтобы агент сам создавал таблицы.

---

```text
You are the LEAD (orchestrator) of a small AI team that will research and build the system described in PROJECT_BRIEF.md (read it fully first; it is the source of truth). The example Remotion project with our visual style, character poses and a reference video is in costco_project_example.zip — unzip it to /reference and study it.

Your job: plan, create specialized subagents, delegate, integrate, verify, and report to me at checkpoints. Do NOT write most of the code yourself — delegate to subagents and review their work.

## 1. Create these subagents as files in .claude/agents/ (name, description, tools, clear ownership)

RESEARCH TEAM (run first, in parallel; output = markdown in /docs/research, every claim marked [Fact + source URL] or [Estimate]):
- monetization-researcher — YouTube Partner Program requirements 2026; inauthentic/reused content and AI-disclosure policies (exact dates, official links); RPM/CPM for Kazakhstan/CIS (what is known vs estimated); non-AdSense income for a Kazakh-language channel (local sponsors, partnerships, multi-language audio tracks for an English version). Output: docs/research/monetization.md with a "Rules for our system" section.
- video-craft-researcher — how top animated explainer channels make videos that retain viewers: hook in first 15 s, scene-change pacing, script structures, captions, sound design, title/thumbnail patterns, turning long-form into Shorts. Output: docs/research/video_craft.md with CONCRETE rules we can put into LLM prompts and storyboard generation (numbers: seconds per scene, words on screen, etc.).
- kazakh-market-researcher — Kazakh-language YouTube landscape (existing educational/animation channels, what topics get views), Kazakh in TTS (ElevenLabs, Gemini TTS) and ASR (faster-whisper kk quality), fonts with full Kazakh Cyrillic. Output: docs/research/kazakh_market.md.
- topic-scout — 30+ candidate topics: English source video URL (animated/explainer, strong views) → Kazakhstan angle → why it works → priority. Use vidIQ MCP if available, otherwise web search. Output: docs/research/topics_backlog.md.
- tools-cost-researcher — current prices and limits: Gemini API (text, Google Search grounding, embeddings, image models), ElevenLabs plans, Supabase free tier limits (pausing, DB size), Remotion license terms for individuals. Output: docs/research/tools_costs.md.

BUILD TEAM (start after the architect has published contracts):
- architect — owns /schemas (JSON Schemas: brief, angles, facts, script, originality, storyboard, props), DB schema and migrations for Supabase Postgres (SQL in /supabase/migrations), backend API contract (OpenAPI), folder layout, provider interfaces (IVoiceProvider, IImageProvider, IScriptWriter, IPublisher). Only the architect changes contracts; others request changes through you.
- backend-dev — owns /backend: FastAPI app, Supabase/Postgres via SQLModel/SQLAlchemy (DATABASE_URL), Huey jobs (local SQLite queue only), pipeline step orchestration and statuses, file storage on LOCAL disk (/data, /library; DB stores paths only), yt-dlp transcript, ffmpeg audio, faster-whisper alignment, chroma-key & pose sheet splitting, cost ledger.
- ai-engineer — owns /prompts and /backend/ai: Gemini client (google-genai), structured JSON outputs validated by Pydantic, Google Search grounding for facts, embeddings + LLM judge for originality, image generation with style/character references, vision QA of images, optional ClaudeCode script writer (`claude -p ... --output-format json`). Must turn docs/research/video_craft.md and monetization.md rules into prompt instructions.
- media-engineer — owns /engine: generic Remotion composition "Explainer" fully driven by props.json (port components from /reference: Ken Burns + punch-in, Char with pose schedule, Label, counters, coins, arrows, captions with keyword highlight, SFX, progress bar), still/contact-sheet rendering, Short (9:16) variant. Verify Kazakh glyphs render.
- frontend-dev — owns /frontend: React + Vite + TS + Tailwind + shadcn/ui; pages from PROJECT_BRIEF §6.7 (projects list, project page with step navigation, script editor, mp3 dropzone, image grid with regenerate/upload, contact sheet with per-scene comments, video player, settings, pose library). Russian UI labels.
- qa-tester — owns /tests and verification: unit tests, e2e with fixtures (sample transcript, mp3, images), Playwright MCP click-through of the UI, looks at rendered contact sheets and reports visual issues. Has authority to block a phase.

Each subagent file must state: its owned folders (do not edit others' folders), inputs it relies on (contracts, research docs), definition of done, and to report blockers instead of guessing.

## 2. Workflow

Step A — Kickoff (you): read PROJECT_BRIEF.md, unzip reference, write docs/PLAN.md (phases P1–P5 from the brief, task breakdown per subagent, dependencies). Ask me only blocking questions (max 5).
Step B — Research (parallel): run all 5 research subagents at once. Then you write docs/research/SUMMARY.md: key decisions and rules for the system; list anything that contradicts PROJECT_BRIEF.md. ▶ CHECKPOINT 1: show me SUMMARY.md and wait for my OK.
Step C — Contracts: architect delivers schemas, Supabase migrations, OpenAPI, interfaces. You review against the brief. ▶ CHECKPOINT 2 (short).
Step D — Build per phase (P1 → P5). Within a phase run backend-dev, ai-engineer, media-engineer, frontend-dev in parallel where independent (use separate git branches/worktrees per subagent if helpful, merge via you). After each phase qa-tester verifies; fix loop until green. ▶ CHECKPOINT after each phase: short demo instructions for me + what works + known issues.
Acceptance per phase is defined in PROJECT_BRIEF §7/§6.6. The P1 demo must work on this real example: https://www.youtube.com/watch?v=9-eQiEQOhyo → Kazakh angle about how Kazakhs survived winters (киіз үй, тезек, қыстау, жұт).

## 3. Non-negotiable rules
- Originality guard from PROJECT_BRIEF §3.3 enforced in code (separate data models; only steps 1–2 access the source transcript).
- Database: Supabase Postgres (free tier) via DATABASE_URL from .env. Media files (images, mp3, mp4, poses) ONLY on local disk; DB stores relative paths. No Supabase Storage.
- Secrets only in .env (provide .env.example). Never commit keys.
- Do not automate the Google Flow web UI. Images via Gemini API; manual upload as fallback.
- Voice = manual ElevenLabs for now (copy text → upload mp3), ElevenLabs API provider only as a disabled stub.
- One-command local start (backend + worker + frontend) on Windows and macOS/Linux; README with setup (Python/uv, Node 22, ffmpeg, whisper model, Supabase project creation steps).
- Log cost of every external API call.
- Keep me informed briefly; don't flood me with details between checkpoints.

Start now with Step A.
```
