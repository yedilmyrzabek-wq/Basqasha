# Персонаж канала — промпты для генерации

Эталон: `reference_sheet.jpg` (рядом). Внешность: круглая белая голова, толстая чёрная обводка, глаза-овалы, брови, без носа/ушей/волос; **белый казахский калпак с чёрным орнаментом**, бирюзовый шарф, тёмно-синяя худи, бежевые брюки, белые кеды. Кремовый фон.

> ⚠ В видео из Flow (первая партия) шапка превратилась в серую панаму — в каждом промпте повторяйте описание калпака и прикладывайте эталон.

## Общий блок описания (вставлять в каждый промпт)
```
Keep this exact character: a stickman with a large perfectly round plain white head with a thick clean black outline, two small black oval eyes, bold curved black eyebrows, simple line mouth, no nose, no ears, no hair; thin black stick neck, arms and legs, simple round white hands; a small WHITE Kazakh KALPAK hat with black ornament trim (NOT a bucket hat, NOT a cap), slightly tilted; a thin turquoise scarf; a dark navy blue hoodie; beige pants; white sneakers. Same art style, same line thickness, same proportions as the reference image.
```

## Референс-лист
```
Character reference sheet of an original stickman mascot for a Kazakh educational explainer YouTube channel, hand-drawn digital cartoon illustration in the style of popular stickman explainer videos. [ОБЩИЙ БЛОК] Show the same character 5 times in one image: front view, side view, three-quarter view, back view, and waving hello with a smile. Identical head size, face, line thickness and outfit in every view. Soft colors, light shadow under the feet, plain light cream background, clean and readable. No text, no watermark.
```

## Листы поз (для новых поз)
Шаблон: `[ОБЩИЙ БЛОК] Pose sheet, N full-body poses in a grid: 1 …, 2 …. Consistent proportions, identical head, hat and outfit. Plain light cream background, no text.`
После генерации положите лист в `incoming/character/` — Claude вырежет позы скриптом `scripts/split_character_sheets.py` (добавьте лист и имена поз в `SHEETS`).

Уже есть (38 поз в `library/poses/`, 10 эмоций крупным планом в `library/character/expressions/`) — см. `poses.json`.
Чего не хватает для рассказчика: `explain_finger_up` (поднятый указательный палец), `point_right`, `proud_arms_crossed`, `side_eye_suspicious`, `talk_gesture`.

## Видео (Google Flow / Veo) — исправленные промпты
Правила, чтобы видео можно было вставить в ролик:
- **фон — сплошной ярко-зелёный #00FF00** (система вырежет его), или однотонный кремовый без теней и текстуры;
- **статичная камера**, персонаж целиком в кадре, ноги на одном уровне в начале и в конце;
- начало и конец — спокойная нейтральная стойка (тогда клип стыкуется с позами);
- 4–6 секунд, 16:9.

```
[ОБЩИЙ БЛОК] Animate this character on a solid pure green (#00FF00) background, no shadows, no ground texture. Static camera, full body always in frame. He starts in a neutral standing pose, {ДЕЙСТВИЕ}, then returns to the neutral standing pose. Smooth motion, 5 seconds, 16:9. Keep the white kalpak hat exactly as in the reference.
```
| Файл | {ДЕЙСТВИЕ} |
|---|---|
| `hello_wave.mp4` | walks in from the left, stops in the center, looks at the camera and waves hello with a big smile |
| `explain.mp4` | raises one finger, nods slightly and gestures with his hands as if explaining something important, mouth moving as if talking |
| `think_idea.mp4` | holds his chin and looks up thinking, then his eyes widen, a light bulb appears above his head and he smiles |
| `shock.mp4` | looks at something off-screen, his eyes suddenly go wide, he jumps back slightly and puts his hands on his cheeks |
| `confused.mp4` | looks left and right, scratches his head and shrugs with both hands up |
| `celebrate.mp4` | jumps up with both arms raised, celebrating happily, then lands and smiles at the camera |

Готовые клипы кладите в `incoming/motion/` с этими именами.
