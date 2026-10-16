// Usage: node scripts/stills.mjs --props <props.json> --frames <f1,f2,…|mid> --out <dir> [--scale 0.5] [--root <dir>]
// `--frames mid` = the middle frame of every scene (input for the contact sheet).
// Writes <out>/frame_000123.png; stdout: JSON lines {"still":"…","frame":123} then {"done":true,"files":[…]}.
import fs from 'node:fs';
import path from 'node:path';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {emit, loadProps, log, makeBundle, parseArgs} from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
if (!args.props || !args.frames || !args.out) {
  console.error('Usage: npm run stills -- --props <props.json> --frames <f1,f2,…|mid> --out <dir> [--scale 0.5]');
  process.exit(2);
}

const t0 = Date.now();
const {props, close} = await loadProps(args.props, args.root);
let browser;
try {
  const frames =
    args.frames === 'mid'
      ? props.scenes.map((s) => s.from + Math.floor(s.duration / 2))
      : args.frames.split(',').map((x) => Number(x.trim()));
  const serveUrl = await makeBundle();
  browser = await openBrowser('chrome', {logLevel: 'error'});
  const composition = await selectComposition({serveUrl, id: props.composition, inputProps: props, puppeteerInstance: browser, logLevel: 'error'});
  const outDir = path.resolve(args.out);
  fs.mkdirSync(outDir, {recursive: true});
  const files = [];
  for (const frame of frames) {
    const f = Math.min(Math.max(0, frame), composition.durationInFrames - 1);
    const output = path.join(outDir, `frame_${String(f).padStart(6, '0')}.png`);
    await renderStill({
      serveUrl,
      composition,
      inputProps: props,
      frame: f,
      output,
      imageFormat: 'png',
      scale: args.scale ? Number(args.scale) : 1,
      puppeteerInstance: browser,
      logLevel: 'error',
    });
    files.push(output);
    emit({still: output, frame: f});
  }
  log(`${files.length} stills in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  emit({done: true, files});
} catch (e) {
  console.error(e?.stack ?? String(e));
  process.exitCode = 1;
} finally {
  await browser?.close({silent: true});
  close();
}
