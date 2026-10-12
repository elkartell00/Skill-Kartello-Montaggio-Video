# B-roll

Il B-roll copre il parlato con immagini che mostrano ciò di cui si sta parlando. Ordine di preferenza
(il profilo può cambiarlo):

1. **Le riprese extra dell'utente** (dettagli, lavorazioni, timelapse, prodotti): sono vere e sue, quindi
   sempre la prima scelta.
2. **Creato con il codice da te**: B-roll animato con il motore di motion-broll (processi, confronti,
   numeri, interfacce, [broll-animato.md](broll-animato.md)), grafiche Remotion pronte o **su misura**
   scritte per quel punto (schemi, grafici, mappe, liste, prima/dopo, citazioni, illustrazioni con forme e
   icone, testi cinetici, [grafiche.md](grafiche.md#grafiche-su-misura)). Provaci in ogni modo prima di
   passare oltre: è la regola dell'utente.
3. **Archivi gratuiti** (Pexels, Pixabay), solo se il profilo li prevede.
4. **Studio AI**, ultima risorsa (vedi [studio-ai.md](studio-ai.md)): solo quando con il codice non si
   arriva (una scena realistica, un ambiente, un oggetto fotografico che nessuna ripresa mostra) oppure
   quando l'utente ha visto la versione fatta col codice e non lo convince; sempre se l'idea si può
   mostrare senza ingannare. Prima mostra il costo e aspetta il sì.

## Flusso

1. **Indice delle riprese extra:**
   ```bash
   $PY $SKILL/scripts/broll.py indice --progetto <nome>   # cerca in da-montare/<nome>/broll/
   ```
   Guarda i fogli `broll-NN.jpg` e scrivi in `indice.json` una descrizione breve di ogni clip.
2. **Punti da coprire:** leggi la trascrizione (`<piano>-parole.json` per i tempi sulla timeline) e trova
   le frasi che descrivono qualcosa da vedere. Non coprire: aggancio iniziale, frasi personali o
   emotive, momenti in cui conta l'espressione del volto. Ogni B-roll 2–6 s, sulla frase che lo nomina.
3. **Proposta all'utente**, prima di generare o scaricare: una tabella
   `| # | Entra–Esce | Frase | Cosa mostra | Fonte (propria / codice / archivio / Studio AI) | Costo |`
   con il **costo totale stimato** dei contenuti AI. Aspetta il sì.
4. **Prepara i file** in `montaggio-video/media/<progetto>/broll/`:
   - proprie: usale direttamente dal percorso originale (non copiarle); `inizio_file` sceglie il tratto;
   - codice: render con `grafiche.py` (Remotion) o con il motore di animazione, e mostralo all'utente;
   - Studio AI (solo ciò che il codice non può fare o che col codice non ha convinto): un solo `genera_lotto` (vedi studio-ai.md); mentre Veo lavora prepara il resto;
   - archivi: `broll.py archivi --cerca "..." --orientamento orizzontale|verticale` (serve la chiave dell'utente).
5. **Nel piano:** una sovrapposizione per B-roll, `modo: "pieno"` (o `riquadro` per un dettaglio in
   un angolo), `dissolvenza: 0.1–0.2` se il profilo la vuole, altrimenti taglio netto.
6. Effetto sonoro sul B-roll se aiuta (un fruscio, un colpo): `audio.effetti`.

## Regole

- Il B-roll deve corrispondere a quello che si dice in quel momento, non solo all'argomento generale.
- Mai far passare un contenuto generato per una ripresa vera di un fatto, di un prodotto reale o di un
  risultato dell'utente: in quei casi serve la ripresa vera, o un'animazione dichiaratamente illustrativa.
- Formato: le clip devono essere dello stesso orientamento del montaggio; una clip orizzontale in un
  verticale viene ritagliata al centro (`modo: "pieno"`): controlla che il soggetto resti dentro.
- Le riprese iPhone HDR usate come B-roll vengono convertite con la stessa conversione del video.
- L'audio dei B-roll non entra nel mix.
