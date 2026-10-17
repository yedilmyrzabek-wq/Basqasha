"""PauseAligner (IAligner, no ASR — owner decision; ARCHITECTURE §3).

1. silencedetect on the normalized voice -> pauses.
2. TTS text -> whitespace tokens (= words.json words; punctuation-only tokens such as "—" are
   dropped) grouped into phrases (end on , ; : — ) and sentences (end on . ! ? … and paragraphs).
3. Phrase/sentence ends are matched to pauses by a monotonic DP on a "speech clock" (time with
   the pauses removed). Segment cost = |measured speech time - expected| where expected = the
   segment's character share x total speech time. Long pauses get a bonus when used and a cost
   when left unused; a missed sentence end costs much more than a missed phrase end (voices often
   do not pause at commas). Unanchored ends are interpolated.
4. Inside a phrase, word times follow the speech clock in proportion to letters + 1.
quality.anchored_ratio = share of sentence ends that landed on a pause.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from app.media import ffmpeg

SENT_END = re.compile(r"[.!?…]+$")
PHRASE_END = re.compile(r"[,;:—–]+$")
CLOSERS = "\"'»”’)]"
MAX_SKIP = 8              # unanchored ends allowed between two anchors (falls back to unlimited)
SKIP_SENTENCE = 1.5       # s of timing error a missed sentence-end pause is worth
SKIP_PHRASE = 0.25
BONUS_SENTENCE = 1.5      # x pause length (capped at 1 s): sentence ends sit on the long pauses
BONUS_PHRASE = 0.5
UNUSED_COST = 1.0         # x pause length (capped at 1 s) for a pause no boundary landed on
EDGE = 0.05


def _letters(w: str) -> int:
    return sum(ch.isalnum() for ch in w)


def tokenize(text: str) -> tuple[list[str], list[int], list[int]]:
    """Words, sentence index per word, phrase index per word."""
    words: list[str] = []
    sent: list[int] = []
    phrase: list[int] = []
    s = ph = 0

    def close(sentence: bool) -> None:
        nonlocal s, ph
        if words and phrase[-1] == ph:
            ph += 1
            if sentence:
                s += 1

    for para in re.split(r"\n\s*\n", text.strip()):
        for tok in para.split():
            core = tok.rstrip(CLOSERS)
            if _letters(tok) == 0:              # "—", "…" alone: not spoken, but a boundary
                close(bool(SENT_END.search(core)))
                continue
            words.append(tok)
            sent.append(s)
            phrase.append(ph)
            if SENT_END.search(core):
                close(True)
            elif PHRASE_END.search(core):
                close(False)
        close(True)                             # paragraph end closes the sentence
    return words, sent, phrase


class _Clock:
    """Real time <-> speech time (real time minus the internal pauses)."""

    def __init__(self, speech_start: float, pauses: list[tuple[float, float]]):
        self.t0 = speech_start
        self.pauses = pauses
        self.pos: list[float] = []
        gone = 0.0
        for a, b in pauses:
            self.pos.append(a - speech_start - gone)
            gone += b - a

    def real(self, c: float, after: bool) -> float:
        """Real time for speech-clock ``c``; exactly at a pause, ``after`` picks the pause end."""
        t = self.t0 + c
        for p, (a, b) in zip(self.pos, self.pauses):
            if p < c - 1e-6 or (after and abs(p - c) <= 1e-6):
                t += b - a
            else:
                break
        return t


class PauseAligner:
    kind = "pause"

    def align(self, audio: Path, tts_text: str, language: str,
              char_alignment: Mapping[str, Any] | None = None) -> dict[str, Any]:
        words, sent, phrase = tokenize(tts_text)
        if not words:
            raise ValueError("TTS text has no words")
        return align_words(words, sent, phrase, ffmpeg.duration(audio), ffmpeg.silences(audio), language)


def align_words(words: list[str], sent: list[int], phrase: list[int], dur: float,
                sil: list[tuple[float, float]], language: str) -> dict[str, Any]:
    warnings: list[str] = []
    sil = sorted(sil)
    speech_start, speech_end = 0.0, dur
    if sil and sil[0][0] <= EDGE:
        speech_start = sil[0][1]
        sil = sil[1:]
    if sil and sil[-1][1] >= dur - EDGE:
        speech_end = sil[-1][0]
        sil = sil[:-1]
    if speech_end - speech_start < 1.0:
        raise ValueError("No speech detected in the voice file")
    internal = [(a, b) for a, b in sil if a > speech_start and b < speech_end]
    clock = _Clock(speech_start, internal)
    speech_total = (speech_end - speech_start) - sum(b - a for a, b in internal)

    # units = phrases; unit u ends a sentence if the next word starts a new sentence
    n_units = phrase[-1] + 1
    weights = np.array([_letters(w) + 1 for w in words], dtype=float)
    uw = np.zeros(n_units)
    np.add.at(uw, np.array(phrase), weights)
    ucum = np.cumsum(uw)
    unit_start = [0] * (n_units + 1)
    for i in range(len(words) - 1, -1, -1):
        unit_start[phrase[i]] = i
    unit_start[n_units] = len(words)
    is_sent_end = np.array([u == n_units - 1 or sent[unit_start[u + 1]] != sent[unit_start[u]]
                            for u in range(n_units)])
    skip_cost = np.where(is_sent_end, SKIP_SENTENCE, SKIP_PHRASE)
    skip_cum = np.concatenate([[0.0], np.cumsum(skip_cost)])   # skip_cum[k] = cost of units < k

    # pause table: 0 = speech start, 1..M = internal pauses, M+1 = speech end
    m = len(internal)
    pos = np.array([0.0] + clock.pos + [speech_total])
    plen = np.minimum(np.array([0.0] + [b - a for a, b in internal] + [0.0]), 1.0)
    unused_cum = np.concatenate([[0.0], np.cumsum(UNUSED_COST * plen)])  # unused_cum[j] = pauses < j

    bonus = np.where(is_sent_end, BONUS_SENTENCE, BONUS_PHRASE)
    anchor = (_match(pos, plen, unused_cum, ucum, skip_cum, bonus, speech_total, n_units, m, MAX_SKIP)
              or _match(pos, plen, unused_cum, ucum, skip_cum, bonus, speech_total, n_units, m, n_units))

    # speech-clock end of every unit (interpolate the unanchored ones by character share)
    ends = np.zeros(n_units)
    keys = sorted(anchor)
    for a, b in zip(keys, keys[1:]):
        ca, cb = pos[anchor[a]], pos[anchor[b]]
        wa = ucum[a] if a >= 0 else 0.0
        for u in range(a + 1, b + 1):
            ends[u] = ca + (ucum[u] - wa) / max(ucum[b] - wa, 1e-9) * (cb - ca)

    out_words: list[dict[str, Any]] = []
    for u in range(n_units):
        c0 = ends[u - 1] if u > 0 else 0.0
        w0, w1 = unit_start[u], unit_start[u + 1]
        ws = weights[w0:w1]
        edges = c0 + np.concatenate([[0.0], np.cumsum(ws)]) / ws.sum() * (ends[u] - c0)
        for i in range(w0, w1):
            out_words.append({"i": i, "w": words[i], "s": sent[i],
                              "start": round(clock.real(edges[i - w0], after=True), 3),
                              "end": round(clock.real(edges[i - w0 + 1], after=False), 3)})
    for w in out_words:                          # guard against rounding inversions
        w["end"] = max(w["end"], w["start"])

    sentences: list[dict[str, Any]] = []
    for u in np.flatnonzero(is_sent_end):
        k = len(sentences)
        w0 = sentences[-1]["end_word"] + 1 if sentences else 0
        w1 = unit_start[u + 1] - 1
        sentences.append({"i": k, "start_word": w0, "end_word": w1, "start": out_words[w0]["start"],
                          "end": out_words[w1]["end"], "anchored": int(u) in anchor})

    n_sent = len(sentences)
    anchored_ratio = round(sum(s["anchored"] for s in sentences) / n_sent, 3)
    wpm = round(len(words) / (dur / 60), 1)
    if not 60 <= wpm <= 220:
        warnings.append(f"Unusual pace {wpm} wpm: does the mp3 match the approved text?")
    if m < n_sent - 1:
        warnings.append(f"Only {m} pauses for {n_sent} sentences: the voice may run sentences together")
    return {"language": language, "duration": round(dur, 3), "aligner": "pause", "words": out_words,
            "sentences": sentences, "pauses": [[a, b] for a, b in internal],
            "quality": {"anchored_ratio": anchored_ratio, "ok": anchored_ratio >= 0.9,
                        "wpm_measured": wpm, "warnings": warnings}}


def _match(pos: np.ndarray, plen: np.ndarray, unused_cum: np.ndarray, ucum: np.ndarray,
           skip_cum: np.ndarray, bonus: np.ndarray, speech_total: float, n_units: int, m: int,
           max_skip: int) -> dict[int, int] | None:
    """Monotonic DP: unit end u -> pause j (1..m internal, m+1 = speech end). None if no path.
    D[u+1][j] = best cost with unit end u anchored at pause j; row 0 = virtual start at pause 0."""
    inf = float("inf")
    wtot = float(ucum[-1])
    D = np.full((n_units + 1, m + 2), inf)
    back: dict[tuple[int, int], tuple[int, int]] = {}
    D[0][0] = 0.0
    for u in range(n_units):
        targets = [m + 1] if u == n_units - 1 else range(1, m + 1)
        for j in targets:
            best, arg = inf, None
            for up in range(u - 1, max(-1, u - 1 - max_skip) - 1, -1):   # previous anchored end
                row = D[up + 1][:j]
                if not np.isfinite(row).any():
                    continue
                exp_span = (ucum[u] - (ucum[up] if up >= 0 else 0.0)) / wtot * speech_total
                skipped = skip_cum[u] - skip_cum[up + 1]                  # units up+1 .. u-1
                unused = unused_cum[j] - unused_cum[1:j + 1]               # pauses jp+1 .. j-1
                cost = row + np.abs(pos[j] - pos[:j] - exp_span) + skipped + unused
                jp = int(np.argmin(cost))
                if cost[jp] < best:
                    best, arg = float(cost[jp]), (up, jp)
            if arg is not None:
                D[u + 1][j] = best - bonus[u] * plen[j]
                back[(u, j)] = arg
    if (n_units - 1, m + 1) not in back:
        return None
    anchor: dict[int, int] = {-1: 0}
    u, j = n_units - 1, m + 1
    while u >= 0:
        anchor[u] = j
        u, j = back[(u, j)]
    return anchor
