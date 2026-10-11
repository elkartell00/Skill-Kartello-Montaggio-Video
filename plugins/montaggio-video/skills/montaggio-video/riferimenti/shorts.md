# Shorts e Reels

Due montaggi diversi. Ogni short è un piano a sé nello stesso progetto (`short-1`, `short-2`, `reel-1`):
ha i suoi sottotitoli e le sue versioni in `risultati/<progetto>/<piano>/`.

## Shorts dal video lungo

1. **Scegli i momenti** (2–3 per video lungo, o quanti ne chiede l'utente) leggendo la trascrizione:
   - funzionano da soli, con un concetto completo (chi non ha visto il video capisce);
   - hanno un momento forte: una rivelazione, un consiglio pratico, un errore da evitare, un prima/dopo,
     una frase che fa discutere;
   - durata 30–60 s dopo la pulizia (dal profilo).
   Proponi all'utente i candidati in una tabella `| # | Da–A (ripresa) | Di cosa parla | Aggancio proposto | Perché funziona |`
   e lascia scegliere.
2. **Aggancio nei primi 1–2 secondi**: il pezzo è preso a metà discorso, quindi serve un inizio forte.
   Opzioni da proporre: partire dalla frase più forte del pezzo (anche spostandola in testa), un titolo
   grande con la domanda o la promessa, uno zoom a scatto sulla prima parola importante.
3. **Piano**, con i tratti nell'ordine voluto (l'aggancio può venire da un punto successivo):
   ```bash
   $PY $SKILL/scripts/pulizia.py --progetto <nome> --formato shorts-dal-lungo --piano short-1 \
       --intervalli 0:301.2-305.0,0:125.3-172.8 --pausa-max 0.2 --pausa-lascia 0.1 --margine 0.05
   ```
   Tempi nella ripresa originale (da `trascrizione.txt`), valori dal profilo.
4. **Riinquadratura 16:9 → 9:16** che segue il soggetto, sfruttando il 4K (il ritaglio è 1215x2160:
   nessuna perdita di qualità a 1080x1920):
   ```bash
   $PY $SKILL/scripts/riinquadra.py --progetto <nome> --piano short-1 --anteprima
   ```
   Guarda `riinquadratura-short-1.jpg`. Se il soggetto non è una persona che guarda in camera (un
   prodotto, le mani, una persona di spalle) usa le maschere: `separa_soggetto.py`, poi
   `riinquadra.py --metodo maschere --maschere <cartella>`. Per una ripresa fissa: `--metodo centro`.
5. Sottotitoli `--stile parole`, grafiche ed effetti dal profilo dello short (ritmo più alto del lungo).
6. **Finale**: rimando al video completo sul canale se il profilo lo vuole (una scritta finale o una
   frase dell'utente).

## Shorts indipendenti

Registrati apposta in verticale: niente ritaglio.
1. Nuovo progetto (o piano) con le riprese verticali:
   ```bash
   $PY $SKILL/scripts/pulizia.py --progetto <nome> --formato shorts-indipendenti --piano short-1 --sorgenti 2
   ```
2. Ritmo e struttura pensati come pezzo unico: aggancio, sviluppo, chiusura.
3. **Finale a loop** dove ha senso: l'ultima frase o immagine si ricollega alla prima, così il video
   riparte senza che si noti. Come:
   - scegli un punto di chiusura che "chiama" l'inizio (una domanda a cui risponde la prima frase);
   - taglia l'ultimo segmento appena prima della pausa finale, senza dissolvenza in nero;
   - evita grafiche o musica che finiscono in modo netto: la musica deve poter ripartire.

## Reels

Come gli shorts, con lo stile del profilo per Instagram se diverso. Tieni testi e sottotitoli lontani
dalla parte bassa (lì Instagram mette descrizione e pulsanti) e dai bordi laterali.

## Formati diversi

Durate e formati sono indicazioni: un video quadrato è `--formato 1080x1080`, un 4:5 `--formato 1080x1350`.
