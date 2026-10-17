"""ILLM over the Claude Code CLI (`claude -p`, Claude subscription; ledger usd = 0).

Text generation goes to Claude; embeddings and the vision QA of generated backgrounds (step "images")
are delegated to Gemini. Other image inputs (e.g. the competitor's thumbnail in step 10) are copied
into the temp dir and Claude looks at them with its Read tool.
`grounding=True` lets Claude use WebSearch/WebFetch, so the facts step cites real pages.
The CLI runs in an empty temp dir with no settings, MCP servers or tools (unless grounding),
which keeps each call light on the subscription limit.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence, TypeVar

from pydantic import BaseModel, ValidationError

from ai.gemini import GeminiLLM, ModelUnavailable
from app import cancel
from app.providers.interfaces import CallContext, ICostLedger, LLMResult

log = logging.getLogger("ai.claude_cli")
M = TypeVar("M", bound=BaseModel)

SYSTEM = ("You are a careful writer and researcher for an educational YouTube channel. "
          "Follow the user's instructions exactly and return only the requested structured data.")
_URL = re.compile(r"https?://[^\s\"'<>)\]]+")


class ClaudeCodeLLM:
    def __init__(self, ledger: ICostLedger, gemini: GeminiLLM, *, cli: str = "claude",
                 model: str = "sonnet", model_map: dict[str, str] | None = None,
                 effort_map: dict[str, str] | None = None, timeout_s: int = 900):
        self.ledger = ledger
        self.gemini = gemini
        self.cli = _resolve_cli(cli)
        self.model = model
        self.model_map = model_map or {}   # gemini model id -> claude model (e.g. script -> opus)
        self.effort_map = effort_map or {}  # claude model -> --effort level
        self.timeout_s = timeout_s
        self.workdir = Path(tempfile.mkdtemp(prefix="claude_llm_"))

    def generate_json(self, *, prompt: str, response_model: type[M], model: str, ctx: CallContext,
                      system: str | None = None, grounding: bool = False,
                      images: Sequence[Path] = (), max_output_tokens: int | None = None) -> LLMResult[M]:
        if images and ctx.step == "images":  # QA of generated backgrounds stays on Gemini (image generation)
            return self.gemini.generate_json(prompt=prompt, response_model=response_model, model=model, ctx=ctx,
                                             system=system, grounding=grounding, images=images,
                                             max_output_tokens=max_output_tokens)
        claude_model = self.model_map.get(model, self.model)
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        tools = ["WebSearch", "WebFetch"] if grounding else []
        if images:
            names = []
            for i, img in enumerate(images):
                dst = self.workdir / f"image_{i + 1}{Path(img).suffix.lower() or '.png'}"
                shutil.copyfile(img, dst)
                names.append(dst.name)
            tools.append("Read")
            prompt = ("First open and look at these image file(s) in the current directory with the Read tool: "
                      + ", ".join(names) + ".\n\n" + prompt)
        cmd = [self.cli, "-p", "--output-format", "json", "--model", claude_model,
               "--strict-mcp-config", "--setting-sources", "", "--json-schema", schema,
               "--system-prompt", system or SYSTEM, "--tools", ",".join(tools) if tools else ""]
        if claude_model in self.effort_map:
            cmd += ["--effort", self.effort_map[claude_model]]
        if tools:
            cmd += ["--allowedTools", *tools]
        if grounding:
            prompt += ("\n\nUse WebSearch/WebFetch to find and open real sources before answering. "
                       "Every source URL you cite must be a page you actually found.")

        last_err = ""
        for attempt in range(2):  # 1 repair retry
            text = prompt if attempt == 0 else (
                f"{prompt}\n\nYour previous answer was invalid: {last_err[:1500]}\nReturn corrected data.")
            env = self._run(cmd, text)
            raw = env.get("structured_output")
            try:
                value = (response_model.model_validate(raw) if raw is not None
                         else response_model.model_validate_json(_strip_fences(str(env.get("result", "")))))
            except ValidationError as ve:
                last_err = str(ve)
                log.warning("invalid structured output from claude (%s), retry", last_err[:200])
                continue
            usage = env.get("usage") or {}
            units = {"call": 1, "input_tokens": int(usage.get("input_tokens", 0))
                     + int(usage.get("cache_read_input_tokens", 0)) + int(usage.get("cache_creation_input_tokens", 0)),
                     "output_tokens": int(usage.get("output_tokens", 0))}
            self.ledger.record(ctx, "anthropic", "claude-code-cli", {"call": 1})  # subscription: usd 0
            urls = tuple(dict.fromkeys(_URL.findall(json.dumps(raw, ensure_ascii=False)))) if grounding else ()
            return LLMResult(value=value, model=f"claude-code-cli:{claude_model}",
                             usage={"input_tokens": units["input_tokens"], "output_tokens": units["output_tokens"],
                                    "thinking_tokens": 0},
                             grounding_urls=urls)
        raise ModelUnavailable(f"claude returned invalid structured output twice: {last_err[:300]}")

    def embed(self, texts: Sequence[str], *, model: str, ctx: CallContext, dim: int = 768) -> list[list[float]]:
        return self.gemini.embed(texts, model=model, ctx=ctx, dim=dim)

    def _run(self, cmd: list[str], prompt: str) -> dict:
        try:
            proc = cancel.run(cmd, input=prompt, timeout=self.timeout_s, cwd=self.workdir)
        except subprocess.TimeoutExpired as e:
            raise ModelUnavailable(f"claude timed out after {self.timeout_s}s") from e
        try:
            env = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise ModelUnavailable(f"claude exit {proc.returncode}: {(proc.stderr or proc.stdout)[:400]}")
        if env.get("is_error") or proc.returncode != 0:
            raise ModelUnavailable(f"claude error: {str(env.get('result') or env.get('subtype'))[:400]}")
        return env


def _resolve_cli(cli: str) -> str:
    """On Windows npm installs `claude.cmd`; going through cmd.exe would mangle the JSON-schema
    argument, so call the bundled claude.exe directly when it exists."""
    found = shutil.which(cli) or cli
    if found.lower().endswith(".cmd"):
        exe = Path(found).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if exe.exists():
            return str(exe)
    return found


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()
