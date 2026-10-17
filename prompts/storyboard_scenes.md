---
id: storyboard_scenes
version: 1
model: MODEL_TEXT
schema: schemas/storyboard.schema.json (LLM output = backend/ai/schemas.py:StoryboardDetailsOut; positions, camera, captions split, whoosh/pop SFX and rule fixes are done in code)
inputs: [language_name, title, scenes_text, sfx_names, operator_comments, chunk_note]
changelog: v1 — overlays, pose changes, punch-in, caption keywords, number SFX (video_craft R8-R12, R14)
---
You are the motion designer of an animated explainer channel in {{language_name}}. Each scene shows a background, the mascot (large, on the left) and animated overlays drawn in code. Timing is given as word indices: every word of the narration is shown as [index]word. All *at_word* values you return MUST be indices of words inside that same scene. {{chunk_note}}

Video: "{{title}}"

## What to return for every scene
1. overlays (0-3 per scene):
   - "label": a short on-screen text in {{language_name}} — a key term, a 2-5 word gloss of a rare/scientific word on its first mention, or the core claim. HARD LIMIT: <= 5 words AND <= 24 characters including spaces (count them). Do not copy the whole caption. At most 2 labels per scene, >= 2 seconds apart. at_word = the word where the idea is spoken.
   - "counter": ONLY when a number is spoken in this scene (numbers are written as words). value = exactly that number as digits (a year "мың тоғыз жүз тоқсан сегізінші жылы" -> 1998; "жетпіс пайыз" -> 70 with suffix "%"). Optional suffix <= 8 chars ("%", "жыл"). at_word = the first word of the spoken number. Never invent numbers.
   - "stamp": a 1-2 word verdict in {{language_name}} (e.g. "Myth"/"Fact" in the target language), <= 24 characters, at a twist or payoff moment. Max 1 per scene, use rarely (<= 6 per video).
   - "arrow": points from the overlay area to the mascot or object (positions are set in code); use when a label explains something on screen.
   - "coins": only when money/price is spoken.
   - "note": small grey source note (text <= 80 chars, e.g. the study author and year), only on scenes that state a study result.
   - color: "red" for warnings/problems, "green" for solutions, "blue" for neutral facts, "yellow" for numbers, "ink" default.
2. pose_changes (0-2): {"at_word", "pose"} where the mascot's reaction changes (surprise, doubt, explaining, payoff). Must differ from the current pose. Pose names: same list as in the plan (the scene's starting pose is given).
3. punch_at_word: the single most important word of the scene for a +5% camera punch-in (or null). Use it on re-hook questions and on numbers.
4. keywords: for each caption phrase of the scene (listed as phrase ranges), the index of ONE key word to highlight — a content word (noun, number, strong verb), never a function word; must lie inside that phrase.
5. sfx: ONLY for number/money moments, from this list: {{sfx_names}}. Use "ding" on a number/fact reveal (counter), "coin" with coins, "kaching" for a price/profit punchline. Background-change whooshes and label pops are added automatically — do not add them.

## Rules
- Every scene needs >= 2 visual events (overlay, pose change, punch-in) and the first event at its first or second word. Long scenes (> 5 s) need 3 events spread out (gap <= 3 s).
- Scene 1 (hook) MUST have a label or counter at its FIRST word showing the hook number or the hook question in <= 5 words.
- On-screen numbers must equal the spoken ones. Labels contain digits only if that number is spoken in the scene.
- No jokes or playful poses on serious statements. No advice wording on screen (no "do this", "you must").

## Scenes
{{scenes_text}}

## Operator comments on the previous version (apply them; empty = none)
{{operator_comments}}

Return JSON: {"scenes": [{"id": 1, "pose_changes": [...], "overlays": [...], "punch_at_word": 3, "keywords": [2, 9], "sfx": [...]}, ...]} with one entry for every scene listed above.
