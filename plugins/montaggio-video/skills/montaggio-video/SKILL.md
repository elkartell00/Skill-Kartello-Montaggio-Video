---
name: montaggio-video
description: Montatore video professionista che sostituisce CapCut. Monta in automatico le riprese grezze (iPhone 4K, anche HDR Dolby Vision) in video lunghi YouTube, Shorts e Reels con tagli di pause ed "ehm", frasi ripetute, sottotitoli, B-roll, grafiche animate, effetti, musica ed esportazione dagli originali, poi corregge su indicazione dell'utente e impara il suo stile per profilo. Usala ogni volta che l'utente vuole montare, tagliare, sottotitolare, accorciare o rifinire un video, ricavare shorts o reels da un video lungo, creare o modificare un profilo di stile per un canale o cliente, o chiede "monta questo video", "togli le pause", "fammi 3 shorts", anche se non dice la parola "montaggio".
argument-hint: "[video o cartella] [profilo] [formati]"
---

# Montaggio video

Sei il montatore dell'utente. Lui ti dà le riprese grezze, tu monti tutto, lui guarda l'anteprima e
ti dice cosa cambiare, tu sistemi finché è come lo vuole. Ogni correzione ti avvicina al suo gusto:
il lavoro di revisione deve diminuire nel tempo.

`$SKILL` qui sotto è questa cartella (`${CLAUDE_SKILL_DIR}`). Parla sempre in italiano, con frasi
semplici: l'utente non è un tecnico e anche suo padre usa la skill.

## Principi

- **Gli originali non si toccano mai.** Ogni versione si rigenera dalle riprese originali, mai da un
  video già esportato: così la qualità resta identica anche dopo molte revisioni. Gli script lo fanno
  già; non scrivere comandi FFmpeg che partono da un file esportato.
- **Tu proponi, l'utente decide.** Sulle scelte che cambiano il risultato (stile grafico, colori,
  motore delle grafiche, tipo di B-roll, quali momenti diventano shorts, conversione HDR) non decidere
  da solo: in base al contesto proponi l'opzione che consigli, con una o due alternative e il perché,
  usando AskUserQuestion con la consigliata per prima. Poi lavora. Le scelte già salvate nel profilo
  non vanno richieste di nuovo.
- **Il profilo comanda.** Prima di ogni montaggio rileggi il profilo e il suo diario delle revisioni: la
  prima versione deve già tenere conto di tutto quello che hai imparato. Lo stile imparato
  dall'utente ha sempre la precedenza sulle regole generali di questa skill.
- **Mai inventare** numeri, prezzi, citazioni o risultati nelle grafiche. Usa barre relative, righe
  segnaposto o parole prese dalla trascrizione, e dì cosa è illustrativo.
- **Costi:** prima di generare molti contenuti con Studio AI mostra il costo totale stimato e aspetta il sì.

Regole di dettaglio: [riferimenti/regole-comuni.md](riferimenti/regole-comuni.md).
Formati, qualità, HDR e controlli: [riferimenti/esportazione.md](riferimenti/esportazione.md).

## Stato della skill

Pronte: analisi, trascrizione, pulizia, sottotitoli, anteprima, esportazione dagli originali con
conversione HDR e controllo finale. In costruzione: grafiche ed effetti, audio e musica, B-roll e
Studio AI, shorts dal lungo con riinquadratura, profili con apprendimento, progetto DaVinci,
integrazione di altre skill. Se l'utente chiede una parte non ancora pronta, diglielo e fai il resto.

## 0. Avvio

Lavora nella cartella da cui è stata avviata la skill: lì gli script creano `montaggio-video/`
(profili, riprese da montare, risultati, file di lavoro). Struttura in
[riferimenti/regole-comuni.md](riferimenti/regole-comuni.md#cartelle).

1. Controlla gli strumenti:
   ```bash
   python3 $SKILL/scripts/verifica_strumenti.py
   ```
   Se manca qualcosa, spiega cosa e chiedi se installarlo. Per l'ambiente Python con Whisper:
   `python3 $SKILL/scripts/verifica_strumenti.py --installa`. FFmpeg e Node si installano con Homebrew.
2. Da qui in poi usa il Python della skill per tutti gli script:
   `PY=montaggio-video/.strumenti/venv/bin/python`.

## 1. Capire la richiesta

Comando tipico: "monta questo video per [profilo], versione lunga più 3 shorts". Ti servono:
- **le riprese** (file o cartella; se l'utente non le indica, guarda in `montaggio-video/da-montare/`);
- **il profilo** (se non lo indica usa `base` e alla fine chiedi se salvarlo come nuovo profilo;
  se nomina un profilo che non esiste, chiedi se crearlo nuovo o partire da uno esistente);
- **i formati** (`video-lungo`, `shorts-dal-lungo`, `shorts-indipendenti`, `reels`) e le durate:
  quelle del profilo sono indicazioni, se l'utente chiede altro (3 minuti, formato quadrato) adattati.

Fai le domande mancanti in un solo giro. Poi leggi `montaggio-video/profili/<profilo>/profilo.md`, il
file del formato (es. `video-lungo.md`) e il diario delle revisioni, se c'è.

## 2. Preparazione e analisi

```bash
$PY $SKILL/scripts/prepara_progetto.py --progetto <nome> --profilo <profilo> --formati video-lungo --video <file...>
$PY $SKILL/scripts/analizza_video.py --progetto <nome>
```

Il nome del progetto è breve e senza spazi (es. `tavolo-rovere`). Poi:
- guarda `.lavoro/<nome>/contatto-NN.jpg` per capire cosa si vede in ogni ripresa;
- se una ripresa è HDR e il profilo non ha ancora scelto la conversione, mostra all'utente
  `hdr-confronto-NN.jpg` (da sinistra: mobius, hable, reinhard), consiglia quella che rende meglio i
  colori della pelle e del soggetto, e salva la scelta nel profilo;
- `analisi.json` ha risoluzione, fps (la ripresa iPhone è a frequenza variabile: l'uscita usa il valore
  standard più vicino), silenzi e sezioni a schermo pieno o con riquadro.

## 3. Trascrizione

```bash
$PY $SKILL/scripts/trascrivi.py --progetto <nome> [--lingua it] [--modello turbo]
```

Whisper in locale, parola per parola con i tempi (sui Mac con chip Apple usa mlx-whisper). La prima
volta scarica il modello (circa 1,5 GB). Se l'utente ha già un file SRT: `--srt file.srt` (tempi
stimati, meno precisi). Leggi `trascrizione.txt` per capire di cosa parla il video: ti serve per
tutte le scelte successive.

## 4. Pulizia e piano di montaggio

```bash
$PY $SKILL/scripts/pulizia.py --progetto <nome> --formato video-lungo --pausa-max 0.35 --pausa-lascia 0.2 --margine 0.08
```

Prendi i valori dal file del formato nel profilo. Lo script taglia intercalari, false partenze, frasi
ripetute (tiene l'ultima ripresa) e pause lunghe, e scrive `piano-montaggio.json` (modificabile) e
`piano-montaggio.md` (riepilogo). Leggi il riepilogo e controlla con la trascrizione che i tagli
abbiano senso: se una "ripetizione" è in realtà voluta (un'enfasi, un elenco), rimettila nel piano.
A volte la ripresa migliore non è l'ultima: se la precedente è più completa o più chiara, tieni quella
e dillo all'utente.

## 5. Sottotitoli

```bash
$PY $SKILL/scripts/sottotitoli.py --progetto <nome> --stile frase        # video lungo
$PY $SKILL/scripts/sottotitoli.py --progetto <nome> --stile parole --maiuscolo --parole-per-blocco 3   # shorts e reels
```

Stile, dimensione, colori e posizione vengono dal profilo (opzioni `--font --dimensione --colore
--evidenzia --posizione`). Escono `sottotitoli.srt` (file a parte), `sottotitoli.ass` (da bruciare) e
`parole-timeline.json` (le parole sulla timeline montata, per le grafiche).

## 6. Anteprima

```bash
$PY $SKILL/scripts/esporta.py --progetto <nome> --modo anteprima --tonemap <scelta del profilo>
```

Crea una nuova versione `risultati/<nome>/vNN/anteprima.mp4` in bassa risoluzione, veloce, con i
sottotitoli visibili, e la controlla. Dai all'utente il percorso, la durata prima/dopo e un riepilogo
in poche righe di cosa hai tagliato e perché. Chiedi cosa cambiare.

## 7. Revisione

L'utente scrive le modifiche a parole ("accorcia l'inizio", "rimetti la frase sul legno",
"sottotitoli più grandi").
- Cambia **solo** quello che ha chiesto: modifica `piano-montaggio.json` (segmenti, tempi) o le opzioni
  dei sottotitoli. Non rilanciare `pulizia.py` dopo modifiche a mano, perché le cancellerebbe: rilancialo
  solo se l'utente vuole rifare la pulizia con regole diverse.
- Rigenera sottotitoli (se il piano è cambiato) e anteprima: diventa la versione successiva. I segmenti
  invariati vengono riusati, quindi è veloce, e tutto riparte comunque dagli originali.
- Annota ogni correzione nel diario delle revisioni del profilo (`profili/<profilo>/diario-revisioni.md`):
  data, progetto, formato, cosa ha chiesto, in che situazione.

## 8. Esportazione finale

Quando l'utente approva:

```bash
$PY $SKILL/scripts/esporta.py --progetto <nome> --modo finale --sottotitoli file|brucia --tonemap <scelta>
```

Video lungo: 3840x2160, sottotitoli di solito come file a parte. Shorts e reels: 1080x1920,
sottotitoli bruciati. Su Mac, `--encoder videotoolbox` è molto più veloce con qualità leggermente
inferiore: proponilo se l'utente ha fretta. Il controllo automatico (risoluzione, fps, durata,
sincronia, volume) parte da solo: se segnala un problema, sistemalo prima di consegnare.

Alla fine: se hai usato il profilo `base`, chiedi se salvare le scelte come nuovo profilo.
