# Skill Kartello Montaggio Video

Marketplace di plugin per [Claude Code](https://code.claude.com) con le skill di Kartello per il montaggio video.

## Cosa fa

Trasforma Claude Code in un montatore: dalle riprese grezze (iPhone 4K, anche HDR) a video lunghi YouTube,
Shorts e Reels con tagli di pause ed "ehm", sottotitoli, B-roll (riprese proprie, Studio AI, grafiche
animate), titoli e grafiche, zoom, transizioni, musica ed effetti sonori. Esporta sempre dagli originali,
crea il progetto per DaVinci Resolve, si corregge su indicazione (anche scena per scena in un player nel
browser) e impara lo stile di ogni canale o cliente in profili che migliorano a ogni revisione.

## Struttura

```text
.claude-plugin/marketplace.json            catalogo del marketplace "kartello-montaggio-video"
plugins/montaggio-video/
  .claude-plugin/plugin.json               manifest del plugin (versione)
  skills/montaggio-video/
    SKILL.md                               flusso di lavoro
    CHANGELOG.md                           ogni modifica, comprese le skill integrate
    riferimenti/                           guide per ogni passaggio (piano, grafiche, audio, B-roll, shorts, profili...)
    scripts/                               script Python (analisi, trascrizione, pulizia, esportazione, DaVinci...)
    profili/base/                          profilo di partenza
    grafiche-remotion/                     progetto Remotion (titoli, scritte, frecce, sottotitoli animati)
    motore-animazioni/                     motore del B-roll animato (da motion-broll)
    revisione-player/                      player di revisione scena per scena (da Motion OS)
    modelli-pagine/, esempi/, assets/      pagine di confronto, esempi, font
templates/SKILL.template.md                modello per nuove skill
VERIFICHE-MAC.md                           cosa verificare sul Mac
```

## Installazione

Da un terminale con Claude Code:

```bash
claude plugin marketplace add elkartell00/Skill-Kartello-Montaggio-Video
claude plugin install montaggio-video@kartello-montaggio-video
```

Oppure dentro una sessione: `/plugin marketplace add elkartell00/Skill-Kartello-Montaggio-Video`, poi `/plugin install montaggio-video@kartello-montaggio-video`.

La skill si richiama con `/montaggio-video:montaggio-video`, oppure Claude la usa da sola quando chiedi di montare un video ("monta questo video per [profilo], versione lunga più 3 shorts").

Requisiti sul Mac: [Homebrew](https://brew.sh), poi `brew install ffmpeg node python git`. Al primo utilizzo la skill controlla gli strumenti e, se gli dai il permesso, installa Whisper in un ambiente Python suo, dentro la cartella di lavoro `montaggio-video/`.

## Sviluppo

Provare il plugin senza installarlo:

```bash
claude --plugin-dir ./plugins/montaggio-video
```

Validare marketplace e plugin prima di ogni push:

```bash
claude plugin validate .
claude plugin validate ./plugins/montaggio-video
```

Per aggiungere una skill: copia `templates/SKILL.template.md` in `plugins/montaggio-video/skills/<nome-skill>/SKILL.md` e compila i campi.
Per integrare una skill esistente in montaggio-video segui `riferimenti/integrare-skill.md`.

Le parti integrate da altre skill mantengono la loro licenza (MIT): vedi i file `LICENSE-*.txt` nella cartella della skill.
