import React from 'react';
import {Composition} from 'remotion';
import {Video, FPS, TOTAL} from './Video';
import {Popcorn, POP_FPS, POP_TOTAL} from './pop/Popcorn';
export const Root: React.FC = () => (
  <>
    <Composition id="Costco" component={Video} durationInFrames={TOTAL} fps={FPS} width={1920} height={1080} />
    <Composition id="Popcorn" component={Popcorn} durationInFrames={POP_TOTAL} fps={POP_FPS} width={1920} height={1080} />
  </>
);
