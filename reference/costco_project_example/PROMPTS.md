# Prompt pack — "Why Things Cost What They Cost" (stickman explainer)

Порядок работы над одним видео:
1. **Claude (чат)** → тема + сценарий + раскадровка (промпты 1–3)
2. **ElevenLabs** → озвучка (раздел 4)
3. **Google Flow** → фоны и 1–2 вау-клипа (разделы 5–6)
4. **Claude Code CLI** → сборка видео в Remotion (раздел 7)
5. **Flow / Nano Banana** → превью (раздел 8)
6. **Claude (чат)** → заголовок, описание, Shorts (раздел 9)

`{{...}}` — подставьте своё.

---

## 1. Claude (чат) — выбор темы

```
You are a YouTube strategist for an animated explainer channel called "Why Things Cost What They Cost".
Format: 3–8 min stickman + animated charts, curious tone, US/global audience 18–45.
Rules: explain business models and prices with real, checkable numbers; no investment, health or legal advice.

Give me 15 video ideas. For each:
- Working title (max 60 chars, curiosity + specific)
- The one surprising fact/number that makes the video work
- Where that number can be verified (company filing, government statistic, etc.)
- Hook in one sentence (first 5 seconds)
- Visual "hero moment" (one chart or scene people will remember)
Rank by: everyday relevance × surprise × ease of verification.
```

## 2. Claude (чат) — сценарий

```
Write a voiceover script for the video: "{{TITLE}}".
Length: {{3.5}} minutes at 150 wpm (~{{525}} words). Plain spoken English, short sentences.

Structure:
1. Hook (0–15 s): a concrete, surprising fact. No "In this video".
2. The question the video answers.
3. 3–4 beats, each built around ONE number and ONE visual.
4. A twist / reframe ("it's not really a store, it's a club").
5. The catch for the viewer (balance).
6. One-line payoff that calls back to the hook.
7. End-screen line (one sentence pointing to the next video).

Rules:
- Every number must come from a source I can check; list sources after the script with exact figures and dates.
- Mark anything not officially disclosed with "reportedly".
- No advice ("you should buy/invest"). Explain mechanisms only.
- Write numbers the way they should be SPOKEN ("five point three billion dollars").
Output: script as plain paragraphs (ready to paste into ElevenLabs), then the source list.
```

## 3. Claude (чат) — раскадровка в JSON (для Remotion)

```
Turn this script into a storyboard JSON for a Remotion stickman explainer.
Available scene components: hook_price_tag, big_number_stamp, bar_grow, two_bars_compare,
report_sheet, loop_diagram, split_screen, transform_building, item_pile, end_screen,
custom (describe it).
Characters: stick figure with poses {neutral, point, shrug, think, shock, hold_item, arms_up}.

For each scene output:
{ "id": n, "start_text": "first 5 words of the narration for this scene",
  "component": "...", "props": {...exact numbers/labels...},
  "stickman": {"pose": "...", "face": "...", "holds": "..."},
  "background": "none | flow_bg_{{name}}",
  "on_screen_text": "max 5 words", "motion_note": "what animates and when" }
Rules: 12–18 scenes, a new visual every 8–20 s, max 5 words of text on screen,
numbers on screen must exactly match the script.
Script:
{{PASTE SCRIPT}}
```

---

## 4. ElevenLabs — озвучка

- Голос: тот же, что в тесте (Arthur — Clear, Engaging American Male), **всегда один и тот же** — это часть бренда канала.
- Модель: Multilingual v2 (качество) — для финального; Flash — для черновиков.
- Настройки (стартовые): Stability 55–65, Similarity 70–75, Style 15–25, Speaker boost ON.
- Текст: вставлять **абзацами**; между смысловыми блоками — пустая строка (даёт паузы, по ним выравниваем сцены).
- Цифры писать словами, как в сценарии.
- Перед монетизацией — платный план (на бесплатном нет коммерческой лицензии).

---

## 5. Google Flow — фоны (изображения)

Фоны должны быть «под стикмена»: плоские, без людей, без текста, с пустым местом снизу/слева. Генерировать в **16:9**, затем класть в `public/bg/` и подключать в сцене.

**Базовый стиль (добавлять в конец каждого промпта):**
```
Flat vector illustration, minimal, warm cream paper background (#F6F1E7), thick dark ink outlines,
limited palette: muted red #E4572E, teal blue #2E86AB, green #3BA55C, mustard #F2C14E.
No people, no characters, no text, no letters, no logos, no brand names.
Large empty area in the lower-left third for a stick figure. Soft paper grain. 16:9.
```

Фоны для текущего видео (Costco):
```
1) Interior of a huge generic warehouse store: tall metal shelves receding into the distance,
   pallets of boxes, high ceiling with industrial lights. [+ base style]

2) Exterior of a big box warehouse building at sunrise, wide empty parking lot,
   simple clouds. [+ base style]

3) Members-only club entrance: velvet rope with brass posts in front of a plain warehouse door,
   soft spotlight. [+ base style]

4) Kitchen counter overflowing with bulk products: giant packs of paper towels, huge jars,
   multipacks, a shopping receipt. [+ base style]

5) Abstract finance backdrop: faint grid, subtle rising line shapes, scattered coins,
   very low contrast so charts can sit on top. [+ base style]
```

Шаблон для любой темы:
```
{{PLACE/OBJECT that represents the topic}}, seen from {{wide angle / eye level}},
{{2–3 concrete details}}. [+ base style]
```

Чего избегать в Flow: слов «Costco», названий брендов, «photo», «realistic», людей (модель нарисует реальных людей вместо стикменов).

---

## 6. Google Flow / Veo — короткий вау-клип (опционально, 1 на видео)

Используйте для хука (первые 3–6 секунд). Только стиль «анимированная иллюстрация», без реалистичных людей.

```
Flat 2D vector animation, cream paper background, thick ink outlines, limited palette
(muted red, teal, green, mustard). Camera slowly pushes in on a single hot dog on a paper plate
with a yellow price tag "$1.50" while calendar pages fly past in the background from 1985 to 2025.
No people, no logos. Smooth, playful motion. 16:9, 6 seconds. Sound: light paper rustle, soft whoosh.
```
Шаблон:
```
Flat 2D vector animation, cream paper background, thick ink outlines, limited palette.
{{ONE object}} {{ONE simple motion}}. {{Background motion}}. No people, no logos, no text
except {{one short price/number}}. 16:9, {{4–8}} seconds. Sound: {{subtle SFX}}.
```
Совет: текст и цифры Veo часто искажает — цифры лучше накладывать в Remotion поверх клипа.

---

## 7. Claude Code CLI — сборка/изменение видео

Запускать в папке проекта (`cd costco && claude`).

**7.1 Новое видео из того же движка:**
```
This is a Remotion project for a stickman explainer channel (see README.md, src/kit.tsx, src/scenes.tsx).
Create a new composition for a new video:
- Audio: public/{{new_voice}}.mp3
- Storyboard: storyboard/{{name}}.json (attached below)
1. Detect pauses in the audio with ffmpeg silencedetect and align each scene's start_text to the
   nearest pause (estimate by word position, then snap). Save timings to src/{{name}}_scenes.json.
2. Implement the scenes in src/{{name}}/scenes.tsx reusing components from kit.tsx
   (Stick, PriceTag, Card, Cart, Warehouse, Coin, Arrow). Add new components to kit.tsx only if needed.
3. Register composition "{{Name}}" in Root.tsx.
4. Render stills at the middle of every scene into out/{{name}}_preview/ and check them visually
   for overlap, cut-off text and empty frames; fix issues.
5. Render the full mp4 to out/{{name}}.mp4.
Rules: keep the visual style (colors in kit.tsx C, Inter font), max 5 words on screen per scene,
numbers on screen must match the script exactly, no emoji (no emoji font in headless Chrome).
Storyboard:
{{PASTE JSON}}
```

**7.2 Правки текущего видео:**
```
In the Costco composition: {{e.g. scene 5 feels empty — add a cart icon; make scene 11 loop arrows
thicker; add subtitles of key numbers}}. Re-render stills for the changed scenes, show me, then render the mp4.
```

**7.3 Фоны из Flow:**
```
I put background images in public/bg/ (warehouse.png, club.png, ...). Add an optional `bg` prop
to scenes: show the image full-frame under the SVG at 35% opacity with a slight slow zoom (Ken Burns 1.0→1.05).
Use: S4 warehouse_interior, S8 club, S13 kitchen, S14 warehouse_exterior.
```

**7.4 Shorts из длинного видео:**
```
Create a vertical 1080x1920 composition "CostcoShort" that reuses scenes 7 and 11 with their audio
segment (trim voice.mp3 to those scene times), re-layout for 9:16 (stack elements vertically,
larger text), add a big hook caption at the top for the first 2 s: "{{hook}}". Max 45 s.
```

**7.5 Шаг к автоматизации (позже):**
```
Refactor so a single command builds a video from storyboard JSON + mp3:
`npm run build-video -- --storyboard storyboard/x.json --audio public/x.mp3`.
Scenes are chosen by "component" field from a registry of reusable scene components.
Write a JSON schema for the storyboard and validate input before rendering.
```

---

## 8. Превью (thumbnail) — Flow / Nano Banana

```
YouTube thumbnail, 16:9, flat vector style, thick ink outlines, cream background.
A large stick figure with a shocked face holding a giant membership card that glows,
a tiny hot dog with a "$1.50" tag in the corner. Bold high contrast, very simple composition,
one focal point, empty space on the right for big text. No logos, no brand names.
```
Текст на превью (2–4 слова) добавлять отдельно (Canva/Figma/код), не генерировать моделью:
- «IT'S NOT THE FOOD»
- «$5.3B FOR A CARD»

---

## 9. Claude (чат) — заголовок, описание, Shorts

```
Video: "{{working title}}". Script below.
1. 10 title options (≤60 chars). Mix: curiosity gap, specific number, "how X really makes money".
   Mark top 3 and why.
2. Description: 2-sentence hook, 3 chapter timestamps (I'll fix times), sources list with links,
   no hashtags spam (max 3).
3. 3 Shorts ideas cut from this script: timestamp range, on-screen hook text (≤6 words), why it works alone.
4. Pinned comment that asks a question viewers want to answer.
Script: {{PASTE}}
```

---

## Что из этого потом автоматизируется
| Этап | Сейчас (вручную) | Потом (пайплайн) |
|---|---|---|
| Тема, сценарий, раскадровка | Claude чат, промпты 1–3 | Claude API, те же промпты как system prompts |
| Озвучка | ElevenLabs сайт | ElevenLabs API |
| Фоны | Flow вручную | Gemini API (Nano Banana) с тем же base style |
| Сборка | Claude Code, промпт 7.1 | `npm run build-video` |
| Превью | Flow + текст вручную | Nano Banana API + шаблон текста в коде |
| Метаданные | промпт 9 | Claude API → YouTube API |
