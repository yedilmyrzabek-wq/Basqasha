import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';

// Full TTFs (no subsetting) so every Kazakh letter (cyrillic-ext: ә ғ қ ң ө ү һ) is present.
const FONTS: [family: string, file: string, weight: string][] = [
  ['Inter', 'fonts/Inter.ttf', '100 900'],
  ['Rubik', 'fonts/Rubik.ttf', '300 900'],
];

let loading: Promise<void> | null = null;
const loadFonts = () =>
  (loading ??= Promise.all(
    FONTS.map(async ([family, file, weight]) => {
      const face = new FontFace(family, `url(${staticFile(file)}) format('truetype')`, {weight});
      await face.load();
      document.fonts.add(face);
    }),
  ).then(() => undefined));

/** Renders children only after the fonts are loaded, so text measurement is exact. */
export const FontGate: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [ready, setReady] = useState(false);
  const [handle] = useState(() => delayRender('Loading fonts'));
  useEffect(() => {
    loadFonts()
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [handle]);
  return ready ? <>{children}</> : null;
};
