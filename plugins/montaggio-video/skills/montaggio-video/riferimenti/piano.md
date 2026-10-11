# Il piano di montaggio

`.lavoro/<progetto>/piani/<piano>.json` descrive un montaggio (video-lungo, short-1...). `pulizia.py` crea la base
(segmenti e tagli); tu aggiungi effetti, transizioni, sovrapposizioni e audio; `esporta.py` lo esegue
sempre dagli originali. Ogni versione in `risultati/` ne conserva una copia.

**Tempi:**
- `inizio`/`fine` dei **segmenti** sono nel tempo della **ripresa originale**;
- `inizio`/`fine` di **sovrapposizioni, musica ed effetti sonori** sono nel tempo della **timeline
  montata**. Le parole sulla timeline sono in `.lavoro/<progetto>/sottotitoli/<piano>-parole.json`: usale per mettere ogni elemento
  sulla parola giusta. Se cambi i segmenti, rigenera `sottotitoli.py` e ricontrolla i tempi.

**Percorsi:** relativi alla cartella `montaggio-video/` (es. `media/<progetto>/titolo-01.mov`) oppure
assoluti.

```json
{
  "schema": 1,
  "progetto": "tavolo-rovere",
  "profilo": "base",
  "formato": "video-lungo",
  "larghezza": 3840, "altezza": 2160, "fps": "30000/1001",
  "adattamento": "riempi",
  "colore": {"lut": "profili/mio/look.cube", "contrasto": 1.05, "saturazione": 1.1, "luminosita": 0.0, "gamma": 1.0},
  "riinquadratura": {"0": {"punti": [[0.0, 0.48], [12.5, 0.55]], "cy": 0.5}},
  "segmenti": [
    {"id": 1, "sorgente": 0, "inizio": 0.0, "fine": 4.2, "testo": "...",
     "velocita": 1.0,
     "zoom": {"tipo": "lento", "da": 1.0, "a": 1.12, "inizio": 0, "durata": 4, "cx": 0.5, "cy": 0.45},
     "tremolio": {"intensita": 0.008},
     "transizione": {"tipo": "dissolvenza", "durata": 0.4}}
  ],
  "tagli": [{"sorgente": 0, "inizio": 4.2, "fine": 5.1, "motivo": "pausa", "testo": ""}],
  "sostituzioni": [{"da": "tavolo di rovare", "a": "tavolo di rovere"}],
  "sovrapposizioni": [
    {"file": "media/tavolo-rovere/titolo-01.mov", "inizio": 0.3, "fine": 3.0, "modo": "sopra", "nota": "titolo iniziale",
     "remotion": {"tipo": "Titolo", "props": "media/tavolo-rovere/titolo-01.json"}},
    {"file": "media/tavolo-rovere/broll-sega.mp4", "inizio": 12.4, "fine": 16.0, "modo": "pieno", "inizio_file": 2.0, "dissolvenza": 0.2},
    {"file": "media/tavolo-rovere/pannello-02.mov", "inizio": 20.0, "fine": 35.0, "modo": "sopra", "livello": 1},
    {"file": "media/tavolo-rovere/prodotto.png", "inizio": 40.0, "fine": 44.0, "modo": "riquadro", "riquadro": [0.6, 0.1, 0.35, 0.35]}
  ],
  "audio": {
    "voce": {"pulizia": true},
    "musica": [{"file": "media/tavolo-rovere/sottofondo.mp3", "inizio": 0, "fine": 0, "volume_db": -18,
                "dissolvenza_in": 1.0, "dissolvenza_out": 2.0, "abbassa_sotto_voce": true, "ripeti": false, "inizio_file": 0}],
    "effetti": [{"file": "media/tavolo-rovere/whoosh.mp3", "inizio": 12.35, "volume_db": -8}]
  },
  "note": ["Le barre del confronto sono illustrative."]
}
```

## Campi dei segmenti

| Campo | Valori | Effetto |
|---|---|---|
| `velocita` | 0.25–4 | accelera (>1) o rallenta (<1) il segmento, audio compreso (tono invariato). Per uno speed ramp spezza il segmento in 3–4 pezzi con velocità crescenti o decrescenti |
| `zoom` | `tipo`: `scatto` (punch-in) o `lento`; `da`, `a` (1 = nessuno zoom); `inizio`, `durata` in secondi dall'inizio del segmento; `cx`, `cy` centro (0–1) | zoom improvviso su una parola o zoom lento continuo |
| `tremolio` | `intensita` 0.003–0.02 | leggero movimento di camera a mano |
| `transizione` | `tipo` (vedi sotto), `durata` 0.15–1 s | transizione **in entrata** da segmento precedente; si sovrappongono le ultime/prime `durata` secondi dei due segmenti, quindi il video si accorcia un poco. Non si combina con `velocita` diversa da 1 |

Transizioni: `dissolvenza`, `flash` (bianco), `nero`, `glitch`, `scorri-sinistra`, `scorri-destra`,
`scorri-su`, `scorri-giu`, `frusta`, `zoom`, `cerchio`, `sfocatura`, `tendina`.

Sul video parlato la regola è il taglio netto: le transizioni vanno sui cambi di argomento, di luogo o
di tempo, non tra una frase e l'altra. Il profilo dice quali usare e quanto.

## Sovrapposizioni

| Campo | Significato |
|---|---|
| `file` | grafica `.mov` trasparente, video (B-roll), immagine (`.png`, `.jpg`) |
| `inizio`, `fine` | entrata e uscita sulla timeline; se `fine` manca, dura quanto il file. Se il file è più corto, resta fermo l'ultimo fotogramma |
| `modo` | `sopra` (trasparente a tutto fotogramma: grafiche e pannelli), `pieno` (copre il video: B-roll, stacchi a tutto schermo), `riquadro` con `riquadro: [x, y, larghezza, altezza]` in frazioni |
| `inizio_file` | da che punto del file partire (s) |
| `dissolvenza` | entrata e uscita sfumate (s) |
| `livello` | ordine: più alto = più in primo piano |
| `nota` | cosa copre o perché: compare nelle pagine di revisione |

I B-roll HDR vengono convertiti con la stessa conversione della ripresa. L'audio dei B-roll non viene
usato (la voce resta quella dell'originale): per un suono usa `audio.effetti`.

## Correzioni del testo

`sostituzioni`: errori di trascrizione da correggere nei sottotitoli (`da` -> `a`, anche più parole).
Restano nel piano, quindi valgono per tutte le versioni successive.

## Grafiche Remotion

Per le grafiche Remotion aggiungi `remotion: {"tipo", "props"}` alla sovrapposizione: così il player di
revisione mostra i testi della grafica come campi modificabili, e sai quale file di proprietà cambiare
prima di rirenderizzarla.

## Audio

Vedi [audio.md](audio.md).
