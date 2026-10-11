# CLAUDE.md

Questa repository è un marketplace di plugin per Claude Code. Contiene il plugin `montaggio-video`, con le skill di Kartello per il montaggio video.

## Convenzioni

- Ogni skill sta in `plugins/montaggio-video/skills/<nome-skill>/SKILL.md`. Il nome della cartella è in kebab-case e coincide con il campo `name` del frontmatter.
- Per una nuova skill parti da `templates/SKILL.template.md`.
- La `description` dice cosa fa la skill e quando usarla, con il caso d'uso principale per primo: è l'unico testo che Claude vede prima di caricare la skill.
- Tieni `SKILL.md` sotto le 500 righe. Il materiale lungo va in file di supporto nella stessa cartella (`reference.md`, `examples.md`), collegati da `SKILL.md`.
- Gli script vanno in `scripts/` dentro la cartella della skill e si richiamano con `${CLAUDE_SKILL_DIR}/scripts/...`.
- Il nome del plugin in `.claude-plugin/marketplace.json` e in `plugins/montaggio-video/.claude-plugin/plugin.json` deve restare identico.
- Quando cambi una skill già pubblicata, alza `version` in `plugin.json`, altrimenti chi l'ha installata non riceve l'aggiornamento.
- La skill `montaggio-video` è in italiano (istruzioni, messaggi degli script, interfacce). Ogni modifica va annotata in `CHANGELOG.md`; per integrare altre skill segui `riferimenti/integrare-skill.md`.
- Gli script non devono mai modificare le riprese originali né partire da un video già esportato; ogni esportazione passa dal controllo finale.
- Gli script lavorano su Mac (piattaforma principale) e restano portabili: Python e Node, niente bash obbligatorio, niente comandi di shell costruiti con testo variabile.

## Verifica

Prima di ogni commit:

```bash
claude plugin validate .
claude plugin validate ./plugins/montaggio-video
```
