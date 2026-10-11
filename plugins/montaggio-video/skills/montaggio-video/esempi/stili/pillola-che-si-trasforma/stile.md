# Stile: pillola-che-si-trasforma

Esempio di stile imparato: dalla clip "01-opus-drop" degli esempi di motion-broll, riprodotto in Remotion
con i colori di un brand diverso (verde e oro). Serve come modello di come si scrive una scheda di stile.

## In una frase
Un'unica forma che non taglia mai: pillola scura con titolo, poi scheda bianca con icona e testo, poi
selettore con un indicatore che scorre di voce in voce.

## Tipo
B-roll animato / titoli / scelta tra opzioni

## Scomposizione
- **Elementi:** una sola forma arrotondata; dentro: icona + titolo (pillola), riquadro colorato + titolo e
  sottotitolo (scheda), voci in fila con indicatore pieno (selettore).
- **Entrate e uscite:** la forma entra da piccola (scala 0,55 -> 1) con un filo di rimbalzo; il contenuto
  vecchio esce in circa 4 fotogrammi sfocandosi, quello nuovo entra dopo 2 fotogrammi in circa 7, da sfocato a nitido.
- **Tempi:** pillola 0–2,2 s; scheda 2,2–4,1 s; selettore da 4,1 s; l'indicatore avanza ogni 0,35–0,45 s.
  Trasformazioni della forma ~0,6 s (18 fotogrammi a 30 fps).
- **Andamento:** molle che partono veloci e frenano (ease-out), rimbalzo appena percettibile.
- **Tipografia:** sans serif semibold, titoli grandi (≈5% dell'altezza), sottotitoli piccoli e grigi.
- **Impaginazione:** tutto al centro; la forma riempie il quadro a ogni stato.
- **Colore:** ruoli -> forma scura = `colore` del profilo; schede e selettore = `sfondo`; icona = `accento`.
- **Effetti e suono:** ombra morbida sotto la forma; nell'originale un cursore guida i cambi (qui omesso).

## Riproduzione
- Componente: `componenti/index.tsx`, composizione `PillolaCheSiTrasforma`.
- Proprietà: `pillola` (testo), `scheda: {titolo, sottotitolo}`, `voci` (elenco), `tempi: {scheda, selettore}`,
  `passiVoce` (secondi in cui l'indicatore avanza), `stile` (colori del profilo), più larghezza, altezza, fps, durata.

## Quando usarlo
Per presentare una novità e poi una scelta tra opzioni (materiali, livelli, versioni). Video lunghi
16:9; per i verticali va adattato (forma più stretta e alta).

## Cosa non copiare
Loghi, marchi, sigle, grafiche identiche, musiche e personaggi dell'esempio: si prende lo stile, non il contenuto.

## Giudizio dell'utente e uso
- (da compilare quando viene usato)
