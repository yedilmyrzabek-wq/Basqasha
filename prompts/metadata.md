---
id: metadata
version: 1
model: MODEL_TEXT
schema: schemas/metadata.schema.json (LLM output = backend/ai/schemas.py:MetadataOut; chapters timing, sources, checklist and the final description are assembled in code)
inputs: [language_name, script_title, script_text, facts_json, beats_json, repair_note]
changelog: v1 — titles/description/chapters/thumbnail texts (video_craft R15-R17, kazakh_market R14, monetization R8, R12)
---
You write YouTube metadata in {{language_name}} for an animated explainer video (general audience 13+, NOT made for kids). The narration is below. All output text is in {{language_name}} except tags may include common English search terms.

## Titles — exactly 5 variants
- Each 25-60 characters (aim 40-55, count them), the core hook in the first 40 characters.
- At least 2 contain a specific number written in digits that the video really says (e.g. a year or a percent from the narration).
- At least 2 are questions ending with "?" (in Kazakh e.g. "...қалай?", "Неге...?").
- Sentence case: no word fully in capitals except standard abbreviations; no emoji; no "<" or ">"; no clickbait the first 15 seconds do not deliver; no "ШОК"-style framing.
- The 5 variants must use different hooks (number, question, paradox, myth-flip, "you" scene).

## Description intro
- 300-900 characters, 2-3 short paragraphs. The FIRST 150 characters restate the hook (the same promise as the video opening). Then 1-2 sentences on what the viewer will understand. No advice (health, finance, law, politics), no "subscribe" spam (one short call to watch the next video is fine).
- Do NOT include chapters, sources or hashtags — they are added in code. Provide chapters_heading (e.g. "Chapters" in {{language_name}}) and sources_heading (e.g. "Sources" in {{language_name}}).

## Chapter titles
- One short title (2-5 words, <= 40 characters) for every beat listed below, in the same order, keyed by beat id. Titles name the content, not "Intro"/"Part 2".

## Hashtags, tags, thumbnails
- hashtags: exactly 3, each "#" + one word or CamelCase phrase without spaces, in {{language_name}} (topic, field, language).
- tags: 8-15 search tags (topic words, key terms, names from the narration).
- thumbnail_texts: exactly 3 visibly different texts, each 1-3 words AND <= 18 characters; must not repeat any title verbatim; strong curiosity (a number, a paradox, a two-word question).

## Narration title: {{script_title}}

## Narration
{{script_text}}

## Verified facts (the only numbers you may use)
{{facts_json}}

## Beats (id, start time)
{{beats_json}}
{{repair_note}}
Return JSON with keys: titles, description_intro, chapters_heading, sources_heading, chapter_titles [{"beat", "title"}], hashtags, tags, thumbnail_texts.
