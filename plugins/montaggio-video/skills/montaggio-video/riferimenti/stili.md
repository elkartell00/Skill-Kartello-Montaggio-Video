# Imparare dagli esempi: la libreria degli stili

L'utente ti dà esempi di video, motion graphics o effetti che gli piacciono. Tu impari **lo stile** e lo
rifai con **i suoi colori, il suo brand, i suoi contenuti e il suo modo di fare i video**. Ogni stile
imparato resta nella libreria e si riusa: più esempi ti dà, più cose sai fare. Insieme al diario delle
revisioni ([profili.md](profili.md)) è il modo in cui la skill diventa sempre più dell'utente.

- **Stile** = linguaggio del movimento e della grafica: forme, entrate e uscite, tempi, andamento,
  tipografia, impaginazione, transizioni, effetti, ritmo dei tagli.
- **Contenuto** = colori, logo, testi, immagini, personaggi, musica dell'esempio. **Non si copia**: si
  sostituisce con quello dell'utente (colori e font dal profilo, testi da ciò che dice nel video).

## Dove sta

`montaggio-video/stili/`, comune a tutti i profili (un profilo può dire quali stili preferisce).
`stili/INDICE.md` elenca gli stili imparati: **leggilo nel piano creativo di ogni video** per proporre
all'utente gli stili adatti. Un esempio di stile finito è in `$SKILL/esempi/stili/pillola-che-si-trasforma/`.

## Quando l'utente dà un esempio

1. **L'esempio**: un file video (o una cartella di esempi) e, se serve, il tratto che gli piace (da–a).
   Se ti dà un link, chiedigli di scaricare il video o di metterlo in una cartella: lo usi solo come
   riferimento di stile.
2. **Analisi**:
   ```bash
   $PY $SKILL/scripts/stili.py analizza --nome <nome-stile> --video <esempio> [--da 12.0 --a 18.5]
   ```
   Crea `stili/<nome>/esempio/`: copia ridotta del tratto, fogli con 8 fotogrammi al secondo (si vedono
   le fasi di ogni movimento), tagli, raffiche di movimento con durata e andamento (ease-out, ease-in,
   ease-in-out), palette. Nome breve e descrittivo (`titoli-pop`, `sottotitoli-karaoke`, `zoom-a-frusta`).
   Se assomiglia molto a uno stile già in libreria, proponi di farne una variante di quello.
3. **Scomposizione**: guarda tutti i fogli e compila `stili/<nome>/stile.md` (il modello è già creato):
   elementi, entrate e uscite, tempi in fotogrammi, andamento, tipografia, impaginazione, ruoli dei
   colori, effetti e suono, e se l'esempio insegna anche un modo di montare (ritmo dei tagli, zoom,
   transizioni, sottotitoli).
4. **Riproduzione con il codice** (regola dell'utente: prima il codice, sempre):
   - grafiche e animazioni: componente Remotion in `stili/<nome>/componenti/index.tsx` che esporta
     `COMPOSIZIONI` (id, componente, proprietà di esempio), parametrico: colori da `stile` (profilo), testi
     e tempi da proprietà. Importa da `../../comune` e `../../su-misura`. Guarda l'esempio di stile nella skill;
   - B-roll animato "a forma unica": anche come `clip-modello.html` del motore di animazione;
   - stili di montaggio (ritmo, zoom, transizioni, sottotitoli): regole e valori nella scheda, da
     applicare con il piano di montaggio e i sottotitoli.
5. **Prova e confronto**: `$PY $SKILL/scripts/stili.py sincronizza`, poi render con **i colori
   dell'esempio** (per giudicare lo stile) e confronto affiancato:
   ```bash
   $PY $SKILL/scripts/grafiche.py remotion <Id> props.json montaggio-video/stili/<nome>/prove/riproduzione.mp4
   $PY $SKILL/scripts/stili.py confronta --nome <nome> --video montaggio-video/stili/<nome>/prove/riproduzione.mp4
   ```
   Guarda il foglio: forme, tempi, andamento e impaginazione devono corrispondere. Correggi e ripeti
   finché sono uguali (lo sfondo nero a destra è la trasparenza). Poi render con **i colori del profilo**.
6. **Mostra all'utente** la riproduzione con i suoi colori, accanto all'esempio. Correggi su sua indicazione.
7. **Salva**: scrivi il suo giudizio nella scheda, poi
   `$PY $SKILL/scripts/stili.py salva --nome <nome> --messaggio "<da quale esempio, cosa è stato imparato>"`
   (aggiorna l'indice e registra la modifica con data, annullabile come per i profili).

## Usare gli stili imparati

- Nel piano creativo leggi `stili/INDICE.md` e proponi per ogni momento lo stile adatto (o due), con il
  perché; l'utente decide. Gli stili che preferisce vanno nel profilo ("titoli: stile titoli-pop").
- Render come qualsiasi grafica: `grafiche.py remotion <Id> props.json uscita.mov` con `stile` = colori
  del profilo e i testi del video; poi nel piano come sovrapposizione.
- Dopo l'uso aggiungi alla scheda: data, progetto, cosa ha detto l'utente. Se l'utente corregge uno
  stile, correggi il componente (vale per tutti i video successivi) e salva.
- Se uno stile non funziona su un formato (es. verticale), crea la variante e annotala.

## Limiti onesti

- Si impara ciò che si vede: effetti 3D complessi, particelle fotorealistiche o riprese vere non si
  rifanno con il codice. In quei casi dillo e proponi l'alternativa più vicina; Studio AI solo come
  ultima risorsa e con il costo mostrato prima.
- La prima riproduzione raramente è perfetta: il confronto affiancato serve proprio a correggerla.
