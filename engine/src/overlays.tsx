import React, {createContext, useContext} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {C, DISPLAY, FONT, clamp, color, lin, usePop, useStage} from './theme';
import type {Overlay} from './types';
import type {Stage} from './theme';

const MARGIN = 40;
const HALOS = [3, 5, 7] as const;
type Halo = (typeof HALOS)[number];

const HaloDefs: React.FC<{k: number}> = ({k}) => (
  <defs>
    {HALOS.map((r) => (
      <filter key={r} id={`halo${r}`} x="-10%" y="-30%" width="120%" height="160%">
        <feMorphology in="SourceAlpha" operator="dilate" radius={r * k} result="d" />
        <feFlood floodColor={C.paper} />
        <feComposite in2="d" operator="in" result="h" />
        <feMerge>
          <feMergeNode in="h" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    ))}
  </defs>
);

const textWidth = (text: string, fontFamily: string, fontSize: number, fontWeight: number) =>
  measureText({text, fontFamily, fontSize, fontWeight, validateFontIsLoaded: false}).width;

/** Largest size ≤ `size` (but ≥ `min`) at which `text` fits `maxW`. */
const fit = (text: string, family: string, weight: number, size: number, min: number, maxW: number) => {
  const w = textWidth(text, family, size, weight);
  const s = w > maxW ? Math.max(min, (size * maxW) / w) : size;
  return {size: s, width: s === size ? w : textWidth(text, family, s, weight)};
};

/** Screen-space box of the character; text overlays are moved off it. */
export type Box = {l: number; r: number; t: number; b: number};
const AvoidCtx = createContext<Box | null>(null);

/**
 * Final centre for an element whose extent is [cx-half, cx+half] × [cy+top, cy+bottom]:
 * pushed sideways off the character box (away from it), then clamped into the frame.
 */
const usePlace = (st: Stage, cx: number, cy: number, half: number, top: number, bottom: number) => {
  const box = useContext(AvoidCtx);
  const gap = 24 * st.k;
  if (box && cx + half > box.l && cx - half < box.r && cy + bottom > box.t && cy + top < box.b) {
    cx = (box.l + box.r) / 2 < st.W / 2 ? box.r + gap + half : box.l - gap - half;
  }
  return {
    x: clamp(cx, half + MARGIN, st.W - half - MARGIN),
    y: clamp(cy, MARGIN - top, st.H - MARGIN - bottom),
  };
};

const T: React.FC<{
  x: number;
  y: number;
  size: number;
  fill: string;
  family?: string;
  weight?: number;
  anchor?: 'start' | 'middle' | 'end';
  /** Paper outline behind the glyphs (filter radius id, see HALOS). Not a stroke: variable fonts have overlapping contours. */
  halo?: Halo;
  opacity?: number;
  children: React.ReactNode;
}> = ({x, y, size, fill, family = FONT, weight = 800, anchor = 'middle', halo = 0, opacity = 1, children}) => (
  <text
    x={x}
    y={y}
    fontSize={size}
    fill={fill}
    fontFamily={family}
    fontWeight={weight}
    textAnchor={anchor}
    dominantBaseline="central"
    opacity={opacity}
    filter={halo ? `url(#halo${halo})` : undefined}
  >
    {children}
  </text>
);

/** Paper card label: pops in, tilted −2°, width from the measured text; shifted (then shrunk) to stay in frame. */
const Label: React.FC<{o: Overlay}> = ({o}) => {
  const st = useStage();
  const p = usePop(o.at, 11);
  const text = o.text ?? '';
  const yellow = o.color === 'yellow';
  const pad = 34 * st.k;
  const {size, width} = fit(text, FONT, 800, 64 * st.k, 44 * st.k, st.W - 2 * MARGIN - 2 * pad);
  const w = width + 2 * pad;
  const h = size * 1.55;
  const {x, y} = usePlace(st, st.px(o.x ?? 960), st.py(o.y ?? 300), w / 2, -h / 2, h / 2);
  return (
    <g transform={`translate(${x},${y}) scale(${p}) rotate(-2)`} opacity={Math.min(1, p * 1.4)}>
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={18 * st.k} fill={yellow ? C.yellow : C.paper} stroke={C.ink} strokeWidth={6 * st.k} />
      <T x={0} y={size * 0.03} size={size} fill={yellow ? C.ink : color(o.color)}>
        {text}
      </T>
    </g>
  );
};

const formatNumber = (v: number, decimals: number, lang: string) => {
  const s = Math.abs(v).toFixed(decimals);
  const [int, frac] = s.split('.');
  const grouped = Math.abs(v) >= 10000 ? int.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : int;
  const sep = lang === 'en' ? '.' : ',';
  return `${v < 0 ? '−' : ''}${grouped}${frac ? sep + frac : ''}`;
};

/** Big animated number (display font) counting from `from` to `value` over 40 frames, optional text below. */
const Counter: React.FC<{o: Overlay; lang: string}> = ({o, lang}) => {
  const f = useCurrentFrame();
  const st = useStage();
  const p = usePop(o.at, 13);
  const target = o.value ?? 0;
  const decimals = (String(target).split('.')[1] ?? '').length;
  const v = interpolate(f, [o.at, o.at + 40], [o.from ?? 0, target], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const num = `${o.prefix ?? ''}${formatNumber(v, decimals, lang)}${o.suffix ?? ''}`;
  const finalNum = `${o.prefix ?? ''}${formatNumber(target, decimals, lang)}${o.suffix ?? ''}`;
  const maxW = st.W - 2 * MARGIN;
  const big = fit(finalNum, DISPLAY, 800, 170 * st.k, 90 * st.k, maxW);
  const small = o.text ? fit(o.text, FONT, 800, 46 * st.k, 32 * st.k, maxW) : null;
  const half = Math.max(big.width, small?.width ?? 0) / 2;
  const bottom = small ? big.size * 0.5 + small.size * 1.4 : big.size * 0.6;
  const {x, y} = usePlace(st, st.px(o.x ?? 960), st.py(o.y ?? 320), half, -big.size * 0.6, bottom);
  return (
    <g transform={`translate(${x},${y}) scale(${0.6 + 0.4 * p})`} opacity={Math.min(1, p * 1.5)}>
      <T x={0} y={0} size={big.size} fill={color(o.color, C.red)} family={DISPLAY} halo={7}>
        {num}
      </T>
      {small && (
        <T x={0} y={big.size * 0.5 + small.size * 0.85} size={small.size} fill={C.ink} halo={5}>
          {o.text}
        </T>
      )}
    </g>
  );
};

/** Coin glyph; the currency sign follows the language. */
const Coin: React.FC<{r: number; lang: string}> = ({r, lang}) => (
  <g>
    <circle r={r} fill={C.yellow} stroke={C.ink} strokeWidth={r * 0.2} />
    <T x={0} y={r * 0.04} size={r * 1.15} fill={C.ink} family={DISPLAY}>
      {lang === 'en' ? '$' : '₸'}
    </T>
  </g>
);

/** `count` coins fly on arcs from (x,y) to (x2,y2), staggered. */
const Coins: React.FC<{o: Overlay; lang: string}> = ({o, lang}) => {
  const f = useCurrentFrame();
  const st = useStage();
  const n = o.count ?? 6;
  const x1 = st.px(o.x ?? 400);
  const y1 = st.py(o.y ?? 720);
  const x2 = st.px(o.x2 ?? 1600);
  const y2 = st.py(o.y2 ?? 820);
  const arc = 120 * st.k + 0.2 * Math.hypot(x2 - x1, y2 - y1);
  return (
    <g>
      {Array.from({length: n}, (_, i) => {
        const p = lin(f, o.at + i * 8, o.at + i * 8 + 32);
        if (p <= 0 || p >= 1) return null;
        const x = x1 + (x2 - x1) * p;
        const y = y1 + (y2 - y1) * p - Math.sin(p * Math.PI) * arc;
        return (
          <g key={i} transform={`translate(${x},${y}) rotate(${p * 360})`}>
            <Coin r={26 * st.k} lang={lang} />
          </g>
        );
      })}
    </g>
  );
};

/** Arrow drawn on over 14 frames, head appears at the end. */
const Arrow: React.FC<{o: Overlay}> = ({o}) => {
  const f = useCurrentFrame();
  const st = useStage();
  const p = lin(f, o.at, o.at + 14);
  const x1 = st.px(o.x ?? 0);
  const y1 = st.py(o.y ?? 0);
  const x2 = st.px(o.x2 ?? 0);
  const y2 = st.py(o.y2 ?? 0);
  const ex = x1 + (x2 - x1) * p;
  const ey = y1 + (y2 - y1) * p;
  const a = Math.atan2(y2 - y1, x2 - x1);
  const hd = 30 * st.k;
  const c = color(o.color);
  if (p <= 0.01) return null;
  const head = `M ${ex - hd * Math.cos(a - 0.5)} ${ey - hd * Math.sin(a - 0.5)} L ${ex} ${ey} L ${ex - hd * Math.cos(a + 0.5)} ${ey - hd * Math.sin(a + 0.5)}`;
  return (
    <g fill="none" strokeLinecap="round" strokeLinejoin="round">
      {[
        [C.paper, 18 * st.k],
        [c, 9 * st.k],
      ].map(([s, w]) => (
        <g key={String(s)} stroke={String(s)} strokeWidth={Number(w)}>
          <line x1={x1} y1={y1} x2={ex} y2={ey} />
          {p > 0.95 && <path d={head} />}
        </g>
      ))}
    </g>
  );
};

/** Rubber stamp: uppercase display text in a double frame, slams in from 1.9x, tilted −8°. */
const Stamp: React.FC<{o: Overlay; lang: string}> = ({o, lang}) => {
  const st = useStage();
  const p = usePop(o.at, 15);
  const text = (o.text ?? '').toLocaleUpperCase(lang);
  const c = color(o.color, C.red);
  const pad = 30 * st.k;
  const {size, width} = fit(text, DISPLAY, 800, 68 * st.k, 44 * st.k, st.W - 2 * MARGIN - 2 * pad);
  const w = width + 2 * pad;
  const h = size * 1.5;
  const {x, y} = usePlace(st, st.px(o.x ?? 960), st.py(o.y ?? 540), w / 2 + 10 * st.k, -h / 2 - 20 * st.k, h / 2 + 20 * st.k);
  const s = 1 + 0.9 * (1 - p);
  const i = 9 * st.k;
  return (
    <g transform={`translate(${x},${y}) rotate(-8) scale(${s})`} opacity={Math.min(1, p * 2)}>
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={12 * st.k} fill={C.paper} fillOpacity={0.9} stroke={c} strokeWidth={7 * st.k} />
      <rect x={-w / 2 + i} y={-h / 2 + i} width={w - 2 * i} height={h - 2 * i} rx={6 * st.k} fill="none" stroke={c} strokeWidth={2.5 * st.k} />
      <T x={0} y={size * 0.04} size={size} fill={c} family={DISPLAY} weight={800}>
        {text}
      </T>
    </g>
  );
};

/** Small grey source note; default bottom-right above the captions. */
const Note: React.FC<{o: Overlay}> = ({o}) => {
  const f = useCurrentFrame();
  const st = useStage();
  const size = (st.short ? 30 : 26) * st.k;
  const hasX = o.x !== undefined;
  return (
    <T
      x={hasX ? st.px(o.x as number) : st.W - MARGIN}
      y={o.y !== undefined ? st.py(o.y) : st.H - (st.short ? 580 : 178 * st.k)}
      size={size}
      fill={C.grey}
      weight={600}
      anchor={hasX ? 'middle' : 'end'}
      halo={3}
      opacity={lin(f, o.at, o.at + 15)}
    >
      {o.text}
    </T>
  );
};

export const Overlays: React.FC<{items: Overlay[]; lang: string; avoid: Box | null}> = ({items, lang, avoid}) => {
  const f = useCurrentFrame();
  const st = useStage();
  return (
    <AvoidCtx.Provider value={avoid}>
    <AbsoluteFill>
      <svg width={st.W} height={st.H} viewBox={`0 0 ${st.W} ${st.H}`}>
        <HaloDefs k={st.k} />
        {items
          .filter((o) => f >= o.at)
          .map((o, i) => {
            switch (o.type) {
              case 'label':
                return <Label key={i} o={o} />;
              case 'counter':
                return <Counter key={i} o={o} lang={lang} />;
              case 'coins':
                return <Coins key={i} o={o} lang={lang} />;
              case 'arrow':
                return <Arrow key={i} o={o} />;
              case 'stamp':
                return <Stamp key={i} o={o} lang={lang} />;
              case 'note':
                return <Note key={i} o={o} />;
              default:
                return null;
            }
          })}
      </svg>
    </AbsoluteFill>
    </AvoidCtx.Provider>
  );
};
