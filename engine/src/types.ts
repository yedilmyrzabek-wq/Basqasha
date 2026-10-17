// Mirrors /schemas/props.schema.json. All frames are absolute except inside a scene (scene-relative).
export type Color = 'ink' | 'red' | 'blue' | 'green' | 'yellow';

export type AudioTrack = {src: string; volume: number; start_from?: number};

export type Pose = {at: number; pose: string; src: string; width: number; height: number; scale?: number};

export type Character = {x: number; y: number; height: number; flip: boolean; schedule: Pose[]};

export type Overlay = {
  type: 'label' | 'counter' | 'arrow' | 'coins' | 'stamp' | 'note';
  at: number;
  x?: number;
  y?: number;
  x2?: number;
  y2?: number;
  color?: Color;
  text?: string;
  value?: number;
  from?: number;
  prefix?: string;
  suffix?: string;
  count?: number;
};

export type Scene = {
  id: number;
  from: number;
  duration: number;
  background: {src: string; zoom_from: number; zoom_to: number; focus: number[]; punch?: number[]};
  character?: Character | null;
  overlays?: Overlay[];
};

export type Caption = {from: number; to: number; text: string; keyword: string};

export type Props = {
  composition: 'Explainer' | 'ExplainerShort';
  width: number;
  height: number;
  fps: number;
  duration_frames: number;
  language: 'kk' | 'ru' | 'en';
  voice: AudioTrack;
  music?: AudioTrack | null;
  progress_bar?: boolean;
  sponsor_badge?: {text: string; from: number; duration: number} | null;
  scenes: Scene[];
  captions: Caption[];
  sfx: {src: string; from: number; volume: number}[];
};
