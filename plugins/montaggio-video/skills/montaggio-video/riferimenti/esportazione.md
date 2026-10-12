# Esportazione

## Preset

| Formato | Uscita | Fps | Sottotitoli |
|---|---|---|---|
| video-lungo | MP4 16:9, 3840x2160, H.264 alta qualità (CRF 16) | come la ripresa | file `.srt` a parte |
| shorts-dal-lungo | MP4 9:16, 1080x1920 | come la ripresa | bruciati |
| shorts-indipendenti | MP4 9:16, 1080x1920 | come la ripresa | bruciati |
| reels | MP4 9:16, 1080x1920 | come la ripresa | bruciati, più in alto |
| su richiesta | `--formato LARGHEZZAxALTEZZA` in `pulizia.py` (es. 1080x1080, 1080x1350) | come la ripresa | a scelta |

- **Anteprima:** lato corto 540 px, codifica veloce, sottotitoli sempre visibili. Serve solo a guardare.
- **Audio:** AAC 320 kbps, 48 kHz, volume medio -14 LUFS, picchi sotto -1,5 dBTP (valori adatti a
  YouTube e Instagram: le piattaforme non abbassano né alzano il video).
- **Colori:** sempre SDR Rec.709 in uscita, il formato che YouTube e Instagram mostrano correttamente
  su tutti i telefoni.
- **Codifica:** `x264` (predefinita, massima qualità) oppure `videotoolbox` (hardware del Mac, molto più
  veloce, file più grande a parità di qualità).

## Sempre dagli originali

Ogni segmento si ricava dalla ripresa originale con una sola codifica. Se ci sono sottotitoli da
bruciare (o grafiche), i segmenti si fanno prima in una qualità intermedia quasi senza perdite e la
codifica finale avviene una sola volta sull'insieme. I segmenti già fatti con le stesse impostazioni
vengono riusati tra una versione e l'altra (sono in `.lavoro/<progetto>/segmenti/`).

## Riprese iPhone HDR

L'iPhone registra in HEVC 10 bit, spesso in HDR Dolby Vision (profilo 8.4, che ha una base HLG). Se
lo si converte in SDR cambiando solo il formato dei pixel, i colori escono slavati e grigi. La catena
corretta (in `comune.py`, funzione `filtro_sdr`):

1. lettura dei valori HLG (o PQ) con i primari BT.2020;
2. passaggio in luce lineare, a virgola mobile;
3. conversione dei primari BT.2020 → BT.709;
4. mappatura dei toni (riporta le luci alte nella gamma SDR senza bruciarle);
5. ritorno in BT.709 a 8 bit.

Gli operatori di mappatura disponibili:
- `mobius` (predefinito): mantiene contrasto e saturazione dei toni medi, comprime solo le luci alte. Di
  solito il più fedele per persone e prodotti.
- `hable`: più "cinematografico", luci morbide, immagine un po' più scura.
- `reinhard`: più piatto e luminoso, utile se le riprese sono molto contrastate.

La scelta è dell'utente: `analizza_video.py` crea `hdr-confronto-NN.jpg` con i tre operatori sullo
stesso fotogramma. La scelta si salva nel profilo (`profilo.md`, sezione "Colore delle riprese") e si
passa a `esporta.py --tonemap`.

## Fotogrammi al secondo

Le riprese iPhone sono a frequenza variabile (VFR). L'uscita usa il valore standard più vicino a quello
della ripresa (29,97, 30, 59,94, 60...) a frequenza costante, come vogliono YouTube e i programmi di
montaggio. Se le riprese di un progetto hanno fps diversi, si usa quello della prima ripresa, salvo
indicazione diversa (`pulizia.py --fps`).

## Controllo finale

`controllo_finale.py` parte da solo dopo ogni esportazione e controlla: risoluzione, fps, colori SDR,
durata attesa, sincronia audio/video (differenza sotto 0,1 s), volume medio (±1 LUFS) e picchi. Il
risultato è in `<video>.controllo.json`. Un controllo fallito va sistemato prima di consegnare.

## Dove finiscono i file

`risultati/<progetto>/<piano>/vNN/`: `anteprima.mp4`, `<progetto>-<piano>-vNN.mp4` (finale),
`sottotitoli.srt`/`.ass`, `piano.json` (il piano usato: per tornare indietro), `riepilogo-tagli.md`,
`*.controllo.json`, pagine di revisione e, se richiesta, cartella `davinci/`. Ogni anteprima crea una nuova versione;
l'export finale va nella versione più recente se il piano non è cambiato.

## Progetto per DaVinci Resolve (in riserva)

Per ora l'utente non usa DaVinci: crea il progetto **solo se lo chiede**. Lo script resta pronto.

```bash
$PY $SKILL/scripts/davinci.py --progetto <nome> --piano <piano> [--versione vNN]
```

Crea `vNN/davinci/` con:
- `<progetto>-<piano>-vNN.fcpxml` (FCPXML 1.9): i segmenti collegati alle **riprese originali** sulla
  traccia principale, grafiche, animazioni e B-roll come clip separate sulle tracce sopra (le grafiche
  sono `.mov` trasparenti a piena risoluzione), musica ed effetti sonori sulle tracce audio con il loro volume;
- `sottotitoli.srt` da importare a parte;
- `LEGGIMI.txt` con i passi di importazione.

Velocità, zoom, tremolio, transizioni, look colore e riinquadratura non passano in modo affidabile
nell'FCPXML: diventano **marcatori** sui clip con l'istruzione, da rifare in DaVinci in pochi clic. Le
riprese HDR vanno gestite con il Color Management di DaVinci (spiegato nel LEGGIMI). Esportando da DaVinci
si parte dagli originali: una sola codifica, nessuna perdita di qualità.
