# Cosa verificare sul Mac

La skill è stata costruita e provata in un computer Linux in cloud, con un video di prova sintetico in 4K
HDR (HLG). Lì funziona tutta la catena: analisi, pulizia, sottotitoli, effetti, transizioni, grafiche
Remotion e motore di animazione, mix audio, esportazione 4K e verticale, revisione, profili, DaVinci.
Alcune cose però si possono verificare solo sul Mac, con riprese vere. In ordine di importanza:

## 1. Prima installazione (10 minuti)

- [ ] Homebrew installato (https://brew.sh), poi `brew install ffmpeg-full node python@3.12 git`.
      Serve `ffmpeg-full` (il normale `ffmpeg` non ha zscale per l'HDR né libass per i sottotitoli);
      Python 3.12 perché il `python3` del Mac è spesso il vecchio 3.9.
- [ ] Installa il plugin: `claude plugin marketplace add elkartell00/Skill-Kartello-Montaggio-Video` e
      `claude plugin install montaggio-video@kartello-montaggio-video` (o dalla sessione con `/plugin`).
- [ ] In una cartella di lavoro avvia Claude Code e chiedi "monta questo video". La skill deve controllare
      gli strumenti e chiedere il permesso di installare l'ambiente Python (Whisper, OpenCV).
- [ ] Prima volta che servono le grafiche: `grafiche.py prepara` (circa 400 MB). Remotion e Playwright
      scaricano da soli il loro browser; se `remotion.media` non è raggiungibile, Remotion usa quello
      di Playwright.

## 2. Da provare con una ripresa vera dell'iPhone (la cosa più importante)

- [ ] **Colori HDR → SDR**: confronta i tre operatori (`hdr-confronto-NN.jpg`) con la ripresa vista sul
      telefono. Scegli quello che rende meglio la pelle e il soggetto e salvalo nel profilo. Se nessuno va
      bene, dimmelo: si possono regolare parametri e luminosità.
- [ ] **Trascrizione italiana con mlx-whisper**: qualità delle parole, tempi, e soprattutto se tiene gli
      "ehm" (servono per tagliarli). Qui in cloud non è stato possibile scaricare il modello.
- [ ] **Pulizia**: tagli delle pause, degli "ehm", delle frasi ripetute. Controlla che non mangi l'inizio o
      la fine delle parole (eventualmente si alza il margine nel profilo).
- [ ] **Riprese verticali e a frequenza variabile**: rotazione corretta, fps giusti, sincronia audio.
- [ ] **Velocità**: decodifica hardware del Mac attiva (VideoToolbox). Prova anche `--encoder videotoolbox`
      per l'export finale e confronta tempi e qualità con quello predefinito.
- [ ] **Riinquadratura 9:16 che segue il volto**: provata qui solo con un percorso simulato (il video di
      prova non ha volti). Controlla che segua bene e senza scatti.

## 3. Funzioni che richiedono il tuo Mac

- [x] **Studio AI**: collegato. Si usa solo quando la versione fatta col codice non basta: in quel caso
      la skill deve mostrare il costo stimato prima di generare.
- [ ] **Separazione del soggetto (SAM 2.1)**: `separa_soggetto.py prepara` (circa 2 GB) e una prova breve
      con `--prova`. Qui è stato provato solo il ritaglio trasparente con maschere finte.
- [ ] **Player di revisione scena per scena** in Safari o Chrome: il video si deve vedere (qui il browser
      di prova non leggeva l'H.264), modifiche, note, "Invia a Claude", ricarica automatica alla versione
      successiva.
- [ ] **Imparare da un esempio**: dai alla skill un video con titoli o grafiche che ti piacciono ("impara questo stile"). Deve analizzarlo, rifarlo con il codice, mostrarti il confronto affiancato e la versione con i tuoi colori, e salvarlo in `montaggio-video/stili/`. Poi, in un video successivo, deve proportelo da sola.
- [ ] **Grafiche su misura**: chiedi una grafica particolare (es. un grafico che cresce, una mappa): Claude deve scriverla in Remotion invece di usare Studio AI.
- [x] **Licenza di Remotion** (verificata: uso da solo, gratuita): gratuita per privati e aziende fino a 3 persone; oltre serve la licenza
      aziendale (remotion.pro). Verifica il tuo caso.

## 4. In riserva

- [ ] **Progetto DaVinci Resolve** (per ora non si usa: la skill lo crea solo su richiesta): importa il file `.fcpxml` (File > Import > Timeline), poi i sottotitoli
      `.srt`. Controlla che le riprese siano collegate, che grafiche e B-roll siano sulle tracce giuste e che
      i marcatori siano leggibili. Il file XML è valido, ma l'importazione in DaVinci non si è potuta provare.

## 5. Da fare quando vuoi

- [ ] Rinominare la repository su GitHub in `Skill-Kartello-Montaggio-Video` (Settings → General).
- [ ] Creare i primi profili (canali, clienti) e mettere i video di riferimento in
      `montaggio-video/profili/<profilo>/riferimenti/`.
- [ ] Sul computer di tuo padre: stessa installazione; avrà i suoi profili. Se volete condividerli, si
      copia la cartella del profilo o si tiene `profili/` in una repository privata comune.
- [ ] Windows: non supportato per ora. Gli script sono in Python e Node e non dipendono dal Mac, quindi
      il passaggio sarà possibile più avanti (va provato e adattato: ambiente Python, mlx-whisper → faster-whisper,
      niente VideoToolbox).

## Esito della prima installazione sul Mac (12 ottobre 2026, Apple Silicon)

| Cosa | Esito |
|---|---|
| FFmpeg | `ffmpeg-full` 9.0.2: tutti i filtri ok (zscale, tonemap, subtitles, xfade...), ProRes 4444 e VideoToolbox ok |
| Ambiente Python | Python 3.12 con numpy, OpenCV 4 e mlx-whisper ok |
| Whisper | modello `whisper-large-v3-turbo` scaricato; frase italiana trascritta perfetta, parola per parola, in 8 s. Da verificare con una ripresa vera: gli "ehm" |
| SAM 2.1 | modello `sam2.1-hiera-base-plus` scaricato e caricato sul chip del Mac (serviva `torchvision`, ora corretto). Da provare su una ripresa |
| Grafiche | Remotion ok con il browser di Playwright (quello di Remotion qui resta fermo); titolo ProRes 4444 trasparente in 9 s. Motore di animazione: browser ok |
| Studio AI | collegato, spesa del mese leggibile |
| Ancora da fare | tutto ciò che richiede una ripresa vera (sezione 2), player di revisione |

## Cosa NON è stato possibile provare qui

| Cosa | Perché | Dove si verifica |
|---|---|---|
| Whisper (trascrizione vera) | il download del modello è bloccato nell'ambiente cloud | sezione 2 |
| Colori HDR su riprese vere | video di prova sintetico | sezione 2 |
| Rilevamento dei volti | nessun volto nel video di prova | sezione 2 |
| SAM 2.1 | download del modello bloccato | sezione 3 |
| Studio AI | è un'app del tuo Mac | sezione 3 |
| Importazione in DaVinci | DaVinci non c'è nel cloud | sezione 3 |
| Video nel player di revisione | il browser di prova non legge l'H.264 | sezione 3 |
