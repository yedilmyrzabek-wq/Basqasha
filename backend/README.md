# backend — FastAPI + Huey pipeline

Start everything (API :8000, worker, frontend :5173) from the repo root:

```
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1     # Windows
./scripts/dev.sh                                              # macOS / Linux
```
A crashed service is restarted after 3 s; Ctrl+C stops all. Needs `uv`, Node 22 (`npm install` in `engine/`
and `frontend/`), ffmpeg/ffprobe on PATH (or `FFMPEG_BIN`/`FFPROBE_BIN`, or `%USERPROFILE%\tools\ffmpeg\bin`).
Without the dev script: `uv run uvicorn app.main:app` and `uv run python -m app.worker` in `backend/`.

## Steps 5–10 (demo after an approved script)
1. **Voice** — copy the text («Копировать текст для ElevenLabs»), voice it in ElevenLabs (Eleven v4/v3), upload the mp3.
   The step normalizes to −16 LUFS (`voice/voice_v{n}.norm.wav`) and aligns without ASR (`voice/words_v{n}.json`,
   `app/media/aligner.py`). If < 90% of sentence ends land on pauses it waits for «Принять синхронизацию».
2. **Storyboard** — runs automatically (`ai.storyboard`); auto-repairs word tiling / unknown poses, rule issues are
   listed under the storyboard (`storyboard/storyboard_v{n}.json`).
3. **Images** — Gemini per slot. On the free tier (HTTP 429) the slots become «нужна вручную»: upload your own, or
   fill them with the placeholder samples from `library/style/samples`:
   `POST /api/projects/{id}/images/use-samples` (only empty slots; `?all_slots=true` = every slot), or set
   `"image_source": "samples"` via `PUT /api/settings` so step 7 always uses samples.
4. **Preview** — Remotion stills of every scene's middle frame → `render/contact_sheet_v{n}.png`; comment scenes,
   «Применить комментарии» (new storyboard version → images → preview) or «Утвердить».
5. **Render** — `engine/scripts/render.mjs` (≈ 2× real time), master −14 LUFS / −1 dBTP → `render/final_v{n}.mp4`;
   fails if the duration differs from the voice by > 0.5 s. «Скачать» = file URL + `?download=1`.
6. **Metadata** — `ai.metadata` → `meta/meta.md` + DB.

Assets in props are paths relative to the common parent of `DATA_DIR` and `LIBRARY_DIR`; the engine serves them
itself (`--root`), so renders do not depend on the API process.
