# Cosa verificare sul Mac

La skill è stata costruita e provata in un computer Linux in cloud, con un video di prova sintetico in 4K
HDR (HLG). Lì funziona tutta la catena: analisi, pulizia, sottotitoli, effetti, transizioni, grafiche
Remotion e motore di animazione, mix audio, esportazione 4K e verticale, revisione, profili, DaVinci.
Alcune cose però si possono verificare solo sul Mac, con riprese vere. In ordine di importanza:

## 1. Prima installazione (10 minuti)

- [ ] Homebrew installato (https://brew.sh), poi `brew install ffmpeg node python git`.
- [ ] Installa il plugin: `claude plugin marketplace add elkartell00/Skill-Kartello-Montaggio-Video` e
      `claude plugin install montaggio-video@kartello-montaggio-video` (o dalla sessione con `/plugin`).
      Se la repository non è ancora rinominata, usa `elkartell00/Skills-Kartello-Video`.
- [ ] In una cartella di lavoro avvia Claude Code e chiedi "monta questo video". La skill deve controllare
      gli strumenti e chiedere il permesso di installare l'ambiente Python (Whisper, OpenCV).
- [ ] Prima volta che servono le grafiche: `grafiche.py prepara` (circa 400 MB). Remotion e Playwright
      scaricano da soli il loro browser.

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

- [ ] **Studio AI**: collega l'app (*Impostazioni → Collega a Claude Code*) e prova un B-roll, una musica
      e un effetto sonoro. Controlla che la skill mostri il costo stimato prima di generare.
- [ ] **Separazione del soggetto (SAM 2.1)**: `separa_soggetto.py prepara` (circa 2 GB) e una prova breve
      con `--prova`. Qui è stato provato solo il ritaglio trasparente con maschere finte.
- [ ] **Player di revisione scena per scena** in Safari o Chrome: il video si deve vedere (qui il browser
      di prova non leggeva l'H.264), modifiche, note, "Invia a Claude", ricarica automatica alla versione
      successiva.
- [ ] **Progetto DaVinci Resolve**: importa il file `.fcpxml` (File > Import > Timeline), poi i sottotitoli
      `.srt`. Controlla che le riprese siano collegate, che grafiche e B-roll siano sulle tracce giuste e che
      i marcatori siano leggibili. Il file XML è valido, ma l'importazione in DaVinci non si è potuta provare.
- [ ] **Grafiche su misura**: chiedi una grafica particolare (es. un grafico che cresce, una mappa): Claude deve scriverla in Remotion invece di usare Studio AI.
- [ ] **Licenza di Remotion**: gratuita per privati e aziende fino a 3 persone; oltre serve la licenza
      aziendale (remotion.pro). Verifica il tuo caso.

## 4. Da fare quando vuoi

- [ ] Rinominare la repository su GitHub in `Skill-Kartello-Montaggio-Video` (Settings → General).
- [ ] Creare i primi profili (canali, clienti) e mettere i video di riferimento in
      `montaggio-video/profili/<profilo>/riferimenti/`.
- [ ] Sul computer di tuo padre: stessa installazione; avrà i suoi profili. Se volete condividerli, si
      copia la cartella del profilo o si tiene `profili/` in una repository privata comune.
- [ ] Windows: non supportato per ora. Gli script sono in Python e Node e non dipendono dal Mac, quindi
      il passaggio sarà possibile più avanti (va provato e adattato: ambiente Python, mlx-whisper → faster-whisper,
      niente VideoToolbox).

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
