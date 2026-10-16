import {createContext, useContext} from 'react';
import {Easing, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Color} from './types';

export const C = {
  bg: '#F6F1E7',
  ink: '#1F1F24',
  red: '#E4572E',
  blue: '#2E86AB',
  green: '#3BA55C',
  yellow: '#F2C14E',
  grey: '#6F6A62',
  paper: '#FFFDF8',
};
export const FONT = "Inter, 'Helvetica Neue', Arial, sans-serif";
export const DISPLAY = "Rubik, Inter, Arial, sans-serif";

export const color = (c: Color | undefined, fallback: string = C.ink): string => (c ? C[c] : fallback);

/** http(s) URLs are used as-is (backend /files/...); anything else is a path inside engine/public. */
export const resolveSrc = (src: string): string => (/^https?:\/\//i.test(src) ? src : staticFile(src));

export const lin = (f: number, a: number, b: number, from = 0, to = 1) =>
  interpolate(f, [a, b], [from, to], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });

export const usePop = (delay = 0, damping = 12) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: f - delay, fps, config: {damping, mass: 0.6}});
};

/**
 * Storyboard coordinates are authored for a 1920x1080 frame. The 16:9 stage is identity;
 * the 9:16 Short squeezes x into the narrow frame, spreads y over the tall one and scales elements by k.
 */
export type Stage = {W: number; H: number; short: boolean; k: number; px: (x: number) => number; py: (y: number) => number};
export const makeStage = (W: number, H: number): Stage =>
  H > W
    ? {W, H, short: true, k: 1, px: (x) => W / 2 + (x - 960) * (W / 1920), py: (y) => 180 + y * 1.11}
    : {W, H, short: false, k: W / 1920, px: (x) => (x * W) / 1920, py: (y) => (y * H) / 1080};
export const StageCtx = createContext<Stage>(makeStage(1920, 1080));
export const useStage = () => useContext(StageCtx);

export const clamp = (v: number, lo: number, hi: number) => (lo > hi ? (lo + hi) / 2 : Math.min(hi, Math.max(lo, v)));
