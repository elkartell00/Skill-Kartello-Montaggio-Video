# Studio AI

Studio AI è l'app locale dell'utente che genera immagini, video e audio (Google Nano Banana e Veo 3.1,
OpenAI GPT Image, ElevenLabs).

**Per immagini e video è l'ultima risorsa.** Regola dell'utente: tutto ciò che si può creare con il codice
(motion graphics, animazioni, schede, grafici, illustrazioni con forme e icone, testi animati, miniature
con testo e grafica) lo crea Claude Code con Remotion, il motore di animazione o grafiche su misura, e ci
prova in ogni modo. Studio AI si usa solo quando con il codice non si arriva: scene realistiche,
ambienti, persone o oggetti fotografici che nessuna ripresa mostra. Per l'audio la priorità è in
[audio.md](audio.md). Si usa **solo** con gli strumenti MCP del server `studio-ai`: mai
chiamare direttamente le API di Google, OpenAI o ElevenLabs, mai chiedere chiavi (stanno nell'app).
Il catalogo completo dell'app fa fede; qui c'è solo ciò che serve al montaggio. Prezzi e modelli
cambiano: in caso di dubbio usa `elenco_modelli` e `stima_costo`.

## Collegamento

All'avvio di un lavoro che ne ha bisogno, cerca gli strumenti `studio-ai` (ToolSearch "studio-ai"). Se
non ci sono: l'utente apre l'app, *Impostazioni → Collega a Claude Code*, poi riapre la sessione di
Claude Code. Non ripiegare su altri servizi. Ognuno (anche il padre dell'utente) collega l'app sul suo computer.

## Costi: prima si chiede

Le richieste a Studio AI partono subito e costano. Per questa skill vale una regola in più: **prima di
generare più di un paio di elementi, mostra all'utente il costo totale stimato** (`stima_costo`, oppure
il controllo di `genera_lotto`, che parte tutto o niente) **e aspetta il sì**. `riepilogo_spese` mostra
spesa del giorno, del mese e tetto residuo.

## Dove salvare

`cartella_destinazione` relativa al progetto di Claude Code (la cartella da cui è stata avviata la
skill): `montaggio-video/media/<progetto>/broll`, `.../audio`, `.../immagini`. Passa sempre `nome_file`
parlante (es. `broll-03-taglio-rovere.mp4`). I video esistono in una sola copia, quella nel progetto: non
cancellarli finché servono. In `contesto.progetto` metti il nome del progetto.

## B-roll video

- `genera_lotto` con una voce per clip (`compito: "genera_video"` o `"anima_immagine"`), valori comuni:
  `cartella_destinazione`, `livello`, `audio: false`, `larghezza`/`altezza`/`fps` del montaggio (video
  lungo: 3840x2160 o 1920x1080 secondo il livello e il budget; verticali: 1080x1920) e `formato` 16:9 o 9:16.
- Per ogni voce passa sempre `contesto`: `scopo: "b-roll"`, `punto_video` (es. "2:31"), `trascrizione`
  (la frase coperta), `stile_video` (dal profilo), `progetto`, `riferimento` (es. "broll-03"). Guida la
  scelta del modello e torna nelle risposte.
- `durata` = durata del B-roll nel piano (Veo genera 4, 6 o 8 s; l'app taglia). Con `attendi_secondi: 0`
  ricevi subito il `lavoro_id`: continua il montaggio e poi `stato_lotto`.
- `livello`: `standard` di base; `low` per prove; `high` solo se l'utente vuole il massimo.
- Per personaggi o stili ricorrenti del canale: `salva_personaggio` / `salva_stile` una volta, poi
  `personaggi`/`stile` nelle richieste. Salva il nome nel profilo.
- Controlla `avvisi` e `durata_secondi` nella risposta; guarda un fotogramma di ogni clip prima di usarla.

## Immagini

Prima prova con il codice: miniature, copertine, schede ed elementi grafici si fanno con
`grafiche.py immagine` (Remotion, anche su misura), usando fotogrammi delle riprese come sfondo. Solo se
serve un'immagine realistica che il codice non può fare: `genera_immagine` (`preset: "miniatura-youtube"`,
`copertina-short`, `sfondo_trasparente: true` per PNG da sovrapporre; testi tra virgolette nel prompt).

## Audio

Vedi [audio.md](audio.md): `cerca_suoni` e `usa_suono` (gratis) prima, poi `genera_effetto_sonoro` e
`genera_musica`; `crea_sottofondo` (gratis) per la durata esatta. Voce fuori campo: `genera_voce` (un
file per paragrafo), `elenco_voci` per scegliere la voce.

## Errori

- `RIFIUTO_SICUREZZA`: riformula seguendo il suggerimento (massimo 2 tentativi). Niente persone reali o
  famose, marchi e loghi altrui.
- `TETTO_SUPERATO`, `CHIAVE_MANCANTE`, `CHIAVE_NON_VALIDA`, `CREDITO_ESAURITO`, `VERIFICA_ORGANIZZAZIONE`:
  fermati e avvisa l'utente (si risolve nell'app o sull'account del fornitore).
- `PARAMETRO_NON_VALIDO`, `FILE_NON_TROVATO`: correggi e riprova.

## Cosa Studio AI non fa

Montaggio, trascrizione, clonazione di voci, pubblicazione, video oltre 148 s in un file: queste cose le
fa la skill (o non si fanno).
