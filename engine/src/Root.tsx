import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Explainer} from './Explainer';
import type {Props} from './types';

const FPS = 30;

// Studio placeholder only; real renders always pass props.json via --props / inputProps.
const placeholder = (composition: Props['composition'], width: number, height: number): Props => ({
  composition,
  width,
  height,
  fps: FPS,
  duration_frames: 90,
  language: 'kk',
  voice: {src: '', volume: 1},
  music: null,
  progress_bar: true,
  sponsor_badge: null,
  scenes: [],
  captions: [{from: 0, to: 90, text: 'Props берілмеді: --props файлын беріңіз', keyword: 'props'}],
  sfx: [],
});

const calculateMetadata: CalculateMetadataFunction<Props> = ({props}) => ({
  durationInFrames: Math.max(1, Math.round(props.duration_frames)),
  fps: FPS,
});

export const Root: React.FC = () => (
  <>
    <Composition
      id="Explainer"
      component={Explainer}
      width={1920}
      height={1080}
      fps={FPS}
      durationInFrames={90}
      defaultProps={placeholder('Explainer', 1920, 1080)}
      calculateMetadata={calculateMetadata}
    />
    <Composition
      id="ExplainerShort"
      component={Explainer}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={90}
      defaultProps={placeholder('ExplainerShort', 1080, 1920)}
      calculateMetadata={calculateMetadata}
    />
  </>
);
