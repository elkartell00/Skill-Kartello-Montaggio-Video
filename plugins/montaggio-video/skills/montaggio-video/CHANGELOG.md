# Registro delle modifiche

Ogni modifica alla skill, comprese le parti integrate da altre skill (con la fonte e il motivo).

## 0.10.0 – Imparare dagli esempi: la libreria degli stili

### Nuovo
- **Libreria degli stili** (`montaggio-video/stili/`, comune a tutti i profili): ogni video o motion graphic di
  esempio che l'utente dà diventa uno stile riutilizzabile, rifatto con il codice e applicato con i colori, il
  brand e i contenuti dell'utente. Più esempi, più stili ed effetti la skill sa fare.
- `stili.py`: `analizza` (copia ridotta dell'esempio, fogli con 8 fotogrammi al secondo, tagli, raffiche di
  movimento con durata e andamento, palette), `confronta` (esempio e riproduzione affiancati agli stessi
  istanti), `sincronizza` (gli stili entrano nel progetto Remotion), `indice` (`stili/INDICE.md`), `salva`
  (modifica datata e annullabile, come i profili), `elenca`.
- Remotion carica in automatico gli stili della libreria (`src/stili/`), accanto alle grafiche su misura.
- Guida `riferimenti/stili.md` e scheda di stile modello; esempio completo in
  `esempi/stili/pillola-che-si-trasforma/` (imparato da una clip di motion-broll e rifatto con altri colori).
- `SKILL.md`, profili e grafiche: il piano creativo consulta la libreria; il profilo annota gli stili preferiti.

## 0.9.0 – Tappe 2–7: grafiche, effetti, audio, B-roll, shorts, profili, DaVinci, revisione, integrazioni

### Nuovo
- **Piani multipli per progetto** (`video-lungo`, `short-1`, `reel-1`...): ognuno con sottotitoli e versioni
  propri in `risultati/<progetto>/<piano>/vNN/`.
- **Grafiche** (`grafiche.py`, `grafiche-remotion/`): progetto Remotion con Titolo, Scritta, Freccia, Emoji,
  Barra di avanzamento e Sottotitoli animati, trasparenti (ProRes 4444) a piena risoluzione.
- **Effetti** nell'esportazione: zoom a scatto e lento, tremolio, velocità (speed ramp a passi),
  13 transizioni, look colore (LUT, contrasto, saturazione, luminosità, gamma).
- **Sovrapposizioni**: grafiche trasparenti, B-roll a tutto schermo o in riquadro, immagini, con dissolvenze
  e livelli; B-roll HDR convertiti come le riprese.
- **Audio**: pulizia della voce, musica che si abbassa sotto la voce, effetti sonori, volume a -14 LUFS sul
  mix completo; `battiti.py` per tagliare a tempo di musica.
- **B-roll** (`broll.py`): indice delle riprese extra con fogli di anteprima, ricerca negli archivi gratuiti
  (Pexels, Pixabay, solo se il profilo li prevede); istruzioni per Studio AI con costo stimato prima di generare.
- **Shorts**: pulizia per intervalli nell'ordine voluto (aggancio in testa), riinquadratura 16:9 -> 9:16
  che segue il volto con movimento ammorbidito (`riinquadra.py`), o le maschere della separazione.
- **Profili e apprendimento**: `profili.py` (crea, copia, rinomina, cestino, storico datato con git o copie,
  annulla), `diario.py` (correzioni, versioni, andamento, correzioni ricorrenti), `video_riferimento.py`
  (ritmo dei tagli, inquadrature, aggancio, volume dei video di riferimento).
- **DaVinci Resolve** (`davinci.py`): FCPXML 1.9 collegato agli originali, grafiche e B-roll come clip
  separate, musica ed effetti con volume, marcatori per ciò che non passa, SRT e istruzioni.
- **Revisione**: pagine di confronto prima/dopo e visore delle clip (`pagine_revisione.py`), player scena per
  scena (`revisione.py`, `revisione-player/`), correzioni del testo dei sottotitoli nel piano (`sostituzioni`).
- **Integrare altre skill**: procedura (`riferimenti/integrare-skill.md`) e `controllo_sicurezza.py`.
- `verifica_strumenti.py` installa anche OpenCV e controlla git, grafiche e separazione.

- **Prima il codice, Studio AI per ultimo** (regola dell'utente): motion graphics, animazioni, schede,
  grafici, illustrazioni e miniature li crea Claude Code con il codice; Studio AI per immagini e video solo
  quando il codice non basta. Grafiche Remotion **su misura** (`su-misura/`, conservate negli
  aggiornamenti) e immagini ferme (`grafiche.py immagine`).

### Corretto
- Il mix audio poteva finire qualche decimo di secondo prima del video quando c'era musica abbassata sotto
  la voce: trovato dal controllo finale, ora il mix ha sempre la durata esatta.
- OpenCV fissato alla versione 4 (la 5 non ha più il rilevatore di volti usato per la riinquadratura).

### Integrato da `motion-broll` (motion-graphics, Bart, licenza MIT, `LICENSE-motion-graphics.txt`)
- Il motore di animazione "forma unica" (`motore-animazioni/`: motion.js, base.css, build.py, render.js,
  beats.js, font Geist) per il B-roll animato, con la sua guida tradotta e adattata
  (`riferimenti/broll-animato.md`): direzione creativa (stacco, pannello o niente), regole sui contenuti,
  API, schemi, vocabolario delle interazioni, stile e attenzioni.
- Gli esempi finiti come riferimento di qualità (`esempi/broll-animato/`).
- Le pagine di confronto e il visore delle clip (`modelli-pagine/`), tradotti e senza font da internet.
- Modifiche: render e fogli con percorsi sicuri (anche con spazi), cartella temporanea di sistema, nessun
  comando di shell costruito con i nomi dei file, browser configurabile, messaggi in italiano, uscita in
  BT.709.

### Integrato da `object-separation` (motion-graphics, Bart, licenza MIT)
- Separazione del soggetto con SAM 2.1 in locale (`separa_soggetto.py`): scelta del modello in base al
  computer, griglia per i punti, separazione a blocchi da 60 fotogrammi, verifica in verde, maschere.
- Aggiunte: maschere usate dalla riinquadratura, ritaglio trasparente a piena risoluzione per l'effetto
  "testo dietro al soggetto", lettura delle riprese già convertite in SDR.

### Integrato da Motion OS (Jason Lee, licenza MIT, `LICENSE-motion-os.txt`)
- Il player di revisione scena per scena (`revisione-player/`): modifica di testi, tempi, posizione e
  dimensione, note fissate al fotogramma, scena approvata, scheda con tutte le parole, messaggio unico da
  incollare in chat, ricarica automatica alla nuova versione.
- Le regole per applicare le correzioni: modifiche esatte, guardare il fotogramma prima di interpretare una
  nota, non toccare le scene approvate, numero di versione che sale.
- Adattamenti: interfaccia e messaggio in italiano, font locali, `reel.json` generato dal piano di montaggio
  (segmenti, sottotitoli, grafiche con i loro testi), correzioni annotate nel diario del profilo.

### Scartato
- Da Motion OS: esportazione dal player (eseguiva un comando scritto in un file e non partiva dagli
  originali), anteprima dal vivo con Remotion, metodo per costruire video interi in Remotion (la skill ha
  già le sue grafiche), esempio e screenshot, ogni riferimento a Higgsfield (immagini e video si creano con
  Studio AI).
- Da motion-graphics: link pubblicitari, GIF dimostrative, anteprima composta da un video già esportato.

## 0.1.0 – Tappa 1: analisi, trascrizione, pulizia, sottotitoli, esportazione

### Nuovo
- Flusso di lavoro in `SKILL.md`: avvio, richiesta, analisi, trascrizione, pulizia, sottotitoli,
  anteprima, revisione, esportazione finale. Principio "la skill propone e consiglia, l'utente decide".
- Cartella di lavoro `montaggio-video/` creata nella cartella da cui si avvia la skill, con profili,
  riprese, risultati a versioni numerate e file di lavoro.
- Profilo `base` con un file per formato (video lungo, shorts dal lungo, shorts indipendenti, reels).
- Script:
  - `verifica_strumenti.py`: controlla FFmpeg (con i filtri per l'HDR), Node, Python; crea l'ambiente
    Python della skill con Whisper.
  - `prepara_progetto.py`: cartelle e registrazione delle riprese, senza copiarle.
  - `analizza_video.py`: dati tecnici, riconoscimento HDR (HLG, PQ, Dolby Vision), fps nominali per le
    riprese a frequenza variabile, foglio di anteprime, confronto dei 3 operatori di conversione HDR,
    silenzi, audio per Whisper.
  - `trascrivi.py`: Whisper in locale parola per parola (mlx-whisper su Mac Apple Silicon,
    faster-whisper altrove), con prompt che conserva gli intercalari.
  - `pulizia.py`: taglio di intercalari, false partenze, frasi ripetute (tiene l'ultima) e pause lunghe;
    piano di montaggio modificabile e riepilogo dei tagli.
  - `sottotitoli.py`: SRT, ASS con stile e parole sulla timeline montata; stile a frase o parola per
    parola con evidenziazione.
  - `esporta.py`: esportazione sempre dagli originali, conversione HDR → SDR corretta, micro
    dissolvenze audio sui tagli, volume a -14 LUFS in due passaggi, riuso dei segmenti tra le versioni.
  - `controllo_finale.py`: risoluzione, fps, colori, durata, sincronia, volume.
- Font Geist convertiti in TTF statici (Regular, SemiBold, Bold, ExtraBold, Mono) per i sottotitoli.

### Integrato da `motion-broll` (motion-graphics, Bart, licenza MIT)
- Riconoscimento delle sezioni a schermo pieno e con riquadro (PiP) e degli spazi vuoti
  (`inspect_video.py` → `analizza_video.py`), con avviso se il riquadro cambia dimensione: servirà per
  posizionare i pannelli delle grafiche.
- Foglio di anteprime dei fotogrammi per capire cosa si vede.
- Stima dei tempi delle parole da un SRT (`words.py` → `trascrivi.py --srt`), come alternativa a Whisper.
- Regola "mai inventare numeri, prezzi, citazioni o risultati" (ora vale per tutta la skill).
- Stile e palette di base (grigio caldo, nero, bianco, accento arancione, font Geist) nel profilo `base`.
- Font Geist (licenza SIL OFL, `assets/fonts/OFL-Geist.txt`).
- Modifiche rispetto all'originale: conversione HDR prima delle analisi; script in Python senza comandi
  di shell costruiti con i nomi dei file; nomi e messaggi in italiano.

### Scartato da `motion-broll` e `object-separation`
- Link pubblicitari del README e GIF dimostrative: non servono alla skill.
- Anteprima composta sopra un video già esportato: qui tutto si rigenera dagli originali.
- Il motore di animazione, le pagine di confronto, gli esempi e la separazione del soggetto sono arrivati
  nella 0.9.0.
