# Costco test video (Remotion)

## Run on your laptop
1. Install Node.js 20+ (https://nodejs.org).
2. In this folder: `npm install`
3. Live preview (scrub timeline, edit code, see changes instantly): `npx remotion studio src/index.ts`
4. Render MP4: `npx remotion render src/index.ts Costco out/costco_test.mp4`

## Files
- `public/voice.mp3` — narration (ElevenLabs)
- `src/scenes.json` — start time (seconds) of each of the 16 scenes, aligned to pauses in the voice
- `src/scenes.tsx` — the 16 scenes (stickman, charts, props)
- `src/kit.tsx` — reusable parts: Stick figure, price tag, card, cart, warehouse, coin, arrow
- `src/Video.tsx` — puts audio + scenes on the timeline

## New video = new voice.mp3 + new scenes.json + new scene list
This is the part we will later generate automatically from a storyboard JSON.
