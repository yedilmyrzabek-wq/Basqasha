import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig} from 'remotion';
import {C, FONT, Stick, Txt, Coin, lin, usePop} from '../kit';

export const POP_FPS = 30;
export const POP_TOTAL = Math.round(26.6 * POP_FPS);
const sec = (s: number) => Math.round(s * POP_FPS);
const W = 1920;
const H = 1080;

/** Full-frame AI background with slow Ken Burns zoom + optional punch-in */
const Bg: React.FC<{src: string; len: number; punchAt?: number[]; origin?: string; children?: React.ReactNode}> = ({src, len, punchAt = [], origin = '60% 50%', children}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  let z = interpolate(f, [0, len], [1.0, 1.08]);
  for (const p of punchAt) z += 0.05 * spring({frame: f - p, fps, config: {damping: 14}}) * Math.max(0, 1 - (f - p) / 40);
  return (
    <AbsoluteFill style={{transform: `scale(${z})`, transformOrigin: origin}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      {children}
    </AbsoluteFill>
  );
};

const Svg: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill>
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      {children}
    </svg>
  </AbsoluteFill>
);

const Scene: React.FC<{len: number; children: React.ReactNode}> = ({len, children}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 6, len - 4, len], [0, 1, 1, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

/** Big label with paper card behind it */
const Label: React.FC<{x: number; y: number; text: string; size?: number; color?: string; delay?: number; bg?: string}> = ({
  x,
  y,
  text,
  size = 80,
  color = C.ink,
  delay = 0,
  bg = C.paper,
}) => {
  const p = usePop(delay, 11);
  const w = text.length * size * 0.6 + 60;
  return (
    <g transform={`translate(${x},${y}) scale(${p}) rotate(-2)`} opacity={Math.min(1, p * 1.4)}>
      <rect x={-w / 2} y={-size * 0.8} width={w} height={size * 1.6} rx={18} fill={bg} stroke={C.ink} strokeWidth={6} />
      <Txt x={0} y={4} size={size} color={color}>
        {text}
      </Txt>
    </g>
  );
};

const PopcornCup: React.FC<{s?: number}> = ({s = 1}) => (
  <g transform={`scale(${s})`}>
    {[-30, -8, 14, 34, -18, 6, 26].map((x, i) => (
      <circle key={i} cx={x} cy={-58 - (i > 3 ? 18 : 0)} r={20} fill="#F7E3A1" stroke={C.ink} strokeWidth={4} />
    ))}
    <path d="M -50 -55 L 50 -55 L 38 50 L -38 50 Z" fill={C.paper} stroke={C.ink} strokeWidth={5} strokeLinejoin="round" />
    {[-28, 0, 28].map((x) => (
      <path key={x} d={`M ${x - 8} -55 L ${x + 8} -55 L ${x * 0.76 + 6} 50 L ${x * 0.76 - 6} 50 Z`} fill={C.red} />
    ))}
  </g>
);


/* ---------- AI character (pose library from Flow) ---------- */
const POSE_SIZE: Record<string, [number, number]> = {
  point: [269, 320], shrug: [300, 320], think: [184, 320], shock: [188, 320],
  excited: [293, 318], popcorn: [245, 318], coin: [191, 318], present: [259, 318],
};
/** x = center, y = feet line, h = height in px; schedule = [[frame, pose], ...] */
const Char: React.FC<{x: number; y: number; h?: number; schedule: [number, string][]; flip?: boolean}> = ({x, y, h = 470, schedule, flip = false}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  let cur = schedule[0];
  for (const s of schedule) if (f >= s[0]) cur = s;
  const [w0, h0] = POSE_SIZE[cur[1]];
  const w = (h * w0) / h0;
  const pop = spring({frame: f - cur[0], fps, config: {damping: 9, mass: 0.5}});
  const sx = 0.85 + 0.15 * pop;
  const sy = (1.12 - 0.12 * pop) * (1 + 0.012 * Math.sin(f / 8));
  return (
    <g transform={`translate(${x},${y}) scale(${flip ? -sx : sx},${sy})`}>
      <ellipse cx={0} cy={0} rx={w * 0.35} ry={14} fill={C.ink} opacity={0.12} />
      <image href={staticFile(`char/pose_${cur[1]}.png`)} x={-w / 2} y={-h} width={w} height={h} />
    </g>
  );
};

/* ---------- Captions (phrase-level, keyword highlighted) ---------- */
const CAPS: [number, number, string, string][] = [
  [0.0, 2.9, 'Why does movie theater popcorn cost so much?', 'popcorn'],
  [3.2, 5.6, 'Because the ticket barely makes money.', 'barely'],
  [6.0, 12.3, 'In 2025, AMC paid about half of each ticket dollar to studios.', 'half'],
  [12.7, 14.5, 'But popcorn and drinks?', 'popcorn'],
  [14.7, 19.2, 'Only about 20¢ of cost for each $1 sold.', '20¢'],
  [19.6, 21.9, "So the theater isn't really selling movies.", 'movies'],
  [22.1, 23.8, "It's selling popcorn…", 'popcorn'],
  [23.9, 26.6, '…and the movie is the ad.', 'ad.'],
];
const Captions: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / POP_FPS;
  const c = CAPS.find(([a, b]) => t >= a && t < b);
  if (!c) return null;
  const local = (t - c[0]) * POP_FPS;
  const p = interpolate(local, [0, 6], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 46}}>
      <div
        style={{
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: 50,
          color: C.ink,
          background: 'rgba(255,253,248,0.94)',
          border: `5px solid ${C.ink}`,
          borderRadius: 18,
          padding: '12px 28px',
          maxWidth: 1500,
          textAlign: 'center',
          opacity: p,
          transform: `translateY(${(1 - p) * 20}px)`,
        }}
      >
        {c[2].split(' ').map((w, i) => (
          <span
            key={i}
            style={
              w.toLowerCase().startsWith(c[3].toLowerCase())
                ? {background: C.yellow, padding: '0 8px', borderRadius: 8, margin: '0 2px'}
                : undefined
            }
          >
            {w}{' '}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/* ---------- Scenes ---------- */
const A: React.FC<{len: number}> = ({len}) => {
  const f = useCurrentFrame();
  return (
    <Scene len={len}>
      <Bg src="pop/counter.jpg" len={len} origin="75% 55%" />
      <Svg>
        <Char x={300} y={880} schedule={[[0, 'shock']]} />
        <Label x={560} y={300} text="WHY SO PRICEY?" size={74} delay={8} />
        <g transform={`translate(1500,${560 + Math.sin(f / 5) * 6}) rotate(${Math.sin(f / 7) * 6})`} opacity={lin(f, 20, 30)}>
          <Txt x={0} y={-170} size={150} color={C.red}>
            ?
          </Txt>
        </g>
      </Svg>
    </Scene>
  );
};

const B: React.FC<{len: number}> = ({len}) => (
  <Scene len={len}>
    <Bg src="pop/ticket.jpg" len={len} origin="65% 40%" punchAt={[20]} />
    <Svg>
      <Char x={230} y={900} schedule={[[0, 'shrug']]} />
      <Label x={640} y={250} text="THE TICKET?" size={78} delay={6} />
      <Label x={640} y={375} text="barely profitable" size={48} color={C.red} delay={30} />
    </Svg>
  </Scene>
);

const Cpart: React.FC<{len: number}> = ({len}) => {
  const f = useCurrentFrame();
  const pct = Math.round(interpolate(f, [40, 110], [0, 48], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  return (
    <Scene len={len}>
      <Bg src="pop/studio.jpg" len={len} origin="80% 70%" punchAt={[60]} />
      <Svg>
        <Char x={270} y={930} h={430} schedule={[[0, 'think'], [sec(1.75), 'point']]} />
        <g opacity={lin(f, 30, 40)}>
          <Txt x={560} y={320} size={190} color={C.red}>
            ≈{pct}%
          </Txt>
          <Txt x={560} y={450} size={44}>
            of every ticket dollar
          </Txt>
          <Txt x={560} y={510} size={44} color={C.blue}>
            → back to the studios
          </Txt>
        </g>
        {[0, 1, 2, 3, 4, 5].map((i) => {
          const p = lin(f, 70 + i * 12, 105 + i * 12);
          const x = 400 + (1630 - 400) * p;
          const y = 720 + (860 - 720) * p - Math.sin(p * Math.PI) * 260;
          return (
            <g key={i} transform={`translate(${x},${y})`} opacity={p > 0 && p < 1 ? 1 : 0}>
              <Coin r={24} />
            </g>
          );
        })}
        <Txt x={560} y={620} size={24} color={C.grey} weight={600} opacity={lin(f, 120, 140)}>
          AMC FY2025: $1.28B film costs on $2.65B admissions
        </Txt>
      </Svg>
    </Scene>
  );
};

const D: React.FC<{len: number}> = ({len}) => {
  const f = useCurrentFrame();
  const t2 = sec(2.0); // "It cost AMC only..."
  return (
    <Scene len={len}>
      <Bg src="pop/kernels.jpg" len={len} origin="50% 60%" punchAt={[t2 + 45]} />
      <Svg>
        <Char x={250} y={770} h={380} schedule={[[0, 'think'], [t2, 'coin']]} />
        <Label x={620} y={250} text="POPCORN & DRINKS?" size={66} delay={4} />
        <g opacity={lin(f, t2 + 30, t2 + 40)}>
          <Label x={560} y={470} text="~20¢ cost" size={58} color={C.green} delay={t2 + 30} />
          <path d="M 560 520 L 560 590" stroke={C.ink} strokeWidth={7} strokeLinecap="round" />
          <path d="M 542 572 L 560 594 L 578 572" stroke={C.ink} strokeWidth={7} fill="none" strokeLinecap="round" />
        </g>
        <g opacity={lin(f, t2 + 65, t2 + 75)}>
          <Label x={1490} y={140} text="$1.00 sold" size={58} color={C.red} delay={t2 + 65} />
        </g>
        <Txt x={W - 40} y={H - 150} size={24} color={C.grey} weight={600} anchor="end" opacity={lin(f, t2 + 90, t2 + 110)}>
          AMC FY2025: $327M F&B costs on $1.67B F&B sales
        </Txt>
      </Svg>
    </Scene>
  );
};

const E: React.FC<{len: number}> = ({len}) => {
  const f = useCurrentFrame();
  const s1 = sec(1.6); // strike "MOVIES"
  const s2 = sec(2.7); // "It's selling popcorn"
  const s3 = sec(4.5); // "and the movie is the ad"
  const flick = f > s2 && f < s2 + 12 ? (Math.floor(f / 2) % 2 ? 0.3 : 1) : 1;
  return (
    <Scene len={len}>
      <Bg src="pop/marquee.jpg" len={len} origin="70% 45%" punchAt={[s2]}>
        <Svg>
        {/* marquee panels (positions match the generated image) */}
        <g opacity={flick}>
          <Txt x={1221} y={551} size={34}>
            {f < s2 ? 'NOW SHOWING' : 'NOW SELLING'}
          </Txt>
          <Txt x={1542} y={551} size={40} color={f < s2 ? C.blue : C.red}>
            {f < s2 ? 'MOVIES' : 'POPCORN'}
          </Txt>
        </g>
        {f < s2 && <line x1={1440} y1={551} x2={1440 + 200 * lin(f, s1, s1 + 10)} y2={551} stroke={C.red} strokeWidth={10} strokeLinecap="round" />}
        </Svg>
      </Bg>
      <Svg>
        <Char x={330} y={940} schedule={[[0, 'present'], [s2, 'popcorn'], [s3, 'excited']]} flip={f < s2} />
        {f > s3 && <Label x={560} y={330} text="THE MOVIE IS THE AD" size={64} color={C.red} delay={s3} />}
      </Svg>
    </Scene>
  );
};

const SCENES: [React.FC<{len: number}>, number, number][] = [
  [A, 0, 3.1],
  [B, 3.1, 5.9],
  [Cpart, 5.9, 12.6],
  [D, 12.6, 19.4],
  [E, 19.4, 26.6],
];

const SFX: [string, number, number][] = [
  ['pop.wav', 0.3, 0.8],
  ['pop.wav', 1.0, 0.6],
  ['whoosh.wav', 3.0, 0.7],
  ['pop.wav', 3.3, 0.6],
  ['pop.wav', 4.2, 0.5],
  ['whoosh.wav', 5.8, 0.7],
  ['coin.wav', 8.3, 0.5],
  ['coin.wav', 8.7, 0.5],
  ['coin.wav', 9.1, 0.5],
  ['coin.wav', 9.5, 0.5],
  ['whoosh.wav', 12.5, 0.7],
  ['pop.wav', 12.8, 0.6],
  ['ding.wav', 15.7, 0.6],
  ['pop.wav', 16.8, 0.6],
  ['whoosh.wav', 19.3, 0.7],
  ['pop.wav', 21.0, 0.6],
  ['kaching.wav', 22.1, 0.7],
  ['pop.wav', 23.9, 0.8],
];

export const Popcorn: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: FONT}}>
      {SCENES.map(([S, a, b], i) => (
        <Sequence key={i} from={sec(a)} durationInFrames={sec(b) - sec(a)}>
          <S len={sec(b) - sec(a)} />
        </Sequence>
      ))}
      <Captions />
      <div style={{position: 'absolute', left: 0, bottom: 0, height: 8, width: `${(f / POP_TOTAL) * 100}%`, background: C.red}} />
      <Audio src={staticFile('pop/voice.mp3')} />
      <Audio src={staticFile('pop/pad.wav')} volume={0.35} />
      {SFX.map(([file, t, v], i) => (
        <Sequence key={`s${i}`} from={sec(t)} durationInFrames={sec(1.4)}>
          <Audio src={staticFile(`pop/${file}`)} volume={v} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
