import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from 'remotion';

export const C = {
  bg: '#F6F1E7',
  ink: '#1F1F24',
  red: '#E4572E',
  blue: '#2E86AB',
  green: '#3BA55C',
  yellow: '#F2C14E',
  grey: '#9A958C',
  paper: '#FFFDF8',
};
export const FONT = "Inter, 'Helvetica Neue', Arial, sans-serif";

export const usePop = (delay = 0, damping = 12) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: f - delay, fps, config: {damping, mass: 0.6}});
};

export const lin = (f: number, a: number, b: number, from = 0, to = 1) =>
  interpolate(f, [a, b], [from, to], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });

/** Pops a child in with scale/opacity after `delay` frames */
export const Pop: React.FC<{delay?: number; x: number; y: number; children: React.ReactNode; origin?: string}> = ({
  delay = 0,
  x,
  y,
  children,
}) => {
  const p = usePop(delay);
  return (
    <g transform={`translate(${x},${y}) scale(${p})`} opacity={Math.min(1, p * 1.5)}>
      {children}
    </g>
  );
};

export const Txt: React.FC<{
  x: number;
  y: number;
  size?: number;
  color?: string;
  weight?: number;
  anchor?: 'start' | 'middle' | 'end';
  children: React.ReactNode;
  opacity?: number;
}> = ({x, y, size = 48, color = C.ink, weight = 800, anchor = 'middle', children, opacity = 1}) => (
  <text
    x={x}
    y={y}
    fontSize={size}
    fill={color}
    fontWeight={weight}
    fontFamily={FONT}
    textAnchor={anchor}
    dominantBaseline="middle"
    opacity={opacity}
  >
    {children}
  </text>
);

type Face = 'happy' | 'neutral' | 'think' | 'shock' | 'smug';

/** Stick figure. Arm/leg angles are degrees from straight down (0 = hanging). */
export const Stick: React.FC<{
  x: number;
  y: number;
  s?: number;
  la?: number;
  ra?: number;
  ll?: number;
  rl?: number;
  face?: Face;
  color?: string;
  bob?: boolean;
  flip?: boolean;
  rightHand?: React.ReactNode;
  leftHand?: React.ReactNode;
  hat?: React.ReactNode;
  seed?: number;
}> = ({x, y, s = 1, la = 25, ra = 25, ll = 14, rl = 14, face = 'happy', color = C.ink, bob = true, flip = false, rightHand, leftHand, hat, seed = 0}) => {
  const f = useCurrentFrame() + seed * 17;
  const b = bob ? Math.sin(f / 9) * 4 : 0;
  const blink = f % 110 > 104;
  const sw = 9;
  const L = 68;
  const sh = {x: 0, y: -112 + b};
  const hip = {x: 0, y: -42};
  const rad = (d: number) => (d * Math.PI) / 180;
  const lHand = {x: sh.x - Math.sin(rad(la)) * L, y: sh.y + Math.cos(rad(la)) * L};
  const rHand = {x: sh.x + Math.sin(rad(ra)) * L, y: sh.y + Math.cos(rad(ra)) * L};
  const lFoot = {x: hip.x - Math.sin(rad(ll)) * 74, y: hip.y + Math.cos(rad(ll)) * 74};
  const rFoot = {x: hip.x + Math.sin(rad(rl)) * 74, y: hip.y + Math.cos(rad(rl)) * 74};
  const hy = -150 + b;
  const eyes = blink ? (
    <>
      <line x1={-11} y1={hy - 4} x2={-4} y2={hy - 4} stroke={color} strokeWidth={4} strokeLinecap="round" />
      <line x1={5} y1={hy - 4} x2={12} y2={hy - 4} stroke={color} strokeWidth={4} strokeLinecap="round" />
    </>
  ) : (
    <>
      <circle cx={-8} cy={hy - 4} r={4} fill={color} />
      <circle cx={9} cy={hy - 4} r={4} fill={color} />
    </>
  );
  const mouth =
    face === 'happy' ? (
      <path d={`M -10 ${hy + 9} Q 0 ${hy + 19} 11 ${hy + 9}`} stroke={color} strokeWidth={4} fill="none" strokeLinecap="round" />
    ) : face === 'shock' ? (
      <circle cx={1} cy={hy + 13} r={6} fill="none" stroke={color} strokeWidth={4} />
    ) : face === 'think' ? (
      <path d={`M -8 ${hy + 13} L 10 ${hy + 9}`} stroke={color} strokeWidth={4} strokeLinecap="round" />
    ) : face === 'smug' ? (
      <path d={`M -10 ${hy + 12} Q 4 ${hy + 16} 12 ${hy + 6}`} stroke={color} strokeWidth={4} fill="none" strokeLinecap="round" />
    ) : (
      <line x1={-8} y1={hy + 12} x2={9} y2={hy + 12} stroke={color} strokeWidth={4} strokeLinecap="round" />
    );
  return (
    <g transform={`translate(${x},${y}) scale(${flip ? -s : s},${s})`}>
      <g stroke={color} strokeWidth={sw} strokeLinecap="round" fill="none">
        <line x1={0} y1={hy + 28} x2={hip.x} y2={hip.y} />
        <line x1={sh.x} y1={sh.y} x2={lHand.x} y2={lHand.y} />
        <line x1={sh.x} y1={sh.y} x2={rHand.x} y2={rHand.y} />
        <line x1={hip.x} y1={hip.y} x2={lFoot.x} y2={lFoot.y} />
        <line x1={hip.x} y1={hip.y} x2={rFoot.x} y2={rFoot.y} />
      </g>
      <circle cx={0} cy={hy} r={28} fill={C.paper} stroke={color} strokeWidth={sw} />
      <g transform={flip ? `scale(-1,1)` : undefined}>{eyes}{mouth}</g>
      {hat && <g transform={`translate(0,${hy - 26})`}>{hat}</g>}
      {rightHand && <g transform={`translate(${rHand.x},${rHand.y})`}>{rightHand}</g>}
      {leftHand && <g transform={`translate(${lHand.x},${lHand.y})`}>{leftHand}</g>}
    </g>
  );
};

/* ---------- Props / icons (all original simple shapes) ---------- */
export const HotDog: React.FC<{s?: number}> = ({s = 1}) => (
  <g transform={`scale(${s}) rotate(-12)`}>
    <rect x={-46} y={-14} width={92} height={28} rx={14} fill="#E9B872" stroke={C.ink} strokeWidth={4} />
    <rect x={-52} y={-8} width={104} height={16} rx={8} fill="#C8553D" stroke={C.ink} strokeWidth={4} />
    <path d="M -36 0 q 8 -8 16 0 t 16 0 t 16 0 t 16 0" stroke={C.yellow} strokeWidth={4} fill="none" />
  </g>
);

export const Chicken: React.FC<{s?: number}> = ({s = 1}) => (
  <g transform={`scale(${s})`}>
    <ellipse cx={0} cy={0} rx={60} ry={40} fill="#D98E3F" stroke={C.ink} strokeWidth={5} />
    <path d="M 50 -10 l 30 -20 m -30 34 l 34 -6" stroke={C.ink} strokeWidth={8} strokeLinecap="round" />
    <circle cx={82} cy={-30} r={8} fill={C.paper} stroke={C.ink} strokeWidth={4} />
    <circle cx={86} cy={-2} r={8} fill={C.paper} stroke={C.ink} strokeWidth={4} />
    <path d="M -30 -15 q 15 -10 30 0" stroke="#F3C27A" strokeWidth={6} fill="none" strokeLinecap="round" />
  </g>
);

export const PriceTag: React.FC<{text: string; color?: string; w?: number; size?: number}> = ({text, color = C.yellow, w = 220, size = 64}) => (
  <g>
    <path
      d={`M ${-w / 2} -50 L ${w / 2 - 30} -50 L ${w / 2 + 20} 0 L ${w / 2 - 30} 50 L ${-w / 2} 50 Z`}
      fill={color}
      stroke={C.ink}
      strokeWidth={6}
      strokeLinejoin="round"
    />
    <circle cx={w / 2 - 20} cy={0} r={9} fill={C.bg} stroke={C.ink} strokeWidth={4} />
    <Txt x={-15} y={4} size={size}>
      {text}
    </Txt>
  </g>
);

export const Card: React.FC<{glow?: number; label?: string}> = ({glow = 0, label = 'MEMBER'}) => (
  <g>
    {glow > 0 && <rect x={-150} y={-95} width={300} height={190} rx={30} fill={C.yellow} opacity={0.35 * glow} />}
    <rect x={-130} y={-80} width={260} height={160} rx={18} fill={C.blue} stroke={C.ink} strokeWidth={6} />
    <rect x={-130} y={-45} width={260} height={30} fill={C.ink} opacity={0.8} />
    <rect x={-105} y={15} width={60} height={42} rx={6} fill={C.yellow} stroke={C.ink} strokeWidth={4} />
    <Txt x={50} y={38} size={30} color={C.paper}>
      {label}
    </Txt>
  </g>
);

export const Cart: React.FC<{s?: number}> = ({s = 1}) => (
  <g transform={`scale(${s})`} stroke={C.ink} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" fill="none">
    <path d="M -140 -110 L -100 -110 L -70 40 L 110 40 L 135 -70 L -88 -70" />
    <circle cx={-50} cy={85} r={18} fill={C.paper} />
    <circle cx={90} cy={85} r={18} fill={C.paper} />
  </g>
);

export const Wallet: React.FC<{s?: number}> = ({s = 1}) => (
  <g transform={`scale(${s})`}>
    <rect x={-170} y={-110} width={340} height={220} rx={26} fill="#8B5E3C" stroke={C.ink} strokeWidth={7} />
    <rect x={60} y={-35} width={130} height={70} rx={16} fill="#A47148" stroke={C.ink} strokeWidth={7} />
    <circle cx={110} cy={0} r={11} fill={C.yellow} stroke={C.ink} strokeWidth={4} />
  </g>
);

export const Coin: React.FC<{r?: number}> = ({r = 26}) => (
  <g>
    <circle r={r} fill={C.yellow} stroke={C.ink} strokeWidth={5} />
    <Txt x={0} y={2} size={r * 1.1}>
      $
    </Txt>
  </g>
);

export const Warehouse: React.FC<{s?: number; sign?: string; signColor?: string}> = ({s = 1, sign, signColor = C.red}) => (
  <g transform={`scale(${s})`}>
    <path d="M -330 120 L -330 -80 L 0 -170 L 330 -80 L 330 120 Z" fill="#DCD3C3" stroke={C.ink} strokeWidth={8} strokeLinejoin="round" />
    <rect x={-80} y={0} width={160} height={120} fill="#B9AE9B" stroke={C.ink} strokeWidth={7} />
    <line x1={0} y1={0} x2={0} y2={120} stroke={C.ink} strokeWidth={5} />
    {[-260, -170, 170, 260].map((xx) => (
      <rect key={xx} x={xx - 30} y={-30} width={60} height={50} fill={C.paper} stroke={C.ink} strokeWidth={5} />
    ))}
    {sign && (
      <g>
        <rect x={-230} y={-130} width={460} height={70} rx={10} fill={signColor} stroke={C.ink} strokeWidth={6} />
        <Txt x={0} y={-93} size={46} color={C.paper}>
          {sign}
        </Txt>
      </g>
    )}
  </g>
);

export const Arrow: React.FC<{x1: number; y1: number; x2: number; y2: number; p?: number; color?: string; w?: number}> = ({
  x1,
  y1,
  x2,
  y2,
  p = 1,
  color = C.ink,
  w = 8,
}) => {
  const ex = x1 + (x2 - x1) * p;
  const ey = y1 + (y2 - y1) * p;
  const a = Math.atan2(y2 - y1, x2 - x1);
  const h = 26;
  return (
    <g stroke={color} strokeWidth={w} strokeLinecap="round" fill="none" opacity={p > 0.01 ? 1 : 0}>
      <line x1={x1} y1={y1} x2={ex} y2={ey} />
      {p > 0.95 && (
        <path
          d={`M ${ex - h * Math.cos(a - 0.5)} ${ey - h * Math.sin(a - 0.5)} L ${ex} ${ey} L ${ex - h * Math.cos(a + 0.5)} ${ey - h * Math.sin(a + 0.5)}`}
          strokeLinejoin="round"
        />
      )}
    </g>
  );
};

export const fmtB = (v: number) => `$${v.toFixed(1)}B`;
