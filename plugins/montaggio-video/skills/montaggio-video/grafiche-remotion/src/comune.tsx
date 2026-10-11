import React from 'react';
import {continueRender, delayRender, spring, staticFile} from 'remotion';

// Font Geist dalla cartella public/fonts (copiati da assets/fonts della skill).
const PESI: [string, string][] = [['400', 'Regular'], ['600', 'SemiBold'], ['700', 'Bold'], ['800', 'ExtraBold']];
if (typeof window !== 'undefined' && typeof FontFace !== 'undefined') {
  const h = delayRender('font Geist');
  Promise.all(PESI.map(([w, n]) => new FontFace('Geist', `url(${staticFile(`fonts/Geist-${n}.ttf`)})`, {weight: w}).load()
    .then((f) => (document.fonts as any).add(f))))
    .then(() => continueRender(h))
    .catch(() => continueRender(h));
}

// Proprietà comuni a tutte le grafiche. I colori vengono dal profilo dell'utente.
export type Stile = {
  font?: string;        // famiglia di caratteri
  colore?: string;      // testo
  accento?: string;     // evidenziazioni, frecce, barre
  sfondo?: string;      // fondo di pillole ed etichette
  contorno?: string;    // contorno del testo sui video
};
export type Base = {larghezza: number; altezza: number; fps: number; durata: number; stile?: Stile};

export const STILE_BASE: Required<Stile> = {
  font: 'Geist', colore: '#0B0B0B', accento: '#FF5A1F', sfondo: '#FFFFFF', contorno: '#0B0B0B',
};
export const stile = (s?: Stile): Required<Stile> => ({...STILE_BASE, ...(s || {})});

// Molla morbida con un filo di rimbalzo al massimo (regola dello stile base: niente rimbalzi vistosi).
export const entra = (frame: number, fps: number, ritardo = 0, durezza = 170) =>
  spring({frame: frame - ritardo, fps, config: {damping: 18, stiffness: durezza, mass: 0.9}});

export const esce = (frame: number, fps: number, totale: number, durata = 0.25) => {
  const f0 = totale - Math.round(durata * fps);
  return frame < f0 ? 1 : Math.max(0, 1 - (frame - f0) / (totale - f0));
};

// Posizione in frazioni del fotogramma (0-1) -> pixel.
export const px = (v: number, lato: number) => (v <= 1 ? v * lato : v);

export const ombraTesto = (contorno: string, spessore: number) =>
  Array.from({length: 16}, (_, i) => {
    const a = (i / 16) * Math.PI * 2;
    return `${(Math.cos(a) * spessore).toFixed(1)}px ${(Math.sin(a) * spessore).toFixed(1)}px 0 ${contorno}`;
  }).join(',');

export const Contenitore: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div style={{position: 'absolute', inset: 0, backgroundColor: 'transparent', overflow: 'hidden'}}>{children}</div>
);
