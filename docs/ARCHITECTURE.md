# ARCHITECTURE (v0.1, architect)

The contracts are in `/schemas` (the JSON that flows between steps, with one Kazakh example each in `/schemas/examples`), `/supabase/migrations/0001_init.sql`, `docs/api/openapi.yaml` and `backend/app/providers/interfaces.py`. The goal is one working end-to-end video, so the design stays lean.

## 1. Layout
```
backend/            uv project (Python 3.12). packages: app/ (FastAPI, pipeline, db, media) + ai/ (ai-engineer)
  app/api/          routers (match openapi.yaml)
  app/pipeline/     orchestrator.py, steps/s01_source.py … s10_metadata.py, originality_feed.py
  app/sources/      SourceMaterial model + SourceRepository  (originality guard, §4)
  app/providers/    interfaces.py (architect) + manual/stub providers
  ai/               Gemini client, prompts runner, script writers, originality checker, image QA
engine/             Remotion: compositions Explainer / ExplainerShort, scripts/render.mjs, scripts/stills.mjs
frontend/           React + Vite UI (Russian labels)
prompts/            versioned *.md prompts
schemas/            JSON Schemas + examples
supabase/migrations numbered SQL, applied in order (schema_migrations table)
library/            poses/ (pose_*.png, poses.json), style/, sfx/ (*.wav, music/)
data/               runtime, git-ignored (below)
```
`data/projects/{project_id}/` contains `source/` (transcript.txt), `brief/`, `facts/`, `script/` (script_v{n}.md, tts_v{n}.txt), `voice/` (upload_v{n}.mp3, voice_v{n}.norm.wav, words_v{n}.json), `storyboard/` (storyboard_v{n}.json), `images/` (bg01.png, plus older attempts as bg01_a{k}.png), `render/` (props_{id}.json, stills/, contact_sheet_v{n}.png, final.mp4, short_{k}.mp4) and `meta/` (meta.md, thumbnails). Also under `data/`: `backups/` (pg_dump, keep 8) and `queue/huey.sqlite3`.
The DB stores POSIX paths relative to `DATA_DIR` (project files) or `LIBRARY_DIR` (poses). No media in the DB.

## 2. Steps and state machine
Steps: `source → idea → facts → script → voice → storyboard → images → preview → render → metadata` (enum `step_key`). The table `project_step` holds one row per step.
Statuses: `pending → running → done | waiting_operator | failed`; `waiting_operator → running/done` after an operator action; `failed → running` (retry); `done → stale` when an upstream input changes; `stale → running`.
A step runs only when all earlier steps are `done`. When a step finishes `done`, the orchestrator queues the next step automatically. Only one step runs per project at a time (Huey, single worker).

| Step | Waits for operator (`wait_reason`) | Completed by |
|---|---|---|
| idea | `choose_angle` | POST angles/{id}/choose or angles/custom |
| script | `approve_script` | POST script/approve |
| voice | `upload_voice`, then `review_alignment` if anchored_ratio < 0.9 | POST voice (mp3), voice/accept-alignment |
| images | `manual_images` if a slot is `needs_manual` after 3 attempts | images/{slot}/upload |
| preview | `approve_preview` | preview/approve (or apply-comments → new storyboard version → re-preview) |
| any | `budget_exceeded` | PATCH project budget_usd, then run step |

**Invalidation rule:** any change to a step's output marks every later step that is `done`/`waiting_operator`/`failed` as `stale`. This covers re-running source, choosing a different angle, editing facts, saving or approving a new script version, uploading a new mp3, saving a storyboard, and replacing or regenerating images. The one exception: storyboard and image changes do not touch `metadata`. Re-running a step creates new versions and never deletes old files.

## 3. Word budget, scenes, alignment
- `target_words = round(wpm_voice × target_seconds / 60)`, accepted range ±8%. `project.target_words` is a generated column. `target_seconds` is 180–300 (default 240), and `wpm_voice` defaults to 110 from settings. Every uploaded mp3 sets `voice_track.wpm_measured = words / (duration/60)`. The settings value `wpm_voice` then becomes the mean of the last 5 measurements. The UI estimates duration as `word_count / wpm_voice × 60`.
- Hook ≤ round(28 × wpm/110) words. Scenes = `clamp(round(voice_seconds / 5.2), 30, 60)`.
- **PauseAligner (no ASR, owner decision):**
  1. ffmpeg `silencedetect=noise=-35dB:d=0.25` runs on the normalized voice and gives the pauses.
  2. The TTS text (exactly what was voiced) is tokenized on whitespace into words.json `words` and split into sentences on `. ! ? …`.
  3. Each sentence end is assigned to a pause by a monotonic DP. The DP minimizes the distance between the pause centre and the expected time, which is the cumulative character share × speech time, and prefers longer pauses.
  4. Inside a sentence, word times are distributed in proportion to `letters + 1`.

  `quality.anchored_ratio` is the share of sentence ends that landed on a pause; it must be ≥ 0.9, otherwise the step waits for `review_alignment`. Later, `ElevenLabsTimestamps` (same `IAligner`) will turn `/with-timestamps` character alignment into word times.

## 4. Originality guard (separate tables and repositories, no tests)
- The transcript lives only in table `source_material`, read and written only by `app/sources/SourceRepository`.
- Only these modules may import `app.sources`: `pipeline/steps/s01_source.py`, `pipeline/steps/s02_idea.py`, `pipeline/originality_feed.py`, and `api/routers/source.py` (the step-1 UI). This is a code-review rule.
- Steps 3+ get a `StepContext` holding the project row, brief, chosen angle, facts and approved script. There is no transcript field. `ScriptRequest` likewise has no source field.
- The originality checker needs the source. The orchestrator calls `originality_feed.load_reference(project_id) -> OriginalityReference` (a frozen dataclass with sentences and title) and passes it **as an explicit, separately typed argument** to `IOriginalityChecker.check()`. Step 10 gets it the same way for its title-overlap check. It is never passed into a generator prompt.
- The checker returns only `source_index` numbers. `originality_report` stores no source text; the API adds excerpts for display.
- After an auto-rewrite (max 2 rounds), the writer receives only the flagged script sentences and a reason.

## 5. Storyboard → props (backend, `app/media/props.py`)
- `frame(t) = round(t × 30)`. `start_word` and `end_word` are inclusive, and scenes must tile all words contiguously.
- Scene 1 starts at frame 0. Scene i starts at `max(frame(words[start_word-1].end), frame(words[start_word].start) − 3)`. Each scene ends where the next starts; the last ends at `duration_frames = ceil(voice_duration × 30)`.
- Inside a scene, `x_at_word → at = frame(words[w].start) − scene.from` (scene-relative, matching Remotion `<Sequence>` local time). Pose schedule = `[{at:0,pose}] + pose_changes`, with width and height taken from `library/poses/poses.json`. `punch_at_word` becomes `punch:[at]`.
- Captions and SFX use absolute frames: caption `from = frame(first word start)`, `to = frame(last word end) + 6`. SFX `src = /files/library/sfx/{file}.wav`.
- The converter adds a `whoosh` on each background change and a `pop` on each label when they are missing. It then drops SFX closer together than 0.25 s and keeps the count ≤ 24 per minute.
- Rule validation (backend `storyboard_rules.py`, run before saving; failures go to `storyboard.errors`): contiguous tiling; scene length 2.5–7.5 s (up to 9 s if ≥ 3 events); each background used 2–4 times; a reused background changes `focus` by ≥ 0.15 or zoom by ≥ 0.05; ≥ 2 events per scene; first event ≤ 0.6 s after the scene starts; hook (first 15 s) has ≥ 4 scenes of ≤ 4 s each; caption phrases are 2–7 words and ≤ 42 characters per line; each keyword prefix-matches exactly one word; all `at_word` values fall inside the scene; poses exist in poses.json. Label limits (≤ 5 words, ≤ 24 characters), the scene count (30–60, for 3–5 min) and the background count (12–15) are enforced by the schema itself.

## 6. Remotion invocation and assets
- The backend serves `DATA_DIR` at `/files/data/` and `LIBRARY_DIR` at `/files/library/` (Starlette StaticFiles). props.json contains **absolute URLs** built from `ASSET_BASE_URL` (default `http://127.0.0.1:8000`). Remotion loads assets over HTTP, so nothing is copied, and the same props work in Remotion Studio and `@remotion/player`. The engine resolves `src` as an http URL, or with `staticFile(src)` for its own fixtures.
- Python runs `[NODE_BIN, "engine/scripts/render.mjs", "--props", p, "--out", mp4]` via `subprocess` with a list of args (no shell, so it works the same on Windows and macOS). It reads JSON lines `{"progress":0.42}` from stdout into `project_step.progress` and uses a 60-minute timeout. A non-zero exit is a failed step with stderr written to job_log. Stills: `engine/scripts/stills.mjs --props p --frames f1,f2,… --out dir` renders mid-scene frames, and the backend composes the contact sheet with Pillow.
- After the render, the backend checks that the duration equals the mp3 duration ± 0.5 s. It masters the audio with ffmpeg loudnorm to −14 LUFS / −1 dBTP and remuxes with `-c:v copy` (the voice stem is −16 LUFS). It also runs a glyph check: every character of the props text must be in the font cmap (fontTools); any miss fails the step.

## 7. Money, settings, DB
- **Budget guard:** before each paid call, `ICostLedger.guard(ctx, estimate)`. If project spent + estimate > `project.budget_usd` (default **$5**, from settings), it raises `BudgetExceeded`; the step goes to `waiting_operator/budget_exceeded`, and the operator can raise `budget_usd` and continue. The UI warns at $2.50. There is also a monthly app stop (default $60 ≈ 12 videos × $5, setting). The call writes a `cost_entry` with prices from `pricing`, using the latest `effective_from ≤ today`. A trigger keeps `project.cost_usd` in sync. Gemini HTTP 429 (spend cap) and 402 errors are reported as BudgetExceeded and not retried.
- **Settings:** secrets and machine paths live in `.env` only. Operator-editable values live in `settings.data` (jsonb, singleton row), seeded from `.env` defaults on first start; after that the DB wins.
- **Supabase:** use the Session pooler URL (`…pooler.supabase.com:5432`, `sslmode=require`). Never use 6543, and the direct host is IPv6-only. SQLAlchemy: `pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=1800`. Keep-alive is `SELECT 1` on start and daily. If the DB is unreachable, the UI shows "Supabase project may be paused — Resume in dashboard". A weekly `pg_dump -Fc` writes to `data/backups/` and keeps 8. The free plan has no automatic backups. RLS is enabled on all tables with no policies, which blocks the public Data API; the app is the owner and bypasses RLS.
- Migrations are applied in order by a backend script (psycopg), which records them in `schema_migrations`.

## 8. Open issues (for LEAD / owner)
1. **pg_dump version:** local client tools are PG 16, and new Supabase projects run PG 17, so `pg_dump` 16 will refuse to dump them. Install the PostgreSQL 17 client, or the backup script must fall back to a per-table JSON export.
2. **Monthly limit** was not re-decided after the $5/video change. I kept the research defaults: app stop $35 and AI Studio spend cap $40. 12 videos at the typical ~$2 fits; 12 at $5 does not.
3. **Word budget wording conflicts:** `kazakh_market` R5 and the ai-engineer agent file still say "500–550 words". The owner decision (brief §10) wins: words come from wpm (440 for 4:00).
4. **Similarity threshold:** 0.8 is a placeholder until it is calibrated on ≥ 20 labelled kk pairs (tools_costs R8).
5. **Example data:** `/schemas/examples` facts and URLs are illustrative, not verified, and must not be reused as real facts.
6. The brief §6.5 example has a scene-level `caption_keyword`. Rule 12 (one keyword per 2–7-word phrase) needs the optional `captions[]` split, which was added.
