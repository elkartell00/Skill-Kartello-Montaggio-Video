# Skill Kartello Montaggio Video

Marketplace di plugin per [Claude Code](https://code.claude.com) con le skill di Kartello per il montaggio video.

## Struttura

```text
.claude-plugin/
  marketplace.json              # catalogo del marketplace "kartello-montaggio-video"
plugins/
  montaggio-video/
    .claude-plugin/plugin.json  # manifest del plugin
    skills/
      <nome-skill>/
        SKILL.md                # istruzioni della skill (obbligatorio)
        reference.md            # dettagli caricati solo se servono (opzionale)
        scripts/                # script eseguiti dalla skill (opzionale)
templates/
  SKILL.template.md             # modello da copiare per una nuova skill
```

## Installazione

Da un terminale con Claude Code:

```bash
claude plugin marketplace add elkartell00/Skill-Kartello-Montaggio-Video
claude plugin install montaggio-video@kartello-montaggio-video
```

Oppure dentro una sessione: `/plugin marketplace add elkartell00/Skill-Kartello-Montaggio-Video`, poi `/plugin install montaggio-video@kartello-montaggio-video`.

La skill si richiama con `/montaggio-video:montaggio-video`, oppure Claude la usa da sola quando chiedi di montare un video ("monta questo video per [profilo], versione lunga più 3 shorts").

Requisiti sul Mac: [Homebrew](https://brew.sh), poi `brew install ffmpeg node python`. Al primo utilizzo la skill controlla gli strumenti e, se gli dai il permesso, installa Whisper in un ambiente Python suo, dentro la cartella di lavoro `montaggio-video/`.

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
