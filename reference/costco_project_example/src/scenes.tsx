import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {C, Txt, Stick, Pop, HotDog, Chicken, PriceTag, Card, Cart, Wallet, Coin, Warehouse, Arrow, lin, usePop, fmtB, FONT} from './kit';

const W = 1920;
const H = 1080;
const Floor = () => <line x1={0} y1={900} x2={W} y2={900} stroke={C.ink} strokeWidth={6} opacity={0.15} />;
const Title: React.FC<{t: string; delay?: number; y?: number; color?: string}> = ({t, delay = 0, y = 120, color = C.ink}) => {
  const p = usePop(delay, 14);
  return (
    <g opacity={p} transform={`translate(0,${(1 - p) * -30})`}>
      <Txt x={W / 2} y={y} size={64} color={color}>
        {t}
      </Txt>
    </g>
  );
};
const Svg: React.FC<{children: React.ReactNode}> = ({children}) => (
  <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
    {children}
  </svg>
);

/* 1. Hot dog price frozen since 1985 */
export const S1: React.FC = () => {
  const f = useCurrentFrame();
  const year = Math.round(interpolate(f, [90, 330], [1985, 2025], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const g = lin(f, 90, 330);
  // "everything else" line rising ~3x
  const pts = Array.from({length: 41}, (_, i) => {
    const t = i / 40;
    return [1050 + t * 700, 760 - (Math.pow(3.0, t) - 1) * 230];
  });
  const shown = pts.slice(0, Math.max(2, Math.floor(g * 41)));
  return (
    <Svg>
      <Floor />
      <Stick x={420} y={900} s={1.6} ra={115} face="happy" rightHand={<HotDog s={0.9} />} />
      <Pop delay={20} x={420} y={330}>
        <PriceTag text="$1.50" />
      </Pop>
      <g opacity={lin(f, 80, 100)}>
        <line x1={1050} y1={780} x2={1780} y2={780} stroke={C.ink} strokeWidth={5} />
        <line x1={1050} y1={780} x2={1050} y2={240} stroke={C.ink} strokeWidth={5} />
        <polyline points={shown.map((p) => p.join(',')).join(' ')} fill="none" stroke={C.red} strokeWidth={10} strokeLinecap="round" />
        <line x1={1050} y1={760} x2={1050 + 700 * g} y2={760} stroke={C.green} strokeWidth={10} strokeLinecap="round" />
        <Txt x={1780} y={260} size={34} color={C.red} anchor="end" opacity={lin(f, 300, 330)}>
          Everything else ≈ 3×
        </Txt>
        <Txt x={1780} y={720} size={34} color={C.green} anchor="end" opacity={lin(f, 300, 330)}>
          Hot dog: $1.50
        </Txt>
        <Txt x={1415} y={850} size={72}>
          {year}
        </Txt>
      </g>
    </Svg>
  );
};

/* 2. $8.1B profit question */
export const S2: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Svg>
      <Floor />
      <Stick x={560} y={900} s={1.6} ra={160} la={20} face="think" />
      <Pop delay={30} x={600} y={420}>
        <Txt x={0} y={0} size={140} color={C.blue}>
          ?
        </Txt>
      </Pop>
      <Pop delay={8} x={1250} y={470}>
        <g transform={`rotate(${-6 + Math.sin(f / 20) * 1.5})`}>
          <rect x={-330} y={-130} width={660} height={260} rx={20} fill="none" stroke={C.red} strokeWidth={14} />
          <Txt x={0} y={-30} size={130} color={C.red}>
            $8.1B
          </Txt>
          <Txt x={0} y={75} size={42} color={C.red}>
            PROFIT IN ONE YEAR
          </Txt>
        </g>
      </Pop>
    </Svg>
  );
};

/* 3. Not the cart — the wallet */
export const S3: React.FC = () => {
  const f = useCurrentFrame();
  const shift = lin(f, 10, 55);
  return (
    <Svg>
      <g transform={`translate(${-shift * 500},0)`}>
        <g opacity={1 - shift * 0.7} transform="translate(560,560)">
          <Cart s={1.6} />
          <line x1={-260} y1={-260} x2={260} y2={260} stroke={C.red} strokeWidth={14} opacity={lin(f, 40, 55)} strokeLinecap="round" />
        </g>
        <g transform="translate(1460,560)">
          <Wallet s={1.5} />
          <g transform={`translate(0,${-lin(f, 45, 90) * 230})`}>
            <Card glow={lin(f, 70, 110)} />
          </g>
        </g>
      </g>
    </Svg>
  );
};

/* 4. $269.9B sales bar */
export const S4: React.FC = () => {
  const f = useCurrentFrame();
  const g = lin(f, 40, 200);
  const val = 269.9 * g;
  return (
    <Svg>
      <Title t="Costco sales, fiscal year 2025" />
      <rect x={260} y={420} width={1400 * g} height={170} rx={14} fill={C.blue} stroke={C.ink} strokeWidth={6} />
      <Txt x={260 + 1400 * g + 20} y={505} size={72} anchor="start">
        {g > 0.02 ? fmtB(val) : ''}
      </Txt>
      {['TVs', 'Tires', 'Peanut butter', 'Paper towels', 'Sofas'].map((e, i) => (
        <Pop key={i} delay={220 + i * 25} x={420 + i * 260} y={760}>
          <circle r={80} fill={C.paper} stroke={C.ink} strokeWidth={6} />
          <Txt x={0} y={2} size={e.length > 6 ? 26 : 36}>
            {e}
          </Txt>
        </Pop>
      ))}
      <Stick x={150} y={980} s={1.0} la={150} ra={30} face="shock" />
    </Svg>
  );
};

/* 5. Thin markup -> almost nothing left */
export const S5: React.FC = () => {
  const f = useCurrentFrame();
  const drain = lin(f, 260, 440);
  return (
    <Svg>
      <Title t="Thin markup, thin margin" />
      <Pop delay={10} x={500} y={330}>
        <PriceTag text="≤ ~15%" color={C.green} w={300} size={56} />
        <Txt x={0} y={90} size={34}>
          Costco markup*
        </Txt>
      </Pop>
      <Pop delay={60} x={1400} y={330}>
        <PriceTag text="more" color={C.red} w={300} size={56} />
        <Txt x={0} y={90} size={34}>
          Typical supermarket
        </Txt>
      </Pop>
      {/* margin pot draining to costs */}
      <g opacity={lin(f, 200, 230)}>
        <rect x={810} y={560} width={300} height={260} rx={16} fill="none" stroke={C.ink} strokeWidth={7} />
        <rect x={816} y={566 + 248 * drain} width={288} height={Math.max(8, 248 * (1 - drain * 0.93))} fill={C.yellow} />
        <Txt x={960} y={860} size={34}>
          What's left
        </Txt>
        {[
          ['Staff', 330],
          ['Rent', 960 - 0],
          ['Trucks', 1590],
        ].map(([label, x], i) => {
          const fly = lin(f, 270 + i * 40, 330 + i * 40);
          return (
            <g key={i}>
              <g transform={`translate(${960 + ((x as number) - 960) * fly},${620 + (i === 1 ? 260 : 120) * fly})`} opacity={fly > 0 && fly < 1 ? 1 : 0}>
                <Coin />
              </g>
              <Txt x={x as number} y={i === 1 ? 960 : 800} size={40} opacity={lin(f, 300 + i * 40, 320 + i * 40)}>
                {label as string}
              </Txt>
            </g>
          );
        })}
      </g>
      <Txt x={W - 40} y={H - 40} size={24} color={C.grey} anchor="end" weight={500}>
        *widely reported, not an official disclosure
      </Txt>
    </Svg>
  );
};

/* 6. Report sheet, line 2 */
export const S6: React.FC = () => {
  const f = useCurrentFrame();
  const hl = lin(f, 40, 70);
  return (
    <Svg>
      <Pop delay={0} x={960} y={540}>
        <rect x={-420} y={-380} width={840} height={760} rx={12} fill={C.paper} stroke={C.ink} strokeWidth={6} />
        <Txt x={0} y={-310} size={40}>
          FY2025 RESULTS
        </Txt>
        <rect x={-380} y={-130} width={760 * hl} height={110} rx={10} fill={C.yellow} opacity={0.7} />
        {[
          ['Net sales', '$269.9B'],
          ['Membership fees', '$5.3B'],
          ['Total revenue', '$275.2B'],
          ['Net income', '$8.1B'],
        ].map(([a, b], i) => (
          <g key={i}>
            <Txt x={-350} y={-200 + i * 125} size={44} anchor="start" weight={i === 1 ? 900 : 600}>
              {a}
            </Txt>
            <Txt x={350} y={-200 + i * 125} size={44} anchor="end" weight={i === 1 ? 900 : 600}>
              {b}
            </Txt>
          </g>
        ))}
        <Txt x={0} y={330} size={24} color={C.grey} weight={500}>
          Source: Costco FY2025 results (52 weeks ended Aug 31, 2025)
        </Txt>
      </Pop>
    </Svg>
  );
};

/* 7. Fees vs profit ≈ 2/3 */
export const S7: React.FC = () => {
  const f = useCurrentFrame();
  const g1 = lin(f, 20, 90);
  const g2 = lin(f, 60, 140);
  const maxH = 520;
  const hFee = (5.3 / 8.1) * maxH;
  return (
    <Svg>
      <Floor />
      <rect x={560} y={850 - hFee * g1} width={260} height={hFee * g1} fill={C.blue} stroke={C.ink} strokeWidth={6} />
      <rect x={960} y={850 - maxH * g2} width={260} height={maxH * g2} fill={C.green} stroke={C.ink} strokeWidth={6} />
      <Txt x={690} y={850 - hFee * g1 - 45} size={56} opacity={g1}>
        $5.3B
      </Txt>
      <Txt x={1090} y={850 - maxH * g2 - 45} size={56} opacity={g2}>
        $8.1B
      </Txt>
      <Txt x={690} y={900} size={36}>
        Membership fees
      </Txt>
      <Txt x={1090} y={900} size={36}>
        Total profit
      </Txt>
      <Pop delay={170} x={1520} y={330}>
        <circle r={130} fill={C.yellow} stroke={C.ink} strokeWidth={7} />
        <Txt x={0} y={0} size={96}>
          ≈⅔
        </Txt>
      </Pop>
      <Stick x={300} y={900} s={1.3} ra={115} face="smug" />
      <g opacity={lin(f, 330, 360)}>
        {['no shelves', 'no inventory', 'no spoiled food'].map((t, i) => (
          <g key={i}>
            <Txt x={1520} y={560 + i * 70} size={38} color={C.grey} weight={700}>
              {t}
            </Txt>
            <line x1={1400} y1={560 + i * 70} x2={1400 + 240 * lin(f, 360 + i * 25, 380 + i * 25)} y2={560 + i * 70} stroke={C.red} strokeWidth={6} />
          </g>
        ))}
        <Txt x={1520} y={790} size={46} color={C.blue} opacity={lin(f, 460, 490)}>
          just a card
        </Txt>
      </g>
    </Svg>
  );
};

/* 8. Store -> Club */
export const S8: React.FC = () => {
  const f = useCurrentFrame();
  const m = lin(f, 90, 140);
  return (
    <Svg>
      <Floor />
      <g transform="translate(960,700)">
        <Warehouse s={1.2} sign={m < 0.5 ? 'STORE' : 'CLUB'} signColor={m < 0.5 ? C.grey : C.red} />
      </g>
      <g opacity={m}>
        {[620, 1300].map((x) => (
          <g key={x}>
            <rect x={x - 10} y={760} width={20} height={140} fill="#C9A227" stroke={C.ink} strokeWidth={4} />
            <circle cx={x} cy={755} r={16} fill={C.yellow} stroke={C.ink} strokeWidth={4} />
          </g>
        ))}
        <path d="M 620 790 Q 960 880 1300 790" stroke={C.red} strokeWidth={16} fill="none" />
      </g>
      <Stick x={1500} y={900} s={1.3} la={20} ra={120} face="neutral" rightHand={<g transform="scale(0.35)"><Card /></g>} />
      <Stick x={380} y={900} s={1.3} face="happy" seed={3} />
    </Svg>
  );
};

/* 9. Proof items */
export const S9: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Svg>
      <Floor />
      {[
        {x: 620, el: <HotDog s={1.4} />, price: '$1.50', d: 0},
        {x: 1300, el: <Chicken s={1.3} />, price: '$4.99', d: 70},
      ].map((o, i) => (
        <Pop key={i} delay={o.d} x={o.x} y={0}>
          <rect x={-170} y={700} width={340} height={200} fill="#E7DFD0" stroke={C.ink} strokeWidth={6} />
          <Txt x={0} y={800} size={48} color={C.red}>
            PROOF
          </Txt>
          <g transform="translate(0,580)">{o.el}</g>
          <g transform="translate(0,420) scale(0.7)">
            <PriceTag text={o.price} />
          </g>
        </Pop>
      ))}
      <g opacity={lin(f, 280, 310)} transform={`translate(960,${150 + Math.sin(f / 25) * 4})`}>
        <rect x={-560} y={-75} width={1120} height={150} rx={14} fill={C.paper} stroke={C.ink} strokeWidth={7} />
        <Txt x={0} y={0} size={56}>
          "Your membership pays for itself"
        </Txt>
      </g>
    </Svg>
  );
};

/* 10. Fee raise, people still pay */
export const S10: React.FC = () => {
  const f = useCurrentFrame();
  const flip = lin(f, 50, 80);
  return (
    <Svg>
      <Floor />
      <g transform="translate(960,280)">
        <g transform={`scale(1,${Math.abs(1 - 2 * flip)})`}>
          <PriceTag text={flip < 0.5 ? '$60' : '$65'} color={flip < 0.5 ? C.yellow : C.red} />
        </g>
        <Txt x={0} y={100} size={34} opacity={lin(f, 80, 100)}>
          Basic card, fee raised in 2024
        </Txt>
      </g>
      {[0, 1, 2, 3, 4].map((i) => {
        const shrug = lin(f, 140 + i * 20, 160 + i * 20);
        return (
          <Stick
            key={i}
            x={460 + i * 250}
            y={920}
            s={1.0}
            la={25 + shrug * 95}
            ra={25 + shrug * 95}
            face={shrug > 0.5 ? 'smug' : 'neutral'}
            seed={i}
          />
        );
      })}
      <g opacity={lin(f, 260, 290)}>
        {[0, 1, 2, 3, 4].map((i) => (
          <g key={i} transform={`translate(${460 + i * 250},${640 - ((f + i * 13) % 50)})`} opacity={0.9}>
            <Coin r={20} />
          </g>
        ))}
      </g>
    </Svg>
  );
};

/* 11. The loop */
export const S11: React.FC = () => {
  const f = useCurrentFrame();
  const nodes = [
    {t: 'Low prices', x: 960, y: 220, c: C.green},
    {t: 'Card feels valuable', x: 1460, y: 540, c: C.blue},
    {t: 'More renewals', x: 960, y: 860, c: C.yellow},
    {t: 'More fees', x: 460, y: 540, c: C.red},
  ];
  const rot = lin(f, 300, 540) * 360;
  return (
    <Svg>
      <g transform={`rotate(${rot} 960 540)`} opacity={lin(f, 280, 300) * 0.25}>
        <circle cx={960} cy={540} r={330} fill="none" stroke={C.ink} strokeWidth={4} strokeDasharray="20 20" />
      </g>
      {nodes.map((n, i) => {
        const nx = nodes[(i + 1) % 4];
        const p = lin(f, 40 + i * 60 + 30, 40 + i * 60 + 60);
        const dx = nx.x - n.x;
        const dy = nx.y - n.y;
        const len = Math.hypot(dx, dy);
        const ux = dx / len;
        const uy = dy / len;
        return (
          <g key={i}>
            <Arrow x1={n.x + ux * 200} y1={n.y + uy * 120} x2={nx.x - ux * 200} y2={nx.y - uy * 120} p={p} />
            <Pop delay={40 + i * 60} x={n.x} y={n.y}>
              <rect x={-230} y={-60} width={460} height={120} rx={60} fill={n.c} stroke={C.ink} strokeWidth={6} />
              <Txt x={0} y={2} size={44}>
                {n.t}
              </Txt>
            </Pop>
          </g>
        );
      })}
      <Stick x={960} y={640} s={0.9} la={140} ra={140} face="happy" />
    </Svg>
  );
};

/* 12. Split */
export const S12: React.FC = () => (
  <Svg>
    <rect x={0} y={0} width={960} height={H} fill="#EDE5D6" />
    <line x1={960} y1={60} x2={960} y2={1020} stroke={C.ink} strokeWidth={6} />
    <Pop delay={0} x={480} y={0}>
      <Txt x={0} y={260} size={48} color={C.grey}>
        Normal store wins when…
      </Txt>
      <Txt x={0} y={360} size={72}>
        you spend more
      </Txt>
      <g transform="translate(0,720)">
        <Cart s={1.1} />
      </g>
    </Pop>
    <Pop delay={30} x={1440} y={0}>
      <Txt x={0} y={260} size={48} color={C.grey}>
        Costco wins when…
      </Txt>
      <Txt x={0} y={360} size={72} color={C.blue}>
        you come back
      </Txt>
      <g transform="translate(0,720) scale(0.9)">
        <Card />
        <path d="M 170 -60 A 120 120 0 1 1 170 60" stroke={C.ink} strokeWidth={8} fill="none" />
        <path d="M 160 40 L 172 66 L 196 52" stroke={C.ink} strokeWidth={8} fill="none" strokeLinecap="round" />
      </g>
    </Pop>
  </Svg>
);

/* 13. The catch: overbuying */
export const S13: React.FC = () => {
  const f = useCurrentFrame();
  const items = [
    {t: '48 batteries', c: C.yellow},
    {t: '3 lb spinach', c: C.green},
    {t: '40 rolls', c: C.paper},
    {t: '10 lb rice', c: '#E8D9B5'},
    {t: '2 gal mayo', c: '#F7F1D0'},
  ];
  return (
    <Svg>
      <Floor />
      <g transform="translate(1100,780)">
        <Cart s={1.8} />
      </g>
      {items.map((it, i) => {
        const p = usePop(80 + i * 55, 10);
        const x = 1000 + (i % 3) * 140 - 40;
        const y = 600 - Math.floor(i / 3) * 110 - i * 8;
        return (
          <g key={i} transform={`translate(${x},${y - (1 - p) * 400}) rotate(${(i % 2 ? 1 : -1) * 6})`} opacity={p}>
            <rect x={-110} y={-45} width={220} height={90} rx={10} fill={it.c} stroke={C.ink} strokeWidth={5} />
            <Txt x={0} y={2} size={30}>
              {it.t}
            </Txt>
          </g>
        );
      })}
      <Stick x={480} y={900} s={1.5} ra={60} la={30} face="shock" />
      <g opacity={lin(f, 20, 40)}>
        <ellipse cx={560} cy={300} rx={260} ry={110} fill={C.paper} stroke={C.ink} strokeWidth={6} />
        <circle cx={520} cy={450} r={18} fill={C.paper} stroke={C.ink} strokeWidth={5} />
        <circle cx={500} cy={500} r={10} fill={C.paper} stroke={C.ink} strokeWidth={4} />
        <Txt x={560} y={300} size={44}>
          "$65… gotta use it"
        </Txt>
      </g>
    </Svg>
  );
};

/* 14. Subscription with a warehouse attached */
export const S14: React.FC = () => {
  const p = usePop(40, 9);
  return (
    <Svg>
      <Floor />
      <g transform="translate(960,740)">
        <Warehouse s={1.3} />
      </g>
      <g transform={`translate(960,${-200 + p * 500})`}>
        <rect x={-430} y={-70} width={860} height={140} rx={16} fill={C.blue} stroke={C.ink} strokeWidth={8} />
        <Txt x={0} y={4} size={80} color={C.paper}>
          SUBSCRIPTION
        </Txt>
      </g>
      <Stick x={260} y={900} s={1.2} ra={140} face="smug" />
    </Svg>
  );
};

/* 15. Callback: best ad ever */
export const S15: React.FC = () => {
  const f = useCurrentFrame();
  const flip = lin(f, 120, 150);
  return (
    <Svg>
      <Floor />
      <Stick x={600} y={900} s={1.6} ra={115} face="smug" rightHand={<HotDog s={0.9} />} />
      <g transform={`translate(1240,420) scale(1,${Math.abs(1 - 2 * flip)})`}>
        {flip < 0.5 ? <PriceTag text="$1.50" /> : <PriceTag text="BEST AD EVER" color={C.red} w={560} size={58} />}
      </g>
    </Svg>
  );
};

/* 16. End screen */
export const S16: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Svg>
      <Floor />
      <Txt x={960} y={140} size={56}>
        How do other companies really make money?
      </Txt>
      <Pop delay={10} x={1150} y={520}>
        <rect x={-380} y={-215} width={760} height={430} rx={22} fill="#E2DACB" stroke={C.ink} strokeWidth={7} strokeDasharray="22 14" />
        <Txt x={0} y={0} size={44} color={C.grey}>
          next video
        </Txt>
      </Pop>
      <Stick x={460} y={900} s={1.5} ra={80 + Math.sin(f / 8) * 6} face="happy" />
      <Txt x={960} y={1010} size={28} color={C.grey} weight={500}>
        Sources in the description
      </Txt>
    </Svg>
  );
};

export const SCENES = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16];
export {FONT};
