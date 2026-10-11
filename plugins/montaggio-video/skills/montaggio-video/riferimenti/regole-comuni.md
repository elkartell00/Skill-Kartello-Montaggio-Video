# Regole comuni

Valgono per tutti i profili e i formati, salvo quando il profilo dell'utente dice diversamente: lo stile
imparato dall'utente ha sempre la precedenza.

## Cartelle

Tutto sta in `montaggio-video/`, dentro la cartella da cui è stata avviata la skill:

```text
montaggio-video/
  profili/<profilo>/              profilo.md, un file per formato, diario delle revisioni, brand/, riferimenti/
  da-montare/<progetto>/          le riprese: si leggono e basta, mai modificate, spostate o rinominate
    broll/                        riprese extra (dettagli, lavorazioni, timelapse, prodotti)
  media/<progetto>/               grafiche, animazioni, B-roll generati, musica ed effetti del progetto
  risultati/<progetto>/<piano>/   un montaggio (video-lungo, short-1, reel-1...):
    vNN/                          una cartella per versione: anteprima, video finale, sottotitoli, piano usato,
                                  controllo, pagine di revisione, progetto DaVinci
    reel.json                     per il player di revisione scena per scena
  .lavoro/<progetto>/             analisi, audio per Whisper, trascrizione, piani/, sottotitoli/, segmenti già
                                  codificati, separazione del soggetto
  .strumenti/                     ambiente Python (venv) e strumenti per le grafiche
```

- Le riprese possono stare anche altrove: `prepara_progetto.py --video` registra il percorso senza copiare.
- `.lavoro/` si può cancellare a lavoro finito per liberare spazio (i segmenti 4K occupano molto).
  Prima di farlo chiedi all'utente.
- Se l'utente lavora in un'altra cartella avrà profili separati: per riusarli basta copiare `profili/`.

## Pulizia del parlato

- **Intercalari** ("ehm", "uhm", "mmm"): si tagliano. "eh" e "ah" solo quando sono isolati da pause,
  perché in italiano spesso hanno un senso ("eh sì", "ah, ecco").
- **Frasi ripetute e false partenze**: si tiene la ripresa migliore, di solito l'ultima. Controlla però
  il senso: un'enfasi voluta ("molto, molto importante") o un elenco non sono ripetizioni.
- **Pause**: quelle lunghe si accorciano lasciando un respiro naturale (valori nel file del formato).
  Una pausa voluta prima di una battuta o di una rivelazione si lascia: se la riconosci, rimettila.
- **Tagli puliti**: ogni taglio cade su un fotogramma intero e ha una micro dissolvenza audio di 10 ms,
  così non si sentono "click". Il margine prima e dopo la voce evita di mangiare le consonanti.
- Whisper a volte non trascrive un "ehm" o lo attacca alla parola vicina: se nell'anteprima ne senti
  parlare l'utente, sposta a mano il confine del segmento nel piano.

## Piano di montaggio

Il piano (`.lavoro/<progetto>/piani/<piano>.json`) è la fonte di verità del montaggio: segmenti (ripresa,
inizio, fine, testo, effetti), tagli con il motivo, sovrapposizioni (grafiche, B-roll, testi), audio,
correzioni dei sottotitoli. Formato completo in [piano.md](piano.md).
- È leggibile e modificabile: per una revisione si cambia il piano e si riesporta.
- I tempi dei segmenti sono nel tempo della ripresa originale; quelli delle sovrapposizioni nel tempo
  della timeline montata (`sottotitoli/<piano>-parole.json` dà i tempi delle parole sulla timeline).
- Ogni versione in `risultati/` contiene una copia del piano usato: si può tornare indietro.

## Revisioni

- Si cambia solo quello che l'utente ha chiesto.
- Ogni revisione è una nuova versione numerata, rigenerata dagli originali.
- Ogni correzione va nel diario delle revisioni del profilo: è così che la skill impara.

## Messaggi

- In italiano, brevi, senza gergo. Al posto di "LUFS" dì "volume", al posto di "tonemap" dì
  "conversione dei colori HDR", e spiega in una frase quando serve.
- In caso di errore: cosa è successo, perché (se lo sai) e cosa fare. Gli script stampano già errori
  in italiano: riportali con parole semplici, non incollare l'output tecnico.
- A fine lavoro: dove sono i file, durata prima/dopo, cosa hai fatto, cosa chiedi all'utente.

## Grafiche e contenuti

- Mai inventare numeri, prezzi, citazioni o risultati. Barre relative, righe segnaposto o parole dalla
  trascrizione; i dati veri si mettono solo se li dà l'utente.
- Ispirarsi a uno stile sì; copiare loghi, sigle, grafiche identiche o musiche altrui no.
