import React, {useMemo} from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {FontGate} from './fonts';
import {SceneView} from './scene';
import {C, FONT, StageCtx, lin, makeStage, resolveSrc, useStage} from './theme';
import type {Caption, Props} from './types';

const clean = (s: string, lang: string) =>
  s
    .normalize('NFC')
    .toLocaleLowerCase(lang)
    .replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');

/** Index of the first word whose letters start with the keyword stem (Kazakh suffixes still match: мұз → мұзды). */
export const keywordIndex = (words: string[], keyword: string, lang: string) => {
  const k = clean(keyword, lang);
  return k ? words.findIndex((w) => clean(w, lang).startsWith(k)) : -1;
};

const activeCaption = (caps: Caption[], f: number) => {
  let cur: Caption | undefined;
  for (const c of caps) if (f >= c.from && f < c.to && (!cur || c.from >= cur.from)) cur = c;
  return cur;
};

/** One phrase box at the bottom (above the progress bar; above the Shorts UI on 9:16), keyword on yellow. */
const Captions: React.FC<{caps: Caption[]; lang: string}> = ({caps, lang}) => {
  const f = useCurrentFrame();
  const st = useStage();
  const c = activeCaption(caps, f);
  if (!c) return null;
  const p = interpolate(f - c.from, [0, 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const words = c.text.split(/\s+/).filter(Boolean);
  const hi = keywordIndex(words, c.keyword, lang);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: st.short ? 400 : 46 * st.k}}>
      <div
        style={{
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: st.short ? 54 : 50 * st.k,
          lineHeight: 1.25,
          color: C.ink,
          background: 'rgba(255,253,248,0.94)',
          border: `${5 * st.k}px solid ${C.ink}`,
          borderRadius: 18 * st.k,
          padding: `${12 * st.k}px ${28 * st.k}px`,
          maxWidth: st.short ? 960 : 1500 * st.k,
          textAlign: 'center',
          opacity: p,
          transform: `translateY(${(1 - p) * 20}px)`,
        }}
      >
        {words.map((w, i) => (
          <React.Fragment key={i}>
            <span style={i === hi ? {background: C.yellow, padding: '0 8px', borderRadius: 8} : undefined}>{w}</span>
            {i < words.length - 1 ? ' ' : ''}
          </React.Fragment>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const Progress: React.FC = () => {
  const f = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const st = useStage();
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        [st.short ? 'top' : 'bottom']: 0,
        height: 8 * (st.short ? 1 : st.k),
        width: `${(f / Math.max(1, durationInFrames - 1)) * 100}%`,
        background: C.red,
      }}
    />
  );
};

const Sponsor: React.FC<{text: string; from: number; duration: number}> = ({text, from, duration}) => {
  const f = useCurrentFrame();
  const st = useStage();
  const o = Math.min(lin(f, from, from + 10), lin(f, from + duration - 10, from + duration, 1, 0));
  if (o <= 0) return null;
  return (
    <div
      style={{
        position: 'absolute',
        top: (st.short ? 120 : 40) * st.k,
        right: 40 * st.k,
        fontFamily: FONT,
        fontWeight: 700,
        fontSize: 28 * (st.short ? 1 : st.k),
        color: C.ink,
        background: C.paper,
        border: `${4 * st.k}px solid ${C.ink}`,
        borderRadius: 999,
        padding: '8px 22px',
        opacity: o,
      }}
    >
      {text}
    </div>
  );
};

/** Music gain: base volume while captions are on screen, +6 dB in pauses ≥ 0.8 s, with 6-frame (200 ms) ramps. */
const useMusicGain = (caps: Caption[], total: number, fps: number) =>
  useMemo(() => {
    const speech = new Uint8Array(total);
    for (const c of caps) for (let f = Math.max(0, c.from); f < Math.min(total, c.to); f++) speech[f] = 1;
    const gain = new Float32Array(total).fill(1);
    const minGap = Math.round(0.8 * fps);
    for (let f = 0; f < total; ) {
      if (speech[f]) {
        f++;
        continue;
      }
      let e = f;
      while (e < total && !speech[e]) e++;
      if (e - f >= minGap) for (let g = f; g < e; g++) gain[g] = 1 + Math.min(1, (g - f) / 6, (e - g) / 6);
      f = e;
    }
    return gain;
  }, [caps, total, fps]);

const Sound: React.FC<{p: Props}> = ({p}) => {
  const {durationInFrames, fps} = useVideoConfig();
  const gain = useMusicGain(p.captions, durationInFrames, fps);
  const music = p.music;
  return (
    <>
      {p.voice.src && <Audio src={resolveSrc(p.voice.src)} volume={p.voice.volume} trimBefore={p.voice.start_from ?? 0} />}
      {music?.src && (
        <Audio
          src={resolveSrc(music.src)}
          loop
          loopVolumeCurveBehavior="extend"
          trimBefore={music.start_from ?? 0}
          volume={(f) => music.volume * (gain[Math.min(gain.length - 1, Math.max(0, f))] ?? 1)}
        />
      )}
      {p.sfx
        .filter((s) => s.from < durationInFrames)
        .map((s, i) => (
          <Sequence key={i} from={s.from} durationInFrames={Math.min(2 * fps, durationInFrames - s.from)} layout="none" name={`sfx ${i}`}>
            <Audio src={resolveSrc(s.src)} volume={s.volume} />
          </Sequence>
        ))}
    </>
  );
};

export const Explainer: React.FC<Props> = (props) => {
  const {width, height} = useVideoConfig();
  const stage = useMemo(() => makeStage(width, height), [width, height]);
  return (
    <FontGate>
      <StageCtx.Provider value={stage}>
        <AbsoluteFill style={{background: C.bg, fontFamily: FONT}}>
          {props.scenes.map((s) => (
            <Sequence key={s.id} from={s.from} durationInFrames={Math.max(1, s.duration)} name={`scene ${s.id}`}>
              <SceneView scene={s} lang={props.language} />
            </Sequence>
          ))}
          <Captions caps={props.captions} lang={props.language} />
          {props.progress_bar !== false && <Progress />}
          {props.sponsor_badge && <Sponsor {...props.sponsor_badge} />}
          <Sound p={props} />
        </AbsoluteFill>
      </StageCtx.Provider>
    </FontGate>
  );
};
