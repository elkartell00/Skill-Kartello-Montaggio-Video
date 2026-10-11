# Registro delle modifiche

Ogni modifica alla skill, comprese le parti integrate da altre skill (con la fonte e il motivo).

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
- Il motore di animazione, le pagine di confronto, gli esempi e la separazione del soggetto non sono
  scartati: arrivano nelle tappe 2–4.
