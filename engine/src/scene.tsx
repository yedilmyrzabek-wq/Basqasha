import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, resolveSrc, useStage} from './theme';
import type {Stage} from './theme';
import type {Character, Scene} from './types';
import {Overlays} from './overlays';
import type {Box} from './overlays';

/** Full-frame background: Ken Burns zoom_from→zoom_to around `focus`, plus spring punch-ins (+5%, decays over 40 frames). */
const Bg: React.FC<{bg: Scene['background']; len: number}> = ({bg, len}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  let z = interpolate(f, [0, len], [bg.zoom_from, bg.zoom_to], {extrapolateRight: 'clamp'});
  for (const p of bg.punch ?? []) z += 0.05 * spring({frame: f - p, fps, config: {damping: 14}}) * Math.max(0, 1 - (f - p) / 40);
  const [fx, fy] = bg.focus;
  const origin = `${fx * 100}% ${fy * 100}%`;
  return (
    <AbsoluteFill style={{transform: `scale(${z})`, transformOrigin: origin}}>
      <Img src={resolveSrc(bg.src)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: origin}} />
    </AbsoluteFill>
  );
};

/**
 * Mascot from the pose library. x = centre, y = feet line, height in px (1920x1080 units).
 * On every pose change: squash & stretch spring; always: slow breathing. All poses of the scene are mounted
 * (hidden) so they are loaded before they are needed.
 */
const Char: React.FC<{c: Character}> = ({c}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const st = useStage();
  let cur = c.schedule[0];
  for (const s of c.schedule) if (f >= s.at) cur = s;
  // scale: figure height relative to a standing pose (lying / sitting poses are shorter)
  const h = c.height * st.k * (cur.scale ?? 1);
  const w = (h * cur.width) / cur.height;
  const x = st.px(c.x);
  const y = st.py(c.y);
  const pop = spring({frame: f - cur.at, fps, config: {damping: 9, mass: 0.5}});
  const sx = 0.85 + 0.15 * pop;
  const sy = (1.12 - 0.12 * pop) * (1 + 0.012 * Math.sin(f / 8));
  const srcs = [...new Set(c.schedule.map((s) => s.src))];
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: x - w * 0.35,
          top: y - 14,
          width: w * 0.7,
          height: 28,
          borderRadius: '50%',
          background: C.ink,
          opacity: 0.12,
          transform: `scaleX(${sx})`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: x - w / 2,
          top: y - h,
          width: w,
          height: h,
          transformOrigin: '50% 100%',
          transform: `scale(${c.flip ? -sx : sx}, ${sy})`,
        }}
      >
        {srcs.map((src) => (
          <Img
            key={src}
            src={resolveSrc(src)}
            style={{position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: src === cur.src ? 1 : 0}}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

/** Widest pose of the schedule, in screen space (feet line = bottom). */
const charBox = (c: Character, st: Stage): Box => {
  const base = c.height * st.k;
  const w = Math.max(...c.schedule.map((s) => (base * (s.scale ?? 1) * s.width) / s.height));
  const h = Math.max(...c.schedule.map((s) => base * (s.scale ?? 1)));
  const x = st.px(c.x);
  const y = st.py(c.y);
  return {l: x - w / 2, r: x + w / 2, t: y - h, b: y};
};

/** One scene inside its <Sequence>: fade-in from the paper colour, background, character, overlays. */
export const SceneView: React.FC<{scene: Scene; lang: string}> = ({scene, lang}) => {
  const f = useCurrentFrame();
  const st = useStage();
  const ch = scene.character && scene.character.schedule.length > 0 ? scene.character : null;
  const o = interpolate(f, [0, 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{opacity: o, overflow: 'hidden'}}>
      <Bg bg={scene.background} len={scene.duration} />
      {ch && <Char c={ch} />}
      <Overlays items={scene.overlays ?? []} lang={lang} avoid={ch ? charBox(ch, st) : null} />
    </AbsoluteFill>
  );
};
