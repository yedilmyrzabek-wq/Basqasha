# engine — Remotion renderer (Explainer / ExplainerShort)

Node 22 + Remotion 4.0.535 + React 18 + TypeScript. One generic composition driven **only** by `props.json`
(`/schemas/props.schema.json`); no per-video code. Duration = `props.duration_frames` (via `calculateMetadata`).

```
npm install
npm run typecheck
npm run render -- --props fixtures/glyphtest.props.json --out out/demo.mp4
npm run stills -- --props fixtures/glyphtest.props.json --frames mid --out out/stills          # middle frame of every scene
npm run stills -- --props fixtures/glyphtest.props.json --frames 45 --out out/glyph       # Kazakh glyph check
npm run studio                                                                             # Remotion Studio (placeholder props)
```

- Compositions: `Explainer` 1920×1080 and `ExplainerShort` 1080×1920, 30 fps; `props.composition` selects one.
- Machine output: `render.mjs` prints JSON lines `{"progress":0.42}` … `{"done":true,"out":…,"seconds":…}` on stdout,
  logs on stderr, exit code ≠ 0 on failure. `stills.mjs` prints `{"still":path,"frame":n}` per file, then `{"done":true,"files":[…]}`.
  Options: `--root <dir>` (base for relative asset paths, default repo root), `--concurrency N` (render), `--scale 0.5` (stills).
- Speed (this Windows PC): bundle ≈ 3–15 s, render ≈ 2× real time (26 s video → 50 s), 4-min video ≈ 8–9 min.

## Assets
- `src` values that are `http(s)://…` are used as-is (backend serves `/files/data/…`, `/files/library/…`; the backend
  must be running during the render).
- Relative `src` values (fixtures, local tests) are resolved against `--root`; the script starts a temporary local
  HTTP server for them. Inside Remotion Studio they go through `staticFile()` (i.e. `engine/public`).
- Fonts are bundled in `public/fonts/` as full (unsubsetted) variable TTFs, OFL: **Inter** (captions, labels, notes) and
  **Rubik** (counters, stamps, coin ₸). Both cover ӘҒҚҢӨҰҮҺІ әғқңөұүһі. The backend's glyph check (fontTools cmap)
  should read these two files.
- The engine is asset-agnostic: character poses (src + native width/height), backgrounds, SFX and music all come from
  props. The backend fills them from `library/poses/poses.json` and `library/sfx/sfx.json`. The library content is a placeholder (see `library/README.md`).

## What props drive
| Element | Behaviour |
|---|---|
| Background | `zoom_from→zoom_to` Ken Burns around `focus` (also the crop point for 9:16), `punch` = +5% spring, decays over 40 frames |
| Scene | fade-in from paper colour over 6 frames |
| Character | pose schedule (scene-relative `at`), size from the native PNG ratio, squash & stretch on each change, breathing, `flip`, ground shadow |
| label | paper card, −2°, pop-in; width from the **measured** text (`@remotion/layout-utils`), shrinks to ≥ 48 px only if wider than the frame, shifted to stay in frame; `color` = text colour (`yellow` → yellow card) |
| counter | display-font number counting `from`→`value` over 40 frames, `prefix`/`suffix`, `text` under it, kk/ru decimal comma, groups ≥ 10 000 |
| coins / arrow | coins (₸, `$` for `en`) fly on arcs x,y→x2,y2 (`count`); arrow draws on in 14 frames |
| stamp | uppercase display text in a double frame, slams in, −8° |
| note | small grey source note, bottom-right by default (or at x,y) |
| Captions | one phrase box, bottom; the keyword is the first word whose letters start with the stem (NFC, kk lower-case, punctuation stripped) |
| Audio | voice (`start_from` trims frames), music bed looped at `volume`, raised +6 dB in caption gaps ≥ 0.8 s with 200 ms ramps; SFX at absolute frames |
| Other | progress bar (bottom; top on 9:16), optional sponsor badge |

Labels, counters and stamps that overlap the character's box are automatically moved to the other side of it.
**9:16 Short:** storyboard coordinates (1920×1080) are mapped as `x' = 540 + (x−960)·0.5625` and `y' = 180 + 1.11·y`;
elements keep full size. Captions sit 400 px above the bottom (clear of the Shorts UI).

## Contact sheet
Chosen approach: `stills.mjs --frames mid --scale 0.5` renders the middle frame of every scene, and the **backend**
tiles them with Pillow into `render/contact_sheet_v{n}.png` (for example 4 columns at 960×540 with the scene id written on each).
There is no Remotion composition for this.

## Mastering
The engine mixes at the props volumes and does no loudness processing. The backend runs ffmpeg loudnorm to −14 LUFS
/ −1 dBTP and remuxes with `-c:v copy`. The demo comes out at about −25 LUFS before mastering.
