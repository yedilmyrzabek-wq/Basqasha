// Shared helpers for render.mjs / stills.mjs. Logs go to stderr; stdout carries only JSON lines.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';

export const ENGINE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const REPO_DIR = path.resolve(ENGINE_DIR, '..');

export const log = (...a) => console.error('[engine]', ...a);
export const emit = (obj) => process.stdout.write(JSON.stringify(obj) + '\n');

/** --key value pairs → object */
export const parseArgs = (argv) => {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const k = argv[i].slice(2);
      const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : 'true';
      out[k] = v;
    }
  }
  return out;
};

const MIME = {
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4', '.ttf': 'font/ttf', '.woff2': 'font/woff2',
};

/** Minimal static server (CORS + Range) used when props contain relative asset paths (fixtures, local tests). */
const serveDir = (root) =>
  new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/+/, '');
      const file = path.resolve(root, rel);
      if (!file.startsWith(root) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        res.writeHead(404).end();
        return;
      }
      const size = fs.statSync(file).size;
      const headers = {
        'Access-Control-Allow-Origin': '*',
        'Accept-Ranges': 'bytes',
        'Content-Type': MIME[path.extname(file).toLowerCase()] ?? 'application/octet-stream',
      };
      const m = /bytes=(\d*)-(\d*)/.exec(req.headers.range ?? '');
      if (m) {
        const start = m[1] ? Number(m[1]) : 0;
        const end = m[2] ? Number(m[2]) : size - 1;
        res.writeHead(206, {...headers, 'Content-Range': `bytes ${start}-${end}/${size}`, 'Content-Length': end - start + 1});
        fs.createReadStream(file, {start, end}).pipe(res);
      } else {
        res.writeHead(200, {...headers, 'Content-Length': size});
        fs.createReadStream(file).pipe(res);
      }
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });

/**
 * Reads props.json. Absolute http(s) URLs (backend /files/...) are kept. Relative `src` values are
 * resolved against --root (default: repo root) and served by a temporary local HTTP server.
 */
export const loadProps = async (propsPath, root) => {
  const props = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
  const srcs = [];
  const walk = (o) => {
    if (Array.isArray(o)) o.forEach(walk);
    else if (o && typeof o === 'object')
      for (const [k, v] of Object.entries(o)) {
        if (k === 'src' && typeof v === 'string' && v && !/^https?:\/\//i.test(v)) srcs.push(o);
        else walk(v);
      }
  };
  walk(props);
  if (!srcs.length) return {props, close: () => {}};
  const absRoot = path.resolve(root ?? REPO_DIR);
  const server = await serveDir(absRoot);
  const base = `http://127.0.0.1:${server.address().port}`;
  for (const o of srcs) {
    const p = o.src.replace(/\\/g, '/').replace(/^\/+/, '');
    if (!fs.existsSync(path.join(absRoot, p))) throw new Error(`Asset not found: ${p} (root ${absRoot})`);
    o.src = `${base}/${p.split('/').map(encodeURIComponent).join('/')}`;
  }
  log(`serving ${srcs.length} relative assets from ${absRoot} at ${base}`);
  return {props, close: () => server.close()};
};

export const makeBundle = async () => {
  const t = Date.now();
  const serveUrl = await bundle({
    entryPoint: path.join(ENGINE_DIR, 'src', 'index.ts'),
    publicDir: path.join(ENGINE_DIR, 'public'),
  });
  log(`bundled in ${((Date.now() - t) / 1000).toFixed(1)} s`);
  return serveUrl;
};
