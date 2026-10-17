"""Step 5: operator uploads the ElevenLabs mp3 -> loudnorm -16 LUFS wav -> PauseAligner -> words.json.
Waits for `upload_voice`, and for `review_alignment` when anchored_ratio < 0.9."""
from __future__ import annotations

import re
import statistics
import uuid
from decimal import Decimal

from sqlalchemy import select, update

from app import app_settings
from app.db import session_scope
from app.media import ffmpeg
from app.media.aligner import PauseAligner
from app.models import Project, VoiceTrack
from app.pipeline.media_state import approved_script, current_track
from app.pipeline.orchestrator import DONE, StepResult, job_log, register
from app.schemas import errors as schema_errors
from app.storage import abs_data, next_version, project_dir, rel, write_json

MAX_SECONDS = 10 * 60
WPM_SANE = (85, 160)     # measurements outside this range (wrong file, test audio) are not averaged


def save_upload(project_id: uuid.UUID, data: bytes, model_id: str, provider_plan: str) -> uuid.UUID:
    """Store upload_v{n}.mp3, validate it is audio, make it the current track (API side)."""
    folder = project_dir(project_id, "voice")
    n = next_version(folder, "upload_v", ".mp3")
    path = folder / f"upload_v{n}.mp3"
    path.write_bytes(data)
    try:
        if not ffmpeg.has_audio(path):
            raise ValueError("no audio stream")
        dur = ffmpeg.duration(path)
    except Exception as e:  # noqa: BLE001
        path.unlink(missing_ok=True)
        raise ValueError(f"Not an audio file: {e}") from e
    if dur > MAX_SECONDS:
        path.unlink(missing_ok=True)
        raise ValueError(f"Audio is {dur:.0f} s; max {MAX_SECONDS} s")
    with session_scope() as db:
        script = approved_script(db, project_id)
        if script is None:
            raise ValueError("No approved script")
        db.execute(update(VoiceTrack).where(VoiceTrack.project_id == project_id).values(is_current=False))
        t = VoiceTrack(project_id=project_id, script_id=script.id, upload_path=rel(path), duration=dur,
                       provider="manual_upload", provider_plan=provider_plan, model_id=model_id, is_current=True)
        db.add(t)
        db.flush()
        job_log(db, project_id, "voice", f"Uploaded {path.name} ({dur:.1f} s, {model_id}, plan {provider_plan})")
        return t.id


def _version(upload_path: str) -> int:
    m = re.search(r"upload_v(\d+)", upload_path)
    return int(m.group(1)) if m else 1


def _update_wpm(db, project_id: uuid.UUID) -> float | None:
    """settings.wpm_voice and project.wpm_voice = mean of the last 5 sane measurements."""
    vals = [v for v in db.scalars(select(VoiceTrack.wpm_measured).where(VoiceTrack.wpm_measured.is_not(None))
                                  .order_by(VoiceTrack.created_at.desc()).limit(20))
            if WPM_SANE[0] <= v <= WPM_SANE[1]][:5]
    if not vals:
        return None
    mean = round(statistics.mean(vals), 1)
    app_settings.save(db, {"wpm_voice": mean})
    db.get(Project, project_id).wpm_voice = Decimal(str(mean))
    return mean


@register("voice")
def run(project_id: uuid.UUID) -> StepResult:
    with session_scope() as db:
        script = approved_script(db, project_id)
        if script is None or not script.tts_text:
            raise RuntimeError("No approved script with TTS text (step 4)")
        track = current_track(db, project_id)
        if track is None or track.script_id != script.id:
            return StepResult.wait("upload_voice")
        track_id, upload, tts_text = track.id, track.upload_path, script.tts_text
        language = db.get(Project, project_id).language

    n = _version(upload)
    folder = project_dir(project_id, "voice")
    norm = folder / f"voice_v{n}.norm.wav"
    loud = ffmpeg.normalize_voice(abs_data(upload), norm)
    doc = PauseAligner().align(norm, tts_text, language)
    words_rel = write_json(folder / f"words_v{n}.json", doc)
    q = doc["quality"]

    with session_scope() as db:
        for e in schema_errors("words", doc):
            job_log(db, project_id, "voice", f"words.schema: {e}", "warning")
        t = db.get(VoiceTrack, track_id)
        t.path, t.duration, t.words_json = rel(norm), doc["duration"], doc
        t.wpm_measured, t.alignment_ok = q["wpm_measured"], q["ok"]
        db.flush()
        mean = _update_wpm(db, project_id)
        job_log(db, project_id, "voice",
                f"Normalized {loud.get('input_i')} -> -16 LUFS; {doc['duration']:.1f} s, {len(doc['words'])} words, "
                f"{len(doc['sentences'])} sentences, {len(doc['pauses'])} pauses, anchored {q['anchored_ratio']:.0%}, "
                f"{q['wpm_measured']} wpm (rolling wpm_voice {mean}) -> {words_rel}")
        for w in q.get("warnings", []):
            job_log(db, project_id, "voice", w, "warning")
    return DONE if q["ok"] else StepResult.wait("review_alignment")

