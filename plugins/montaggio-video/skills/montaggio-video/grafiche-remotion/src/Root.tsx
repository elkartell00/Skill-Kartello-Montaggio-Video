import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Barra, Emoji, Freccia, Scritta, Sottotitoli, Titolo} from './grafiche';
import {Base} from './comune';

// Dimensioni, fps e durata arrivano dalle proprietà (--props), così ogni grafica nasce già della
// misura del video in cui va: 3840x2160 per il video lungo, 1080x1920 per shorts e reels.
const metadati: CalculateMetadataFunction<Base> = ({props}) => ({
  durationInFrames: Math.max(1, Math.round(props.durata * props.fps)),
  fps: props.fps,
  width: props.larghezza,
  height: props.altezza,
});

const BASE: Base = {larghezza: 1920, altezza: 1080, fps: 30, durata: 3};

export const Root: React.FC = () => (
  <>
    <Composition id="Titolo" component={Titolo as any} calculateMetadata={metadati as any} durationInFrames={90} fps={30} width={1920} height={1080}
      defaultProps={{...BASE, testo: 'Titolo di prova', sottotitolo: 'sottotitolo', posizione: 'centro', entrata: 'pop'}} />
    <Composition id="Scritta" component={Scritta as any} calculateMetadata={metadati as any} durationInFrames={90} fps={30} width={1920} height={1080}
      defaultProps={{...BASE, testo: 'Scritta di prova', x: 0.5, y: 0.8, forma: 'pillola'}} />
    <Composition id="Freccia" component={Freccia as any} calculateMetadata={metadati as any} durationInFrames={90} fps={30} width={1920} height={1080}
      defaultProps={{...BASE, da: [0.3, 0.3], a: [0.6, 0.6]}} />
    <Composition id="Emoji" component={Emoji as any} calculateMetadata={metadati as any} durationInFrames={90} fps={30} width={1920} height={1080}
      defaultProps={{...BASE, emoji: '🔥'}} />
    <Composition id="Barra" component={Barra as any} calculateMetadata={metadati as any} durationInFrames={90} fps={30} width={1920} height={1080}
      defaultProps={{...BASE, posizione: 'basso'}} />
    <Composition id="Sottotitoli" component={Sottotitoli as any} calculateMetadata={metadati as any} durationInFrames={90} fps={30} width={1080} height={1920}
      defaultProps={{...BASE, larghezza: 1080, altezza: 1920, parole: [{w: 'Prova', inizio: 0.1, fine: 0.5}, {w: 'dei', inizio: 0.5, fine: 0.7}, {w: 'sottotitoli', inizio: 0.7, fine: 1.4}]}} />
  </>
);
