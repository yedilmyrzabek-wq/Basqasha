---
id: metadata
version: 2
model: MODEL_TEXT
schema: schemas/metadata.schema.json (LLM output = backend/ai/schemas.py:MetadataOut; chapters timing, sources, checklist and the final description are assembled in code)
inputs: [language_name, script_title, script_text, facts_json, beats_json, source_title, source_views, thumb_note, character_block, repair_note]
changelog: v2 — packaging like the competitor (owner 2026-10-18): analyse the source video's title + thumbnail, title 1 adapts its proven hook, simple spoken words instead of "literary" titles; 3 thumbnail prompts for Google Flow with our character. v1 — titles/description/chapters/thumbnail texts (video_craft R15-R17, kazakh_market R14, monetization R8, R12)
---
You write YouTube metadata in {{language_name}} for an animated stickman explainer video (general audience 13+, NOT made for kids). Our video retells, in our own words and pictures, the idea of a viral English video (the "source"). The source's PACKAGING (title + thumbnail) is already proven by millions of views — learn from it like a competitor analyst. All output text is in {{language_name}} except packaging_notes (RUSSIAN), thumbnail_prompts (ENGLISH) and tags (may include common English search terms).

## Step 1 — competitor packaging analysis (packaging_notes, RUSSIAN, 3-6 sentences)
Source title: "{{source_title}}" ({{source_views}} views).
{{thumb_note}}
Explain to the operator why this packaging works: the hook type of the title (simple curiosity question / bold claim / number / "you" scene), how short and spoken it is, which emotion it promises; the thumbnail concept (who is shown, how big, what emotion, which 1-3 words, colours, contrast). Then say what our titles and thumbnail take from it.

## Step 2 — titles: exactly 5 variants
- Titles must sound like a person talking, in simple everyday {{language_name}} words that a 13-year-old understands. Short and punchy (25-60 characters, aim 30-50). The hook in the first 40 characters.
- Title 1 = the SAME hook as the source title, adapted naturally to {{language_name}} (a close adaptation of a title is fine — titles are not the content; the video itself is ours). It must not read like a word-for-word machine translation.
- Titles 2-5: other proven hooks in the same simple spirit — a curiosity question, a surprising contrast ("X емес, Y"), a "you" scene, a bold claim the video really proves. At least 1 of the 5 is a question ending with "?". A number only if it is striking and really said in the video (at most 2 titles with numbers). No "literary" or poetic titles, no "құпиясы"-style vague mystery words unless the source does that.
- Sentence case: no word fully in capitals except standard abbreviations; no emoji; no "<" or ">"; no clickbait the video does not deliver; no "ШОК"-style framing.

## Step 3 — description intro
- 300-900 characters, 2-3 short paragraphs. The FIRST 150 characters restate the hook (the same promise as the video opening). Then 1-2 sentences on what the viewer will understand. No advice (health, finance, law, politics), no "subscribe" spam (one short call to watch the next video is fine).
- Do NOT include chapters, sources or hashtags — they are added in code. Provide chapters_heading (e.g. "Chapters" in {{language_name}}) and sources_heading (e.g. "Sources" in {{language_name}}).

## Step 4 — chapter titles
- One short title (2-5 words, <= 40 characters) for every beat listed below, in the same order, keyed by beat id. Titles name the content, not "Intro"/"Part 2".

## Step 5 — hashtags, tags
- hashtags: exactly 3, each "#" + one word or CamelCase phrase without spaces, in {{language_name}} (topic, field, language).
- tags: 8-15 search tags (topic words, key terms, names from the narration).

## Step 6 — thumbnail
- thumbnail_texts: exactly 3 texts in {{language_name}}, each 1-3 words AND <= 18 characters, like "NO JOBS" on a winning thumbnail: huge, instantly readable, a strong emotion or contrast; must not repeat any title verbatim. Text 1 adapts the source thumbnail text if it has one.
- thumbnail_prompts: exactly 3 ENGLISH prompts for Google Flow (image model), one per thumbnail text, in the same order. Each prompt describes a 16:9 YouTube thumbnail in the winning concept from Step 1, but with OUR character (insert the character block below verbatim): the character very large and close (head and upper body fill 40-60% of the frame, usually on one side), a strong readable facial emotion, a simple bright illustrated background that tells the topic in one glance (2-3 objects max), high contrast, thick outlines, flat colours. Put the thumbnail text in the prompt as huge bold yellow letters with a thick black outline, in quotes, exactly as written (Cyrillic). No other text, no logos, no real people. End with: "16:9, 1280x720, YouTube thumbnail, hand-drawn stickman cartoon style."

Character block (insert verbatim into every thumbnail prompt):
{{character_block}}

{{playbook}}

## Narration title: {{script_title}}

## Narration
{{script_text}}

## Verified facts (the only numbers you may use)
{{facts_json}}

## Beats (id, start time)
{{beats_json}}
{{repair_note}}
Return JSON with keys: packaging_notes, titles, description_intro, chapters_heading, sources_heading, chapter_titles [{"beat", "title"}], hashtags, tags, thumbnail_texts, thumbnail_prompts.
