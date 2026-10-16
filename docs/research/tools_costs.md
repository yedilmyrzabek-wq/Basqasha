# Tools & costs: Gemini API, ElevenLabs, Supabase, Remotion, local tools, cost per video

> Researcher: tools-cost-researcher · Date: 2026-10-16 · Scope: PROJECT_BRIEF §4.3, §6.2, §6.8
> Legend: **[Fact — URL]** = verified on the cited page (page date given where shown); **[Estimate]** = our reasoning, not a published number.

## TL;DR

- **Gemini model line-up changed a lot.** Current stable IDs are `gemini-4-argon` (flagship, the "pro" tier), `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-nano-banana-2.1` (image), `gemini-embedding-2`, and `gemini-3.8-flash-tts`. The original "Nano Banana" (`gemini-2.5-flash-image`) was due to shut down on 2026-10-02. **[Fact — https://ai.google.dev/gemini-api/docs/models, updated 2026-10-13; https://ai.google.dev/gemini-api/docs/pricing, updated 2026-10-15]**
- **Gemini prices will double soon.** Argon goes from $2/$10 to $4/$20 per 1M tokens on **2026-12-01**. 3.8/3.6 Flash goes from $0.75/$3.75 to $1.50/$7.50 on **2027-01-01**. Flash-Lite 3.5 and the image models are not on that list. **[Fact — pricing page, 2026-10-15]**
- **Estimated cost per video: ~$1.57 now and ~$2.15 after 2027-01-01** with our default settings. Images are ~60% of the cost: 13 backgrounds at 2K plus retries is about $0.92. A "lean" setup (Flash everywhere, 1K images) costs about $0.93. **12 videos/month comes to about $19 now and $26 after Jan 2027 for Gemini**, plus the ElevenLabs subscription. **[Estimate — token model in §6]**
- **Google Search grounding (Gemini 3+)** is billed **per search query**, not per prompt. The first 5,000 queries/month are free, then $14 per 1,000. At our volume (~240 queries/month) it costs **$0**. **[Fact — https://ai.google.dev/gemini-api/docs/google-search, 2026-10-13]**
- **A real spending cap exists only in AI Studio.** Use the AI Studio "Project spend cap" (experimental, ~10 min enforcement lag). Tier 1 billing accounts also have a hard $250/month cap. Cloud Billing *alert* budgets do **not** stop spend. **[Fact — https://ai.google.dev/gemini-api/docs/billing, 2026-09-28; https://docs.cloud.google.com/billing/docs/how-to/budgets, 2026-10-13]**
- **ElevenLabs: Kazakh works only on `eleven_v3`/`eleven_v4` (and their turbo/conversational variants)**, not on `multilingual_v2` or `flash_v2_5`. **Starter costs $6/month for 30k credits (~30 min)**, which covers only ~4–6 Kazakh videos. For 12 videos/month you need **Creator, $22/month for 121k credits**. The Free plan has no commercial licence. **[Fact — https://elevenlabs.io/docs/overview/models; https://elevenlabs.io/pricing; ElevenLabs help center] + [Estimate for chars/video]**
- **Supabase Free plan:** 500 MB DB, 5 GB egress, 2 active projects, **no automatic backups**. A project **pauses after 7 days of low DB activity**, and you resume it in the dashboard. From a Windows laptop use the **Session pooler (IPv4, port 5432)**, because the direct host is IPv6-only. **[Fact — https://supabase.com/pricing; https://supabase.com/docs/guides/database/connecting-to-postgres; https://supabase.com/docs/guides/platform/free-project-pausing]**
- **Remotion is free for individuals and for companies with ≤3 employees, including commercial use.** **`claude -p` currently counts against the normal Pro subscription limits.** Since 2026, **yt-dlp needs a JS runtime** (Node ≥22 works) and may need a PO token for subtitles via the `web` client. **[Fact — Remotion LICENSE.md; support.claude.com 2026-10-07; yt-dlp wiki 2026-07-12]**

---

## 1. Gemini API (paid tier, as of 2026-10-15)

### 1.1 Text models: price per 1M tokens (Standard, paid)
Source for the whole table: **[Fact — https://ai.google.dev/gemini-api/docs/pricing, "Last updated 2026-10-15 UTC"]**. Output prices include thinking tokens ("Output price (including thinking tokens)") **[Fact — same page]**.

| Role | Model ID | Status | Input | Output | Scheduled change |
|---|---|---|---|---|---|
| Pro / flagship | `gemini-4-argon` | Stable | $2.00 | $10.00 | → $4.00 / $20.00 from **2026-12-01** |
| Pro (older) | `gemini-3.1-pro-preview` | Preview | $2.00 (≤200k) / $4.00 | $12.00 / $18.00 | — |
| Flash | `gemini-3.8-flash` | Stable | $0.75 | $3.75 | → $1.50 / $7.50 from **2027-01-01** |
| Flash (prev) | `gemini-3.6-flash` | Stable | $0.75 | $3.75 | → $1.50 / $7.50 from 2027-01-01 |
| Flash-Lite | `gemini-3.5-flash-lite` | Stable | $0.30 | $2.50 | none listed |
| Flash-Lite (cheapest) | `gemini-3.1-flash-lite` | Stable | $0.25 (audio $0.50) | $1.50 | none listed |
| Legacy | `gemini-2.5-flash` / `gemini-2.5-pro` | "limited access" | $0.30 / $1.25 | $2.50 / $10.00 | — |

- **Batch and Flex** cost about **50% of Standard**, for example 3.8 Flash at $0.375/$1.875. **Priority** costs about 1.8×. Batch turnaround is up to 24 h. **[Fact — pricing page; image-generation page]**
- **Free tier** covers 3.8 Flash, 3.6 Flash and the Flash-Lite models, but **not** Argon, any image model, or Search grounding for Gemini 3+. Free-tier data is "used to improve our products"; paid-tier data is not. **[Fact — pricing page]** → We must use the paid tier: we need image models, and our scripts should not be used for training.
- Model status per the models page: Argon, 3.8 Flash and Nano Banana 2.1 are "Stable (New)". `gemini-3-pro-preview` and `gemini-2.0-flash*` are shut down. **[Fact — https://ai.google.dev/gemini-api/docs/models, 2026-10-13]**
- **SDK note:** the current docs use `client.interactions.create(model=..., input=..., tools=[{"type":"google_search"}], response_format={...})`. **[Fact — https://ai.google.dev/gemini-api/docs/structured-output, 2026-10-13]** Structured JSON output **can be combined with Google Search / URL context** on Gemini 3+ models. This combination is still a **preview** feature. **[Fact — same page]**

### 1.2 Google Search grounding
- Gemini 3+ models get **5,000 free search queries/month** (shared across all Gemini 3+ models), then **$14 per 1,000 queries**. You are billed for *each* query the model executes; one prompt can trigger several. **[Fact — https://ai.google.dev/gemini-api/docs/google-search, 2026-10-13]**
- Gemini 2.5 models are billed per prompt: 1,500 free/day (paid tier), then $35 per 1,000. **[Fact — pricing page]**
- Our usage is ~15–25 queries per facts run × 12 videos ≈ 180–300 queries/month, which stays inside the free 5,000. **[Estimate]**
- The ToS requires displaying `search_suggestions` in some contexts. The exact obligations are in the ToS, which we did not read. **[Fact — google-search page; requirement details unverified]**

### 1.3 Embeddings
- **`gemini-embedding-2`** is listed as stable on the embeddings page. **Default dimension is 3072, configurable 128–3072**, with 768/1536/3072 recommended. Truncated dimensions are **auto-normalized**. Max input is **8,192 tokens**. It has **no `task_type` parameter**; you use text prefixes instead, e.g. `task: search result | query: …`. It supports ">100 languages", and **Kazakh is not named explicitly**. **[Fact — https://ai.google.dev/gemini-api/docs/embeddings, 2026-10-09]**
  - ⚠ The models page lists it as `gemini-embedding-2-preview` (Preview), while the pricing and embeddings pages say `gemini-embedding-2`. **[Fact — models page vs embeddings page]** → Treat the model ID as a setting and verify with `models.list()` at startup.
- Price: **$0.20 per 1M text tokens** (Batch $0.10). **[Fact — pricing page]**
- `gemini-embedding-001` still exists: 2,048-token input, has `task_type` (incl. `SEMANTIC_SIMILARITY`), and needs manual normalization below 3072 dims. **[Fact — embeddings page]**
- Kazakh quality for sentence-level similarity is **unverified**. Calibrate the threshold on 20–30 known pairs before trusting it. **[Estimate]**

### 1.4 Image generation ("Nano Banana" family)
**[Fact — pricing page 2026-10-15; models page 2026-10-13]**

| Marketing name | Model ID | Text/image input /1M | Per output image | Batch per image |
|---|---|---|---|---|
| Nano Banana 2.1 | `gemini-nano-banana-2.1` | $1.50 | 1K $0.0336 · 2K $0.0504 · 4K $0.113 | $0.0168 / $0.0252 / $0.0567 |
| Nano Banana 2 | `gemini-3.1-flash-image` | $0.50 | 0.5K $0.045 · 1K $0.067 · 2K $0.101 · 4K $0.151 | $0.022 / $0.034 / $0.050 / $0.076 |
| Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | $0.25 | 1K only $0.0336 | $0.0168 |
| Nano Banana Pro | `gemini-3-pro-image` | $2.00 | 1K/2K $0.134 · 4K $0.24 | $0.067 / $0.12 |
| Nano Banana (old) | `gemini-2.5-flash-image` | $0.30 | $0.039 | — "shut down on October 2, 2026" (pricing page) / "limited access" (models page) |

- Output tokens per Nano Banana 2.1 image: **1K = 1,120, 2K = 1,680, 4K = 3,780**. **[Fact — pricing page]**
- `image_size` takes `"1K"`, `"2K"` or `"4K"` and **must use an uppercase K**. Lowercase values are rejected. **[Fact — https://ai.google.dev/gemini-api/docs/image-generation]**
- Aspect ratios include 1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, **16:9**, 21:9. **[Fact — image-generation page]** Exact pixel sizes for 16:9 at each size were not readable (the page was truncated). **Unverified.**
- Reference images:
  - Nano Banana 2.1 and 3.1 Flash Image: up to 10 object images + up to 5 character images.
  - 3 Pro Image: 6 object + 5 character + 3 style references.
  - Flash-Lite Image: up to 14 object images, "not optimized for multiple references".
  - **[Fact — image-generation page; the table mapping was partially ambiguous in the fetch]**
- All outputs carry a **SynthID** watermark. **[Fact — image-generation page]**
- Thinking level: Nano Banana 2.1 supports `minimal`/`medium`/`high`, default `medium`, and thinking tokens are billed. **[Fact — image-generation page]**
- Transparent-background output: **not confirmed**. Keep the green-screen #00FF00 approach from the brief. **[Unverified]**
- **None of the image models has a free tier.** **[Fact — pricing page]**

### 1.5 Vision input (image QA)
- Gemini 3 and 4 models charge ~**280 / 560 / 1,120 / 2,240 tokens per image** for `media_resolution` low / medium / high / ultra_high. The default (unspecified) is **1,120**. **[Fact — https://ai.google.dev/gemini-api/docs/media-resolution]**
- Images are billed at the model's normal input rate. For example, a 1,120-token image on `gemini-3.5-flash-lite` costs ≈ $0.00034. **[Estimate from Fact prices]**

### 1.6 TTS (for reference; voice-over is manual in ElevenLabs for now)
- `gemini-3.8-flash-tts`: $0.50 in / $9.00 out per 1M tokens (≈ $0.00225 per 10 s), doubling on 2027-01-01. **[Fact — pricing page]**
- `gemini-3.8-flash-lite-tts`: $6.00 out per 1M tokens (≈ $0.0015 per 10 s). **[Fact — pricing page]**
- **Kazakh is supported** by both 3.8 TTS models. There are 30 prebuilt voices, and output is 24 kHz mono 16-bit WAV. **[Fact — https://ai.google.dev/gemini-api/docs/speech-generation, 2026-10-12]**
- A 4-min voice-over costs ≈ $0.05–0.06. This is a cheap fallback/preview voice, but the quality in Kazakh is untested. **[Estimate]**

### 1.7 Rate limits and tiers
**[Fact — https://ai.google.dev/gemini-api/docs/rate-limits, 2026-10-15]**

| Tier | How you get it | Monthly billing-account cap | Spend rate limit |
|---|---|---|---|
| Free | — | — | — |
| Tier 1 | billing account linked | **$250** | $10 / 10 min |
| Tier 2 | $100 paid + 3 days | $2,000 | $50 / 10 min |
| Tier 3 | $1,000 paid + 30 days | $20k–100k+ | $200 / 10 min |

- RPM/TPM/RPD numbers are **not published on the docs page**. They are shown per project in AI Studio, and limits apply **per project, not per API key**. **[Fact — same page]**
- When a tier cap is reached, "service is paused for all projects linked to that billing account until the start of the next billing cycle". **[Fact — https://ai.google.dev/gemini-api/docs/billing, 2026-09-28]**
- Prepaid credits: $5–$5,000, expire in 12 months. At a $0 balance requests fail with **HTTP 402**. **[Fact — billing page]**

### 1.8 How to cap spending
1. **AI Studio → Spend → Project spend cap**: a monthly $ limit per project. It is experimental, ~10 min enforcement delay, and overages during that window are on you. **[Fact — billing page; Google blog https://blog.google/innovation-and-ai/technology/developers-tools/more-control-over-gemini-api-costs/ (2026-03)]**
2. **Tier 1 hard cap of $250/month** is automatic. **[Fact — billing page]**
3. **Google Cloud Billing budget** with alert thresholds. Alerts-only budgets **do not cap spend**. A Pub/Sub notification can programmatically disable billing. Separate "spend cap budgets" exist only "if supported for your service", and **Gemini API eligibility was not confirmed**. **[Fact — https://docs.cloud.google.com/billing/docs/how-to/budgets, 2026-10-13]**
4. Optionally use **prepaid credits** without auto-reload. Running out then means hard stop (HTTP 402). **[Fact — billing page]**
5. The app-side ledger and caps (rules below) are our own extra layer. **[Estimate]**

---

## 2. ElevenLabs

### 2.1 Plans
**[Fact — https://elevenlabs.io/pricing, fetched 2026-10-16; promo shown "Until Oct 18"]**

| Plan | Regular price/mo | Credits/mo | ≈ TTS minutes | Commercial licence | Voice cloning | Audio |
|---|---|---|---|---|---|---|
| Free | $0 | 10k | ~10 | **No**; attribution "elevenlabs.io"/"11.ai" in title required | No | 128 kbps |
| Starter | **$6** (promo $1 first month) | 30k | ~30 | Yes | Instant (IVC) | 128 kbps |
| Creator | **$22** (promo $11 first month) | 121k | ~121 | Yes | IVC + 1 Professional (PVC) | 192 kbps |
| Pro | $99 | 600k | ~600 | Yes | IVC + PVC | 192 kbps, 44.1 kHz PCM via API |
| Scale / Business | $299 / $990 | 1.8M / 6M | — | Yes | 3 / 10 PVC | — |

- Commercial licence: "All paid plans include a commercial license". The Free plan cannot be used commercially and needs attribution. **[Fact — https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform]**
  - Content made with **Beta services** may not be used commercially (secondary source). Check whether `eleven_v4` is still beta before relying on it. **[Unverified — https://terms.law/ai-output-rights/elevenlabs/]**
- **API:** sold separately and billed in **USD per 1K characters**:
  - v4 / v3 / Multilingual v2: **$0.08**
  - v4 Turbo / v3 Conversational / Flash: $0.04
  - **[Fact — https://elevenlabs.io/pricing/api]**
  - Per-plan API inclusion is not shown on the plan cards. **[Unverified]**
- **Web UI cost: Eleven v3 = 1 credit per character.** **[Fact — https://help.elevenlabs.io/hc/en-us/articles/35869113958801-How-much-does-it-cost-to-generate-using-Eleven-v3]**

### 2.2 Kazakh
- **Kazakh is supported by `eleven_v4`, `eleven_v4_turbo`, `eleven_v3` and `eleven_v3_conversational`.** It is **not** supported by `eleven_multilingual_v2`, `eleven_flash_v2_5` or `eleven_flash_v2`. **[Fact — https://elevenlabs.io/docs/overview/models]**
- Max characters per request: v3 5,000; v4 10,000. **[Fact — same page]** A 4-min script (~4.4k chars) fits in one v3 request, but only just. **[Estimate]**

### 2.3 Credits needed per video
- 550 Kazakh words × ~8 characters per word (incl. space and punctuation) ≈ **4,400 characters**. With retakes and partial regenerations (×1.5–2.0), that is **≈ 6.6k–8.8k credits per video**. **[Estimate]**
- 12 videos come to **≈ 80k–106k credits/month**, so **Creator (121k) is needed**. Starter (30k) covers ~4–6 videos. Shorts reuse the main audio and need no extra credits. **[Estimate]**

---

## 3. Supabase (Free plan)

| Item | Free plan | Source |
|---|---|---|
| DB size | 500 MB per project, shared CPU, 500 MB RAM | [Fact — https://supabase.com/pricing] |
| Egress | 5 GB uncached + 5 GB cached | [Fact — pricing] |
| File storage | 1 GB (we don't use it) | [Fact — pricing] |
| Active projects | 2 | [Fact — pricing] |
| Backups | **No automatic backups on Free** | [Fact — pricing] |
| Logs | 1-day retention | [Fact — pricing] |
| Pro plan | from $25/month (incl. $10 compute credits) | [Fact — pricing] |

- **Pausing rule:** "Free projects are paused after 1 week of inactivity". **[Fact — pricing]**
  - A project is inactive "if it does not receive sufficient user database activity over the past week". "A few user requests to the database each day" usually prevents the pause. **[Fact — https://supabase.com/docs/guides/platform/free-project-pausing]**
  - The owner gets a warning email ~1 week before the pause and another email when it happens. Dashboard visits, API calls and app requests all count as activity. **[Fact — same page]**
  - To restore: Dashboard → project → **Resume project**. Data and config come back. **[Fact — same page]**
  - Restore window: the page body says **up to 1 year**, but a heading says "90-day window", so the docs are inconsistent. **[Fact — same page; changelog https://supabase.com/changelog/27497-paused-free-plan-projects-are-restorable-for-90-days]**
- **Data volume estimate:** text-only rows (scripts, facts, storyboards ~50–150 KB/video) → < 10 MB/year. 500 MB is ample. **[Estimate]**

### 3.1 Connection strings
**[Fact — https://supabase.com/docs/guides/database/connecting-to-postgres]**

| Mode | Host:port | IP | Notes |
|---|---|---|---|
| Direct | `db.<ref>.supabase.co:5432` | **IPv6 only** (IPv4 needs a paid add-on) | full Postgres features |
| **Session pooler** (Supavisor) | `aws-<n>-<region>.pooler.supabase.com:5432`, user `postgres.<ref>` | **IPv4** on all plans | supports prepared statements and session state |
| Transaction pooler | same host, port **6543** | IPv4 | **no prepared statements**, no LISTEN/NOTIFY or temp tables; meant for serverless |

- **Recommendation for our Windows laptop:** "Persistent backend … on an IPv4-only network without the add-on, use the session pooler". **[Fact — same page]** Many home and mobile ISPs are IPv4-only, so the Session pooler is the safe default. **[Estimate]**
- Copy the pooler host from the **Connect** dialog, because it cannot be derived from the region. Percent-encode special characters in the password. **[Fact — same page]**
- SQLAlchemy + psycopg 3 URL:
  `postgresql+psycopg://postgres.<ref>:<url-encoded-password>@aws-<n>-<region>.pooler.supabase.com:5432/postgres?sslmode=require`
  **[Estimate — standard SQLAlchemy dialect format applied to the Fact host]**

### 3.2 Backups
- The official guide uses the CLI (needs Docker Desktop):
  `supabase db dump --db-url "$URL" -f roles.sql --role-only`
  `supabase db dump --db-url "$URL" -f schema.sql`
  `supabase db dump --db-url "$URL" -f data.sql --use-copy --data-only`
  It says to use the **Session pooler string by default**. **[Fact — https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore]**
- The guide's Windows install instructions are for Postgres 17 client tools. **[Fact — same page]**
- Without Docker you can run a plain `pg_dump`, which must be the same or newer major version than the server:
  `pg_dump "$URL" -Fc --no-owner --no-privileges -n public -f backup_YYYYMMDD.dump`
  **[Estimate]**

---

## 4. Remotion licence
- The **Free License** applies if you are "an individual", "a for-profit organization with up to 3 employees", a non-profit, or still evaluating. **[Fact — https://github.com/remotion-dev/remotion/blob/main/LICENSE.md]**
- Commercial and unlimited use is allowed; you must upgrade when the team grows. **[Fact — https://www.remotion.pro/license]**
- The **Company License** is for 4+ people:
  - Creators: $25/seat/month
  - Automators: $0.01/render with a $100/month minimum
  - Enterprise: from $500/month
  - **[Fact — https://www.remotion.pro/license]**
- **Our case:** one individual running a monetized channel is covered by the free licence. **[Estimate — individuals are eligible without a revenue condition in the LICENSE text]**

---

## 5. Other tools

### 5.1 yt-dlp (transcripts) in 2026
- yt-dlp **requires an external JS runtime for YouTube** (EJS challenge solver):
  - Deno ≥ 2.3.0 is the default.
  - **Node ≥ 22.0.0 works with `--js-runtimes node`** (put it in the yt-dlp config file).
  - Without a runtime, formats may be missing.
  - **[Fact — https://github.com/yt-dlp/yt-dlp/wiki/EJS, edited 2026-07-12]**
- **PO tokens:**
  - The `web` client needs a PO token for GVS **and subtitles ("Subs")**.
  - `tv`, `web_embedded` and `android_vr` don't need one.
  - Recommended setup is a PO-token provider plugin (`bgutil-ytdlp-pot-provider`) with the `mweb` client.
  - Without a token you may get HTTP 403 or have the account/IP blocked.
  - **[Fact — https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide, edited 2026-07-12]**
- When YouTube flags the IP, the "Sign in to confirm you're not a bot" error shows up and asks for cookies. **[Fact — https://github.com/yt-dlp/yt-dlp/issues/15897 and search summary]**
- **Reliability estimate:** subtitle fetch for a handful of videos per week from a residential IP usually works. Expect intermittent failures and keep the brief's **manual paste fallback** as a first-class path. **[Estimate]**

### 5.2 faster-whisper large-v3 (word timestamps)
- Published benchmark for 13 min of audio:
  - GPU, large-v2, RTX 3070 Ti: fp16 **63 s, 4.5 GB VRAM**; int8 **59 s, 2.9 GB VRAM**; batch=8 ≈ 16–17 s.
  - CPU, *small* model, i7-12700K, 8 threads: int8 102 s, 1.5 GB RAM.
  - **[Fact — https://github.com/SYSTRAN/faster-whisper]**
- GPU needs **CUDA 12 + cuDNN 9** (latest ctranslate2). Word timestamps come from `word_timestamps=True`. **[Fact — same page]**
- Kazakh: `"kk": "kazakh"` is in Whisper's language list. **[Fact — https://github.com/openai/whisper/blob/main/whisper/tokenizer.py]**
- **Estimates for 4 min of audio with large-v3** (same architecture size as v2):
  - NVIDIA GPU (≥4 GB VRAM, int8_float16): **~20–40 s**.
  - Laptop CPU int8: **~3–8 min, ~3–4 GB RAM** (large ≈ 6× the parameters of small).
  - **[Estimate]**
- Kazakh transcription accuracy is lower than English, but we only need *alignment* to the known approved text, so transcription errors matter less. **[Estimate]**

### 5.3 Claude Code CLI `claude -p` on Pro
- As of **2026-10-07**: "You can still use the Claude Agent SDK, `claude -p`, and third-party apps with your subscription limits." The previously announced changes were paused (2026-06-15). The new monthly API credits apply to **Max and Team**, not Pro. **[Fact — https://support.claude.com/articles/15036540]**
- This means `claude -p` script writing costs $0 marginal but uses Pro 5-hour/weekly limits. Policy has changed twice in 2026, so treat it as revocable. **[Estimate]**

---

## 6. Cost per video (pipeline §4.2)

Assumptions (all **[Estimate]**):
- Prices are current Standard paid tier from §1.
- Default models:
  - `gemini-3.8-flash` for analysis/JSON steps
  - `gemini-4-argon` for the Kazakh script
  - `gemini-3.5-flash-lite` for QA
  - `gemini-nano-banana-2.1` at 2K for images
- Kazakh uses ≈ 2–3 tokens/word.
- Thinking tokens are included in "out".

| Step | Model | In tok | Out tok (incl. thinking) | Other | Cost now | After 2027-01-01 |
|---|---|---|---|---|---|---|
| 1 Transcript clean | none (regex) | – | – | – | $0.000 | $0.000 |
| 2 Brief + 3 angles | 3.8 Flash | 8k | 6k | – | $0.029 | $0.057 |
| 3 Facts + grounding | 3.8 Flash | 40k | 12k | ~20 search queries (free quota) | $0.075 | $0.150 |
| 4 Script (2 drafts) | 4 Argon | 2×10k | 2×12k | – | $0.280 | $0.560 |
| 4b Originality | embedding-2 + 3.8 Flash judge ×2 | 15k emb + 24k | 6k | – | $0.045 | $0.085 |
| 5 ElevenLabs text prep | 3.5 Flash-Lite | 3k | 2k | – | $0.006 | $0.006 |
| 6 Storyboard (+30% repair) | 3.8 Flash | 20k (+30%) | 18k (+30%) | – | $0.100 | $0.200 |
| 7 Backgrounds | Nano Banana 2.1, 2K | ~2.5k/img | – | 13 slots × 1.3 attempts ≈ 17 imgs | $0.920 | $0.920 |
| 7b Vision QA | 3.5 Flash-Lite | 17 × 1.7k | 17 × 1.5k | – | $0.073 | $0.073 |
| 8–9 Contact sheet, render | local | – | – | – | $0.000 | $0.000 |
| 10 Metadata + 3 Shorts metadata | 3.8 Flash | 12k | 8k | – | $0.044 | $0.088 |
| **Total per video** | | | | | **≈ $1.57** | **≈ $2.14** |

- **Lean profile** (3.8 Flash for the script, 1K images, single attempt): ≈ **$0.93** now and ≈ $1.25 after Jan 2027. **[Estimate]**
- **Heavy profile** (Argon everywhere, 2K, 2 attempts/slot): ≈ **$3.0** now and ≈ $4.5 after Dec 2026/Jan 2027. **[Estimate]**
- **Batch/Flex** for non-interactive steps (images, QA) would halve those lines, at the cost of up to 24 h latency for Batch. **[Fact for the 50% discount; Estimate for the applicability]**
- Occasional pose sheets on `gemini-3-pro-image` cost ≈ $0.13–0.27 each, roughly 1–2/month. That is negligible. **[Estimate]**

**Monthly budget for 12 videos (+ Shorts, no extra AI cost):**

| Item | Now | From 2027-01 |
|---|---|---|
| Gemini API | ≈ $19 | ≈ $26 |
| Search grounding | $0 (≤5,000 free queries) | $0 |
| ElevenLabs Creator | $22 | $22 |
| Supabase / Remotion / yt-dlp / faster-whisper | $0 | $0 |
| Claude Pro | already paid | already paid |
| **Total variable + subscriptions** | **≈ $41** | **≈ $48** |

---

## Rules for our system

1. **Default model settings** (all overridable in Settings; verify each ID with `models.list()` at startup and refuse to run with a missing ID):
   `MODEL_TEXT=gemini-3.8-flash`, `MODEL_SCRIPT=gemini-4-argon` (fallback `gemini-3.8-flash`), `MODEL_CHEAP=gemini-3.5-flash-lite`, `MODEL_IMAGE=gemini-nano-banana-2.1` (fallback `gemini-3.1-flash-image`), `MODEL_POSE_SHEET=gemini-3-pro-image`, `MODEL_EMBED=gemini-embedding-2` (alias `gemini-embedding-2-preview`), `MODEL_TTS_FALLBACK=gemini-3.8-flash-tts`.
2. **Never use** `gemini-2.5-flash-image`, `gemini-3-pro-preview`, `gemini-2.0-flash*` or `imagen-4.0-*`. They are shut down or being shut down. Block them in settings validation.
3. **Image defaults:** `aspect_ratio="16:9"`, `image_size="2K"` (uppercase K, lowercase is rejected), Nano Banana 2.1 thinking `minimal` for backgrounds. **Max 3 attempts per slot.** After the 3rd QA failure, mark the slot `needs_manual` and stop retrying.
4. **Per-video budget guard:**
   - Estimate cost before every API call from the pricing table.
   - Above **$2.50 per project**, show a warning in the UI.
   - Above **$4.00 per project**, hard-stop and require an operator click to continue.
   - Store every call as a `CostEntry` (provider, model, unit counts, usd).
5. **Monthly guard:**
   - Set the AI Studio **Project spend cap = $40/month**.
   - Add a Cloud Billing alert budget of $40 with alerts at 50/90/100%.
   - App-side: refuse new Gemini calls when the ledger month-to-date ≥ **$35**, unless the operator overrides.
   - Treat HTTP **429** "spending cap" and **402** (prepaid balance 0) as non-retryable `BudgetExceeded` errors.
6. **Search grounding guard:** at most **30 search queries per facts run** (count `grounding_metadata.web_search_queries`). Alert at **4,000 queries/month** (free quota 5,000; $14/1,000 after).
7. **Script and LLM caps:** max **2 auto-rewrites** per originality check, max **1 JSON-repair retry** per structured step, and `max_output_tokens` ≤ 16k on Flash and ≤ 20k on Argon.
8. **Embeddings:** `gemini-embedding-2` with `output_dimensionality=768`. Do not pass `task_type`; prefix inputs with `task: sentence similarity | query: `. Calibrate the originality threshold on ≥20 labelled Kazakh pairs before enforcing it, and store the threshold in Settings.
9. **Price-change awareness:** the pricing table carries `effective_from`. The ledger must select the row valid at call time. Rows for 2026-12-01 (Argon ×2) and 2027-01-01 (3.8 Flash and TTS ×2) are pre-loaded (see table below).
10. **ElevenLabs:**
    - Model for Kazakh must be **`eleven_v3` or `eleven_v4`**. Never `eleven_multilingual_v2` or `eleven_flash_*`, which have no Kazakh.
    - The "Copy for ElevenLabs" text must be **≤ 5,000 characters** (v3 per-request limit). Show the char count, and split at a sentence boundary if longer.
    - The plan must be paid (Starter or above) before publishing. Free-plan audio is not licensed for commercial use.
11. **Supabase connection:**
    - `DATABASE_URL=postgresql+psycopg://postgres.<ref>:<urlencoded-pw>@aws-<n>-<region>.pooler.supabase.com:5432/postgres?sslmode=require` (Session pooler).
    - SQLAlchemy `pool_pre_ping=True`, `pool_size=5`, `max_overflow=5`, `pool_recycle=1800`.
    - Never use port 6543 (transaction pooler) from the app.
    - On connection failure, show the message "Supabase project may be paused — open dashboard → Resume project".
12. **Supabase keep-alive and backup:**
    - On app start, and once per day while the app runs, execute `SELECT 1` and log `last_db_activity`.
    - If the app hasn't touched the DB for **≥ 5 days**, show a banner.
    - Run a **weekly backup** (`pg_dump -Fc` or `supabase db dump`) into `/data/backups/`. Keep the last 8 and warn if the newest is > 8 days old. The Free plan has no automatic backups.
13. **yt-dlp:**
    - Run with `--js-runtimes node --skip-download --write-subs --write-auto-subs --sub-langs "en.*" --sub-format vtt`.
    - Timeout is 60 s. On a bot-check or 403 error, try the `mweb` client once, then fall back to the manual paste UI.
    - Do not use cookies from the operator's main Google account by default (ban risk).
    - Run `yt-dlp -U` weekly.
14. **faster-whisper:**
    - Use `device="cuda", compute_type="int8_float16"` if CUDA 12 + cuDNN 9 and ≥4 GB VRAM are available. Otherwise use `device="cpu", compute_type="int8"`.
    - Always `language="kk"`, `word_timestamps=True`, `vad_filter=True`.
    - Expected step time is ≤1 min on GPU and ≤10 min on CPU. Warn the operator when running on CPU.
15. **Claude Code CLI writer:** log `claude -p` calls in the ledger with `usd=0` and provider `claude-subscription`. If it exits non-zero or reports a usage limit, fall back automatically to `MODEL_SCRIPT`.
16. **Remotion:** the free licence is valid while the operator is an individual or the company has ≤3 employees. If a 4th person joins, budget $25/seat/month (Creators licence).

### Pricing constants for the cost ledger

| provider | model | unit | usd_per_unit | effective_from | source | date checked |
|---|---|---|---|---|---|---|
| google | gemini-4-argon | 1M_input_tokens | 2.00 | – | https://ai.google.dev/gemini-api/docs/pricing | 2026-10-16 |
| google | gemini-4-argon | 1M_output_tokens | 10.00 | – | same | 2026-10-16 |
| google | gemini-4-argon | 1M_input_tokens | 4.00 | 2026-12-01 | same | 2026-10-16 |
| google | gemini-4-argon | 1M_output_tokens | 20.00 | 2026-12-01 | same | 2026-10-16 |
| google | gemini-3.8-flash | 1M_input_tokens | 0.75 | – | same | 2026-10-16 |
| google | gemini-3.8-flash | 1M_output_tokens | 3.75 | – | same | 2026-10-16 |
| google | gemini-3.8-flash | 1M_input_tokens | 1.50 | 2027-01-01 | same | 2026-10-16 |
| google | gemini-3.8-flash | 1M_output_tokens | 7.50 | 2027-01-01 | same | 2026-10-16 |
| google | gemini-3.5-flash-lite | 1M_input_tokens | 0.30 | – | same | 2026-10-16 |
| google | gemini-3.5-flash-lite | 1M_output_tokens | 2.50 | – | same | 2026-10-16 |
| google | gemini-3.1-flash-lite | 1M_input_tokens | 0.25 | – | same | 2026-10-16 |
| google | gemini-3.1-flash-lite | 1M_output_tokens | 1.50 | – | same | 2026-10-16 |
| google | gemini-embedding-2 | 1M_input_tokens | 0.20 | – | same | 2026-10-16 |
| google | gemini-nano-banana-2.1 | 1M_input_tokens | 1.50 | – | same | 2026-10-16 |
| google | gemini-nano-banana-2.1 | image_1K | 0.0336 | – | same | 2026-10-16 |
| google | gemini-nano-banana-2.1 | image_2K | 0.0504 | – | same | 2026-10-16 |
| google | gemini-nano-banana-2.1 | image_4K | 0.113 | – | same | 2026-10-16 |
| google | gemini-3.1-flash-image | image_1K | 0.067 | – | same | 2026-10-16 |
| google | gemini-3.1-flash-image | image_2K | 0.101 | – | same | 2026-10-16 |
| google | gemini-3-pro-image | 1M_input_tokens | 2.00 | – | same | 2026-10-16 |
| google | gemini-3-pro-image | image_1K_2K | 0.134 | – | same | 2026-10-16 |
| google | gemini-3.8-flash-tts | 1M_output_tokens | 9.00 | – | same | 2026-10-16 |
| google | gemini-3.8-flash-tts | 1M_output_tokens | 18.00 | 2027-01-01 | same | 2026-10-16 |
| google | google_search_grounding (Gemini 3+) | search_query (after 5,000 free/month) | 0.014 | – | https://ai.google.dev/gemini-api/docs/google-search | 2026-10-16 |
| elevenlabs | eleven_v3 / eleven_v4 (API) | 1K_characters | 0.08 | – | https://elevenlabs.io/pricing/api | 2026-10-16 |
| elevenlabs | creator_plan | month | 22.00 | – | https://elevenlabs.io/pricing | 2026-10-16 |
| elevenlabs | starter_plan | month | 6.00 | – | https://elevenlabs.io/pricing | 2026-10-16 |
| supabase | free_plan | month | 0.00 | – | https://supabase.com/pricing | 2026-10-16 |
| anthropic | claude-code-cli (Pro subscription) | call | 0.00 | – | https://support.claude.com/articles/15036540 | 2026-10-16 |

Ledger notes (all **[Estimate]**):
- Token counts come from the response usage metadata (input / output / thinking). Bill thinking tokens at the output rate.
- Images are billed per image at the requested `image_size`, **plus** input tokens for prompt and reference images.
- Batch/Flex calls use 50% of the Standard row. Store `tier` in the `CostEntry`.

---

## Contradictions with PROJECT_BRIEF

1. **§6.8 "ElevenLabs Starter $5":** the regular price is **$6/month** (promo $1 first month). More importantly, Starter's 30k credits (~30 min) cover only ~4–6 Kazakh videos/month with retakes. **Creator $22 (121k credits) is needed for the 12-video goal (§4.4).** **[Fact — elevenlabs.io/pricing; Estimate for usage]**
2. **§6.8 "Gemini ~$1–2/video":** this holds today (≈ $1.57 with the default profile). After the scheduled increases (Argon ×2 from 2026-12-01, 3.8 Flash ×2 from 2027-01-01) the default rises to **≈ $2.14**. Staying under $2 needs the lean profile: Flash script, 1K images, or Batch for images. **[Fact for prices; Estimate for totals]**
3. **§4.3 cost split:** images are ~$0.9–1.0 (consistent with "$0.5–1"), but "facts and script ~$0.05–0.3" is low if Argon writes the script with one rewrite (~$0.35–0.4 with facts). **[Estimate]**
4. **§6.8 "set a budget limit in Google Cloud":** a Cloud Billing budget only **alerts** and does not cap spend. The actual cap is the **AI Studio Project spend cap** (experimental, ~10 min lag) plus the Tier-1 $250 billing-account cap. **[Fact — Cloud budgets doc; Gemini billing doc]**
5. **§6.2 "Nano Banana":** the original Nano Banana (`gemini-2.5-flash-image`) is shut down or limited. Use **Nano Banana 2.1 (`gemini-nano-banana-2.1`)**. **[Fact — pricing/models pages]**
6. **§6.8 Supabase "sleeps after ~a week":** confirmed as 7 days of low DB activity. The brief's "export regularly" is **mandatory** rather than optional, because the Free plan has **no automatic backups**. Wake-up is a manual "Resume project" in the dashboard. **[Fact — Supabase pricing / pausing docs]**
7. **§6.2 `DATABASE_URL`:** the brief doesn't say which string to use. The direct host is IPv6-only, so a Windows laptop on an IPv4 network must use the **Session pooler (port 5432)**. **[Fact — Supabase connect docs]**
8. **§4.2 step 1 "yt-dlp":** now requires a JS runtime (Node 22 from the stack works) and may need a PO-token plugin. The brief's manual paste fallback is essential, not optional. **[Fact — yt-dlp wiki]**

## Open questions

1. Exact pixel dimensions of a 16:9 image at `1K`/`2K` for `gemini-nano-banana-2.1` were not readable. Verify with one test call. If 1K at 16:9 is ≥1376×768, consider 1K plus a local upscale to save ~33%.
2. Is the embedding model ID `gemini-embedding-2` or `gemini-embedding-2-preview`? The docs disagree. How good is it on Kazakh sentence similarity? Needs a calibration test.
3. Are the Gemini API services eligible for Cloud "spend cap budgets"? Not confirmed.
4. RPM/TPM/RPD for Tier 1 are only visible in AI Studio. Check after enabling billing. Image-generation RPM may throttle 17 images per video.
5. Is `eleven_v4` a "Beta service" (no commercial use)? What is its credit cost per character in the web UI? Kazakh voice quality of v3 vs v4 needs a listening test by the operator.
6. Supabase restore window for paused projects: 1 year or 90 days? The docs are inconsistent.
7. Is the `usage_metadata` field naming in the new `client.interactions` API the same as in `generate_content`? Verify when implementing the ledger.
8. Is `claude -p` on Pro stable? The policy has changed twice in 2026. Re-check https://support.claude.com/articles/15036540 monthly.
9. Does the operator's laptop have an NVIDIA GPU? This changes the faster-whisper step time from ~30 s to several minutes.

## Sources

- https://ai.google.dev/gemini-api/docs/pricing (updated 2026-10-15)
- https://ai.google.dev/gemini-api/docs/models (updated 2026-10-13)
- https://ai.google.dev/gemini-api/docs/google-search (updated 2026-10-13)
- https://ai.google.dev/gemini-api/docs/structured-output (updated 2026-10-13)
- https://ai.google.dev/gemini-api/docs/embeddings (updated 2026-10-09)
- https://ai.google.dev/gemini-api/docs/image-generation
- https://ai.google.dev/gemini-api/docs/image-understanding (updated 2026-09-23)
- https://ai.google.dev/gemini-api/docs/media-resolution
- https://ai.google.dev/gemini-api/docs/speech-generation (updated 2026-10-12)
- https://ai.google.dev/gemini-api/docs/rate-limits (updated 2026-10-15)
- https://ai.google.dev/gemini-api/docs/billing (updated 2026-09-28)
- https://blog.google/innovation-and-ai/technology/developers-tools/more-control-over-gemini-api-costs/ (2026-03)
- https://docs.cloud.google.com/billing/docs/how-to/budgets (updated 2026-10-13)
- https://elevenlabs.io/pricing (fetched 2026-10-16)
- https://elevenlabs.io/pricing/api (fetched 2026-10-16)
- https://elevenlabs.io/docs/overview/models
- https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform
- https://help.elevenlabs.io/hc/en-us/articles/35869113958801-How-much-does-it-cost-to-generate-using-Eleven-v3
- https://terms.law/ai-output-rights/elevenlabs/ (secondary)
- https://supabase.com/pricing
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/platform/free-project-pausing
- https://supabase.com/changelog/27497-paused-free-plan-projects-are-restorable-for-90-days
- https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore
- https://github.com/remotion-dev/remotion/blob/main/LICENSE.md
- https://www.remotion.pro/license
- https://github.com/yt-dlp/yt-dlp/wiki/EJS (edited 2026-07-12)
- https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide (edited 2026-07-12)
- https://github.com/yt-dlp/yt-dlp/issues/15897
- https://github.com/SYSTRAN/faster-whisper
- https://github.com/openai/whisper/blob/main/whisper/tokenizer.py
- https://support.claude.com/articles/15036540 (updates 2026-06-15, 2026-10-07)
