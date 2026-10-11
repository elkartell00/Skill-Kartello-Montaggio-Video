# Revisione

Tre modi per far vedere una versione all'utente: proponi quello adatto, o usali insieme.

| Strumento | Quando |
|---|---|
| `anteprima.mp4` | sempre: si guarda e si scrivono le modifiche a parole in chat |
| `confronto.html` e `clip.html` (`pagine_revisione.py`) | per vedere prima/dopo rispetto alla versione precedente, e le grafiche una per una |
| **Revisione scena per scena** (player di Motion OS) | per correzioni precise al fotogramma: testi, sottotitoli, tempi, posizione delle grafiche, note su un punto esatto |

## Revisione scena per scena

```bash
$PY $SKILL/scripts/pagine_revisione.py --progetto <nome> --piano <piano>   # facoltativo
$PY $SKILL/scripts/revisione.py --progetto <nome> --piano <piano>
node $SKILL/revisione-player/serve.mjs montaggio-video/risultati/<nome>/<piano>     # in background
```

Il server stampa l'indirizzo (porta 4321 o la successiva libera) e apre il browser. Funziona solo sul
computer dell'utente, senza internet. Se è già acceso per quel piano, lascialo: si aggiorna da solo.

Spiega all'utente in due o tre righe:
- **Anteprima** riproduce; **Modifica** (tasto E) ferma il video: clic su un elemento per cambiarne testo
  o tempi, trascinalo per spostarlo, trascina un angolo per ridimensionarlo;
- **N** e clic sul fotogramma per fissare una nota in quel punto e in quel momento;
- la scheda **Testi** ha tutte le parole: è il modo più veloce per correggere i sottotitoli;
- ogni scena si può segnare **Approvata**;
- alla fine **Invia a Claude**, **Copia messaggio** e incollalo qui in chat.

## Applicare il messaggio "Revisione Motion OS per ..."

Gli elementi hanno id stabili che portano al piano:

| Id | Cosa cambiare |
|---|---|
| `seg-N` | segmento con `id` N: "Nel montaggio: togli" = togli il segmento; "Zoom" = imposta `zoom` (scatto/lento); il campo "Altro" è una richiesta a parole |
| `sub-N` | testo dei sottotitoli: aggiungi a `sostituzioni` del piano `{"da": testo vecchio (solo la parte cambiata), "a": testo nuovo}` e rigenera `sottotitoli.py`. Se la parola sbagliata è anche detta male nel video, chiedi se tagliarla |
| `ov-N` | sovrapposizione N (in ordine nel piano): tempi -> `inizio`/`fine`; dimensione e posizione -> `riquadro` (o `x`/`y`/`dimensione` della grafica Remotion); testi -> nel file `props` della grafica Remotion, poi rirenderizza la grafica |

- **Modifiche**: applicale esattamente come scritte.
- **Note**: hanno tempo, scena e posizione (x/y in % del fotogramma). Prima di decidere cosa significano,
  guarda quel fotogramma: `ffmpeg -ss <tempo> -i anteprima.mp4 -frames:v 1 nota.jpg`.
- **Scene approvate**: non toccarle (né tagli, né grafiche, né tempi al loro interno).
- Dimensioni e posizioni arrivano come `[x, y, larghezza, altezza]` in % del fotogramma più una scala.
- Ogni modifica e ogni nota va nel diario delle revisioni del profilo (vedi [profili.md](profili.md)).
- Poi: rigenera sottotitoli e anteprima (nuova versione, sempre dagli originali), rilancia `revisione.py`
  (il numero di versione sale e il player si ricarica da solo in pochi secondi) e rispondi con un breve
  elenco di cosa hai cambiato e di cosa non hai potuto fare.

L'esportazione dal player è disattivata di proposito: il video finale si fa con `esporta.py --modo finale`.
