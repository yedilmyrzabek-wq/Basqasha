"""One place that wires the AI layer from settings. The backend calls build_ai(ledger)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.config import Settings, get_settings
from app.providers.interfaces import CallContext, ICostLedger, OriginalityReference
from ai.facts import FactsResult, research_facts
from ai.claude_cli import ClaudeCodeLLM
from ai.gemini import GeminiLLM
from ai.idea import generate_idea
from ai.originality import GeminiOriginalityChecker, run_originality
from ai.script import ClaudeCodeScriptWriter, GeminiScriptWriter
from ai.tts import TtsExport, export_tts

TEXT_FALLBACK = "gemini-3.6-flash"


@dataclass
class AI:
    settings: Settings
    llm: GeminiLLM | ClaudeCodeLLM
    writer: GeminiScriptWriter | ClaudeCodeScriptWriter
    checker: GeminiOriginalityChecker

    def idea(self, transcript: str, *, language: str, ctx: CallContext, source_title: str = "",
             source_minutes: float = 0, source_views: int | None = None,
             operator_hint: str | None = None) -> dict[str, Any]:
        return generate_idea(self.llm, transcript, language=language, ctx=ctx, model=self.settings.model_text,
                             source_title=source_title, source_minutes=source_minutes,
                             source_views=source_views, operator_hint=operator_hint)

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


def build_ai(ledger: ICostLedger, settings: Settings | None = None, *, wpm: float | None = None,
             script_writer: str | None = None, shortlist_k: int = 15) -> AI:
    s = settings or get_settings()
    # Chain: argon -> 3.8-flash -> 3.6-flash (same price) -> 3.5-flash-lite. Matters on the free tier
    # (argon/grounding limit 0, 20 requests/day per model); on the paid tier only argon->flash is used.
    llm = GeminiLLM(s.gemini_api_key, ledger, fallbacks={
        s.model_script: s.model_script_fallback,
        s.model_text: TEXT_FALLBACK,
        TEXT_FALLBACK: s.model_cheap,
        s.model_cheap: s.model_text,
    })
    if s.text_llm == "claude_code":
        # All text steps via the Claude subscription; Gemini only for embeddings and images.
        llm = ClaudeCodeLLM(ledger, llm, cli=s.claude_cli, model=s.claude_model,
                            model_map={s.model_script: s.claude_model_script,
                                       s.model_script_fallback: s.claude_model_script})
    gemini_writer = GeminiScriptWriter(llm, model=s.model_script, check_model=s.model_cheap,
                                       check_fallback=s.model_text, wpm=wpm or s.default_wpm_voice)
    kind = script_writer or s.script_writer
    use_cli_writer = kind == "claude_code" and s.text_llm != "claude_code"  # already Claude otherwise
    writer = ClaudeCodeScriptWriter(gemini_writer, ledger, s.claude_cli) if use_cli_writer else gemini_writer
    checker = GeminiOriginalityChecker(llm, embed_model=s.model_embed, judge_model=s.model_text,
                                       judge_fallback=s.model_script_fallback, shortlist_k=shortlist_k)
    return AI(settings=s, llm=llm, writer=writer, checker=checker)
