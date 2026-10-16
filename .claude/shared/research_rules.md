# Common rules for all research subagents (referenced by each researcher)

- Source of truth: `docs/PROJECT_BRIEF.md`. Read it first (at least the sections named in your task).
- Today is 2026-10-16. Prefer sources from 2025–2026; state the date of every policy/price you cite.
- Mark EVERY claim as **[Fact — <URL>]** or **[Estimate]** (with short reasoning). Never present an unsourced number as a fact.
- Write ONLY your own output file under `docs/research/`. Do not edit any other file.
- Document layout: `# Title` → `## TL;DR` (5–8 bullets) → topic sections → `## Rules for our system` → `## Contradictions with PROJECT_BRIEF` (or "none found") → `## Open questions` → `## Sources` (list of URLs).
- "Rules for our system": numbered, concrete, testable rules that can be pasted into LLM prompts, settings or code (numbers, thresholds, do / don't). At least 8 rules.
- If something cannot be verified, say so explicitly instead of guessing. If you are blocked, stop and report the blocker to the LEAD.
- Definition of done: file exists, every section filled, every claim marked, rules section ≥ 8 rules.
- Final reply to the LEAD: ≤ 12 lines — top findings, contradictions with the brief, blockers.
