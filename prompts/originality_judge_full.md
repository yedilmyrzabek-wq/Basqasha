---
id: originality_judge_full
version: 1
model: MODEL_TEXT
schema: backend/ai/schemas.py:JudgeOut
inputs: [sentences_json, source_text]
note: fallback when embeddings are unavailable; the ONLY other prompt that sees source text. Output never reaches a generator except as a generic reason string.
---
You check whether our narration copies a foreign source video. Below are OUR sentences (Kazakh or another language, each with an index) and the full SOURCE transcript (usually English).

For each of our sentences decide:
- copied = true if it is a translation or close paraphrase of the source's distinctive wording: the same metaphor, joke, image, rhetorical device, unusual phrasing, or the same specific sequence of details.
- copied = false if it merely states a common fact, study result or topic in ordinary words — shared facts and topics are allowed.
Give a short reason in English (<= 20 words).

OUR sentences:
{{sentences_json}}

SOURCE transcript:
{{source_text}}

Return JSON: {"items": [{"index": <our sentence index>, "copied": true|false, "reason": "..."}]} covering every one of our sentences.
