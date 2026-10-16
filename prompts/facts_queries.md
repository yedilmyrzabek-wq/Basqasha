---
id: facts_queries
version: 1
model: MODEL_CHEAP (fallback MODEL_TEXT)
schema: backend/ai/schemas.py:QueriesOut
inputs: [brief_json, angle_json, max_queries]
note: used only by the facts fallback (no Google Search grounding) to pick Wikipedia articles.
---
We need reference documents for a short explainer video. Give up to {{max_queries}} ENGLISH Wikipedia search queries (ideally exact article titles) that together cover the key studies, concepts, numbers and mechanisms of this brief and presentation variant. Most important first; no duplicates; 1-5 words each.

Brief:
{{brief_json}}

Presentation variant:
{{angle_json}}

Return JSON: {"queries": ["...", "..."]}
