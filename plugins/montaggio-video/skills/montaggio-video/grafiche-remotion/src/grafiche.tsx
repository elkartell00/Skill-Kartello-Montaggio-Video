import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Base, Contenitore, entra, esce, ombraTesto, px, stile} from './comune';

// Tutte le grafiche hanno lo sfondo trasparente: si renderizzano in ProRes 4444 e si sovrappongono al video.
// Dimensioni del testo in frazioni dell'altezza (0.06 = 6% dell'altezza del video), così vanno bene a ogni risoluzione.

// ---------------------------------------------------------------- Titolo
export type TitoloProps = Base & {
  testo: string;
  sottotitolo?: string;
  posizione?: 'centro' | 'alto' | 'basso';
  entrata?: 'pop' | 'scorri' | 'macchina';   // macchina = una lettera alla volta
  dimensione?: number;
  conFondo?: boolean;                          // pillola dietro al testo
};
export const Titolo: React.FC<TitoloProps> = (p) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();
  const s = stile(p.stile);
  const dim = (p.dimensione || 0.075) * height;
  const e = entra(f, fps);
  const u = esce(f, fps, durationInFrames);
  const testo = p.entrata === 'macchina' ? p.testo.slice(0, Math.floor(interpolate(f, [0, fps * 0.9], [0, p.testo.length], {extrapolateRight: 'clamp'}))) : p.testo;
  const y = p.posizione === 'alto' ? '18%' : p.posizione === 'basso' ? '78%' : '50%';
  const sposta = p.entrata === 'scorri' ? (1 - e) * width * 0.08 : 0;
  const scala = p.entrata === 'pop' || !p.entrata ? 0.85 + 0.15 * e : 1;
  const conFondo = p.conFondo ?? true;
  return (
    <Contenitore>
      <div style={{position: 'absolute', left: 0, right: 0, top: y, transform: `translateY(-50%) translateX(${sposta}px) scale(${scala})`,
        opacity: Math.min(1, e * 1.4) * u, textAlign: 'center', fontFamily: s.font, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{display: 'inline-block', maxWidth: width * 0.86, padding: conFondo ? `${dim * 0.28}px ${dim * 0.55}px` : 0, borderRadius: dim * 0.6,
          background: conFondo ? s.sfondo : 'transparent', color: s.colore, fontSize: dim, fontWeight: 700, letterSpacing: '-0.02em',
          lineHeight: 1.1, textShadow: conFondo ? 'none' : ombraTesto(s.contorno, dim * 0.06)}}>{testo}</div>
        {p.sottotitolo ? (
          <div style={{marginTop: dim * 0.3, fontSize: dim * 0.42, fontWeight: 600, color: conFondo ? s.sfondo : s.colore,
            opacity: entra(f, fps, 6), textShadow: ombraTesto(s.contorno, dim * 0.03)}}>{p.sottotitolo}</div>
        ) : null}
      </div>
    </Contenitore>
  );
};

// ---------------------------------------------------------------- Scritta (etichetta, terzo inferiore, richiamo)
export type ScrittaProps = Base & {
  testo: string;
  x?: number; y?: number;                  // centro, in frazioni (0-1)
  forma?: 'pillola' | 'etichetta' | 'evidenziatore';
  dimensione?: number;
  icona?: string;                          // un'emoji o un carattere davanti al testo
};
export const Scritta: React.FC<ScrittaProps> = (p) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();
  const s = stile(p.stile);
  const dim = (p.dimensione || 0.045) * height;
  const e = entra(f, fps);
  const u = esce(f, fps, durationInFrames);
  const forma = p.forma || 'pillola';
  const largh = interpolate(e, [0, 1], [0, 1]);
  const fondo = forma === 'evidenziatore' ? s.accento : s.sfondo;
  const col = forma === 'evidenziatore' ? s.sfondo : s.colore;
  return (
    <Contenitore>
      <div style={{position: 'absolute', left: px(p.x ?? 0.5, width), top: px(p.y ?? 0.8, height), transform: 'translate(-50%,-50%)',
        opacity: u, fontFamily: s.font}}>
        <div style={{position: 'relative', display: 'inline-flex', alignItems: 'center', gap: dim * 0.4, whiteSpace: 'nowrap',
          padding: `${dim * 0.32}px ${dim * 0.6}px`, borderRadius: forma === 'pillola' ? dim : dim * 0.25,
          clipPath: `inset(0 ${(1 - largh) * 100}% 0 0 round ${dim}px)`, background: fondo, color: col, fontSize: dim, fontWeight: 600,
          borderLeft: forma === 'etichetta' ? `${dim * 0.18}px solid ${s.accento}` : 'none',
          boxShadow: forma === 'evidenziatore' ? 'none' : '0 6px 24px rgba(0,0,0,.18)'}}>
          {p.icona ? <span style={{fontSize: dim * 1.05}}>{p.icona}</span> : null}
          <span style={{opacity: interpolate(f, [fps * 0.12, fps * 0.3], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>{p.testo}</span>
        </div>
      </div>
    </Contenitore>
  );
};

// ---------------------------------------------------------------- Freccia (si disegna da sola)
export type FrecciaProps = Base & {
  da: [number, number]; a: [number, number];   // punti in frazioni (0-1) o pixel
  curva?: number;                                // -1..1, piega della freccia
  spessore?: number;                             // frazione dell'altezza
  colore?: string;
};
export const Freccia: React.FC<FrecciaProps> = (p) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();
  const s = stile(p.stile);
  const col = p.colore || s.accento;
  const sp = (p.spessore || 0.008) * height;
  const [x1, y1] = [px(p.da[0], width), px(p.da[1], height)];
  const [x2, y2] = [px(p.a[0], width), px(p.a[1], height)];
  const c = p.curva ?? 0.25;
  const mx = (x1 + x2) / 2 - (y2 - y1) * c, my = (y1 + y2) / 2 + (x2 - x1) * c;
  const d = `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
  const lung = Math.hypot(x2 - x1, y2 - y1) * 1.25 + 1;
  const t = interpolate(f, [0, fps * 0.45], [0, 1], {extrapolateRight: 'clamp', easing: (x) => 1 - Math.pow(1 - x, 3)});
  const ang = Math.atan2(y2 - my, x2 - mx);
  const punta = sp * 4;
  const testa = `M ${x2 - punta * Math.cos(ang - 0.5)} ${y2 - punta * Math.sin(ang - 0.5)} L ${x2} ${y2} L ${x2 - punta * Math.cos(ang + 0.5)} ${y2 - punta * Math.sin(ang + 0.5)}`;
  return (
    <Contenitore>
      <svg width={width} height={height} style={{position: 'absolute', inset: 0, opacity: esce(f, fps, durationInFrames)}}>
        <path d={d} fill="none" stroke={col} strokeWidth={sp} strokeLinecap="round" strokeDasharray={lung} strokeDashoffset={lung * (1 - t)} />
        <path d={testa} fill="none" stroke={col} strokeWidth={sp} strokeLinecap="round" strokeLinejoin="round"
          opacity={interpolate(t, [0.85, 1], [0, 1], {extrapolateLeft: 'clamp'})} />
      </svg>
    </Contenitore>
  );
};

// ---------------------------------------------------------------- Emoji
export type EmojiProps = Base & {emoji: string; x?: number; y?: number; dimensione?: number; dondola?: boolean};
export const Emoji: React.FC<EmojiProps> = (p) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();
  const e = entra(f, fps, 0, 220);
  const rot = p.dondola === false ? 0 : Math.sin((f / fps) * 5) * 6 * Math.min(1, f / (fps * 0.4));
  return (
    <Contenitore>
      <div style={{position: 'absolute', left: px(p.x ?? 0.75, width), top: px(p.y ?? 0.3, height), fontSize: (p.dimensione || 0.12) * height,
        transform: `translate(-50%,-50%) scale(${e}) rotate(${rot}deg)`, opacity: esce(f, fps, durationInFrames), lineHeight: 1}}>{p.emoji}</div>
    </Contenitore>
  );
};

// ---------------------------------------------------------------- Barra di avanzamento
export type BarraProps = Base & {posizione?: 'alto' | 'basso'; spessore?: number; colore?: string; fondo?: string};
export const Barra: React.FC<BarraProps> = (p) => {
  const f = useCurrentFrame();
  const {durationInFrames, width, height} = useVideoConfig();
  const s = stile(p.stile);
  const h = (p.spessore || 0.008) * height;
  return (
    <Contenitore>
      <div style={{position: 'absolute', left: 0, right: 0, height: h, [p.posizione === 'alto' ? 'top' : 'bottom']: 0, background: p.fondo || 'rgba(255,255,255,0.25)'}}>
        <div style={{height: '100%', width: `${(f / Math.max(1, durationInFrames - 1)) * 100}%`, background: p.colore || s.accento}} />
      </div>
    </Contenitore>
  );
};

// ---------------------------------------------------------------- Sottotitoli animati (parola per parola)
export type Parola = {w: string; inizio: number; fine: number};
export type SottotitoliProps = Base & {
  parole: Parola[];                 // tempi sulla timeline montata (parole-timeline.json)
  parolePerBlocco?: number;
  maiuscolo?: boolean;
  y?: number;                       // altezza del centro del testo, 0-1
  dimensione?: number;
  animazione?: 'pop' | 'nessuna';
  coloreTesto?: string;             // di solito bianco sui video
};
const blocchi = (parole: Parola[], n: number) => {
  const out: Parola[][] = []; let cur: Parola[] = [];
  for (const p of parole) {
    const prec = cur[cur.length - 1];
    if (cur.length && (cur.length >= n || p.inizio - prec.fine > 0.5 || /[.?!]$/.test(prec.w))) { out.push(cur); cur = []; }
    cur.push(p);
  }
  if (cur.length) out.push(cur);
  return out;
};
export const Sottotitoli: React.FC<SottotitoliProps> = (p) => {
  const f = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = stile(p.stile);
  const t = f / fps;
  const bl = blocchi(p.parole, p.parolePerBlocco || 3);
  const b = bl.find((x, i) => t >= x[0].inizio && t < (bl[i + 1] ? Math.min(bl[i + 1][0].inizio, x[x.length - 1].fine + 0.6) : x[x.length - 1].fine + 0.3));
  if (!b) return <Contenitore>{null}</Contenitore>;
  const dim = (p.dimensione || 0.055) * height;
  const fb = Math.round(b[0].inizio * fps);
  const pop = p.animazione === 'nessuna' ? 1 : 0.8 + 0.2 * entra(f, fps, fb, 260);
  const col = p.coloreTesto || '#FFFFFF';
  return (
    <Contenitore>
      <div style={{position: 'absolute', left: '50%', top: `${(p.y ?? 0.7) * 100}%`, transform: `translate(-50%,-50%) scale(${pop})`,
        width: width * 0.88, textAlign: 'center', fontFamily: s.font, fontWeight: 800, fontSize: dim, lineHeight: 1.15,
        color: col, textShadow: ombraTesto(s.contorno, dim * 0.07)}}>
        {b.map((w, i) => {
          const attiva = t >= w.inizio && t < (b[i + 1]?.inizio ?? w.fine + 0.6);
          const sp = p.animazione === 'nessuna' ? 1 : (attiva ? 1 + 0.08 * entra(f, fps, Math.round(w.inizio * fps), 300) : 1);
          return (
            <span key={i} style={{display: 'inline-block', margin: `0 ${dim * 0.14}px`, color: attiva ? s.accento : col, transform: `scale(${sp})`}}>
              {p.maiuscolo ? w.w.toUpperCase() : w.w}
            </span>
          );
        })}
      </div>
    </Contenitore>
  );
};
