# Grafiche, testi e sottotitoli animati

Due motori, ognuno per il suo compito. **Non scegliere da solo:** in base al contesto proponi
all'utente il motore che consigli per quel punto, con l'alternativa e il perché, e lascia a lui
l'ultima parola. La scelta può restare salvata nel profilo ("titoli sempre con Remotion").

| | Remotion | Motore di animazione (motion-broll) |
|---|---|---|
| Serve per | titoli, scritte, etichette, frecce, emoji, barra di avanzamento, sottotitoli animati | B-roll animato: spiegare un processo, un confronto, un numero, un'interfaccia con un'unica forma che si trasforma, guidata da un cursore |
| Come si usa | componenti pronti con proprietà (JSON) | una pagina HTML per clip, scritta su misura ([broll-animato.md](broll-animato.md)) |
| Uscita | `.mov` ProRes 4444 trasparente a piena risoluzione | `.mp4` a tutto fotogramma o `.mov` trasparente (pannello) |
| Licenza | gratuito per privati e aziende fino a 3 persone; oltre serve la licenza aziendale (remotion.pro). Dillo all'utente la prima volta | MIT, gratuito |

Preparazione (una volta, chiedi prima all'utente): `$PY $SKILL/scripts/grafiche.py prepara`.
Installa in `montaggio-video/.strumenti/grafiche/` Remotion, Playwright e Chromium (circa 400 MB).

Tutte le grafiche si salvano in `montaggio-video/media/<progetto>/` e si aggiungono al piano come
`sovrapposizioni` (vedi [piano.md](piano.md)). Restano file separati a piena risoluzione: vanno anche
nel progetto DaVinci.

## Remotion

```bash
$PY $SKILL/scripts/grafiche.py remotion <Tipo> props.json montaggio-video/media/<progetto>/<nome>.mov
```

Ogni `props.json` contiene sempre `larghezza`, `altezza`, `fps` (numero, es. 29.97) e `durata`
(secondi), uguali al formato del montaggio, più `stile` dal profilo:
`{"font": "Geist", "colore": "#0B0B0B", "accento": "#FF5A1F", "sfondo": "#FFFFFF", "contorno": "#0B0B0B"}`.
Dimensioni del testo in frazioni dell'altezza (0.06 = 6%); posizioni in frazioni (0–1).

| Tipo | Proprietà |
|---|---|
| `Titolo` | `testo`, `sottotitolo`, `posizione` (centro/alto/basso), `entrata` (pop/scorri/macchina), `dimensione`, `conFondo` |
| `Scritta` | `testo`, `x`, `y`, `forma` (pillola/etichetta/evidenziatore), `icona` (emoji), `dimensione` |
| `Freccia` | `da: [x, y]`, `a: [x, y]`, `curva` (-1..1), `spessore`, `colore` |
| `Emoji` | `emoji`, `x`, `y`, `dimensione`, `dondola` |
| `Barra` | `posizione` (alto/basso), `spessore`, `colore`, `fondo`: barra di avanzamento per tutta la durata |
| `Sottotitoli` | `parole` (da `parole-timeline.json`), `parolePerBlocco`, `maiuscolo`, `y`, `dimensione`, `animazione` (pop/nessuna), `coloreTesto` |

Il render di una grafica breve richiede da qualche secondo a un minuto. Controlla sempre un fotogramma
(sovrapposto a un fotogramma del video) prima di metterla nel piano.

### Sottotitoli: ASS o Remotion?

- **ASS** (`sottotitoli.py`): istantanei, parola evidenziata, nessun movimento. Adatti a tutto, video
  lunghi compresi.
- **Remotion** (`Sottotitoli`): parola che "salta" con un piccolo pop, più vivace. Per shorts e reels
  (fino a qualche minuto: il render è più lento). Si mettono come sovrapposizione `sopra` per tutta la
  durata e si esporta con `--sottotitoli no` per non averli doppi.

Proponi all'utente l'opzione adatta e salva la scelta nel profilo.

## Stile e colori

Stile e colori sono due scelte separate. Lo stile è il modo di muoversi e di apparire: forma unica di
motion-broll, pillole pulite, testi grandi e vivaci, minimale. I colori sono la palette. Quando un
profilo non ha ancora deciso, o l'utente porta un logo o un brand:
1. guarda il logo, le immagini o il sito del brand che ti dà (mettili in `montaggio-video/profili/<profilo>/brand/`);
2. proponi **lo stile** che consigli per quel contesto più due alternative, e **la palette** ricavata dal
   brand (testo, accento, fondo, contorno; un solo accento forte), più l'opzione "scegli tu";
3. prima di renderizzare tutto, mostra una grafica di prova sovrapposta a un fotogramma vero;
4. salva stile e colori nel profilo.

Regole dello stile base (motion-broll): niente rimbalzi vistosi, particelle, bagliori, sfumature sui
componenti, icone con spessori diversi, tempi morti, dati inventati, niente che sembri un modello già visto.
