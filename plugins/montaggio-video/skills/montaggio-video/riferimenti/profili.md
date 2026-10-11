# Profili e apprendimento

È la parte più importante: la skill deve diventare sempre più dell'utente, montaggio dopo montaggio, così
la prima versione arriva sempre più vicina al risultato finale e le revisioni diminuiscono.

## Dove stanno

`montaggio-video/profili/` nella cartella da cui è stata avviata la skill. Un profilo per canale,
cliente o progetto:

```text
profili/<nome>/
  profilo.md              di cosa parla, formati attivi, stile, colori, font, colore delle riprese, audio, regole generali
  video-lungo.md          regole del formato (pulizia, sottotitoli, ritmo, grafiche, effetti, B-roll, musica)
  shorts-dal-lungo.md     solo i formati che il profilo usa
  shorts-indipendenti.md
  reels.md
  diario-revisioni.md     le correzioni dell'utente, leggibili
  diario.jsonl            le stesse, per le statistiche
  brand/                  logo, colori, materiali del brand
  riferimenti/            video di riferimento e la loro analisi
```

`base` è il profilo neutro di partenza e non si modifica. Gestione: `$PY $SKILL/scripts/profili.py`
(elenca, crea, copia, rinomina, elimina nel cestino, salva, storico, annulla).

## Creazione dei profili

- **Primo utilizzo** (`profili.py elenca` dice che c'è solo `base`): chiedi se l'utente vuole creare
  subito i suoi profili. Per ognuno: nome, di cosa parla il canale o il progetto, quali formati usa, e se
  ha una cartella di video di riferimento da analizzare. Poi stile e colori (vedi [grafiche.md](grafiche.md#stile-e-colori)).
- **Durante l'uso**, se l'utente nomina un profilo che non esiste ("monta questo per il cliente Rossi"):
  chiedi se crearlo nuovo (da `base`) o partire da un profilo esistente.
- **Nessun profilo indicato**: usa `base` e alla fine chiedi se salvare le scelte come nuovo profilo.
- Un profilo può avere solo alcuni formati: cancella i file dei formati che non usa e aggiorna
  "Formati attivi" in `profilo.md`.

## Video di riferimento

Quando l'utente mette in `profili/<nome>/riferimenti/` dei video che gli piacciono:

```bash
$PY $SKILL/scripts/video_riferimento.py --profilo <nome>
```

Misura durata, tagli al minuto (nei primi 5 secondi e nel resto), durata media delle inquadrature,
volume e quota di silenzio, e crea per ogni video un foglio dell'aggancio (primi 3 secondi) e un foglio
generale. Guarda i fogli e scrivi le regole nel file del formato giusto: ritmo dei tagli, durata,
aggancio iniziale, stile dei sottotitoli (dimensione, colore, posizione, quante parole), grafiche, uso
degli zoom, musica ed effetti sonori. Possono servire anche screenshot e descrizioni dell'utente.
Ispirarsi allo stile sì; copiare loghi, sigle, grafiche identiche o musiche no.

## Prima di ogni montaggio

Rileggi `profilo.md`, il file del formato e `diario-revisioni.md`: anche gli indizi (correzioni
specifiche) aiutano a evitare errori già visti. La prima versione deve già tenerne conto.

## Durante la revisione: annotare

Per ogni correzione dell'utente (in chat o dal player):

```bash
$PY $SKILL/scripts/diario.py aggiungi --profilo <nome> --progetto <progetto> --formato <formato> \
    --categoria sottotitoli --richiesta "sottotitoli più piccoli" --situazione "coprivano il viso nei primi piani" \
    --tipo generale --dimensione piccola
```

- `--tipo generale`: preferenza chiara e valida sempre ("sottotitoli più piccoli", "meno zoom");
  `--tipo specifica`: legata a questo video ("togli la grafica al minuto 2").
- `--dimensione`: piccola (un ritocco), media (una parte da rifare), grande (cambia il montaggio).
- `--chi`: chi ha chiesto la correzione, se lo sai (l'utente o suo padre).
- Ogni anteprima: `diario.py versione --profilo <nome> --progetto <p> --piano <piano> --versione vNN`.

## A fine lavoro: aggiornare il profilo

1. **Preferenze generali e chiare**: salvale subito nel profilo (file del formato o `profilo.md`) e
   mostra all'utente un breve riepilogo di cosa è cambiato. Poi
   `profili.py salva --nome <nome> --messaggio "<cosa è cambiato>"`.
2. **Correzioni specifiche**: restano nel diario come indizio, senza diventare regola.
3. **Correzioni ricorrenti**: quando la stessa correzione torna in più lavori (`diario.py` lo segnala dal
   terzo lavoro; anche prima se è evidente), diventa una regola fissa del profilo. Dillo all'utente.
4. **Contraddizioni**: se una nuova preferenza contraddice una regola esistente, segnalalo e chiedi quale
   tenere. Non sovrascrivere in silenzio.

Scrivi le regole in modo concreto e misurabile ("sottotitoli all'altezza 0.04, massimo 3 parole",
"zoom a scatto al massimo uno ogni 20 secondi, 1.15"), con il motivo se l'utente l'ha detto.

## Misurare il miglioramento

```bash
$PY $SKILL/scripts/diario.py statistiche --profilo <nome>
```

Mostra revisioni e peso delle correzioni per lavoro nel tempo e le categorie ricorrenti. Mostralo ogni
tanto (per esempio ogni 5 lavori) o quando l'utente lo chiede. Se le revisioni scendono, la skill sta
imparando. Se restano alte su una categoria, proponi come correggere il profilo.

## Sicurezza delle modifiche

- Ogni aggiornamento del profilo si salva con data e descrizione (`profili.py salva`): con git se c'è,
  altrimenti con copie datate. `profili.py storico` mostra le modifiche, `profili.py annulla` annulla
  l'ultima (o quella indicata).
- Il padre dell'utente usa la skill dal suo computer: ha la sua cartella `montaggio-video/` e i suoi
  profili, che migliorano con le sue correzioni. Se vogliono condividere un profilo, basta copiarne la
  cartella (o tenere `profili/` in una repository privata comune).
