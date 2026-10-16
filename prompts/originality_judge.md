---
id: originality_judge
version: 1
model: MODEL_TEXT
schema: backend/ai/schemas.py:JudgeOut
inputs: [pairs_json]
note: the ONLY prompt that sees source text; its output never goes to a generator except as a reason string.
---
You check whether our narration copies a foreign source video. Each pair has OUR sentence (Kazakh or another language) and the most similar SOURCE sentence (usually English), found by embeddings.

For each pair decide:
- copied = true if our sentence is a translation or close paraphrase of the source sentence's distinctive wording: the same metaphor, joke, image, rhetorical device, unusual phrasing or the same specific sequence of details.
- copied = false if both merely state the same common fact or topic in ordinary words (e.g. "winters were very cold", "people burned dried dung") — shared facts and topics are allowed.
Give a short reason in English (<= 20 words).

Pairs:
{{pairs_json}}

Return JSON: {"items": [{"index": <pair index>, "copied": true|false, "reason": "..."}]} covering every pair.
