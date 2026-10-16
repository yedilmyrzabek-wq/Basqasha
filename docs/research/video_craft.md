# Video craft for ~4-minute animated explainers: research and rules

> Owner: video-craft-researcher · Date: 2026-10-16 · Scope: brief §5 (format), §4.4 (metrics), §6.5–6.6 (storyboard, metadata).
> Labels: **[Fact — URL]** is sourced. **[Estimate]** is reasoning or an unverified figure. Local code facts cite the repo path.
> Caveat: public, rigorous data on explainer pacing is scarce. Most "benchmarks" online come from vendor blogs. Where a number only exists in such blogs, it is labeled **[Estimate]** and the blog is named, even if the blog itself presents it as fact.

---

## TL;DR

- **The biggest risk is word count versus duration.** Professionally read Kazakh in the KazakhTTS2 corpus runs about **93–115 words/min, mean ≈107** (calculated from the corpus table). At that rate, 500–550 words come out to roughly **4:40–5:30, not 4:00**. Calibrate the operator's ElevenLabs voice in words per minute and derive the word budget from it. Until that is done, use **≈440 words (range 420–480) for 4:00**. [Estimate derived from Fact — https://arxiv.org/html/2201.05771]
- **The 30-second mark is YouTube's own hook metric.** Studio's "Intro" is the share of viewers still watching after 30 s. YouTube's advice is to make the title and thumbnail match the video and to experiment with the first 30 s. [Fact — https://support.google.com/youtube/answer/9314415?hl=en] Our hook therefore has to land the promise within 15 s and pay off a first fact within 30 s.
- **Pacing.** The brief's "40–50 shots, new action every 4–6 s" is consistent with a 4-min video (4.8–6.0 s per shot). The reference `Popcorn.tsx` gets its liveliness from intra-scene events (pose change, counter, label, punch-in, coins) every ~1–2 s, not from fast cuts. Encode both a scene-length rule and a "visual event" rule. [Fact — reference/costco_project_example/src/pop/Popcorn.tsx]
- **Retention benchmarks are soft.** The widely quoted "average video keeps 23.7%; 55% leave in the first minute" figures come from the Retention Rabbit 2025 report, and I could only find them through secondary blogs. [Estimate — https://async.com/blog/audience-retention-challenges/] The brief's targets (30-s retention ≥65–70%, AVP ≥35–40%) are reasonable for a 4-min video. A good 4-min explainer should aim for AVP ≥50%. [Estimate]
- **Audio.** YouTube turns loud content down to about −14 LUFS. [Fact — https://en.wikipedia.org/wiki/Audio_normalization] Several sources say it does not turn quiet content up, but I found no official confirmation. Master the **final mix to −14 LUFS integrated, ≤ −1 dBTP**, and keep the music bed **15–20 dB under the voice**. [Estimate — https://sounddesign.irpr.agency/guides/how-to-mix-audio-for-youtube/] The brief's "−16 LUFS" is fine for the voice stem but not for the final master.
- **Test & Compare (now "A/B test titles & thumbnails").** Up to 3 variants per video, winner chosen by **watch time share**, not CTR. Tests run up to 2 weeks, desktop Studio only. Not available for Shorts or for **made-for-kids** videos. [Fact — https://support.google.com/youtube/answer/16391400?hl=en]
- **Shorts.** Vertical videos up to **3 min** count as Shorts (uploads since 15 Oct 2024). Any Short **over 1 min with any active copyright claim is blocked globally**. [Fact — https://support.google.com/youtube/answer/15424877?hl=en] Keep our Shorts at **≤ 59 s**, which also matches the brief.
- **Metadata limits matter for Kazakh.** The API description limit is **5000 bytes, not characters**. Kazakh Cyrillic takes 2 bytes per character in UTF-8, so plan for **≤ 2400 characters**. Chapters need 00:00, at least 3 timestamps, each chapter ≥ 10 s, in ascending order. [Fact — https://developers.google.com/youtube/v3/docs/videos ; https://support.google.com/youtube/answer/9884579?hl=en]

---

## 1. What our engine can already do (baseline for all rules)

Measured from `reference/costco_project_example/src/pop/Popcorn.tsx` (26.6-s demo). [Fact — local file]

| Element | What the code does | Implication for rules |
|---|---|---|
| Scenes | 5 scenes in 26.6 s, 2.8–7.2 s long, avg ≈ 5.3 s | Our target scene length is already proven in the engine |
| Background | Ken Burns zoom 1.00 → 1.08 per scene, plus spring "punch-in" of +5% at given frames, decaying over 40 frames | Punch-ins are the cheap "pattern interrupt" and should be tied to keywords |
| Mascot | Pose schedule per frame, squash-and-stretch on change, breathing sine, flip, shadow | A pose change is a visual event that costs nothing |
| Label | Paper card, pop-in, rotate −2°, width = `len × size × 0.6 + 60` px | At size 80 a label overflows 1920 px past ≈ 30 characters. Kazakh words are long, so a character limit is needed on top of the word limit |
| Counter | Animated number (e.g. 0 → 48%) over ~70 frames | One hero number per beat |
| Captions | One phrase box at the bottom, 50 px, max-width 1500, fade+rise in 6 frames; keyword matched by `startsWith`, so suffixed Kazakh forms match (мұз → мұзды) | Keyword must be the **stem** and should match only one word |
| Caption phrases | 8 phrases, 1.7–6.3 s each, 4–11 English words | Phrase-level captions work at ≈ 2–6 s each |
| SFX | 18 one-shots in 26.6 s (≈ 40/min): whoosh at every cut, pop on every label, coin/ding/kaching on numbers; gain 0.5–0.8 | Too dense for 4 min. Needs a per-minute cap (see rules) |
| Music | `pad.wav` at gain 0.35 (≈ −9 dB relative to the file's own level) | Gain alone is not a mix spec. Use loudness targets |
| Progress bar | 8 px red bar at the bottom | Captions must sit above it |

---

## 2. Reference channels and the first 15 seconds

**Verification limit:** I could not fetch transcripts of specific Kurzgesagt, Wendover, Polymatter and similar videos in this session (transcript sites returned 403, and ted.com transcript pages showed only descriptions). The patterns below are therefore **[Estimate]**: a synthesis of general familiarity with these channels plus the generic hook guidance cited. Before encoding them as channel-specific claims, verify them with 3–5 transcripts per channel (see Open questions).

| Channel family | Typical opening move (pattern) | Our adaptable version |
|---|---|---|
| Kurzgesagt | Big-scale "imagine…" or second-person scenario, then a reveal that flips the premise; calm narrator, one surprising image per sentence | «Елестетіп көріңізші: …» + a scale/number reveal within 5 s [Estimate] |
| TED-Ed (narrative/riddle lessons) | Drops the viewer into a situation in the first sentence ("You and nine others have been captured…"), then poses the question | Start inside the story: a person, a place, a year, a problem. [Fact for the example line — https://www.ted.com/talks/alex_gendler_can_you_solve_the_prisoner_hat_riddle/transcript (lesson description)] |
| Wendover / Half as Interesting | A concrete, oddly specific fact or paradox, then "but why?" and quick context; HAI adds a joke beat within ~10 s | Paradox hook: «X — бірақ Y. Неге?» [Estimate] |
| Polymatter / Economics Explained / Business Casual | A thesis-level claim or a counter-intuitive number up front ("this country is…"), then stakes | Claim + number: «1880 жылы бір қыста малдың жартысы қырылды.» [Estimate] |
| The Infographics Show | Second-person, high-stakes scenario ("What if you…"), fast to the premise | «Сіз 1880 жылғы қыстаудасыз…» [Estimate] |
| Stickman / whiteboard channels | Visual gag + question on screen in the first 2–3 s; the character reacts (shock/shrug) | Mascot pose `shock` / `think` on frame 0 + question label [Estimate] |

Common denominators that external sources also back:
- No greeting, logo or "in this video" before the first hook. Lead with something visual or intriguing. [Estimate — vendor advice, https://www.collabpals.com/tools/youtube-intro-script-generator ; https://uppbeat.io/blog/youtube-growth/youtube-analytics/youtube-audience-retention] PROMPTS.md already forbids "In this video". [Fact — reference/costco_project_example/PROMPTS.md]
- The title/thumbnail promise must be confirmed early. YouTube's own fix for a weak "Intro" metric is to align the title and thumbnail with the content and to rework the first 30 s. [Fact — https://support.google.com/youtube/answer/9314415?hl=en] The leaked MrBeast production guide (2022, authenticity unconfirmed) likewise treats the first minute as the main drop-off zone and says the opening must show the thumbnail promise is real. [Estimate — secondary reporting: https://www.netinfluencer.com/mrbeast-productions-leaked-internal-document-rosanna-pansino/ ; https://www.creatorhandbook.net/leaked-document-allegedly-reveals-mrbeasts-secrets-to-youtube-success-the-key-takeaways/]
- A workable 30-s structure: first ~10 s prove the promise with a concrete example, next ~10 s say why it matters, last ~10 s preview. Going past 30 s before the first payoff is where viewers leave. [Estimate — https://outlierkit.com/resources/youtube-hooks-and-retention/]
- Typical recommended hook length is 5–15 s. [Estimate — https://www.getresponse.com/blog/youtube-hacks ; https://youtubeconsultant.com/blog/youtube-shorts-to-longform-funnel/]

**Hook pattern library** (each must be adapted to the topic, never copied from the source video, per brief §3.1):
1. **Shocking number**: one concrete figure with a unit and a year. «Бір ғана қыста — малдың жартысы.» [Estimate]
2. **Paradox**: «Олар отынсыз жылынды. Бірақ қалай?» [Estimate]
3. **You-are-there**: second person, place and year. [Estimate]
4. **Myth-flip**: a common belief, then «шын мәнінде…». [Estimate]
5. **Mystery object**: an unfamiliar thing on screen (тезек, қыстау), asking "what is it and why did it save lives?" [Estimate]

---

## 3. Pacing: shot length, visual events, re-hooks

- **Film reference points:** Hollywood average shot length has reportedly fallen to ~3 s. [Estimate — secondhand CinemaStix figure via https://nostr.at] The shortest director ASL in Stephen Follows' dataset is 2.4 s. [Fact — https://stephenfollows.com/many-shots-average-movie/] Animated explainers sit in a similar 2.5–6 s band. [Estimate]
- **Kurzgesagt** reportedly illustrates ~200 panels per video with 2–3 illustrators over 8–12 weeks. [Estimate — mirrored team write-up summarized at https://www.lingq.com/en/learn-english-online/courses/689474/how-to-make-a-kurzgesagt-video-in-120-4887128/ ; official page https://kurzgesagt.org/youtube/ confirms the process but not the count] For a typical 8–12-min video that is one new panel every ~2.5–3.5 s. [Estimate]
- **Our format:** 40–50 scenes in 240 s is 4.8–6.0 s per scene (brief §5.1). To match the visual density of top channels, each scene needs **2–3 intra-scene events** (pose change, label pop, counter, punch-in, arrow, coin). That gives a visual event every ≈ 2–2.5 s. Popcorn scene C already does this: background, pose change at 1.75 s, counter at ~1 s, coins at 2.3–3.5 s, footnote at 4 s. [Fact — Popcorn.tsx; interval reading is Estimate]
- **Re-hooks / pattern interrupts:** no official interval exists. YouTube publishes no fixed interval, and retention graphs do not prove what caused a change. [Estimate — glossary note https://www.creatoressentials.com/glossary/pattern-interrupt/] Blogs suggest an attention reset every 60–90 s in long-form [Estimate — https://outlierkit.com/resources/youtube-script-writing/], and a first deliberate interrupt around 25–35 s [Estimate — https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8]. The leaked MrBeast guide places extra-strong moments at ~3 and ~6 min in long videos. [Estimate — secondary reporting, see §2] For a 4-min video, re-hook every **45–60 s** (3–4 re-hooks). [Estimate]
- **What counts as a re-hook** in our engine: a new open question in the script + a punch-in + a background change + an SFX "ding/whoosh" + a mascot pose change, all within the same 1 s. [Estimate]
- **YouTube retention diagnostics** to read after publishing: "top moments" (move them earlier next time), "spikes" (rewatched or shared), "dips" (skipped or abandoned). [Fact — https://support.google.com/youtube/answer/9314415?hl=en]

---

## 4. Script structures, speaking rate, sentence length

- **Structure:** the PROMPTS.md template already encodes hook → question → 3–4 beats (one number + one visual each) → twist/reframe → catch → payoff calling back to the hook → end line. [Fact — reference/costco_project_example/PROMPTS.md] That matches common retention advice: open loops paid off later, re-hooks between sections. [Estimate — https://outlierkit.com/resources/youtube-hooks-and-retention/]
- **Causality between beats:** connect beats with "but / therefore", not "and then". This is the South Park / Tony Zhou storytelling rule. [Fact — https://nofilmschool.com/2015/04/tony-zhou-storytelling-video-essay-f-fake-therefore-but-and-then] In Kazakh: «бірақ», «сондықтан», «соның салдарынан», not «содан кейін». [Estimate]
- **Open loops:** use 1–2 per video, and always pay them off. Too many erode trust. [Estimate — https://outlierkit.com/resources/youtube-script-writing/]
- **Shorter is more engaging in educational video:** the edX study of 6.9M sessions found that shorter videos and Khan-style drawings are more engaging, and that speaking fast with enthusiasm helps. [Fact (abstract level) — https://pg.ucsd.edu/publications/edX-MOOC-video-production-and-engagement_LAS-2014.txt ; https://blogs.ubc.ca/videolearninghub/?p=569] The often-quoted "≈6 min median engagement" figure comes from a 2013 edX blog post, cited via secondary summaries. [Estimate — https://multimedia.ucsd.edu/best-practices/video-length.html] Our ~4 min sits safely below it.
- **Words per minute (English):** narration norms are 150–160 wpm (widely repeated, primary source unclear) [Estimate — https://www.mentalfloss.com/language/how-many-words-per-minute-do-people-speak]. PROMPTS.md assumed 150 wpm for English. [Fact — PROMPTS.md]
- **Words per minute (Kazakh), calculated:** KazakhTTS2 (professional read speech, 5 speakers, 271.7 h) reports per-speaker duration and token counts. [Fact — https://arxiv.org/html/2201.05771]
  - F1 14.1 tok / 7.5 s ≈ **113 wpm**; F2 ≈ **115**; F3 ≈ **114**; M1 news ≈ **93**; M1 wiki ≈ **94**; M1 book ≈ **107**; M2 ≈ **113**; whole corpus 1.74M / 271.7 h ≈ **107 wpm**. [Estimate — arithmetic on the Fact table; assumes "tokens" ≈ words, and segment durations include some leading/trailing silence]
  - Kazakh conversational speech runs 4.6–5.7 syllables/s depending on region. [Fact — https://nomadit.co.uk/conference/cess2023/paper/74409] With long agglutinative words, that gives far fewer words per minute than English. [Estimate]
  - **Consequence:** 500–550 words ÷ 107 wpm ≈ 4:40–5:08. A 4:00 video needs ≈ 430 words at 107 wpm, or 500–550 words only if the voice runs at 125–138 wpm (≈ 20–30% faster than corpus narration). [Estimate]
- **Sentence length:** KazakhTTS2 news sentences average 12–14 words; book narration averages 9.4 words per segment. [Fact — https://arxiv.org/html/2201.05771] General scripting advice caps a crisp sentence at ~20 English words. [Estimate — https://elearningindustry.com/writing-awesome-animation-scripts] For spoken Kazakh explainers, target **6–12 words per sentence, hard max 16**. [Estimate]
- **Numbers spoken as words** in the TTS text (ElevenLabs reads digits unreliably). This is already a project convention. [Fact — PROMPTS.md §4]

---

## 5. On-screen text and captions

- **Reference limits for Cyrillic subtitles (Netflix Russian guide):** 42 characters per line, max 2 lines, reading speed ≤ 17 characters/s for adult programs (13 for children). [Fact — https://partnerhelp.netflixstudios.com/hc/en-us/articles/215346638-Russian-Timed-Text-Style-Guide] The BBC targets 160–180 wpm and 2 lines. [Estimate — secondary summary https://clevercast.com/bbc-subtitling-guidelines]
- **Our reading load:** at ~107 wpm and ~7–8 characters per Kazakh word including the space, captions run ≈ 13–15 characters/s, below the 17 cps ceiling. [Estimate] Phrase captions are therefore readable if each phrase stays on screen for its spoken duration.
- **Labels:** the brief's ≤ 5 words is right in spirit and matches PROMPTS.md "max 5 words on screen". [Fact — PROMPTS.md] The code imposes a stricter **character** limit: label width ≈ `chars × size × 0.6 + 60` px. [Fact — Popcorn.tsx]
- **Keyword highlight:** one keyword per phrase, matched by prefix. Use the Kazakh **stem** so suffixed forms still match. [Fact — Popcorn.tsx uses `startsWith`] Prefer the number or the noun that carries the beat. [Estimate]
- **Closed captions:** upload the approved script as an SRT/closed-caption track (generated from words.json), in addition to burned-in captions. I could not confirm whether YouTube auto-captions support Kazakh. [Estimate — open question]

---

## 6. Sound design

- **Loudness target:** YouTube's reference level is −14 LUFS; louder programmes get turned down (−10 LUFS is lowered by 4 dB). [Fact — https://en.wikipedia.org/wiki/Audio_normalization] Several sources say YouTube does **not** raise quiet content, so a −16 LUFS master would play ~2 dB quieter than peers, but no official YouTube document confirms this. [Estimate — https://youlean.co/?p=30813] True peak ≤ −1 dBTP to survive re-encoding. [Estimate — https://sounddesign.irpr.agency/guides/how-to-mix-audio-for-youtube/]
- **Music under voice:** duck the music 15–20 dB below the voice during speech and raise it only in gaps. [Estimate — single industry guide, https://sounddesign.irpr.agency/guides/how-to-mix-audio-for-youtube/] Premiere's Essential Sound auto-ducking reportedly defaults to ~18 dB. [Estimate — user forum, https://community.adobe.com/bug-reports-733/ducking-doesn-t-work-when-audio-track-keyframes-is-selected-906025]
- **SFX density:** I found no published standard. Popcorn uses ≈ 40 SFX/min, which suits a 26-s demo but would fatigue viewers over 4 min. [Fact for count — Popcorn.tsx; judgement is Estimate] Recommended: one transition whoosh per scene change plus 1 accent per scene, giving **≈ 12–20 SFX/min**, never two within 0.25 s, and SFX peaks ~6–10 dB below voice peaks. [Estimate]
- **Silence:** a 0.4–0.8 s beat of near-silence (music dipped ≥ 10 dB further, no SFX) right before the twist or reveal makes it land. Use it at most 2–3 times per video. [Estimate]
- **Licensing:** music and SFX only from licensed or royalty-free libraries (brief §3.2). In Shorts, any claim on a >1-min Short blocks it globally, which is one more reason to stay ≤ 59 s. [Fact — https://support.google.com/youtube/answer/15424877?hl=en]

---

## 7. Titles and thumbnails

- **Hard limits:** title ≤ 100 characters, no `<` or `>`; description ≤ **5000 bytes**; tags ≤ 500 characters total. [Fact — https://developers.google.com/youtube/v3/docs/videos] Cyrillic letters are 2 bytes in UTF-8. [Fact — https://www.rfc-editor.org/rfc/rfc3629]
- **Visible title length:** truncation is reported at ~60 characters in desktop search, ~50 on the mobile home feed and ~40 in Shorts. These are vendor measurements and vary by device. [Estimate — https://creaticalc.com/blog/youtube-title-mobile-feed ; https://howmanywords.app/blog/youtube-character-limits] The brief's ≤ 60 characters is right. Front-load the hook into the first ~40 characters. [Estimate]
- **Title patterns that work for explainers:** curiosity gap + specific number; "how/why X really…"; a question with a stake. [Fact as our existing convention — PROMPTS.md §9; effectiveness is Estimate] Must match the first 15 s (see §2).
- **Thumbnail specs:** 16:9; JPG/PNG; recommended 3840×2160 (min width 640); upload limit 2 MB on mobile, 50 MB on desktop. Custom thumbnails need a verified account. For Shorts, custom thumbnails can be added only in desktop Studio, and a 16:9 thumbnail on a vertical video gets replaced by an auto 4:5 frame on home, explore and subscriptions. [Fact — https://support.google.com/youtube/answer/72431?hl=en]
- **Thumbnail text:** analyses repeated by vidIQ claim that ≤ 3 words outperform 4+ [Estimate — https://vidiq.com/blog/post/youtube-custom-thumbnails-ctr/]. Another study finds 3–5 high-contrast words help in search and dense text hurts in browse/suggested. [Estimate — https://www.tubeanalytics.net/resources/research/thumbnail-ctr-patterns-study-2026] PROMPTS.md says 2–4 words, added in code rather than generated by the model. [Fact — PROMPTS.md §8]
- **A/B testing (formerly "Test & Compare"):** up to 3 titles and/or thumbnails; the winner has the highest **watch time** (not CTR); a test takes a few days up to 2 weeks; desktop Studio only; advanced features must be enabled. Not available for Shorts, scheduled lives or premieres before they end, or videos that are **made for kids**, mature or private. Editing the title or thumbnail mid-test stops it. A thumbnail below 720p downgrades all variants to 480p. Use visibly different variants. [Fact — https://support.google.com/youtube/answer/16391400?hl=en] Title testing began as a limited experiment in 2025. [Fact — https://www.socialsamosa.com/news-2/youtube-thumbnail-testing-tool-more-creators-9498934 (Sep 2025)]
- **End screens:** last 5–20 s, video ≥ 25 s, ≤ 4 elements; unavailable on made-for-kids videos. [Fact — https://support.google.com/youtube/answer/6388789?hl=en]
- **Chapters:** first timestamp 00:00, at least 3 timestamps, each chapter ≥ 10 s, ascending order. [Fact — https://support.google.com/youtube/answer/9884579?hl=en]

---

## 8. Long-form → Shorts

- **Length and classification:** a square or vertical video up to 3 min uploaded on or after 15 Oct 2024 is a Short. A Short > 1 min with an active claim of any type is blocked globally, without a channel penalty. [Fact — https://support.google.com/youtube/answer/15424877?hl=en]
- **View counting:** since 31 Mar 2025, Shorts views count every start and replay. The old metric, now called "engaged views", still drives YPP eligibility and earnings. [Fact — https://techcrunch.com/?p=2986224 ; https://www.socialsamosa.com/news-2/youtube-shorts-now-count-every-play-replay-view-8895256] Loops therefore inflate public views but not engaged views. [Estimate]
- **Swipe metric:** Studio shows "viewed vs. swiped away". Community rules of thumb aim for ≥ 70–80% viewed; there is no official threshold. [Estimate — https://subscribr.ai/youtube-strategy/youtube-shorts-analytics-metrics-growth ; https://www.bytecap.io/research/youtube-shorts-retention-benchmarks]
- **Length sweet spot:** vendor analyses cluster around 15–60 s, with ~30 s as the most common recommendation. No authoritative study exists. [Estimate — https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention ; https://quso.ai/research/youtube-shorts-length]
- **Linking:** Shorts have a "Related video" field that puts a tap-through link to a long-form video under the Short. [Fact — https://searchengineland.com/youtube-enables-linking-shorts-long-form-videos-430655 (2023)] YouTube's "Edit into a Short" reportedly clips up to 60 s from your own long video and links back to it. [Estimate — https://www.tubefilter.com/?p=168674]
- **Hook in Shorts:** the first 1–3 s decide the swipe, and an on-screen hook caption in the first ~2 s is common practice. [Estimate — https://joinbrands.com/blog/youtube-shorts-best-practices/] PROMPTS.md already plans "a big hook caption at the top for the first 2 s", ≤ 6 words. [Fact — PROMPTS.md §7.4, §9]
- **Loops:** Shorts autoplay on loop. An ending that flows back into the first line encourages replays. [Estimate — https://theleap.co/how-to-make-youtube-shorts-viral]
- **What to cut:** a self-contained beat (one question, one number, one payoff), usually the hook+beat 1, or the twist. Never cut mid-sentence. [Estimate]

---

## 9. Retention benchmarks

| Metric | Value | Status |
|---|---|---|
| YouTube "Intro" metric | % still watching at 0:30; compared against "typical retention" of your last 10 videos of similar length | [Fact — https://support.google.com/youtube/answer/9314415?hl=en] |
| "Above typical intros" bucket | videos with ≥ 50% watching after 0:30 | [Estimate — reported for a newer help page, https://support.google.com/youtube/answer/12942217 ; not seen on the page I fetched] |
| Average retention, all videos | ≈ 23.7%; 55% leave in first 60 s; 5–10-min videos ≈ 31.5% | [Estimate — Retention Rabbit 2025 via secondary sources, https://async.com/blog/audience-retention-challenges/ ; https://humbleandbrag.com/blog/youtube-audience-retention-benchmarks] |
| Educational how-to average | ≈ 42% | [Estimate — unsourced glossary, https://www.kontentino.com/social-media-urban-dictionary/retention-rate/] |
| Animated < 5 min | 50–70% AVP "target" | [Estimate — vendor blogs, https://longstories.ai/blog/retention-benchmarks-animated-youtube-videos] |
| Early drop | 20–40% lost in first 15–30 s "typical" | [Estimate — https://ytshark.com/?p=271] |

Reading: the brief's thresholds (30-s ≥ 65–70%, AVP ≥ 35–40%, CTR ≥ 4–5%) are plausible minimums for a 4-min video. "Good" is AVP ≥ 50% and 30-s ≥ 70%. Use the channel's own "typical retention" after ~5 uploads as the real baseline. [Estimate]

---

## Rules for our system

Paste-ready. Values are defaults for `/prompts` and Settings; anything marked (cal) must be recalibrated after the first 3 videos.

**Script (step 4)**
1. **Word budget from measured speaking rate:** `target_words = round(wpm_voice × target_seconds / 60)`. Default `wpm_voice = 110` (cal) → 4:00 = **440 words**, acceptable range ±8% (405–475). After each voice upload, update `wpm_voice = words / (mp3_seconds / 60)` as a rolling mean. The UI duration estimate must use this value, not a fixed 130.
2. **Hook (0–15 s, ≤ 28 words at 110 wpm; scale with `wpm_voice`):** sentence 1 is a concrete fact, number, paradox or scene with a place or year (≤ 12 words). Sentence 2 is the question the title promises. Sentence 3 is the stake + open loop ("by the end we'll see why…"). Forbidden in the first 15 s: greetings, channel name, «бұл видеода», «сәлеметсіздер», definitions, sponsor.
3. **First payoff by 0:30:** one verified fact that partly answers the hook question must be spoken before 30 s.
4. **Beat template for 240 s** (percent of word budget; words for 440 / 520 budgets):

| # | Beat | Time | % | 440 w | 520 w | Must contain |
|---|---|---|---|---|---|---|
| 1 | Hook | 0–15 s | 6% | 26 | 31 | fact/paradox + question + open loop |
| 2 | Context & promise | 15–35 s | 8% | 35 | 42 | why it matters to a Kazakh viewer; first payoff |
| 3 | Beat A | 35–80 s | 19% | 84 | 99 | 1 number + 1 hero visual; ends on a question (re-hook 1 ≈ 0:50–1:00) |
| 4 | Beat B | 80–125 s | 19% | 84 | 99 | "бірақ / сондықтан" link; 1 number; re-hook 2 ≈ 1:50 |
| 5 | Beat C | 125–170 s | 19.5% | 86 | 101 | escalation; 1 number; re-hook 3 ≈ 2:40 |
| 6 | Twist / reframe | 170–200 s | 12.5% | 55 | 65 | counter-intuitive turn; 0.5 s silence before it |
| 7 | Payoff + callback | 200–225 s | 10% | 44 | 52 | answers the hook in its own words; closes every open loop |
| 8 | Outro / next video | 225–240 s | 6% | 26 | 31 | one sentence to the next video (end screen lives here, 5–20 s) |

5. **Re-hook every 45–60 s** (3 per 4-min video): a new explicit question or "but" turn in the script, aligned with a background change + punch-in + SFX accent.
6. **Sentences:** mean 6–12 words, hard max 16 words; ≥ 70% of beat transitions start with a causal connector («бірақ», «сондықтан», «сол себепті»), not «содан кейін». Max 2 open loops, each paid off. Numbers written as words for TTS. Every on-screen number must equal the spoken one.

**Storyboard (step 6)**
7. **Scene count derived from duration:** `scenes = clamp(round(voice_seconds / 5.2), 40, 55)`. Scene length min **2.5 s**, target **4.5–5.5 s**, max **7.5 s** (max **9 s** only if the scene has ≥ 3 events). Scenes break on sentence or clause boundaries from words.json.
8. **Visual-event density:** every scene has ≥ 2 timed events (pose change, label, counter, arrow, coin, punch-in, stamp). Gap between consecutive visual events ≤ 3.0 s across the whole video; first event at ≤ 0.6 s after the scene start.
9. **Hook visuals (0–15 s):** ≥ 4 scenes (each ≤ 4 s); scene 1 shows the mascot in `shock`/`think` and the hook number or question as a Label within 0.5 s; no title card, no logo.
10. **Backgrounds:** 12–15 unique, each used 2–4 times; consecutive scenes must not reuse the same background with the same zoom/focus; a reused background must change `focus` by ≥ 0.15 or zoom range by ≥ 0.05. Ken Burns 1.00 → 1.06–1.10; punch-in +5% on the scene's keyword (`punch_at_word`), max 1 per scene.
11. **Labels:** ≤ 5 words **and** ≤ 24 characters at size ≥ 64 px (auto-shrink to ≥ 48 px, else split or reject); max 2 labels visible at once; ≤ 1 label per 2 s.
12. **Captions:** one phrase per caption, 2–7 words, ≤ 42 characters per line, ≤ 2 lines, on screen 1.2–6.0 s, reading speed ≤ 17 characters/s (else split the phrase). Exactly one `caption_keyword` per phrase, given as a stem (≥ 3 letters) that prefix-matches **one** word in the phrase (highlight the first match only). Captions sit above the progress bar and never overlap the mascot's face or a Label (contact-sheet check).

**Audio (steps 5, 9)**
13. **Loudness:** voice stem normalized to −16 LUFS (as in the brief); **final mix mastered to −14 LUFS integrated (±1), true peak ≤ −1.0 dBTP**. Music bed −18 dB relative to the voice during speech (allowed −15…−20 dB), +6 dB in pauses > 0.8 s, with 150–300 ms ramps.
14. **SFX:** 12–20 per minute (hard cap 24/min, and ≤ 1 per 0.25 s); whoosh at each background change; pop at each Label; coin/ding/kaching only on numbers; SFX peaks 6–10 dB under voice peaks. Total silence (music −10 dB extra, no SFX) for 0.4–0.8 s before the twist, ≤ 3 times per video.

**Metadata (step 10)**
15. **Titles:** 5 variants, each ≤ 60 characters (aim 40–55), core hook in the first 40 characters; ≥ 2 variants with a specific number; no clickbait the first 15 s does not deliver; no `<` `>`; ≤ 1 emoji-free ALL-CAPS word.
16. **Description:** ≤ 2400 characters (5000-byte API limit with Cyrillic); first 150 characters restate the hook; chapters at 00:00 + ≥ 3 more, each ≥ 10 s, ascending (map to the beat template); source list; ≤ 3 hashtags.
17. **Thumbnail:** 3840×2160 (min 1280×720) JPG/PNG, < 2 MB for mobile upload; text added in code (never generated), **≤ 3 words, ≤ 18 characters**, must stay readable at 320×180; one focal object + mascot face with a strong emotion occupying ≥ 25% of the height; text never duplicates the title verbatim. Produce **3 visibly different variants** for A/B testing (title+thumbnail), run tests only on non-made-for-kids long-form videos, and never edit metadata during a test.

**Shorts (step 9, P5)**
18. **Shorts:** 1080×1920, **20–58 s** (never > 59 s); built from 1 self-contained beat (hook/twist + one number + payoff), cut on sentence boundaries only; on-screen hook caption ≤ 6 words in the top third for 0–2 s; first frame is the strongest visual, not a title card; the last line or visual flows back into the first for a loop; captions larger (≥ 64 px) and kept out of the bottom ~20% and right ~15% of the frame (UI overlay zones, estimate); set "Related video" to the source long-form; 2–3 Shorts per long video.

**Evaluation**
19. **Quality gates after publishing (per video, at 7 days):** 30-s retention ≥ 65% (good ≥ 70%), AVP ≥ 40% (good ≥ 50%), CTR ≥ 4%. If 30-s < 60% on 2 consecutive videos, regenerate hook patterns first. If AVP drops mainly mid-video (a slow slide, not a cliff), shorten scenes and add re-hooks. Store the Studio "dips/spikes" notes per video to feed back into prompts.

---

## Contradictions with PROJECT_BRIEF

1. **500–550 Kazakh words ≠ ~4:00.** Measured read-Kazakh narration (KazakhTTS2) averages ≈ 107 wpm (93–115). 500–550 words would come out at ≈ 4:40–5:10. Either set the budget to ≈ 440 words for 4:00 or accept ~4:45 (and ~50–55 scenes). Fix: make the word budget derive from the measured voice wpm (Rule 1). [Estimate from Fact data]
2. **"Normalization −16 LUFS" (§6.2)** is fine for the voice stem. If it is applied to the final master, the video will likely play ~2 dB quieter than competitors on YouTube (the "no boost" behavior is not officially documented). Master the final to −14 LUFS / −1 dBTP (Rule 13). [Estimate]
3. **"40–50 shots" is tied to 4:00.** If duration drifts (see 1), the fixed count breaks the 4–6 s rhythm. Derive the count from the audio length (Rule 7). [Estimate]
4. **"Labels ≤ 5 words"** is insufficient for Kazakh. The engine's label width scales with characters, so add ≤ 24 characters (Rule 11). [Fact — Popcorn.tsx; threshold Estimate]
5. **Not a contradiction, but a hidden dependency:** A/B testing and end screens are unavailable on **made-for-kids** videos. A mascot-led animated channel may be pushed toward an MFK classification. The audience setting must be decided deliberately (see Open questions). [Fact — https://support.google.com/youtube/answer/16391400?hl=en ; https://support.google.com/youtube/answer/6388789?hl=en]

---

## Open questions

1. **Real wpm of the chosen ElevenLabs Kazakh voice:** measure on the pilot (words ÷ minutes), and check whether ElevenLabs' speed setting can lift it to ~125 wpm without hurting naturalness. Owner: operator + `kazakh_market.md`.
2. **Channel-specific hook verification:** pull 3–5 transcripts each from Kurzgesagt, TED-Ed, Wendover/HAI, Polymatter, Economics Explained and The Infographics Show (e.g., via vidIQ transcript tool or yt-dlp subtitles), and measure the first 15 s (words, hook type) and shot length (scene-detect on downloaded video, for analysis only). Transcript sites were blocked in this session.
3. **Does YouTube auto-caption Kazakh?** Not confirmed. Either way, upload our own SRT.
4. **"Made for kids" status** for a mascot-led educational channel: this affects A/B tests, end screens, comments and ad types. Owner: `monetization.md`.
5. **Retention Rabbit 2025 report:** the original could not be reached (404). The benchmark numbers in §9 remain secondary.
6. **YouTube "does not boost quiet audio":** no official source found. Verify with "Stats for nerds → content loudness" on our first upload.
7. **Shorts UI safe zones:** the 20% bottom / 15% right margins are estimates. Verify on a phone with the first Short.

---

## Sources

- https://support.google.com/youtube/answer/9314415?hl=en
- https://support.google.com/youtube/answer/12942217
- https://support.google.com/youtube/answer/16391400?hl=en
- https://support.google.com/youtube/answer/15424877?hl=en
- https://support.google.com/youtube/answer/72431?hl=en
- https://support.google.com/youtube/answer/9884579?hl=en
- https://support.google.com/youtube/answer/6388789?hl=en
- https://developers.google.com/youtube/v3/docs/videos
- https://www.rfc-editor.org/rfc/rfc3629
- https://arxiv.org/html/2201.05771 (KazakhTTS2, Table 3)
- https://nomadit.co.uk/conference/cess2023/paper/74409
- https://partnerhelp.netflixstudios.com/hc/en-us/articles/215346638-Russian-Timed-Text-Style-Guide
- https://clevercast.com/bbc-subtitling-guidelines
- https://en.wikipedia.org/wiki/Audio_normalization
- https://youlean.co/?p=30813
- https://sounddesign.irpr.agency/guides/how-to-mix-audio-for-youtube/
- https://community.adobe.com/bug-reports-733/ducking-doesn-t-work-when-audio-track-keyframes-is-selected-906025
- https://kurzgesagt.org/youtube/
- https://www.lingq.com/en/learn-english-online/courses/689474/how-to-make-a-kurzgesagt-video-in-120-4887128/
- https://www.ted.com/talks/alex_gendler_can_you_solve_the_prisoner_hat_riddle/transcript
- https://pg.ucsd.edu/publications/edX-MOOC-video-production-and-engagement_LAS-2014.txt
- https://blogs.ubc.ca/videolearninghub/?p=569
- https://multimedia.ucsd.edu/best-practices/video-length.html
- https://nofilmschool.com/2015/04/tony-zhou-storytelling-video-essay-f-fake-therefore-but-and-then
- https://outlierkit.com/resources/youtube-hooks-and-retention/
- https://outlierkit.com/resources/youtube-script-writing/
- https://www.getresponse.com/blog/youtube-hacks
- https://youtubeconsultant.com/blog/youtube-shorts-to-longform-funnel/
- https://www.collabpals.com/tools/youtube-intro-script-generator
- https://uppbeat.io/blog/youtube-growth/youtube-analytics/youtube-audience-retention
- https://www.netinfluencer.com/mrbeast-productions-leaked-internal-document-rosanna-pansino/
- https://www.creatorhandbook.net/leaked-document-allegedly-reveals-mrbeasts-secrets-to-youtube-success-the-key-takeaways/
- https://stephenfollows.com/many-shots-average-movie/
- https://www.creatoressentials.com/glossary/pattern-interrupt/
- https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8
- https://async.com/blog/audience-retention-challenges/
- https://humbleandbrag.com/blog/youtube-audience-retention-benchmarks
- https://www.kontentino.com/social-media-urban-dictionary/retention-rate/
- https://longstories.ai/blog/retention-benchmarks-animated-youtube-videos
- https://ytshark.com/?p=271
- https://www.mentalfloss.com/language/how-many-words-per-minute-do-people-speak
- https://elearningindustry.com/writing-awesome-animation-scripts
- https://creaticalc.com/blog/youtube-title-mobile-feed
- https://howmanywords.app/blog/youtube-character-limits
- https://vidiq.com/blog/post/youtube-custom-thumbnails-ctr/
- https://www.tubeanalytics.net/resources/research/thumbnail-ctr-patterns-study-2026
- https://www.socialsamosa.com/news-2/youtube-thumbnail-testing-tool-more-creators-9498934
- https://techcrunch.com/?p=2986224
- https://www.socialsamosa.com/news-2/youtube-shorts-now-count-every-play-replay-view-8895256
- https://subscribr.ai/youtube-strategy/youtube-shorts-analytics-metrics-growth
- https://www.bytecap.io/research/youtube-shorts-retention-benchmarks
- https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention
- https://quso.ai/research/youtube-shorts-length
- https://searchengineland.com/youtube-enables-linking-shorts-long-form-videos-430655
- https://www.tubefilter.com/?p=168674
- https://joinbrands.com/blog/youtube-shorts-best-practices/
- https://theleap.co/how-to-make-youtube-shorts-viral
- Local: reference/costco_project_example/src/pop/Popcorn.tsx ; reference/costco_project_example/PROMPTS.md ; docs/PROJECT_BRIEF.md
