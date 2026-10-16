# vidIQ prompts — готовые запросы для ручного прогона владельцем

> Автор: topic-scout (итерация 2) · Дата: 2026-10-17 · Основание: PROJECT_BRIEF v1.2 §10.6 (vidIQ запускает владелец с другого аккаунта) и §10.7 (только свежие вирусные источники). Связанный файл: `docs/research/topics_backlog.md`.
> В этой сессии у vidIQ 0 кредитов, поэтому vidIQ не вызывался. Ни один результат ниже не получен из vidIQ: это только запросы и шаблоны ответа.

## TL;DR
- 6 промптов (P0–P5). Их можно вставлять в чат vidIQ AI (Coach) как есть. Для вкладок Outliers и Keywords дан ручной вариант с фильтрами.
- **Порядок прогона при нехватке кредитов:** P0 → P2 (проверка источников топ-12) → P3 (спрос на ключевые слова kk/ru) → P1 (новые выбросы по жанрам) → P5 (кто уже снял эти темы на казахском и русском) → P4 (вернуть хорошие идеи v1 со свежим источником).
- **Ответ возвращать только в CSV-блоках** с заголовками из раздела «Форматы ответа» (таблицы A, B, C). Не пересказывать и не сокращать.
- LEAD переносит данные в backlog по правилам из раздела «Rules for our system»: outlier-score vidIQ заменяет нашу оценку O, а спрос на ключевые слова используется как тай-брейкер.
- Языки: промпты на английском (vidIQ AI лучше понимает английский), ключевые слова — на казахском и русском.

## Как запускать

1. Откройте vidIQ (веб-версию) в аккаунте с кредитами. Каналу подключаться не нужно.
2. Откройте чат vidIQ AI (Coach). Вставьте **P0** один раз в начале сессии.
3. Вставляйте промпты по одному. Если ответ не помещается, напишите `continue the CSV from row N`.
4. Если чат не умеет выдать нужное поле (например, `outlier_score`), откройте соответствующую вкладку (Outliers или Keywords), выставьте фильтры из блока «Ручной вариант» и перепишите значения в тот же CSV. Неизвестное значение = `NA`, а не пусто и не догадка.
5. Скопируйте все CSV-блоки целиком в один ответ LEAD-у (или в файл `vidiq_results_<дата>.md`, если LEAD попросит) и добавьте строку: `checked_at: YYYY-MM-DD, account: <какой>, credits_used: <сколько>`.

---

## P0 — контекст (вставить один раз)

```
You are helping me research topics for a new Kazakh-language YouTube channel: 3–5 minute animated explainer videos (flat vector style, one mascot), audience 13+ in Kazakhstan, languages Kazakh (main) and Russian (audience overlap).
We take only the IDEA from successful fresh English videos and remake it with a Kazakhstan angle.
Rules for every answer in this session:
1) Only long-form videos (duration >= 3:00). Exclude Shorts, kids content, music, live streams, gaming, news clips under 3 minutes.
2) Freshness: published within the last 12 months unless I say otherwise.
3) Return data ONLY as CSV inside a code block, with exactly the header I give. One row per item. Use NA for unknown values; never estimate silently.
4) Do not summarize or comment outside the CSV unless I ask. If you hit a limit, stop and say "TRUNCATED at row N".
Reply "OK" if understood.
```

---

## P1 — свежие выбросы по жанрам (Outliers)

Запускайте шаблон один раз на жанр: подставьте `{GENRE}` и `{SEEDS}` из таблицы ниже. Ответ — **таблица A**.

```
Find outlier videos for genre: {GENRE}.
Seed keywords (search each, then merge): {SEEDS}.
Filters: language English; published in the last 12 months; duration >= 3:00; views >= 300,000; outlier score >= 3x (video views vs the channel's typical views).
Return the top 15 by outlier score, deduplicated by video.
Output CSV with exactly this header:
video_id,url,title,channel,channel_subs,published_date,views,vph,outlier_score,duration_sec,language,genre,seed_keyword
Use the genre code {CODE} in the genre column. Dates as YYYY-MM-DD, numbers without separators.
```

| CODE | {GENRE} | {SEEDS} |
|---|---|---|
| NAT | nature and animals | wild horses; eagles hunting; snow leopard; desert animals survival; steppe wildlife; venomous spiders |
| SCI | science and surprising nature facts | ancient seas fossils; impact craters; salt lakes; glaciers melting; El Nino explained; dinosaurs discovered |
| SPACE | space | Soviet space program; Soyuz rocket; spacesuit how it works; moon race; asteroid impact Earth; space station cost |
| PSY | psychology and the brain | brain science explained; memory and forgetting; bilingual brain; reading and the brain; attention span; risky play children |
| MOT | motivation and discipline (stories and research only) | psychology of discipline; procrastination animation; laziness science; habits research; self control experiment |
| HIST | history and culture | nomads history; steppe empires; Golden Horde; traditional games history; ancient horse riders; Silk Road cities |
| GEO | geography | why nobody lives here; coldest cities; shrinking sea; lake drying up; landlocked countries; desert cities |
| HOW | how it works | railway border gauge change; mining explained; dams engineering; roads engineering; banknote printing; ports logistics |
| ECON | economics of everyday things | how restaurants make money; why food is expensive; wedding costs; street food economics; currency design |
| FACT | surprising facts | most expensive things; strange traditions; weird country facts; record breaking facts |
| FOOD | food science and history | food preservation history; fermented milk drinks; meat curing; tea traditions; bread history |
| STORY | famous stories | walk around the world; epic survival journey; record swim; extraordinary expedition |

**Ручной вариант (вкладка Outliers):** ключевое слово = один seed → Published: Last 12 months → Duration: Long (> 3 min) или «Exclude Shorts» → Outlier score: ≥ 3x → Language: English → сортировка по Outlier score. Перепишите первые 15 строк в таблицу A.

**Дополнительный проход на русском** (наша аудитория смотрит и русский YouTube): тот же шаблон, но `language Russian` и seeds на русском — например, для GEO: «почему здесь никто не живёт; самый холодный город; Каспий мелеет; Арал возвращается». В колонке `language` ставьте `ru`.

---

## P2 — проверка источников из backlog (сначала топ-12)

Ответ — **таблица A** (`genre` = код из backlog, `seed_keyword` = номер темы, например `#7`).

```
Look up these YouTube videos and return their current stats. For each: views, VPH (views per hour, current), outlier score vs the channel's typical performance, channel subscribers, published date, duration.
Video IDs (in this order):
9-eQiEQOhyo, CkP_8bkjf1E, ikUSFU7TlYc, 80dkYKwJPv4, aJVyUwKhH5k, 7_VKQ1T6BeM, aob7rM5PV5A, gLkbK8h_9fc, Hl8vErrqjKY, wG-tBlxfxgs, XQURgDXevf0, I5QMtbO-DNk
Output CSV with exactly this header:
video_id,url,title,channel,channel_subs,published_date,views,vph,outlier_score,duration_sec,language,genre,seed_keyword
```

Если кредиты остались, второй запрос — резерв и B-темы (тот же текст, другие ID):

```
cJ2NJC_h0XI, vfIaNeGVaVo, cwGnjsK2-2s, dXRRLQEd5r4, X1L1Hd3xfrU, nBdjwRmJRbU, 3YvwqMDDb3k, cfT46UVhTfo, twMvQ64jom8, tcAbgMN3wl8, jXwOcpkMQAA, 0NVb5M7m9xg, F8zqVO8UqTM, wtovy-1-QUM, LOn-mmezykQ, 68lNiatVLfc, ZSch_NgZpQs, -3UDbjjiOxs, TAIHGFF_RD0, hX21ctsGhNc, tdIUMkXxtHg, kRAl4Xgs_NU, 2Tu4da82mF4, oNmxLEHwaqY
```

**Ручной вариант:** откройте каждое видео на YouTube с расширением vidIQ — в боковой панели видны Views, VPH и Outlier score. Перепишите их в таблицу A.

---

## P3 — спрос на ключевые слова (казахский и русский)

Ответ — **таблица B**. Запускайте двумя частями (по 12 тем), чтобы не обрезалось.

```
Do keyword research for the keywords below. Region: Kazakhstan if available, otherwise worldwide. For each keyword give: monthly search volume on YouTube, competition, overall score (vidIQ 0–100), 12-month trend (rising/stable/falling), and the top 3 related keywords in the same language.
If there is no data for a keyword, still output the row with NA — do not drop it.
Output CSV with exactly this header:
topic_num,keyword,language,search_volume_monthly,competition,overall_score,trend_12m,related_1,related_2,related_3
Keywords (topic_num | language | keyword):
#0 | kk | қазақтар қыста қалай өмір сүрді
#0 | kk | жұт деген не
#0 | ru | как казахи жили зимой
#0 | ru | джут
#7 | kk | Абай бес дұшпан
#7 | kk | еріншектік
#7 | ru | как перестать лениться
#7 | ru | психология дисциплины
#3 | kk | ең суық астана
#3 | ru | самая холодная столица мира
#3 | ru | почему в Астане так холодно
#2 | kk | алманың отаны
#2 | ru | родина яблок
#2 | ru | яблоня Сиверса
#30 | kk | Карл Бушби
#30 | ru | Карл Бушби Каспий
#40 | kk | теңге тарихы
#40 | ru | история тенге
#40 | ru | лучшая банкнота мира
#11 | kk | асық ату
#11 | ru | игра в асыки
#39 | kk | Қорғас құрғақ порт
#39 | ru | сухой порт Хоргос
#39 | ru | смена колеи поезда
```

Вторая часть:

```
(same instructions and header as before)
#21 | kk | Пржевальский жылқысы
#21 | ru | лошадь Пржевальского Казахстан
#26 | kk | соғым
#26 | kk | сүр ет
#26 | ru | как хранили мясо без холодильника
#44 | kk | Маңғыстау акула тісі
#44 | ru | Мангистау дно океана
#4 | kk | Бетпақдала
#4 | ru | Бетпак-Дала голодная степь
#23 | kk | бүркітші
#23 | ru | охота с беркутом
#17 | kk | Тұйықсу мұздығы
#17 | ru | ледники Алматы тают
#42 | kk | Арал теңізі қайта оралды
#42 | ru | Аральское море возвращается
#22 | kk | ілбіс
#22 | ru | снежный барс Казахстан
#10 | ru | как чтение меняет мозг
#15 | ru | советская лунная ракета Н1
#43 | ru | Каспий мелеет
```

**Ручной вариант (вкладка Keywords):** по одному ключу → запишите Search volume, Competition, Overall score и 3 первых Related. Если vidIQ пишет «not enough data», ставьте `NA` во все числовые поля.

---

## P4 — вернуть идеи v1 со свежим источником

Эти темы убраны из backlog только потому, что их источники старше 24 месяцев. Ищем свежий выброс на тот же вопрос. Ответ — **таблица A** (`seed_keyword` = тема).

```
For each topic below, find the single best English long-form video (>= 3:00) published in the last 12 months (if none, last 24 months) with the highest outlier score on that topic. Minimum 300,000 views.
Topics:
1) why seasons and equinoxes happen (spring equinox)
2) largest landlocked country / how landlocked countries trade
3) mudflow or debris-flow protection dams
4) Baikonur cosmodrome / why rockets launch from Kazakhstan
5) navigating by the stars (North Star) without instruments
6) Silk Road cities and trade
7) horse domestication (Botai)
8) hunting dogs / sighthounds history
9) buzkashi / kokpar horse sport
10) why countries move their capital city
11) caviar and sturgeon (why so expensive)
12) birth of a new national currency
Output CSV with exactly this header:
video_id,url,title,channel,channel_subs,published_date,views,vph,outlier_score,duration_sec,language,genre,seed_keyword
If no video meets the filters for a topic, output one row with NA values and the topic in seed_keyword.
```

---

## P5 — конкуренты: кто уже снял наши темы на казахском и русском

Ответ — **таблица C**. Нужен, чтобы понять, где мы будем первыми, а где — догоняющими.

```
For each query below, search YouTube in the stated language and return the top 3 long-form videos (>= 3:00) by views, any publish date.
Mark whether the video is animated (yes/no/unsure from thumbnail and title).
Output CSV with exactly this header:
topic_num,query,language,rank,url,title,channel,channel_subs,published_date,views,outlier_score,is_animated
Queries (topic_num | language | query):
#0 | kk | қазақтар қыста қалай өмір сүрді
#7 | kk | Абай бес дұшпан
#3 | ru | почему Астана такая холодная
#2 | ru | родина яблок Алматы
#30 | ru | Карл Бушби Каспий
#40 | kk | теңге тарихы
#11 | kk | асық тарихы
#39 | ru | Хоргос сухой порт как работает
#21 | ru | лошади Пржевальского Алтын Дала
#26 | kk | соғым сүр ет
#44 | ru | Мангистау древний океан
#4 | ru | Бетпак-Дала
```

---

## Форматы ответа (что именно копировать обратно)

Все три таблицы — CSV с запятой, заголовок ровно как ниже, даты `YYYY-MM-DD`, числа без пробелов и запятых внутри (например `1022329`), `outlier_score` — число (например `4.2`), неизвестно → `NA`.

**Таблица A — видео (P1, P2, P4):**
```
video_id,url,title,channel,channel_subs,published_date,views,vph,outlier_score,duration_sec,language,genre,seed_keyword
```

**Таблица B — ключевые слова (P3):**
```
topic_num,keyword,language,search_volume_monthly,competition,overall_score,trend_12m,related_1,related_2,related_3
```

**Таблица C — конкуренты (P5):**
```
topic_num,query,language,rank,url,title,channel,channel_subs,published_date,views,outlier_score,is_animated
```

В конце ответа добавьте одну строку: `checked_at: YYYY-MM-DD; account: <имя>; credits_used: <число или NA>; prompts_run: P0,P2,...`.

## Rules for our system

Как LEAD переносит результаты vidIQ в `topics_backlog.md`:

1. **O из vidIQ важнее нашего.** Если `outlier_score` ≠ NA, O пересчитывается по шкале backlog: <1 → 0; 1–2 → 1; 2–3 → 2; 3–5 → 3; 5–20 → 4; >20 → 5. Наш расчёт по медиане канала остаётся в заметке.
2. **D и Fr** пересчитываются по свежим `views` и `published_date` из таблицы A (шкалы из backlog, правило 3).
3. **Новая тема из P1/P4** попадает в backlog, только если: `published_date` ≤ 365 дней (или ≤ 730 при `outlier_score` ≥ 3), `views` ≥ 300 000, длительность ≥ 180 с, и LEAD или topic-scout придумал казахский угол с K ≥ 3.
4. **Спрос на ключевые слова — тай-брейкер, а не слагаемое.** При равном балле выше ставим тему, у которой сумма `search_volume_monthly` (kk + ru) больше. Если у всех ключей темы `NA`, пишем в заметке «спрос kk/ru не измерен».
5. **Сигнал «казахский пробел»:** если по запросу на kk в таблице C нет ни одного ролика с ≥ 50 000 просмотров, ставим теме метку `kk_gap` (мы будем первыми). Если есть анимированный kk-ролик с ≥ 200 000 просмотров, ставим метку `kk_competitor` и требуем другой подвопрос.
6. **Низкое доверие:** если в таблице A `channel_subs` < 10 000, а `views` > 1 000 000, ролик помечается `low_trust_source` (вероятно, AI-канал): спрос учитываем, факты не берём.
7. **NA не превращать в ноль.** Пустые поля vidIQ не понижают тему. Тема сохраняет прежнюю оценку и получает пометку «vidIQ: NA».
8. **Снимок:** в backlog у каждой обновлённой строки пишется `vidIQ <checked_at>`, чтобы через 30 дней было видно, какие данные устарели. Повторная проверка — не чаще раза в 30 дней на тему.
9. **Кредиты:** при остатке меньше чем на 3 промпта запускать только P2 (топ-12) и первую часть P3.

## Contradictions with PROJECT_BRIEF

1. Роль `.claude/agents/topic-scout.md` разрешает агенту до 25 вызовов vidIQ, а §10.6 брифа — только ручной прогон владельцем. Этот файл следует §10.6.
2. P1 включает русскоязычный проход, а бриф §1 говорит об англоязычных источниках. Это сделано намеренно: русский — сигнал спроса для нашей аудитории (см. backlog, Contradictions 1). Если владелец против, русскоязычный проход можно пропустить.

## Open questions

1. Какие функции есть в тарифе второго аккаунта vidIQ (Outliers, Keywords, AI Coach)? Названия полей в интерфейсе могут отличаться от шаблонов. Тогда переписывайте значения вручную в те же колонки.
2. Даёт ли vidIQ данные по казахскоязычным ключам? Скорее всего, объёмы будут `NA` или очень малыми **[Estimate — казахский поиск мал по объёму]**. Тогда опираемся на русские ключи и таблицу C.
3. Сколько кредитов стоит каждый промпт — неизвестно. Попросите владельца записать `credits_used`, чтобы спланировать следующие прогоны.

## Sources

- `docs/PROJECT_BRIEF.md` v1.2, §10.6–10.7 (решения владельца 17.10.2026).
- `docs/research/topics_backlog.md` v2 (ID видео, номера тем, шкалы D/O/Fr).
- Видео из P2 — страницы YouTube, проверены 2026-10-17 (список URL — в `topics_backlog.md`, раздел Sources).
