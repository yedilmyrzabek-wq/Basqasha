---
id: script_adjust
version: 1
model: same as script
schema: backend/ai/schemas.py:ScriptOut
inputs: [language_name, target_words, min_words, max_words, current_words, beat_report, script_json, facts_json, language_rules]
---
The {{language_name}} narration below has {{current_words}} words, but it must have {{target_words}} words (allowed {{min_words}}-{{max_words}}). Words = space-separated tokens.

Per-beat word counts now vs target:
{{beat_report}}

Fix the LENGTH of the beats that are off target:
- too short: add concrete, vivid sentences (mechanism, a sensory detail, a local example, a facts-list number written as words) — never filler or repetition;
- too long: cut the weakest sentences.
Keep the beat order, beat ids, hook_type, title, the hook's first sentence, and all rules: 6-12 words per sentence (max 16), numbers only from the facts list and written as words, no advice, no abbreviations.

Language rules:
{{language_rules}}

Facts (only allowed numbers):
{{facts_json}}

Current script JSON:
{{script_json}}

Return the full corrected script JSON matching the response schema.
