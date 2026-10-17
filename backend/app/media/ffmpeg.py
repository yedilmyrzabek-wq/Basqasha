"""ffmpeg / ffprobe via subprocess (list args, no shell: same on Windows and macOS)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

_SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


@lru_cache
def _bin(name: str) -> str:
    """Configured binary, else PATH, else ~/tools/ffmpeg/bin (the owner's Windows install)."""
    configured = getattr(get_settings(), f"{name}_bin")
    found = shutil.which(configured) or (configured if Path(configured).is_file() else None)
    if found:
        return found
    for cand in (Path.home() / "tools" / "ffmpeg" / "bin" / f"{name}.exe",
                 Path.home() / "tools" / "ffmpeg" / "bin" / name):
        if cand.is_file():
            return str(cand)
    raise RuntimeError(f"{name} not found (set {name.upper()}_BIN in .env)")


def _run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{Path(args[0]).name} failed ({r.returncode}): {r.stderr[-1500:]}")
    return r


def duration(path: Path) -> float:
    r = _run([_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
    return float(json.loads(r.stdout)["format"]["duration"])


def has_audio(path: Path) -> bool:
    r = _run([_bin("ffprobe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
              "-of", "json", str(path)])
    return bool(json.loads(r.stdout).get("streams"))


def _loudnorm_measure(src: Path, i: float, tp: float, lra: float) -> dict:
    r = _run([_bin("ffmpeg"), "-hide_banner", "-nostats", "-i", str(src), "-af",
              f"loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        raise RuntimeError("loudnorm measurement not found in ffmpeg output")
    return json.loads(m.group(0))


def _loudnorm_filter(src: Path, i: float, tp: float, lra: float) -> tuple[str, dict]:
    """Two-pass loudnorm: measure, then apply linearly with the measured values."""
    m = _loudnorm_measure(src, i, tp, lra)
    f = (f"loudnorm=I={i}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
         f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
         "linear=true:print_format=summary")
    return f, m


def normalize_voice(src: Path, out_wav: Path, lufs: float = -16.0) -> dict:
    """Voice stem -> mono 48 kHz wav at ``lufs`` (two-pass loudnorm). Returns the measurement."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    f, m = _loudnorm_filter(src, lufs, -1.5, 11)
    _run([_bin("ffmpeg"), "-hide_banner", "-y", "-i", str(src), "-af", f, "-ac", "1", "-ar", "48000",
          "-c:a", "pcm_s16le", str(out_wav)])
    return m


def silences(path: Path, noise_db: float = -35, min_d: float = 0.25) -> list[tuple[float, float]]:
    """ffmpeg silencedetect -> [(start, end)] in seconds (a trailing open silence ends at the file end)."""
    r = _run([_bin("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-af",
              f"silencedetect=noise={noise_db}dB:d={min_d}", "-f", "null", "-"])
    out, start = [], None
    for line in r.stderr.splitlines():
        if (m := _SIL_START.search(line)):
            start = max(0.0, float(m.group(1)))
        elif (m := _SIL_END.search(line)) and start is not None:
            out.append((round(start, 3), round(float(m.group(1)), 3)))
            start = None
    if start is not None:
        out.append((round(start, 3), round(duration(path), 3)))
    return out


def master_video(src_mp4: Path, out_mp4: Path, lufs: float = -14.0, tp: float = -1.0) -> dict:
    """Final audio mastering (-14 LUFS / -1 dBTP), video stream copied."""
    f, m = _loudnorm_filter(src_mp4, lufs, tp, 11)
    _run([_bin("ffmpeg"), "-hide_banner", "-y", "-i", str(src_mp4), "-af", f, "-c:v", "copy",
          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out_mp4)], timeout=1800)
    return m


def loudness(path: Path) -> float:
    """Integrated loudness (LUFS) of a file."""
    return float(_loudnorm_measure(path, -14, -1, 11)["input_i"])
