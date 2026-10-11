# Effetti disponibili

Il profilo decide quali usare e quanto: questa è la cassetta degli attrezzi, non una lista da usare
tutta. Un effetto deve avere un motivo (sottolineare una parola, cambiare ritmo, segnare un passaggio).
Se il profilo non dice niente, usali con misura e chiedi all'utente se ne vuole di più o di meno.

| Effetto | Dove si imposta | Uso tipico | Note |
|---|---|---|---|
| Zoom a scatto (punch-in) | segmento `zoom: {"tipo": "scatto", "a": 1.15–1.3, "inizio": s}` | enfasi su una parola, battuta, cambio di frase senza taglio | sulla parola esatta (tempo da `sottotitoli/<piano>-parole.json` meno inizio del segmento sulla timeline) |
| Zoom lento | segmento `zoom: {"tipo": "lento", "da": 1.0, "a": 1.08–1.15, "durata": s}` | tenere viva un'inquadratura lunga | con `cx`/`cy` si zooma verso un punto (il viso, il prodotto) |
| Tremolio di camera | segmento `tremolio: {"intensita": 0.005–0.015}` | energia, impatto, scene d'azione | breve: 1–3 s |
| Accelerazione / rallentamento | segmento `velocita` | accelerare una lavorazione, rallentare un dettaglio | sotto 0.5 servono riprese a 60/120 fps per restare fluidi |
| Speed ramp | 3–4 segmenti consecutivi della stessa ripresa con velocità che salgono o scendono (es. 1 → 2 → 4 → 1) | passaggi spettacolari in lavorazioni e timelapse | spezza il segmento con lo stesso `sorgente` e tempi contigui |
| Transizioni | segmento `transizione: {"tipo", "durata"}` | cambi di argomento, luogo o tempo | dissolvenza, flash, nero, glitch, scorri-*, frusta, zoom, cerchio, sfocatura, tendina |
| Look colore | piano `colore` (LUT `.cube`, contrasto, saturazione, luminosità, gamma) | look uniforme del profilo | vale per tutte le riprese, non per le grafiche |
| Effetti sonori sui tagli | `audio.effetti` con `inizio` 1–2 fotogrammi prima del taglio o dell'azione | whoosh su transizioni e zoom, pop su scritte, impact su un titolo | vedi [audio.md](audio.md) |
| Tagli a ritmo di musica | `battiti.py` dà i battiti: fai cadere tagli, entrate di B-roll e grafiche sui battiti (o sui forti) | sequenze di B-roll, intro, reels solo musica | sul parlato il ritmo lo dà la voce, non la musica |
| Finale a loop | ultimo segmento che si ricollega al primo (frase, gesto o inquadratura) | shorts indipendenti | vedi [shorts.md](shorts.md) |

## Combinazioni

- Zoom e tremolio si sommano allo stesso segmento.
- Transizioni e velocità diversa da 1 non si combinano: la transizione viene ignorata con un avviso.
- Gli zoom lavorano a piena risoluzione dalla ripresa 4K: fino a 1.3 la perdita di nitidezza in un video
  4K è minima; oltre, avvisa l'utente.

## Grafiche come effetti

Frecce, emoji, scritte, evidenziazioni e barre di avanzamento sono grafiche Remotion: vedi
[grafiche.md](grafiche.md).
