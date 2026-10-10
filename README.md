# Skills Kartello Video

Marketplace di plugin per [Claude Code](https://code.claude.com) con le skill di Kartello dedicate ai video.

## Struttura

```text
.claude-plugin/
  marketplace.json              # catalogo del marketplace "kartello-skills"
plugins/
  kartello-video/
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
claude plugin marketplace add elkartell00/Skills-Kartello-Video
claude plugin install kartello-video@kartello-skills
```

Oppure dentro una sessione: `/plugin marketplace add elkartell00/Skills-Kartello-Video`, poi `/plugin install kartello-video@kartello-skills`.

Le skill si richiamano con `/kartello-video:<nome-skill>`, oppure Claude le usa da solo quando la richiesta corrisponde alla loro `description`.

## Sviluppo

Provare il plugin senza installarlo:

```bash
claude --plugin-dir ./plugins/kartello-video
```

Validare marketplace e plugin prima di ogni push:

```bash
claude plugin validate .
claude plugin validate ./plugins/kartello-video
```

Per aggiungere una skill: copia `templates/SKILL.template.md` in `plugins/kartello-video/skills/<nome-skill>/SKILL.md` e compila i campi.
