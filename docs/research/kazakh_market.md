# Kazakh market and language tech: YouTube landscape, TTS, ASR, fonts

> Owner: kazakh-market-researcher · Date: 2026-10-17 · Brief sections: §2.1, §5.2, §6.2
> Method: vidIQ was unavailable because the account had 0 credits (2 calls refused, nothing charged). Channel and video numbers come from public YouTube pages, read on 2026-10-16/17 with a small script (`ytInitialData`), plus web search. View counts are rounded the way YouTube shows them. "м." in Kazakh UI means thousand (мың).

## TL;DR
- **The niche has competitors.** Kazakh-language history and "interesting facts" channels already exist and reach 100–850K views per video: SHKAMURO (503K subs), Тарих Марих (195K), qaztarih (43.6K, animated maps). Low-effort AI channels in Kazakh are appearing in large numbers. The real gap is in well-made animated explainers about science, economics and "how it works": in Kazakh these topics mostly get 1–20K views, and supply is very low. [Fact — YouTube pages listed below; Estimate for the gap]
- **Our pilot topic has proven demand, but in Russian.** Qalam History covers Kazakh topics in Russian and gets 85–300K views per video on exactly our angles: "Kystau and the ancient technologies of the steppe" 136K, "How did Kazakhs live 200 years ago" 210K. [Fact — https://www.youtube.com/@Qalamhistory] A Russian audio track is a cheaper second-language win than English. [Estimate]
- **ElevenLabs: only Eleven v3, v4 and v4 Turbo support Kazakh (`kk`).** Multilingual v2 (the API default), Flash v2.5 and Turbo v2.5 do **not**. Eleven v4 was released on 2026-09-28. [Fact — https://elevenlabs.io/docs/overview/models]
- **Gemini 3.8 Flash TTS and 3.8 Flash-Lite TTS list Kazakh.** [Fact — https://ai.google.dev/gemini-api/docs/speech-generation] I found no independent Kazakh quality test for ElevenLabs or Gemini TTS. [Fact — searches returned only vendor marketing]
- **faster-whisper large-v3 zero-shot is weak on Kazakh:** about 31–39% WER on FLEURS. Better options: ElevenLabs Scribe v2 (Kazakh in the "High accuracy" 5–10% WER band, word timestamps), Gemini 3.5 Transcribe (`kk-KZ`, word timestamps), and Kazakh fine-tunes at about 12% WER. If the voice is generated through the ElevenLabs API, `/with-timestamps` returns character timings directly, so no ASR is needed. [Fact — sources in §4]
- **Inter covers the full Kazakh Cyrillic set (checked via the font cmap).** Many popular display fonts do **not**: Unbounded, Russo One, Dela Gothic One, Days One, Jost, Sofia Sans, Wix Madefor, and Manrope (partly). Seven of the nine Kazakh letters sit in Google's `cyrillic-ext` subset, so that subset must be loaded. [Fact — local fontTools check + Google Fonts CSS]
- **Latin-script reform has no timeline** as of 2026-09-08, after the 2025 target was missed. Cyrillic is correct for now. [Fact — https://hronika.kz/?p=18619]
- **Real Kazakh text mixes in homoglyphs**, e.g. Latin `ə` U+0259 instead of Cyrillic `ә` U+04D9 (seen in a 343K-subscriber channel's description). Normalize before TTS, alignment and rendering. [Fact — https://www.youtube.com/@kazvoice_channel]

## 1. Kazakh-language YouTube: who is there, what gets views

### 1.1 Channels close to our format (data from 2026-10-16/17)
| Channel | URL | Subs | Lang | Format | Typical recent views | Notes |
|---|---|---|---|---|---|---|
| SHKAMURO | https://www.youtube.com/@SHAKAMURO | 503K | kk | Narrated documentary (stock footage), world mysteries, true crime, history | 26K–263K; most 60–150K | "Шымкенттің қасапшысы" 148K; "Ғаламның шегі бар ма?" 398K (4 y). Strongest Kazakh "explainer-like" channel [Fact] |
| Тарих Марих | https://www.youtube.com/@tarihmarih | 195K | kk + ru | Talking head with humour and graphics, Kazakh history | 6K–114K recently; older hits 368K–854K | "3 жүз" 854K, "Қазақтар қайдан шықты" 368K (6 y). Mostly inactive for about 2 years [Fact] |
| qaztarih | https://www.youtube.com/@tarih.1269 | 43.6K | kk | **Animated maps and graphics**, world and Turkic history | 13K–78K | "Түрік қағанаты" 60K, "Орыс-жапон соғысы" 78K. Closest to an animated explainer; last uploads about 1 year ago [Fact] |
| Qazaqstan tarihy (e-history) | https://www.youtube.com/@e-history | 179K | kk (some ru) | Institutional: interviews, lectures | 0.2K–10K | State-portal style, low engagement per video [Fact] |
| Qalam History | https://www.youtube.com/@Qalamhistory | 98.8K | **ru** | Documentary and talking head, Kazakh ethnography and history | 12K–295K | "Мүшел" 216K, "Как жили казахи 200 лет назад" 210K, "Kystau…" 136K. Same topics as ours, in Russian [Fact] |
| DOMALAQ elder | https://www.youtube.com/@DOMALAQ-777 | 19.7K | kk | **3D countryballs animated satire** | 60K–160K | Views per video are 5–8× the subscriber count: character animation plus local geopolitics works [Fact] |
| kazvoice | https://www.youtube.com/@kazvoice_channel | 343K | kk | Film and franchise recaps ("жалпақ тілде") | 21K–119K | Shows that pop-culture explaining in Kazakh has an audience [Fact] |
| ANIMATION KZ | https://www.youtube.com/@ANIMATIONKZ | 12.7K | kk | Animated horror stories | 33K–363K | Inactive for about 1 year [Fact] |
| Olzhas Tokhabai animation | https://www.youtube.com/@olzhastokhabaianimation | 30.6K | kk | Indie animation and cartoon reviews | 2K–67K | [Fact] |
| BN KZ | https://www.youtube.com/@bnkz9873 | 28.6K | kk | Fact compilations (dubbed docs) | 1.5K–18K | Inactive for 3 years [Fact] |
| SAQ Kinostudiasy | https://www.youtube.com/@SAQKinostudiasy | 219K | kk | Kids' cartoons and films | 1K–373K | Kids' segment, not our audience [Fact] |

Additional context:
- Large Kazakh-language channels are mostly **gaming and entertainment**: Nurlan Qalam 817K, QalamGo 324K. [Fact — https://www.youtube.com/@NurlanQalam, https://www.youtube.com/@Qalamgo]
- A Kazakh search for "қазақша ғылым анимация" or "қазақша қызықты фактілер" returns dozens of **new channels with 1–300 subscribers** (e.g. "Qazaq History | Анимация" 88 subs, "Қызық ФАКТ KZ", "Ежелгі Тарих", "Dala shejiresy"). Their recent videos get 0.2–3K views. [Fact — YouTube search, 2026-10-16] These look like AI-generated channels. [Estimate] This is the "inauthentic content" crowd the brief wants to stand apart from. [Estimate]

### 1.2 Which topics get views (Kazakh-language videos, from YouTube search)
| Topic cluster | Evidence | Signal |
|---|---|---|
| Origins and identity of Kazakhs, zhuz, khanate | "3 жүз" 854K, "Қазақтар қайдан шықты" 368K (Тарих Марих); "Қазақ хандығы қалай құрылды" 213K (JUZ40 ONLINE); "Қазақ хандығының ШЫНАЙЫ ТАРИХЫ" 125K (Тарихстан) [Fact — YouTube search] | **Strong** |
| School and exam (ҰБТ/UNT) history | "Алғашқы адамдар… 5-класс" 125K (QHistory); JUZ40 213K [Fact — YouTube search] | Strong, evergreen; students are a large audience [Estimate] |
| Everyday life and ethnography of the past (our pilot) | Russian-language Qalam: 136–216K. Kazakh "Қазақтар бұрын қалай сүйді?" 24K in 1 month (50 минуттық тарих) [Fact] | Strong in RU, emerging in KK |
| World history, wars, empires | qaztarih 13–78K; SHKAMURO "Бейбарыс" 87K, "Собибор" 147K [Fact] | Medium–strong |
| Dark, mysterious, true crime | SHKAMURO 100–263K [Fact] | Strong, but conflicts with brand tone and with YouTube's "emotionally manipulative" category (brief §3.2) [Estimate] |
| Local geopolitics with characters | DOMALAQ elder 60–160K [Fact] | Strong, but politically sensitive [Estimate] |
| Science, space, "how it works", economics, money | "Теңге қалай пайда болды?" 84K (9 y); "Ғарыштағы ең керемет 8 минут" 243K (7 y). Most others 0.04–27K ("ПРОЦЕССОР деген не?" 1.7K; "Жел электр қондырғылары" 4.4K; Balapan TV "Ақша қалай пайда болды?" 8–18K) [Fact — YouTube search] | **Low supply, unproven demand.** This is the real gap, and also the riskiest bet [Estimate] |
| Jut / natural disasters | Kazakh videos on "жұт" are mostly news or rural talk shows (6–134K); there is no explainer [Fact] | A "white spot" for our pilot [Estimate] |
| Self-development and money podcasts | 100–650K (Абдрашит Түлкібай etc.) [Fact] | High demand, but finance/health advice is off-limits for us (brief §3.2) |

Takeaway [Estimate]: lead with **Kazakh history and everyday-life explainers** (proven demand, weak animated supply). Mix in "how it works" and economics as tests. Hooks should use the identity framing that drives views ("Қазақтар қалай…", "Неге қазақтар…").

## 2. Audience
- **Internet use:** 19.5M users, 93.4% penetration (end of 2025). 16.9M social-media identities, 80.8% of the population. Median mobile download speed is 91.7 Mbps, *higher* than fixed broadband at 81.7 Mbps. [Fact — https://datareportal.com/reports/digital-2026-kazakhstan, published 2025-11-08] Phones are the primary screen, so text on screen must be readable on mobile. [Estimate]
- **TikTok is the largest platform** (16.9M ad reach, 18+). Instagram has 13.1M. The 2026 report page has no YouTube figure. [Fact — same source] Short-form distribution matters. [Estimate]
- **Language:** 80.1% of citizens reported speaking Kazakh in the 2021 census, and Kazakhs are 70.4% of the population. [Fact — https://rep.vsu.by/bitstream/123456789/46586/1/49-53.pdf (secondary); https://stat.gov.kz/ru/national/2021/] About 70% of parents chose Kazakh-medium first grade, and 90% did in Almaty. [Fact — https://www.lada.kz/kazakhstan-news/140949-iazykovoi-vybor-roditeli-delaiut-stavku-na-kazakhskii-iazyk-v-nachalnoi-shkole.html; https://bes.media/amp/90-pervoklassnikov-v-almati-vibirayut-shkoli-s-kazahskim-yazikom-obucheniya-dosaev-5169c5/; year not shown, likely 2025] The Kazakh-speaking share of young viewers keeps growing. [Estimate]
- **Youth survey** (N=1,570, ages 14–35, Feb–Apr 2024, convenience sample; published 2026-09-04): the main reading language is Russian for 49.3% and Kazakh for 45.6%. People who *think* in Russian were 80.6% less likely to consume Kazakh media often (OR 0.194). 64–66% were satisfied with the amount and quality of Kazakh content. [Fact — https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2026.1819486/full] Kazakh content mainly reaches the Kazakh-dominant half. The bilingual half is reachable through a Russian track or subtitles. [Estimate]
- **Earlier industry view (2018):** Kazakh-language views were already about half of Kazakhstan's YouTube traffic. The core audience was 25–34, creator income was $200–500 per month, and there was "not enough content". [Fact — https://tengrinews.kz/article/kompleksov-mense-iuzerov-bolse-rastet-kazaxoiazycnyi-723/, dated 2018-02-28, so outdated]
- **Gaps in educational content are acknowledged but unfunded.** A 2023 review of 15 Kazakh kids' channels found no science or language-learning channels, and producers reported no state support. [Fact — https://forbes.kz/articles/balalara_arnalan_beynekontentt_kmder_jasaydyi, 2023-12-29] A deputy called for a state strategy for Kazakh children's digital content (undated). [Fact — https://tengrinews.kz/kazakhstan_news/vospityivaet-shkola-tiktok-deputat-predlojil-ogranichit-601794/] The state funded Kazakh cartoons that had to be uploaded to YouTube (350M KZT). [Fact — https://forbes.kz/articles/350mln-tenge-vydelili-nasozdanie-multfilmov-nakazahskom-yazyke; date not verified] I could not confirm any 2025–2026 grants for Kazakh educational bloggers. [Fact — search returned nothing]

## 3. TTS for Kazakh

### 3.1 ElevenLabs (checked 2026-10-17)
| Model | ID | Kazakh | Char limit | Notes |
|---|---|---|---|---|
| Eleven v4 | `eleven_v4` | **Yes** (`kk`) | 10,000 | Released 2026-09-28; flagship. Accepts inline IPA `/.../` [Fact — https://elevenlabs.io/docs/overview/models; https://elevenlabs.io/docs/best-practices/prompting/normalization; release date per https://www.vktr.com/ai-platforms/elevenlabs-launches-eleven-v4-and-v4-turbo/] |
| Eleven v4 Turbo | `eleven_v4_turbo` | Yes | n/a | Real-time, about 100 ms latency [Fact — same] |
| Eleven v3 | `eleven_v3` | Yes (`kk`) | 5,000 | "Previous generation"; known for expressiveness at some cost to stability [Fact — https://elevenlabs.io/docs/help-center/other/what-languages-do-you-support.md; stability note from secondary review https://framia.converge.ai/ru/models/eleven-v3] |
| Multilingual v2 | `eleven_multilingual_v2` | **No** (29 languages) | 10,000 | **This is the API default `model_id`** [Fact — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps] |
| Flash v2.5 / Turbo v2.5 | `eleven_flash_v2_5` | **No** (32 languages) | 40,000 | [Fact — models page] |

- **Normalization:** `apply_text_normalization` is `auto`/`on`/`off`, and `language_code` (ISO 639-1) enforces the language for normalization. `apply_language_text_normalization` is **Japanese only**. [Fact — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps] There is no evidence that ElevenLabs reads Kazakh numerals, dates or abbreviations correctly. [Fact — no source found] **We must spell everything out ourselves.** [Estimate]
- **Pronunciation dictionaries:** phoneme tags work only on `eleven_flash_v2`, which has no Kazakh. Alias tags (plain text replacement) work elsewhere. v4 accepts inline IPA. [Fact — https://elevenlabs.io/docs/best-practices/prompting/normalization] For Kazakh, use alias-style respellings and, on v4, IPA as a last resort. [Estimate]
- **Independent quality:** a peer-reviewed comparison (MDPI *Information* 16(10):879, Oct 2025) found ElevenLabs Kazakh speech "natural but less spectrally accurate". KazakhTTS2 had the most natural perceptual quality. The model version tested is unknown. [Fact — https://www.mdpi.com/2078-2489/16/10/879 (403 on fetch; read via search snippets)]
- **Known issues** (no Kazakh-specific public bug list found): expected risks are word stress on Russian loanwords, ordinals and years read as cardinals, Roman-numeral centuries, abbreviations read letter by letter, and drift between takes on v3. [Estimate — from general v3 stability notes and the absence of Kazakh normalization] Kazakh stress is usually on the last syllable, so loanwords with Russian stress can be read either way. [Estimate]

### 3.2 Gemini TTS
- `gemini-3.8-flash-tts` (130+ languages) and `gemini-3.8-flash-lite-tts` (100+) list **Kazakh**. Language is detected automatically. Both support voice design and voice replication. [Fact — https://ai.google.dev/gemini-api/docs/speech-generation, read 2026-10-17] Older preview models (2.5, 3.1) have no per-language table there. [Fact — same]
- I found no Kazakh quality evaluation. [Fact — search] Gemini TTS returns no word timestamps, so alignment would still need ASR. [Estimate — the docs page mentions no timestamp output]
- Possible role: a cheap automatic **draft voice for timing previews** before the operator records in ElevenLabs. [Estimate]

### 3.3 Writing text for Kazakh TTS (rules derive from §3.1)
Convert to words: years as **ordinals** ("1880 жылы" → "мың сегіз жүз сексенінші жылы"); centuries ("XIX ғ." → "он тоғызыншы ғасыр"); percentages ("50%" → "елу пайыз"); currency ("$5" → "бес доллар", "1 000 ₸" → "мың теңге"); decimals ("2,5" → "екі жарым" or "екі бүтін оннан бес"); ranges ("1–2" → "бір-екі"); abbreviations ("ж." → "жылы", "млн" → "миллион", "т.б." → "тағы басқа", "ҚР" → "Қазақстан Республикасы", "б.з.д." → "біздің заманымызға дейін", "км" → "шақырым"). [Estimate — standard Kazakh usage; the native-speaker operator confirms] The ordinal suffix follows vowel harmony: -ыншы/-інші after a consonant (бесінші, оныншы), -ншы/-нші after a vowel (екінші, алтыншы). [Estimate — standard grammar; cf. https://web.do.metacpan.org/pod/Lingua::KAZ::Word2Num] The written date format (CLDR) is "2026 ж. 16 қазан". [Fact — https://metacpan.org/dist/DateTime-Locale/view/lib/DateTime/Locale/kk.pod] For voice, write "екі мың жиырма алтыншы жылғы он алтыншы қазан" or "қазанның он алтысы". [Estimate]

## 4. ASR and word alignment
| Option | Kazakh accuracy | Word timestamps | Notes |
|---|---|---|---|
| faster-whisper large-v3, `language="kk"` (current brief) | FLEURS WER **31.1%** (CER 6.6%); 40.8% on an internal set [Fact — https://huggingface.co/shyngys879/kazakh-whisper-large-v3-turbo]. 38.6% per ElevenLabs [Fact — https://elevenlabs.io/speech-to-text/kazakh, vendor]. Zero-shot CER 7.9 (FLEURS) and 12.6 (Common Voice 25) [Fact — https://huggingface.co/BuzzASR/kazakh] | Yes | Weak, and timestamps drift on misrecognized words [Estimate]. A domain study found Whisper WER 77% vs Soyle 18.6% [Fact — https://www.mdpi.com/2078-2489/16/10/879, via search snippet] |
| Whisper large-v3 **turbo**, zero-shot | FLEURS WER 19.75% [Fact — shyngys879 card] | Yes | Better and faster than large-v3 on kk [Fact — same card] |
| Kazakh fine-tune `shyngys879/kazakh-whisper-large-v3-turbo` (Apache-2.0) | FLEURS WER **11.8%**, CER 5.0% [Fact — same card] | Yes, via whisper | Needs CTranslate2 conversion for faster-whisper (`ct2-transformers-converter`); the card has no CT2 build [Fact — card]. Self-reported numbers |
| `InflexionLab/sybyrla` (large-v3 fine-tune, kk+ru) | ~17.7% WER on KSC2 test [Fact — https://huggingface.co/InflexionLab/sybyrla/blob/main/README.md] | Yes | Handles kk/ru code-switching [Fact — training mix] |
| ElevenLabs Scribe v2 | "High accuracy" band, 5–10% WER (`kaz`) [Fact — https://elevenlabs.io/docs/overview/capabilities/speech-to-text]; Scribe v1 8.2% FLEURS [Fact — vendor page] | **Yes** | Paid; same vendor as voice |
| Gemini 3.5 Transcribe (`gemini-3.5-transcribe`) | Kazakh `kk-KZ` listed; no Kazakh WER published [Fact — https://ai.google.dev/gemini-api/docs/models/gemini-3.5-transcribe, updated 2026-09-01]. Gemini 2.0 Flash had 8.8% FLEURS WER (vendor-reported by ElevenLabs) [Fact — https://elevenlabs.io/speech-to-text/kazakh] | Yes (≤30 min per request with timestamps; the docs say timestamps *degrade* accuracy) | Already in our Gemini stack |
| ElevenLabs TTS `/with-timestamps` (when the `ElevenLabsApi` provider is used) | No ASR involved | Character-level `alignment` and `normalized_alignment` [Fact — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps] | **Best option for P5**: exact timings for the exact text |
| ElevenLabs Forced Alignment API | Kazakh **not** listed (29 v2 languages) [Fact — https://elevenlabs.io/docs/overview/capabilities/forced-alignment] | — | Do not rely on it for kk |

What this means for alignment against a known, approved text [Estimate]:
- Do not trust ASR words. Align ASR word timings to approved-script tokens with a **character-level** fuzzy sequence alignment (e.g. Needleman–Wunsch or `difflib` on lowercased, normalized text). CER (5–8%) is much better than WER on Kazakh because the language is agglutinative: one wrong suffix makes the whole word an error.
- Interpolate timings for unmatched words between anchored neighbours. Fall back to silencedetect (already in the brief) for phrase boundaries.
- Acceptance metrics: ≥ 90% of script words anchored; median |Δt| at caption boundaries ≤ 150 ms. Otherwise re-run with the next engine.

## 5. Fonts and script
Coverage was checked by reading the cmap of current Google Fonts TTFs from `github.com/google/fonts` on 2026-10-17 for: әғқңөұүһі ӘҒҚҢӨҰҮҺІ.
- **Full Kazakh coverage** [Fact — local fontTools check of https://github.com/google/fonts/tree/main/ofl]: **Inter** (variable, opsz 14–32, wght 100–900), Montserrat (100–900), Rubik (300–900), Rubik Mono One, Nunito (200–1000), Mulish, Golos Text (400–900), Onest (100–900), Exo 2, Oswald, Tektur, Commissioner, Comfortaa, Balsamiq Sans, Roboto, Noto Sans, Open Sans, PT Sans, Fira Sans, IBM Plex Sans, Raleway. All of these also cover the 2021 Kazakh Latin letters (Ä Ö Ü Ş Ç Ğ I ı Ń Ū).
- **Missing Kazakh letters**, so do NOT use them: Unbounded, Russo One, Dela Gothic One, Days One, Sofia Sans, Wix Madefor Text (missing әғқңөұүһ). Jost lacks all of them, including і. Manrope lacks әғқңұ. [Fact — same check]
- **Subsetting trap:** Google Fonts' `cyrillic` subset covers U+0400–045F and U+04B0–04B1 (і, ұ). ә ғ қ ң ө ү һ live in **`cyrillic-ext`** (U+0460–052F). [Fact — https://fonts.googleapis.com/css2?family=Inter:wght@800] If only `cyrillic` is loaded, Remotion renders fallback glyphs. [Estimate]
- **Recommended pairing for the flat cream style** [Estimate]: captions and labels in Inter 700–800; display numbers and titles in Montserrat 800–900 or Rubik 800–900 (rounded and friendly, fits the mascot). Golos Text and Onest are designed for Russian/CIS interfaces and are a good alternative. Thumbnails: Montserrat Black or Rubik Black.
- **Latin reform:** the 2021 plan was a phased transition through 2031 [Fact — https://astanatimes.com/2021/02/kazakhstan-presents-new-latin-alphabet-plans-gradual-transition-through-2031/]. As of **2026-09-08** there is no set timeline: the alphabet and orthography are "still being refined" and a government directive is required. [Fact — https://hronika.kz/?p=18619] **Do not build Latin support now.** Keeping text as clean Unicode is enough, and the fonts above already cover Latin if needed. [Estimate]
- **Homoglyphs:** a top Kazakh channel's description uses Latin `ə` (U+0259) instead of Cyrillic `ә` (U+04D9). [Fact — https://www.youtube.com/@kazvoice_channel] Other common lookalikes are Latin i/h vs Cyrillic і/һ, and Latin o/a/e/c/p/x vs their Cyrillic twins. These break TTS, tokenization, similarity checks and alignment. [Estimate]

## 6. Cultural and tone notes
- **Tone:** curious, respectful, lightly humorous (Тарих Марих shows humour works for history). Avoid sensationalism; SHKAMURO-style "ШОК / СҰМДЫҚ" titles get views but clash with the brand and with the "emotionally manipulative" category. [Fact for the examples — channel pages; Estimate for the recommendation]
- **Sensitive topics** (handle with sources and neutral wording; avoid jokes): Ашаршылық (1930s famine), 1916 uprising, Desert/Alash repressions, жүз and ру (tribal) comparisons or rankings, religion, relations with Russia and China, borders, and current politics. [Estimate] These are also among the most-viewed topics (Alash 295K, 1930s, 1916 on Qalam). [Fact — channel pages]
- **Terminology:** use established Kazakh terms (киіз үй, қыстау, жұт, тезек, көш, ру, жүз, хандық). Gloss rare archaic or neologism terms once on screen. Prefer the forms used in school textbooks so ҰБТ students recognise them. [Estimate] Pure Kazakh voice-over is fine: the top Kazakh channels use pure Kazakh, while Тарих Марих mixes in Russian. [Fact — channel pages]
- **Names:** use Kazakh forms (Абылай хан, Кенесары, Қасым хан, Алматы, Шымкент). Do not use Russified spellings in Kazakh text. [Estimate]
- **Titles:** the identity framing "Қазақтар қалай/неге…" is a proven hook (§1.2). [Fact for the views; Estimate for causality] Use sentence case or mixed case: ALL-CAPS Kazakh titles are common, but they hide the diacritics in thumbnails at small sizes. [Estimate]

## Rules for our system
1. **TTS model whitelist (kk):** `eleven_v4` (default) or `eleven_v3`. Block `eleven_multilingual_v2`, `eleven_flash_v2_5` and `eleven_turbo_v2_5` when `language=kk`. The "Copy for ElevenLabs" step shows the reminder "Model: Eleven v4". Any `ElevenLabsApi` call must set `model_id` explicitly, because the default is v2.
2. **No digits in TTS text (kk).** Before step 5, `tts_normalize_kk()` must output text that matches `^[^0-9%$€₸№§]*$` and contains no standalone Roman-numeral tokens (`\b[IVXLC]+\b`). Years become ordinals ("1880 жылы" → "мың сегіз жүз сексенінші жылы"), centuries become ordinal words, % → "пайыз", currency → words, ranges → "бір-екі".
3. **Abbreviation expansion table** (`/prompts/kk_abbrev.json`, at least: ж., ғ., млн, млрд, мың, т.б., т.с.с., ҚР, КСРО, б.з.д., км, кг, га, %, ₸, $). Run it before TTS. A unit test asserts that the output contains no "." inside a word token.
4. **Homoglyph normalization** on every Kazakh text entering the DB: map U+0259→ә, U+018F→Ә, Latin i/I→і/І *inside Cyrillic words*, h→һ, and Latin a/e/o/p/c/x/y/k/H/B/M/T→Cyrillic twins inside Cyrillic words. Reject a script if any token mixes scripts after normalization.
5. **Script word budget:** keep 500–550 words, but compute expected duration from a measured speaking rate. After the first 3 voice-overs, store `words_per_sec` per voice and use it for the step-4 counter. Default until measured: 2.2 words/s. [Estimate]
6. **Alignment engine order (kk):** (a) if the voice came from the ElevenLabs API, use `/with-timestamps` character alignment; (b) otherwise use ElevenLabs Scribe v2 or `gemini-3.5-transcribe` with word timestamps; (c) offline fallback is faster-whisper with **`large-v3-turbo`** or a CT2-converted Kazakh fine-tune (e.g. `shyngys879/kazakh-whisper-large-v3-turbo`), **not** plain `large-v3`. Make it a setting.
7. **Alignment acceptance:** align at the character level to the approved script. Pass if ≥ 90% of script words are anchored and every caption start is within 150 ms of an anchored word. Otherwise try the next engine, then silencedetect, and flag the result to the operator.
8. **Fonts:** a render-time check fails the build if any glyph in props text is missing from the chosen font (fontTools cmap check). Allowed defaults: Inter (body and captions), Montserrat or Rubik (display). Never use Unbounded, Russo One, Dela Gothic One, Days One, Jost, Manrope, Sofia Sans or Wix Madefor for kk.
9. **Font loading:** self-host full TTF/WOFF2 files, or include the `cyrillic-ext` subset (U+0460–052F) along with `cyrillic` and `latin`. Never ship `cyrillic` only.
10. **Script stays Cyrillic** (`kk-Cyrl`). Store a `script` field on `Project` (default `Cyrl`) so a `Latn` transliteration step can be added later without schema change. Do not build that step now.
11. **Topic scoring prompt (step 2):** give +2 to angles framed around Kazakh identity, everyday life or history ("Қазақтар қалай/неге…"), +1 to ҰБТ-curriculum relevance, and +1 to "how it works" or economics *only* when tied to a Kazakhstan object (теңге, Байқоңыр, мұнай, жұт). Give −2 to true crime, gore, "ШОК" framing, and current politics.
12. **Sensitive-topic gate:** if the brief touches Ашаршылық, 1916, repressions, жүз/ру, religion, Russia/China, or borders, require ≥ 2 independent sources per numeric fact and a neutral-tone check by the LLM judge. Ban jokes and mascot "popcorn/excited" poses in those scenes.
13. **Terminology:** the script-writer prompt must use Kazakh name forms (Абылай хан, Қасым хан, Алматы). On first mention, gloss terms outside a school-textbook vocabulary with a ≤ 5-word on-screen label.
14. **Titles:** step-10 titles must be ≤ 60 characters, in sentence case (no ALL-CAPS longer than 2 words), and emoji-free in the render. At least 2 of the 5 options use a question hook ("…қалай?", "Неге…?").
15. **Second language order:** set the `language` enum to `kk`, then `ru`, then `en`. Plan a Russian audio track and subtitles as the first expansion, since Russian-language channels on Kazakh topics get 2–5× more views (Qalam).

## Contradictions with PROJECT_BRIEF
1. **§2.1 "almost no competition"** overstates it. Kazakh history/explainer channels with 40–500K subscribers exist (SHKAMURO, Тарих Марих, qaztarih), and the pilot-style ethnography topics are already covered in Russian by Qalam History (99K subs, 100–300K views). The gap is narrower: *high-quality animated* Kazakh explainers, especially science, economics and "how it works". A wave of low-effort AI Kazakh channels has also started.
2. **§4.2/§6.2 ElevenLabs** has no model specified. The default `eleven_multilingual_v2` (and Flash/Turbo) does **not** support Kazakh. Only v3, v4 and v4 Turbo do. If `PROMPTS.md` assumes Multilingual v2, it must be updated.
3. **§6.2 faster-whisper large-v3 `language="kk"`** is the weakest option measured (FLEURS WER about 31–39%). The turbo model (about 20%), Kazakh fine-tunes (about 12%), Scribe v2 (5–10%) or ElevenLabs `/with-timestamps` are better. Keep faster-whisper only as an offline fallback with a better checkpoint.
4. **§2.2 "later — English version"**: the data suggests a **Russian** track is the cheaper, larger second audience in Kazakhstan. English remains an option for diaspora and global reach.
5. **§5.2 "Inter or another font with full support"** is correct for Inter, but many trendy Google display fonts fail. The brief should name an explicit allow-list (Rule 8) and require the `cyrillic-ext` subset.
6. **§5.1 "500–550 words ≈ 4:00"** assumes about 2.2 words/s. That has not been verified for Kazakh TTS (long agglutinative words) and needs measuring (Rule 5).

## Open questions
- Real Kazakh quality of Eleven v4 vs v3 vs Gemini 3.8 Flash TTS: stress on loanwords, ordinals, pace. **Action:** the operator reads a 200-word test script containing numbers, dates and loanwords through all three and rates them. No public evaluation exists.
- Speaking rate (words/s) of the chosen ElevenLabs Kazakh voice. Measure it on the first 3 videos.
- Actual Kazakh WER of `gemini-3.5-transcribe` and Scribe v2 on *our* TTS audio. Synthetic speech is likely much easier than FLEURS. [Estimate] Measure on fixtures.
- YouTube audience size in Kazakhstan for 2025–2026. DataReportal's 2026 page has no YouTube figure, and Statista is paywalled.
- Kazakh vs Russian split of YouTube watch time in Kazakhstan. No 2025–2026 public study found.
- Whether any 2026 state grant or order (Ministry of Culture and Information, Ministry of Enlightenment) funds Kazakh educational online content. Not found; check goszakup.gov.kz.
- Full subscriber and view data for competitors was collected without vidIQ. A vidIQ re-run (outliers, keyword volume for kk queries) is recommended once credits are available.

## Sources
- https://www.youtube.com/@SHAKAMURO
- https://www.youtube.com/@tarihmarih
- https://www.youtube.com/@tarih.1269
- https://www.youtube.com/@e-history
- https://www.youtube.com/@Qalamhistory
- https://www.youtube.com/@DOMALAQ-777
- https://www.youtube.com/@kazvoice_channel
- https://www.youtube.com/@ANIMATIONKZ
- https://www.youtube.com/@olzhastokhabaianimation
- https://www.youtube.com/@bnkz9873
- https://www.youtube.com/@SAQKinostudiasy
- https://www.youtube.com/@NurlanQalam
- https://www.youtube.com/@Qalamgo
- https://www.youtube.com/results?search_query=қазақ+хандығы+анимация (and other kk queries, 2026-10-16)
- https://youth.kz/article/podborka-youtube-kanalov-ob-istorii-kazahstana-i-mira-e1bwURXWqq6PmLt4u92c
- https://liter.kz/kazakhoiazychnyi-kontent-pogruzhaemsia-v-mir-podkastov-nauki-i-stendapa-1743664448/
- https://forbes.kz/articles/balalara_arnalan_beynekontentt_kmder_jasaydyi
- https://forbes.kz/articles/350mln-tenge-vydelili-nasozdanie-multfilmov-nakazahskom-yazyke
- https://tengrinews.kz/article/kompleksov-mense-iuzerov-bolse-rastet-kazaxoiazycnyi-723/
- https://tengrinews.kz/kazakhstan_news/vospityivaet-shkola-tiktok-deputat-predlojil-ogranichit-601794/
- https://datareportal.com/reports/digital-2026-kazakhstan
- https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2026.1819486/full
- https://stat.gov.kz/ru/national/2021/
- https://rep.vsu.by/bitstream/123456789/46586/1/49-53.pdf
- https://www.lada.kz/kazakhstan-news/140949-iazykovoi-vybor-roditeli-delaiut-stavku-na-kazakhskii-iazyk-v-nachalnoi-shkole.html
- https://bes.media/amp/90-pervoklassnikov-v-almati-vibirayut-shkoli-s-kazahskim-yazikom-obucheniya-dosaev-5169c5/
- https://elevenlabs.io/docs/overview/models
- https://elevenlabs.io/docs/help-center/other/what-languages-do-you-support.md
- https://elevenlabs.io/docs/best-practices/prompting/normalization
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- https://elevenlabs.io/docs/overview/capabilities/forced-alignment
- https://elevenlabs.io/docs/overview/capabilities/speech-to-text
- https://elevenlabs.io/speech-to-text/kazakh
- https://www.vktr.com/ai-platforms/elevenlabs-launches-eleven-v4-and-v4-turbo/
- https://framia.converge.ai/ru/models/eleven-v3
- https://www.mdpi.com/2078-2489/16/10/879
- https://ai.google.dev/gemini-api/docs/speech-generation
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-transcribe
- https://huggingface.co/shyngys879/kazakh-whisper-large-v3-turbo
- https://huggingface.co/InflexionLab/sybyrla/blob/main/README.md
- https://huggingface.co/BuzzASR/kazakh
- https://github.com/google/fonts/tree/main/ofl
- https://fonts.googleapis.com/css2?family=Inter:wght@800
- https://metacpan.org/dist/DateTime-Locale/view/lib/DateTime/Locale/kk.pod
- https://web.do.metacpan.org/pod/Lingua::KAZ::Word2Num
- https://hronika.kz/?p=18619
- https://astanatimes.com/2021/02/kazakhstan-presents-new-latin-alphabet-plans-gradual-transition-through-2031/
