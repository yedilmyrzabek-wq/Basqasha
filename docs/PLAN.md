# PLAN — «Идея → казахское анимационное видео»

Источник истины: `docs/PROJECT_BRIEF.md` (v1.1). Пример стиля: `reference/costco_project_example/`.
LEAD (оркестратор) — основная сессия Claude Code. Код пишут субагенты из `.claude/agents/`.

## 0. Что уже известно из примера (`reference/`)
- `src/kit.tsx` — палитра `C`, `FONT`, `usePop`, `lin`, `Pop`, `Txt`, `Coin`, `Arrow`, `PriceTag`, `Card` и т.п.
- `src/pop/Popcorn.tsx` — эталон всех приёмов: `Bg` (Ken Burns + punch-in по spring), `Svg`-слой 1920×1080, `Scene` (fade-in 6 кадров),
  `Label` (плашка с поворотом −2°), `Char` (PNG-поза по расписанию, squash&stretch, «дыхание», тень, flip),
  `Captions` (фраза + жёлтая подсветка ключевого слова), прогресс-бар 8 px красный, `pad.wav` 0.35, SFX (pop/whoosh/coin/ding/kaching).
- Сейчас всё захардкожено в секундах/кадрах → в `/engine` всё должно стать props-driven (`*_word` → кадры).
- `public/char/pose_*.png` — 8 поз (point, shrug, think, shock, excited, popcorn, coin, present) + `ref_sheet.jpg`, `front/side/three.png`.
- `public/pop/*.jpg` — 5 фонов в стиле; `*.wav` — SFX и подложка; `voice.mp3` — пример озвучки.
- `PROMPTS.md` — промпты для LLM/Flow/ElevenLabs (основа для `/prompts`).

## 1. Окружение (проверено на ноутбуке владельца, Windows 10)
| Инструмент | Статус |
|---|---|
| Node 22.16 | ✅ |
| uv | ✅ (Python 3.12 поставит uv) |
| Python | 3.11 системный → проект на 3.12 через `uv` |
| ffmpeg | ✅ 9.0.2 portable в `%USERPROFILE%/tools/ffmpeg/bin` (добавлен в user PATH; виден в новых терминалах) |
| yt-dlp | ❌ — ставится как Python-зависимость backend |
| git | ✅ репозиторий, вся работа в ветке `main-agent` (без push) |
| GPU | NVIDIA RTX 3050 Laptop 4 GB (ASR не используем — решение владельца) |
| Ключи | ✅ `.env` заполнен и проверен 2026-10-17: Supabase (PostgreSQL 17.11, Session pooler :5432, ap-southeast-1) и Gemini (63 модели; есть `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-nano-banana-2.1`, `gemini-embedding-2`, `gemini-3.5-transcribe`) |
| MCP | vidIQ ✅, chrome-devtools ✅ (вместо Playwright MCP для QA); Supabase MCP ❌ |

## 2. Фазы и критерии приёмки (из брифа §6.6, §8)
| Фаза | Объём | Приёмка |
|---|---|---|
| **P0** Research + контракты | 5 исследований, SUMMARY, схемы, миграции, OpenAPI, интерфейсы | CHECKPOINT 1 (SUMMARY.md), CHECKPOINT 2 (контракты) |
| **P1** Каркас + шаги 1–4 | одна команда запуска, настройки, проекты, шаги источник/идея/факты/сценарий + originality | Демо: `https://www.youtube.com/watch?v=CkP_8bkjf1E` (PsychToons, «Psychology of Discipline») → 3 варианта подачи на казахском → выбран один → facts.json с источниками → script_kk (бюджет слов из длительности 3–5 мин) + originality.json ниже порога → «Утвердить» |
| **P2** Шаги 5–6 | текст для ElevenLabs, загрузка mp3, −16 LUFS, выравнивание по паузам, раскадровка | у каждого предложения время; storyboard проходит схему, сцены 2.5–7.5 с, 12–15 фонов |
| **P3** Движок + шаги 8–9 | Remotion `Explainer` из props.json, contact sheet, рендер MP4 | contact_sheet без обрезок/наложений; длительность = mp3 ± 0.5 с; казахские глифы ок |
| **P4** Шаг 7 + позы + шаг 10 | Gemini image + vision QA, ручная замена, библиотека поз (chroma-key, нарезка листа), метаданные | видео целиком из ссылки + mp3 |
| **P5** Масштаб | cost-дашборд, Shorts 9:16, ElevenLabs API за флагом, задел YouTube API и `en` | — |

## 3. Команда и ответственность
| Агент | Владеет | Фазы |
|---|---|---|
| monetization-researcher | `docs/research/monetization.md` | P0 |
| video-craft-researcher | `docs/research/video_craft.md` | P0 |
| kazakh-market-researcher | `docs/research/kazakh_market.md` | P0 |
| topic-scout | `docs/research/topics_backlog.md` | P0 |
| tools-cost-researcher | `docs/research/tools_costs.md` | P0 |
| architect | `/schemas`, `/supabase/migrations`, `/docs/api/openapi.yaml`, `/docs/ARCHITECTURE.md`, `backend/app/providers/interfaces.py`, `.env.example` | P0 (+ изменения контрактов по запросу) |
| backend-dev | `/backend` (кроме `backend/ai`, `interfaces.py`), `/scripts` (запуск) | P1–P5 |
| ai-engineer | `/prompts`, `/backend/ai` | P1–P5 |
| media-engineer | `/engine`, `/library` (структура, poses.json) | P3–P5 (каркас движка можно начать в P1) |
| frontend-dev | `/frontend` | P1–P5 |
| qa-tester | `/tests` | после каждой фазы, право блокировать |

LEAD владеет: `docs/PLAN.md`, `docs/research/SUMMARY.md`, `README.md`, `.gitignore`, корневые файлы, слияние веток.

## 4. Разбивка задач

### P0-A Research (параллельно, 5 агентов)
Каждый документ: выводы с пометкой **[Факт + URL]** / **[Оценка]**, раздел «Rules for our system» (что положить в промпты/настройки).

### P0-B LEAD → `docs/research/SUMMARY.md` ▶ CHECKPOINT 1

### P0-C Contracts (architect)
1. `/schemas/*.schema.json`: brief, angles, facts, script, originality, storyboard (по §6.5 + выводы video_craft), props (вход Remotion, всё в кадрах), words (выравнивание), metadata.
2. `/supabase/migrations/0001_init.sql`: таблицы §6.4 + `job_log`, `cost_entry`, `settings`; статусы шагов (enum), индексы. `SourceMaterial` — отдельная таблица.
3. `/docs/api/openapi.yaml`: проекты, шаги (run/retry/status), angles/choose, facts CRUD, script edit/approve, voice upload, storyboard, images (regenerate/upload/prompt), contact sheet + comments, render, metadata, poses, settings, costs.
4. `backend/app/providers/interfaces.py`: `IVoiceProvider`, `IImageProvider`, `IScriptWriter`, `IPublisher` (+ `ILLM` для Gemini).
5. **Originality guard в типах**: контекст шагов 3+ (`DownstreamContext`) не содержит поля transcript; доступ к `SourceMaterial` только через `SourceRepository`, который импортируют только модули steps/source.py и steps/idea.py (проверяется тестом-линтером импорта).
6. `docs/ARCHITECTURE.md`: структура папок, жизненный цикл статусов, путь файлов `/data/projects/{id}/...`.
▶ CHECKPOINT 2

### P1 (параллельно)
- **backend-dev:** FastAPI skeleton, конфиг из `.env`, SQLModel-модели под миграции, Huey (SQLite), state machine шагов, `/data` файловое хранилище, step1 (yt-dlp субтитры → чистка, ручная вставка), раннер шагов 2–4 через ai-модуль, cost ledger, job log, `scripts/dev.ps1` + `scripts/dev.sh` (backend + worker + frontend одной командой).
- **ai-engineer:** Gemini-клиент (google-genai) c учётом стоимости; промпты: brief+angles, facts (Search grounding), script_kk (правила из video_craft/monetization), originality (embeddings по предложениям + LLM-судья + авто-переписывание); Pydantic-модели = JSON Schema; `ClaudeCodeScriptWriter` (`claude -p --output-format json`).
- **frontend-dev:** каркас React/Vite/TS/Tailwind/shadcn, список проектов, страница проекта со шагами, шаги 2/3/4, настройки.
- **media-engineer (опережающе):** `/engine` каркас, порт компонентов из reference, композиция Explainer на фикстурном props.json.
- **qa-tester:** unit + e2e на фикстурах, клик-тест UI, прогон демо-ссылки.

### P2
backend: загрузка mp3, ffmpeg loudnorm −16 LUFS, выравнивание без ASR: silencedetect + раскладка предложений по паузам + пропорционально длине → words.json; пересчёт темпа голоса (wpm). ai: storyboard-генерация (40–50 сцен, 12–15 фонов, правила темпа). frontend: шаги 5–6. qa.

### P3
media: Explainer полностью из props.json, stills/contact sheet, рендер, проверка казахских глифов (шрифт с ә ғ қ ң ө ұ ү һ і). backend: storyboard → props.json (word→frame), запуск Remotion из Python, шаги 8–9. frontend: шаг 8 (комментарии к сценам), шаг 9 (плеер). qa: визуальная проверка листов.

### P4
ai: Gemini image (style suffix + референсы), vision QA, перегенерация; метаданные (шаг 10). backend: chroma-key #00FF00, нарезка листа поз, poses.json, шаг 7 оркестрация. frontend: сетка картинок, библиотека поз, шаг 10. qa.

### P5
Shorts 9:16, cost-дашборд, `ElevenLabsApiVoiceProvider` за флагом (выключен), `YouTubeApiPublisher`-заглушка, `language=en` прогон.

## 5. Зависимости
```
Research ─► SUMMARY ─► (OK) ─► Contracts ─► (OK) ─► P1 ─► P2 ─► P3 ─► P4 ─► P5
                                              └─ media-engineer каркас Explainer может стартовать в P1
```

## 6. Решения владельца
- 2026-10-17: озвучка пока вручную — система отдаёт текст, оператор генерирует mp3 в ElevenLabs и загружает. ElevenLabs API подключим позже (P5, провайдер за флагом; тогда можно брать таймкоды из `/with-timestamps` вместо ASR).
- 2026-10-17: длительность 3–5 мин (параметр); ASR не используем; лимит ≈ $5/видео (картинки); второй язык и vidIQ — в будущем (vidIQ — через промпты, которые оператор прогоняет сам); темы — свежие популярные источники любых жанров.
- 2026-10-17: **приоритет — рабочая система, которая доводит видео до конца**, а не идеальная архитектура. Контракты и код — минимально достаточные; checkpoint 2 — короткий, без остановки работы. **Автотесты не пишем** — проверка запуском (qa-tester прогоняет сценарий вручную/через браузер и смотрит результат).
- 2026-10-17: **бэкап БД не нужен** (pg_dump / weekly backup не делаем).
- Git: работа в ветке `main-agent`, push в `origin` (github.com/yedilmyrzabek-wq/Basqasha) разрешён.

## 7. Правила процесса
- Каждый агент правит только свои папки; изменения контрактов — запрос LEAD → architect.
- Работа агентов-разработчиков — в отдельных git worktree/ветках, слияние через LEAD.
- Секреты только в `.env`; `.env.example` в репозитории.
- После каждой фазы — qa-tester, цикл исправлений до зелёного, затем CHECKPOINT владельцу.
