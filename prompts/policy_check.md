---
id: policy_check
version: 2
model: MODEL_CHEAP (fallback MODEL_TEXT)
schema: backend/ai/schemas.py:PolicyOut
inputs: [text, sensitive_topics]
---
You review a narration script (may be in Kazakh) for YouTube monetization policy. Find sentences that:
1. advice: give prescriptive advice (imperative or "you should / it is better to...") about health/medicine/mental health/diet (incl. diagnoses, treatment, supplements), finance/investing, law, or politics. Explaining history, research findings or how something works (incl. what studies observed about habits) is NOT advice.
2. manipulation: emotionally manipulative, shock for its own sake, graphic suffering of people or animals.
3. tone: non-neutral statements on sensitive subjects (mental-health conditions, famine/Ашаршылық, repressions, ethnic groups, жүз/ру, religion, neighbouring states, borders, current politics). Sensitive topics flagged by the brief: {{sensitive_topics}}.
4. kids: tone aimed at small children (lullaby tone, songs, preschool topics).

Script:
<<<
{{text}}
>>>

Return JSON: {"no_advice": bool, "issues": [{"kind": "advice|manipulation|tone|kids", "sentence": "<exact sentence>", "reason": "<Russian, short>"}]}. no_advice = false only if there is at least one "advice" issue. Empty issues if clean.
