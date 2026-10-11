# Audio: voce, musica, effetti sonori

## Da dove arrivano musica ed effetti

Dall'app **Studio AI** dell'utente, attraverso il suo server MCP `studio-ai` (vedi [studio-ai.md](studio-ai.md)).
**Regola d'oro: prima cerca, poi genera solo ciò che manca.**

1. `cerca_suoni` (gratis) nelle librerie Suoni e Musiche: per gli effetti cerca in italiano o inglese
   ("whoosh", "pop", "impact"); per la musica `categoria: "musica"`. Poi `usa_suono` per copiarlo in
   `montaggio-video/media/<progetto>/audio/` (con `durata` per accorciarlo).
2. Se manca:
   - effetti: `genera_effetto_sonoro` con `durata` sempre indicata (whoosh/pop/click 1–2 s, impact 2–3 s,
     riser 3–6 s), prompt in inglese, concreto;
   - musica: `genera_musica` 60–120 s, strumentale, prompt in inglese (genere, atmosfera, strumenti, BPM,
     energia, "unobtrusive under voiceover"), niente artisti reali.
   Mostra prima il costo stimato (`stima_costo`) se generi più di qualche elemento.
3. **Sottofondo della durata esatta:** `crea_sottofondo` (gratis) con la musica e `durata` = durata della
   timeline (o `video` = l'anteprima): ripete solo il corpo del brano senza stacchi, con dissolvenze. Usa
   la traccia ottenuta (senza `mixa`), così il mix lo fa `esporta.py` dagli originali.
4. Se il profilo ha cartelle di musica o effetti propri senza diritti, puoi usarli in alternativa.

Se `studio-ai` non risponde: l'utente deve collegare l'app (nell'app: *Impostazioni → Collega a Claude
Code*) e riaprire la sessione. Non usare altri servizi.

## Nel piano

```json
"audio": {
  "voce": {"pulizia": true},
  "musica": [{"file": "media/p/audio/sottofondo.mp3", "inizio": 0, "fine": 0, "volume_db": -18,
              "dissolvenza_in": 1.0, "dissolvenza_out": 2.0, "abbassa_sotto_voce": true}],
  "effetti": [{"file": "media/p/audio/whoosh.mp3", "inizio": 12.35, "volume_db": -8}]
}
```

- `fine: 0` = fino alla fine del video. Più brani in sequenza: più voci in `musica` con `inizio`/`fine`.
- `volume_db` della musica: -18/-22 sotto il parlato, -8/-12 per parti solo musica (reels senza voce).
- `abbassa_sotto_voce`: la musica si abbassa da sola quando si parla (compressione comandata dalla voce)
  e risale nelle pause.
- `ripeti: true` ripete il file se è più corto (meglio un sottofondo fatto con `crea_sottofondo`).
- `voce.pulizia`: taglio dei bassi sotto 80 Hz, riduzione del rumore di fondo, compressione leggera:
  utile con il microfono dell'iPhone. Ascolta l'anteprima: se la voce suona "metallica", toglila.
- Effetti sonori: il picco va sul taglio o sull'azione (1–2 fotogrammi prima). Volume -6/-12 dB.

## Volume finale

`esporta.py` misura il mix completo e lo porta a -14 LUFS (picchi sotto -1,5 dBTP) con due passaggi:
il livello di YouTube e Instagram. Il controllo finale lo verifica.

## Tagli a tempo di musica

```bash
$PY $SKILL/scripts/battiti.py montaggio-video/media/<progetto>/audio/sottofondo.mp3 --json .lavoro/<progetto>/battiti.json
```

Restituisce i BPM, i battiti e i battiti forti (inizio battuta) in secondi dall'inizio del file: somma
l'`inizio` della musica sulla timeline per usarli.
