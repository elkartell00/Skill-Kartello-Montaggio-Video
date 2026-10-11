import React from 'react';

// Grafiche su misura scritte da Claude per l'utente (una per file in questa cartella).
// Questa cartella, nella copia di lavoro (montaggio-video/.strumenti/grafiche/src/su-misura/), NON viene
// sovrascritta quando la skill si aggiorna: qui restano le animazioni create nei progetti.
//
// Ogni voce: id (usato da "grafiche.py remotion <id>"), componente e proprietà di esempio.
// Le proprietà ricevono sempre larghezza, altezza, fps e durata (vedi Base in ../comune.tsx).
export type SuMisura = {id: string; component: React.FC<any>; defaultProps: Record<string, unknown>};

export const SU_MISURA: SuMisura[] = [
  // {id: 'GraficoCrescita', component: GraficoCrescita, defaultProps: {larghezza: 1920, altezza: 1080, fps: 30, durata: 4}},
];
