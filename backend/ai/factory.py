"""One place that wires the AI layer from settings. The backend calls build_ai(ledger)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.app_settings import STYLE_SUFFIX
from app.config import Settings, get_settings
from app.providers.interfaces import CallContext, ICostLedger, OriginalityReference
from ai.facts import FactsResult, research_facts
from ai.claude_cli import ClaudeCodeLLM
from ai.gemini import GeminiLLM
from ai.idea import generate_idea
from ai.images import GeminiImageProvider, generate_background
from ai.metadata import build_metadata
from ai.originality import OriginalityChecker, run_originality
from ai.script import ScriptWriter
from ai.storyboard import build_storyboard
from ai.tts import TtsExport, export_tts

TEXT_FALLBACK = "gemini-3.6-flash"


@dataclass
class AI:
    settings: Settings
    llm: GeminiLLM | ClaudeCodeLLM
    writer: ScriptWriter
    checker: OriginalityChecker
    images: GeminiImageProvider
    style_suffix: str = STYLE_SUFFIX       # operator setting settings.data.style_suffix (pass to build_ai)

    def idea(self, transcript: str, *, language: str, ctx: CallContext, source_title: str = "",
             source_minutes: float = 0, source_views: int | None = None,
             operator_hint: str | None = None, target_seconds: int = 240, wpm: float = 110) -> dict[str, Any]:
        # idea uses the script model (Opus via Claude CLI): picking the angle is as important as the text
        return generate_idea(self.llm, transcript, language=language, ctx=ctx, model=self.settings.model_script,
                             source_title=source_title, source_minutes=source_minutes,
                             source_views=source_views, operator_hint=operator_hint,
                             target_seconds=target_seconds, wpm=wpm)

    def facts(self, brief: Mapping[str, Any], angle: Mapping[str, Any], *, language: str,
              ctx: CallContext, max_facts: int = 12) -> FactsResult:
        return research_facts(self.llm, brief, angle, language=language, ctx=ctx,
                              model=self.settings.model_text, cheap_model=self.settings.model_cheap,
                              max_facts=max_facts)

    def originality(self, script: Mapping[str, Any], reference: OriginalityReference,
                    ctx: CallContext) -> tuple[Mapping[str, Any], dict[str, Any]]:
        return run_originality(self.writer, self.checker, script, reference, ctx)

    @staticmethod
    def tts(script: Mapping[str, Any]) -> TtsExport:
        return export_tts(script)

    def storyboard(self, script_doc: Mapping[str, Any], words_doc: Mapping[str, Any], poses: list[dict],
                   sfx_names: list[str], *, language: str, ctx: CallContext,
                   operator_comments: str | None = None, n_backgrounds: int = 30) -> dict[str, Any]:
        """Step 6: storyboard.schema.json document (2-3 LLM calls; timing/layout/fixes in code)."""
        return build_storyboard(self.llm, self.settings.model_text, script_doc, words_doc, poses, sfx_names,
                                language=language, ctx=ctx, operator_comments=operator_comments,
                                n_backgrounds=n_backgrounds)

    def background_image(self, prompt: str, out_path: Path, *, ctx: CallContext,
                         style_refs: Sequence[Path] = (), style_suffix: str | None = None) -> dict[str, Any]:
        """Step 7, one slot: generate -> vision QA -> retry (max 3). Returns {path, model, qa_status:
        ok|failed|needs_manual, qa_notes, attempts, width, height, is_photoreal, depicts_real_person}.
        failed = 3 QA rejections (last image kept at path); needs_manual = no usable image or QA
        unavailable (429 / free tier / no key) — the operator uploads or reviews the slot."""
        refs = list(style_refs) or sorted(
            p for p in (self.settings.library_path / "style" / "samples").glob("*")
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
        return generate_background(self.images, self.llm, prompt, Path(out_path),
                                   style_suffix=style_suffix or self.style_suffix, style_refs=refs,
                                   qa_model=self.settings.model_cheap, ctx=ctx)

    def metadata(self, script_doc: Mapping[str, Any], facts_doc: Mapping[str, Any],
                 storyboard_doc: Mapping[str, Any], *, language: str, ctx: CallContext,
                 words_doc: Mapping[str, Any] | None = None, ai_disclosure: bool = False,
                 paid_promotion: bool = False, voice_plan_paid: bool | None = None,
                 reference: OriginalityReference | None = None, **source: Any) -> dict[str, Any]:
        """Step 10: metadata.schema.json document (1 LLM call, +1 only to repair broken titles).
        words_doc gives exact chapter times (otherwise estimated from wpm_voice); reference = the
        OriginalityReference for the title-overlap check (ARCHITECTURE §4)."""
        return build_metadata(self.llm, self.settings.model_text, script_doc, facts_doc, storyboard_doc,
                              language=language, ctx=ctx, words_doc=words_doc, ai_disclosure=ai_disclosure,
                              paid_promotion=paid_promotion, voice_plan_paid=voice_plan_paid,
                              reference=reference, **source)


def build_ai(ledger: ICostLedger, settings: Settings | None = None, *, wpm: float | None = None,
             script_writer: str | None = None, shortlist_k: int = 15, style_suffix: str | None = None) -> AI:
    s = settings or get_settings()
    # Chain: argon -> 3.8-flash -> 3.6-flash (same price) -> 3.5-flash-lite. Matters on the free tier
    # (argon/grounding limit 0, 20 requests/day per model); on the paid tier only argon->flash is used.
    gemini = GeminiLLM(s.gemini_api_key, ledger, fallbacks={
        s.model_script: s.model_script_fallback,
        s.model_text: TEXT_FALLBACK,
        TEXT_FALLBACK: s.model_cheap,
        s.model_cheap: s.model_text,
    })
    llm: GeminiLLM | ClaudeCodeLLM = gemini
    # "Кто пишет сценарий" in Settings: claude_code = ALL text steps via the Claude subscription
    # (Opus: idea + script, Sonnet: facts/storyboard/judge/metadata, Haiku: quick checks);
    # Gemini is then used only for background images and their vision QA.
    claude_mode = (script_writer or s.script_writer) == "claude_code"
    if claude_mode:
        llm = ClaudeCodeLLM(ledger, gemini, cli=s.claude_cli, model=s.claude_model,
                            model_map={s.model_script: s.claude_model_script,
                                       s.model_script_fallback: s.claude_model_script,
                                       s.model_text: s.claude_model,
                                       s.model_cheap: s.claude_model_cheap},
                            effort_map={s.claude_model_script: s.claude_effort_script})
    writer = ScriptWriter(llm, model=s.model_script, check_model=s.model_cheap,
                                check_fallback=s.model_text, wpm=wpm or s.default_wpm_voice)
    checker = OriginalityChecker(llm, embed_model=s.model_embed, judge_model=s.model_text,
                                       judge_fallback=s.model_script_fallback, shortlist_k=shortlist_k)
    if claude_mode:
        checker.embed_down = True  # Claude has no embeddings: the judge compares against the full source text
    return AI(settings=s, llm=llm, writer=writer, checker=checker,
              images=GeminiImageProvider(gemini, ledger, s.model_image),
              style_suffix=style_suffix or STYLE_SUFFIX)
