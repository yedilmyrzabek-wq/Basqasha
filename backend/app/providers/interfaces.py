"""Provider contracts (owned by architect). Protocols + DTOs only — no implementations.

JSON documents are passed as ``Mapping[str, Any]`` conforming to ``/schemas/*.schema.json``.
Every implementation that calls a paid external API must call ``ICostLedger.guard`` before
and ``ICostLedger.record`` after the call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol, Sequence, TypeVar
from uuid import UUID

Language = Literal["kk", "ru", "en"]
StepKey = Literal["source", "idea", "facts", "script", "voice",
                  "storyboard", "images", "preview", "render", "metadata"]
T = TypeVar("T")  # a Pydantic model class mirroring a JSON Schema


class BudgetExceeded(Exception):
    """Project budget (project.budget_usd) or the monthly app stop would be exceeded.
    The orchestrator sets the step to waiting_operator / wait_reason='budget_exceeded'."""


class OperatorActionRequired(Exception):
    """A manual provider cannot proceed without the operator (upload, approval)."""


@dataclass(frozen=True)
class CallContext:
    """Who pays for a call: used by the cost ledger and the job log."""
    project_id: UUID | None
    step: StepKey | None


@dataclass(frozen=True)
class OriginalityReference:
    """The ONLY way source-transcript content reaches code after step 2.
    Built by ``app.pipeline.originality_feed`` (allowed to use SourceRepository) and passed
    explicitly by the orchestrator to the originality checker (step 4) and the title-overlap
    check (step 10). Never given to a generator prompt."""
    sentences: tuple[str, ...]
    title: str | None = None


# ----------------------------------------------------------------- cost
class ICostLedger(Protocol):
    def estimate(self, provider: str, model: str, units: Mapping[str, float]) -> Decimal:
        """USD for ``units`` (e.g. {"input_tokens": 8000, "output_tokens": 6000} or {"images": 1,
        "image_size": "2K"}) using the pricing row with the latest effective_from <= today."""
        ...

    def guard(self, ctx: CallContext, estimated_usd: Decimal) -> None:
        """Raise BudgetExceeded if project spent + estimate > project.budget_usd (default $5)
        or month-to-date + estimate >= monthly stop. Returns None when the call may proceed."""
        ...

    def record(self, ctx: CallContext, provider: str, model: str,
               units: Mapping[str, float], tier: str = "standard") -> Decimal:
        """Insert a cost_entry row (usd computed from pricing; Claude CLI = 0) and return usd."""
        ...


# ----------------------------------------------------------------- LLM
@dataclass(frozen=True)
class LLMResult[R]:
    value: R
    model: str
    usage: Mapping[str, int]                      # input_tokens, output_tokens, thinking_tokens
    grounding_urls: tuple[str, ...] = ()          # when grounding=True


class ILLM(Protocol):
    """Gemini (google-genai) client. Implementations log cost per call."""

    def generate_json(self, *, prompt: str, response_model: type[T], model: str, ctx: CallContext,
                      system: str | None = None, grounding: bool = False,
                      images: Sequence[Path] = (), max_output_tokens: int | None = None) -> LLMResult[T]:
        """Structured output validated into ``response_model``; at most 1 JSON-repair retry.
        ``grounding`` enables Google Search (facts step); ``images`` enables vision (image QA)."""
        ...

    def embed(self, texts: Sequence[str], *, model: str, ctx: CallContext, dim: int = 768) -> list[list[float]]:
        """Sentence embeddings (gemini-embedding-2, 768 dims) for originality / topic similarity."""
        ...


# ----------------------------------------------------------------- script
@dataclass(frozen=True)
class ScriptRequest:
    """Everything a writer may see. Deliberately has NO source/transcript field."""
    language: Language
    brief: Mapping[str, Any]                      # brief.schema.json#/properties/brief
    angle: Mapping[str, Any]                      # brief.schema.json#/$defs/angle
    facts: Sequence[Mapping[str, Any]]            # verified facts only
    target_words: int
    avoid_hook_types: Sequence[str] = ()          # hook types of the last 3 projects
    avoid_structures: Sequence[str] = ()
    operator_notes: str | None = None


class IScriptWriter(Protocol):
    """Gemini (default) or ClaudeCodeCLI (`claude -p`, usd=0, falls back to Gemini on failure)."""
    kind: Literal["gemini", "claude_code"]

    def write(self, req: ScriptRequest, ctx: CallContext) -> Mapping[str, Any]:
        """Return a script.schema.json document (word count within target +-8%)."""
        ...

    def rewrite_sentences(self, script: Mapping[str, Any], sentence_indexes: Sequence[int],
                          reason: str, ctx: CallContext) -> Mapping[str, Any]:
        """Rewrite only the given sentences (originality auto-rewrite, max 2 rounds). The writer
        gets the reason, never the source text."""
        ...


class IOriginalityChecker(Protocol):
    def check(self, script: Mapping[str, Any], reference: OriginalityReference,
              ctx: CallContext) -> Mapping[str, Any]:
        """Sentence embeddings + LLM judge. Returns {max_similarity, verdict, flagged_sentences:
        [{index, text, similarity, source_index}], ...}. Source text is not copied into the result."""
        ...


# ----------------------------------------------------------------- voice + alignment
@dataclass(frozen=True)
class VoiceAudio:
    path: Path                                    # file as received / synthesized
    provider: Literal["manual_upload", "elevenlabs_api"]
    model_id: str                                 # eleven_v4 | eleven_v3 for kk
    provider_plan: str = "unknown"                # free | starter | creator | pro | unknown
    char_alignment: Mapping[str, Any] | None = None  # ElevenLabs /with-timestamps payload


class IVoiceProvider(Protocol):
    """ManualUpload now; ElevenLabsApi later behind ELEVENLABS_API_ENABLED."""
    kind: Literal["manual_upload", "elevenlabs_api"]

    def synthesize(self, tts_text: str, language: Language, ctx: CallContext) -> VoiceAudio:
        """API provider: produce audio. ManualUpload raises OperatorActionRequired."""
        ...

    def ingest_upload(self, upload: Path, model_id: str, provider_plan: str) -> VoiceAudio:
        """ManualUpload: accept the operator's mp3 (reject non-audio, > 10 min)."""
        ...


class IAligner(Protocol):
    """PauseAligner now (no ASR, owner decision); ElevenLabsTimestamps later."""
    kind: Literal["pause", "elevenlabs_timestamps"]

    def align(self, audio: Path, tts_text: str, language: Language,
              char_alignment: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Return a words.schema.json document for ``tts_text`` tokens. PauseAligner: ffmpeg
        silencedetect -> map sentence ends onto pauses -> distribute word times inside a
        sentence proportionally to character length. quality.ok = anchored_ratio >= 0.9."""
        ...


# ----------------------------------------------------------------- images
@dataclass(frozen=True)
class ImageRequest:
    slot: str                                     # 'bg01'
    prompt: str                                   # STYLE SUFFIX is appended by the provider
    out_path: Path
    style_suffix: str
    reference_images: Sequence[Path] = ()
    aspect_ratio: str = "16:9"
    image_size: str = "2K"


@dataclass(frozen=True)
class GeneratedImage:
    path: Path
    width: int
    height: int
    model: str
    source: Literal["generated", "manual_upload", "library", "purchased"] = "generated"
    license: str = "own:gemini-api-output"
    is_photoreal: bool = False
    depicts_real_person: bool = False


class IImageProvider(Protocol):
    """GeminiImage (gemini-nano-banana-2.1) now; ManualUpload fallback (images from Flow)."""
    kind: Literal["gemini", "manual_upload"]

    def generate(self, req: ImageRequest, ctx: CallContext) -> GeneratedImage:
        """One attempt. The image step does QA and retries (max 3, then needs_manual).
        ManualUpload raises OperatorActionRequired."""
        ...


# ----------------------------------------------------------------- publish
@dataclass(frozen=True)
class PublishRequest:
    project_id: UUID
    video: Path
    metadata: Mapping[str, Any]                   # metadata.schema.json
    thumbnail: Path | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)


class IPublisher(Protocol):
    """Manual now (operator uploads in YouTube Studio and pastes the URL); YouTubeApi later."""
    kind: Literal["manual", "youtube_api"]

    def publish(self, req: PublishRequest) -> str | None:
        """Return the video URL, or None when the operator must finish manually.
        Must refuse if checklist.made_for_kids is not false or the voice plan is free."""
        ...
