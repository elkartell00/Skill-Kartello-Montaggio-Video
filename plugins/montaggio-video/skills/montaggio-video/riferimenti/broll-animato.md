# B-roll animato (motore di motion-broll)

Clip di grafica animata sincronizzate con le parole. Ogni clip è **una forma che non taglia mai**: cambia
dimensione, angoli e colore da uno stato all'altro, mentre il contenuto si scambia con una breve
sfocatura. Un cursore guida i cambi con clic e trascinamenti veri, e ogni cambio cade su una parola.
Esempi finiti (qualità di riferimento e punto di partenza): `$SKILL/esempi/broll-animato/`.

Il motore è in `$SKILL/motore-animazioni/`: `motion.js` (motore), `base.css`, `build.py` (frammento ->
pagina autonoma), `render.js` (render con motion blur), `beats.js` (fogli di fotogrammi), font Geist.

## Flusso

1. **Guarda le riprese**: `analisi.json` dice per ogni ripresa le sezioni `pieno` (soggetto a tutto
   schermo) e `pip` (soggetto in un riquadro, resto vuoto: lì vanno i pannelli). Se il riquadro cambia
   dimensione, chiedi se è voluto e dimensiona il pannello per il riquadro più grande.
2. **Densità** (dal profilo, altrimenti chiedi): leggera 2–4 clip al minuto, media 4–7, intensa quasi
   ogni frase con brevi pause sul volto.
3. **Piano, prima di qualsiasi codice.** Tabella con una riga per clip:
   `| # | Entra–Esce | Frase coperta | Cosa fa la forma, su quali parole | Trattamento | Perché |`
   e aspetta l'approvazione dell'utente.
4. **Costruisci** un frammento per clip in `montaggio-video/media/<progetto>/animazioni/NN-nome.html`:
   ```bash
   $PY $SKILL/scripts/grafiche.py anima build montaggio-video/media/<progetto>/animazioni/dist montaggio-video/media/<progetto>/animazioni/*.html
   ```
   Ogni cambio di stato sulla sua parola: tempo nella clip = tempo della parola (da `parole-timeline.json`) − entrata della clip.
5. **Controlla i fotogrammi** sui momenti chiave e a metà trasformazione:
   ```bash
   $PY $SKILL/scripts/grafiche.py anima fogli <dist/NN-nome.html> <foglio.png> 0.4 1.2 2.1 ...
   ```
   Guarda ogni foglio. Correggi testo stretto, tagliato, illeggibile, fuori parola, cursore fuori
   quadro. Poi ricontrolla.
6. **Render** con gli fps del montaggio:
   ```bash
   $PY $SKILL/scripts/grafiche.py anima render <dist/NN-nome.html> montaggio-video/media/<progetto>/NN-nome_0m32s40.mp4 30000/1001
   ```
   I pannelli trasparenti (`bg:null`) vanno in `.mov`. Il nome finisce con il punto della timeline
   (`0m32s40` = 0:32.40). Il render fa 4 sotto-fotogrammi per fotogramma: è più lento del tempo reale.
7. **Nel piano**: stacco a tutto schermo = `modo: "pieno"`; pannello = `modo: "sopra"`.

## Direzione creativa: quanto spazio prende ogni clip

È la scelta più importante: falla clip per clip e dì il perché.
- **Stacco a tutto schermo.** Il fotogramma è tutto il soggetto e la frase descrive qualcosa da *vedere*:
  un prodotto, un processo, un confronto, un numero, un cambio di capitolo. Copri l'idea (3–10 s), poi
  ridai il volto. Mai nel primo secondo dell'aggancio, mai su frasi personali, emotive o di opinione.
  Almeno 2 s di volto tra due stacchi.
- **Pannello nello spazio vuoto.** Il montaggio lascia spazio (riquadro, divisione, zona libera): clip
  trasparente centrata nella zona vuota, lontana dal riquadro del soggetto in ogni istante. Può durare
  a lungo (15 s e più) come un'unica trasformazione, perché il soggetto resta visibile.
- **Niente.** La frase parla della persona, o è troppo vicina a un'altra clip.

Contenuti:
- Mostra gli oggetti reali dell'argomento (cartella, file, prodotto, risultato), presi dalle parole.
  Ogni idea va su un'interazione del vocabolario qui sotto.
- **Mai inventare numeri, citazioni, prezzi o risultati**: barre relative, righe segnaposto o etichette
  dalla trascrizione; scrivi in `note` del piano cosa è illustrativo. I dati veri solo se li dà l'utente.
- Un'idea per clip. Ritmo sul parlato, non sulla musica: un cambio per battuta parlata, 0,4–1,2 s.

## Scrivere una clip

Una clip è un frammento HTML. `build.py` lo avvolge con motore, font e cursore in una pagina autonoma,
dove `seek(t)` disegna il fotogramma al tempo `t`. Ogni stile è una funzione pura di `t`: niente
transizioni CSS, timer o stato tra un fotogramma e l'altro. È questo che permette il render fotogramma
per fotogramma con motion blur.

```html
<title>04 Master prompt</title>
<style>/* CSS della clip */</style>

<div data-slot="world">  <!-- facoltativo: elementi accanto alla forma (un bersaglio, una linguetta) --> </div><!--/world-->
<div data-slot="shape">
  <!-- un livello per stato; i livelli .L sono ancorati dentro la forma -->
  <div class="L" id="Lnotes"> … </div>
  <div class="L" id="Ldoc"> … </div>
</div><!--/shape-->

<script>
M.scene({
  W:1920, H:1080, T:10,            // dimensioni (uguali al video) e durata della clip in secondi
  bg:'#E9E7E2',                    // colore di fondo; null = trasparente (pannello -> .mov)
  center:[960,540],                // punto dello schermo su cui centra la camera (spostalo per i pannelli)
  intro:0.15,                      // la forma entra a questo tempo; null = già in scena
  SH:{                             // gli stati attraverso cui si trasforma la forma
    notes:{w:780,h:560,r:36,bg:'#FFFFFF',cam:1.3},
    doc:{w:600,h:720,r:28,bg:'#FFFFFF',cam:1.2},
  },
  start:'notes', SEQ:[[5.1,'doc']],               // [tempo nella clip, stato]: ognuno sulla sua parola
  layers:[
    {el:'Lnotes', tin:0.15, tout:5.1, anchor:'t'}, // anchor 'c' centro (predefinito), 't' centro in alto, 'l' centro a sinistra
    {el:'Ldoc', tin:5.1, tout:null, anchor:'t', update:(t,g)=>{ /* contenuto per fotogramma, es. digitazione */ }},
  ],
  cursor:{size:44, clicks:[2.3], drags:[[6.9,7.8]], keys:[[0,760,460],[1.2,760,460],[1.9,330,250]]},
  geom:(t,g)=>g,     // facoltativo: cambia la geometria (es. segue il cursore mentre trascina; g.fx/g.fy fuoco della camera)
  extra:(t,g)=>{},   // facoltativo: lavoro per fotogramma fuori dai livelli
});
</script>
```

Le coordinate sono **pixel del mondo**. La forma è centrata in (0,0) del mondo salvo che `geom` la
sposti (`g.cx`, `g.cy`). La camera disegna mondo -> schermo come `center + cam × (mondo − fuoco)`.
Scegli `cam` per stato in modo che lo stato riempia il quadro: circa 1.2–1.6 per le schede, 1.8–2.2
per le pillole. Il cursore ha dimensione costante sullo schermo.

Il contenuto di un livello è posizionato rispetto alla sua ancora: `left:-330px; top:40px` in un livello
`anchor:'t'` = 330 px a sinistra del centro, 40 px sotto il bordo superiore della forma. Il contenuto
ancorato in alto segue il bordo superiore quando la forma cresce.

Per i video verticali (1080x1920) usa `W:1080, H:1920` e stati più stretti e alti.

### API del motore (`window.M`)

| Chiamata | Cosa fa |
|---|---|
| `M.track(v0, [[t, valore, molla?], …])` | Un valore che cambia obiettivo più volte: somma di una molla per ogni cambio. Restituisce `t => valore` |
| `M.ctrack('#hex', [[t,'#hex'], …])` | Lo stesso per i colori. Restituisce `t => 'rgb(...)'` |
| `M.MORPH`, `M.FAST`, `M.SLOW`, `M.SOFT`, `M.CAM`, `M.INSTANT` | Molle pronte `[rigidità ω, smorzamento ζ]`. FAST/SLOW per bordo anteriore/posteriore; INSTANT per reset invisibili |
| `M.vis(t, tin, tout, {din, lin, lout})` | Scambio di contenuto: l'uscita sfuma veloce, l'entrata aspetta `din` e appare in `lin`. Restituisce `{o, blur, s, a, b}` |
| `M.apply(el, v)` | Applica un risultato di `vis` a un elemento (opacità, sfocatura, scala) |
| `M.path([[t,x,y], …])` | Percorso del cursore (o di un punto), ammorbidito con un leggero arco umano |
| `M.crossTimes(f, t0, t1, soglie)` | Quando un valore crescente supera ogni soglia: per far partire molle da un valore trascinato |
| `M.icon(nome, dimensione, colore, spessore?)` | Icona dal set `M.IC`, con tratto normalizzato |
| `M.setText(el, s)` | Cambia il testo solo se è diverso (economico per fotogramma) |
| `M.eo`, `M.eio`, `M.clamp`, `M.lerp`, `M.S`, `M.step` | Curve e molle di supporto |

Icone in `M.IC`: arrow, check, x, plus, folder, terminal, file, pencil, coin, clock, chip, sparkle,
castle, search. Se ne servono altre: tracciati su griglia 24 con lo stesso spessore (es. da Lucide, licenza ISC).

### Schemi (vedi gli esempi)

| Schema | Come | Esempio |
|---|---|---|
| Pillola → scheda → controllo | stati SH + livelli con tin/tout | 01 |
| Indicatore liquido | due `M.track` per i bordi sinistro/destro: quello che avanza usa `M.FAST`, quello dietro `M.SLOW` | 01, 02 |
| Digitazione | `TESTO.slice(0, n)` con `n` dal tempo, più un cursore di testo | 02 |
| Righe o barre che appaiono sulle parole | `M.vis(t, tempoParola, …)` per riga + larghezza o altezza da una molla | 02, 04, 05 |
| Manipolazione diretta | mentre il cursore è premuto il valore viene dalla sua posizione; al rilascio torna con una molla | 03 |
| Trascina e rilascia | `geom` imposta `g.cx/cy` dal cursore mentre trascina; bersaglio nello slot world; `g.fx` sposta il fuoco | 04 |
| Pannello trasparente | `bg:null`, `center` nella zona vuota, forme chiare | 02 |

### Vocabolario delle interazioni

Porta ciò che dice il parlato su uno di questi: azione principale (pillola + clic), avanzamento
(caricamento, barre, corsie), conferma (spunta, notifica), stato in tempo reale (isola), scheda di
dettaglio con trascinamento, cursore con effetto elastico, interruttore, schede, grafico con etichetta,
ricerca e filtro, file → trascina → bersaglio, terminale che scrive, confronto affiancato, scheda di capitolo.

### Stile predefinito (il profilo dell'utente lo sostituisce)

- Colori: fondo `#E9E7E2`, inchiostro `#0B0B0B`, componenti bianchi, un accento `#FF5A1F`. Pannelli su
  riprese scure: forme chiare `#F4F2EE`.
- Testi: Geist per l'interfaccia, Geist Mono per codice, nomi di file e terminali. Un solo set di
  icone con un solo spessore (`M.icon`).
- Movimento: molle con al massimo un piccolissimo rimbalzo. Bordo anteriore e posteriore su molle
  diverse, così gli indicatori si allungano. La camera zooma perché ogni stato riempia il quadro.
- Vietati: rimbalzi vistosi, particelle, bagliori, sfumature sui componenti, spessori misti, tempi
  morti, aspetto da modello già visto, dati inventati.

### Attenzione a

- Mai `will-change` su qualcosa che la camera scala: il testo diventa sfocato.
- Il testo che cambia dentro una forma in trasformazione ha bisogno di tempi propri di entrata e uscita
  (`M.vis` din/lin/lout), altrimenti vecchio e nuovo si sovrappongono.
- Le etichette con `mix-blend-mode: difference` devono stare in un livello che ha la fusione: un genitore
  con filtro le isola.
- Gli elementi che scorrono sotto un evidenziatore vogliono molle `M.FAST`, o la riga evidenziata
  resta vuota per un attimo.
- Tieni il cursore dentro il quadro a ogni zoom della camera, anche durante le trasformazioni.
- I tempi stimati da un SRT si spostano dentro un sottotitolo: con Whisper i tempi sono veri, ma metti
  comunque i cambi importanti sulla prima o sull'ultima parola di una frase.
- Una clip finisce tenendo l'ultimo stato; se il suo spazio nel piano è più lungo, resta fermo l'ultimo fotogramma.
