import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate} from 'remotion';
import {C, FONT} from './kit';
import {SCENES} from './scenes';
import starts from './scenes.json';

export const FPS = 30;
export const DURATION_S = 198.6;
export const TOTAL = Math.ceil(DURATION_S * FPS);

const Fade: React.FC<{len: number; children: React.ReactNode}> = ({len, children}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 8, len - 6, len], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const y = interpolate(f, [0, 10], [18, 0], {extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{opacity: o, transform: `translateY(${y}px)`}}>{children}</AbsoluteFill>;
};

export const Video: React.FC = () => {
  const f = useCurrentFrame();
  const s = starts as number[];
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: FONT}}>
      <Audio src={staticFile('voice.mp3')} />
      {SCENES.map((Scene, i) => {
        const from = Math.round(s[i] * FPS);
        const to = i + 1 < s.length ? Math.round(s[i + 1] * FPS) : TOTAL;
        return (
          <Sequence key={i} from={from} durationInFrames={to - from}>
            <Fade len={to - from}>
              <Scene />
            </Fade>
          </Sequence>
        );
      })}
      <div style={{position: 'absolute', left: 0, bottom: 0, height: 8, width: `${(f / TOTAL) * 100}%`, background: C.red}} />
    </AbsoluteFill>
  );
};
