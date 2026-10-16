// Usage: node scripts/render.mjs --props <props.json> --out <file.mp4> [--root <dir>] [--concurrency N]
// stdout: JSON lines {"progress":0.42} … {"done":true,"out":"…","seconds":12.3}; logs on stderr; exit 1 on error.
import fs from 'node:fs';
import path from 'node:path';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {emit, loadProps, log, makeBundle, parseArgs} from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
if (!args.props || !args.out) {
  console.error('Usage: npm run render -- --props <props.json> --out <file.mp4> [--root <dir>]');
  process.exit(2);
}

const t0 = Date.now();
const {props, close} = await loadProps(args.props, args.root);
try {
  const serveUrl = await makeBundle();
  const composition = await selectComposition({serveUrl, id: props.composition, inputProps: props, logLevel: 'error'});
  const out = path.resolve(args.out);
  fs.mkdirSync(path.dirname(out), {recursive: true});
  let last = -1;
  await renderMedia({
    serveUrl,
    composition,
    inputProps: props,
    codec: 'h264',
    crf: 18,
    audioCodec: 'aac',
    audioBitrate: '192k',
    outputLocation: out,
    concurrency: args.concurrency ? Number(args.concurrency) : null,
    logLevel: 'error',
    onProgress: ({progress}) => {
      const p = Math.floor(progress * 100);
      if (p !== last) {
        last = p;
        emit({progress: p / 100});
      }
    },
  });
  const seconds = (Date.now() - t0) / 1000;
  log(`rendered ${composition.durationInFrames} frames → ${out} in ${seconds.toFixed(1)} s`);
  emit({done: true, out, seconds});
} catch (e) {
  console.error(e?.stack ?? String(e));
  process.exitCode = 1;
} finally {
  close();
}
