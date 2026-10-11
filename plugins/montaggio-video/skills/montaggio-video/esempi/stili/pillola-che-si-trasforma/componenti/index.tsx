import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Base, Contenitore, stile} from '../../comune';
import type {SuMisura} from '../../su-misura';

// Stile "pillola che si trasforma": un'unica forma che non taglia mai (pillola -> scheda -> selettore),
// molle con entrata veloce e frenata (~0,6 s), contenuto che si scambia con una breve sfocatura,
// indicatore del selettore che scorre. Colori e testi dal profilo.
type Props = Base & {
  pillola: string; scheda: {titolo: string; sottotitolo: string}; voci: string[];
  tempi?: {scheda: number; selettore: number}; passiVoce?: number[];
};
const molla = (f: number, fps: number, da: number) => spring({frame: f - da, fps, config: {damping: 16, stiffness: 140, mass: 1}});

const PillolaCheSiTrasforma: React.FC<Props> = (p) => {
  const f = useCurrentFrame(); const {fps, width, height} = useVideoConfig(); const s = stile(p.stile);
  const t1 = Math.round((p.tempi?.scheda ?? 2.2) * fps), t2 = Math.round((p.tempi?.selettore ?? 4.1) * fps);
  const u = height / 1080;
  const S = [{w: 440, h: 120, r: 60, bg: s.colore}, {w: 840, h: 300, r: 44, bg: s.sfondo}, {w: 920, h: 124, r: 62, bg: s.sfondo}];
  const a1 = molla(f, fps, t1), a2 = molla(f, fps, t2);
  const mix = (k: 'w' | 'h' | 'r') => S[0][k] + (S[1][k] - S[0][k]) * a1 + (S[2][k] - S[1][k]) * a2;
  const entrata = spring({frame: f - 3, fps, config: {damping: 12, stiffness: 180}});
  const vis = (da: number, a?: number) => {
    const inn = interpolate(f, [da + 2, da + 9], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    const out = a === undefined ? 0 : interpolate(f, [a, a + 4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    const o = inn * (1 - out); return {opacity: o, filter: `blur(${((1 - inn) * 12 + out * 10).toFixed(1)}px)`};
  };
  // L'indicatore del selettore avanza di una voce a ogni tempo di passiVoce, ognuno con la sua molla.
  const passi = p.passiVoce ?? [4.5, 4.85, 5.3];
  let pos = 0; passi.forEach((ts) => { pos += molla(f, fps, Math.round(ts * fps)); });
  const larg = mix('w'), alt = mix('h'), raggio = Math.min(mix('r'), alt / 2);
  const fondo = a1 < 0.5 ? S[0].bg : S[1].bg;
  const cella = (S[2].w - 24) / Math.max(1, p.voci.length);
  return (
    <Contenitore>
      <div style={{position: 'absolute', left: '50%', top: '50%', width: larg * u * 1.5, height: alt * u * 1.5, borderRadius: raggio * u * 1.5,
        transform: `translate(-50%,-50%) scale(${0.55 + 0.45 * entrata})`, background: fondo, overflow: 'hidden', fontFamily: s.font,
        boxShadow: '0 10px 30px -8px rgba(0,0,0,.25)'}}>
        <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 * u,
          color: s.sfondo, fontSize: 48 * u * 1.5, fontWeight: 600, ...vis(0, t1)}}>
          <span style={{color: s.accento}}>✦</span>{p.pillola}
        </div>
        <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', gap: 32 * u, padding: `0 ${50 * u}px`, ...vis(t1, t2)}}>
          <div style={{width: 190 * u, height: 190 * u, borderRadius: 38 * u, background: s.accento, flex: 'none'}} />
          <div><div style={{fontSize: 54 * u * 1.3, fontWeight: 700, color: s.colore}}>{p.scheda.titolo}</div>
            <div style={{fontSize: 25 * u * 1.3, color: '#8A8782'}}>{p.scheda.sottotitolo}</div></div>
        </div>
        <div style={{position: 'absolute', inset: 0, ...vis(t2)}}>
          <div style={{position: 'absolute', top: 12 * u * 1.5, bottom: 12 * u * 1.5, left: (12 + pos * cella) * u * 1.5, width: cella * u * 1.5,
            borderRadius: 999, background: s.colore}} />
          {p.voci.map((v, i) => (
            <div key={i} style={{position: 'absolute', top: 0, bottom: 0, left: (12 + i * cella) * u * 1.5, width: cella * u * 1.5, display: 'flex',
              alignItems: 'center', justifyContent: 'center', fontSize: 30 * u * 1.5, fontWeight: 500,
              color: Math.abs(pos - i) < 0.5 ? s.sfondo : s.colore}}>{v}</div>))}
        </div>
      </div>
    </Contenitore>
  );
};

export const COMPOSIZIONI: SuMisura[] = [
  {id: 'PillolaCheSiTrasforma', component: PillolaCheSiTrasforma,
   defaultProps: {larghezza: 1920, altezza: 1080, fps: 30, durata: 6.2, pillola: 'Novità', scheda: {titolo: 'Titolo', sottotitolo: 'sottotitolo'}, voci: ['A', 'B', 'C', 'D']}},
];
