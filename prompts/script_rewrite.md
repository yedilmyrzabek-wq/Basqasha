---
id: script_rewrite
version: 1
model: same as script
schema: backend/ai/schemas.py:RewriteOut
inputs: [language_name, reason, sentences_json, context_text, language_rules]
---
An automatic originality check flagged some sentences of our {{language_name}} narration as too close to a foreign source video (you do NOT see the source, and you must not try to guess it).
Reason: {{reason}}

Rewrite ONLY the flagged sentences so they say the needed thing in clearly different words and from a different angle: change the image, the order of information, the sentence structure, use a Kazakhstan-specific detail or example. Keep each rewritten sentence's role in the story, the same facts and numbers (as words), roughly the same length (6-12 words, max 16), and smooth flow with the surrounding text.

Language rules:
{{language_rules}}

Flagged sentences (index -> text):
{{sentences_json}}

Full narration for context:
{{context_text}}

Return JSON: {"items": [{"index": <same index>, "text": "<new sentence(s)>"}]} — one item per flagged index.
