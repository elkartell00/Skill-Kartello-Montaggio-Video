"""Diario delle revisioni e misura del miglioramento, per profilo.

uso:
  python diario.py aggiungi --profilo rossi --progetto tavolo --formato shorts-dal-lungo --categoria sottotitoli
                            --richiesta "sottotitoli più piccoli" --situazione "testo sopra il viso" --tipo generale
                            --dimensione piccola [--chi papà]
  python diario.py versione --profilo rossi --progetto tavolo --piano short-1 --versione v03
  python diario.py statistiche --profilo rossi

aggiungi:     una correzione dell'utente. tipo: generale (preferenza da applicare sempre) o specifica (legata
              a questo video: resta un indizio). dimensione: piccola, media, grande.
              categorie: tagli, ritmo, sottotitoli, grafiche, zoom, effetti, transizioni, broll, musica, audio,
              colore, inquadratura, durata, testi, altro.
versione:     registra che è stata prodotta una versione (per contare quante revisioni servono per lavoro).
statistiche:  revisioni per lavoro nel tempo e correzioni che ritornano (candidate a diventare regole).

Scrive profili/<profilo>/diario.jsonl (dati) e aggiunge una riga a diario-revisioni.md (leggibile).
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import cartella_lavoro, errore, info  # noqa: E402

CATEGORIE = ["tagli", "ritmo", "sottotitoli", "grafiche", "zoom", "effetti", "transizioni", "broll", "musica", "audio",
             "colore", "inquadratura", "durata", "testi", "altro"]
PESO = {"piccola": 1, "media": 2, "grande": 4}


def cartella(profilo):
    d = cartella_lavoro() / "profili" / profilo
    if not d.exists():
        errore(f"il profilo '{profilo}' non esiste.")
    return d


def leggi(d):
    f = d / "diario.jsonl"
    if not f.exists():
        return []
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def scrivi(d, voce):
    with open(d / "diario.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Diario delle revisioni")
    ap.add_argument("azione", choices=["aggiungi", "versione", "statistiche"])
    ap.add_argument("--profilo", required=True)
    ap.add_argument("--progetto")
    ap.add_argument("--formato")
    ap.add_argument("--piano")
    ap.add_argument("--versione")
    ap.add_argument("--categoria", choices=CATEGORIE)
    ap.add_argument("--richiesta")
    ap.add_argument("--situazione", default="")
    ap.add_argument("--tipo", choices=["generale", "specifica"], default="specifica")
    ap.add_argument("--dimensione", choices=list(PESO), default="piccola")
    ap.add_argument("--chi", default="")
    a = ap.parse_args()
    d = cartella(a.profilo)
    ora = datetime.now().isoformat(timespec="minutes")

    if a.azione == "aggiungi":
        if a.profilo == "base":
            errore("il profilo base non registra correzioni: crea un profilo per questo canale o cliente.")
        if not (a.progetto and a.categoria and a.richiesta):
            errore("servono --progetto, --categoria e --richiesta")
        voce = {"tipo_voce": "correzione", "data": ora, "chi": a.chi, "progetto": a.progetto, "formato": a.formato or a.piano or "",
                "categoria": a.categoria, "tipo": a.tipo, "dimensione": a.dimensione, "richiesta": a.richiesta, "situazione": a.situazione}
        scrivi(d, voce)
        md = d / "diario-revisioni.md"
        if not md.exists():
            md.write_text(f"# Diario delle revisioni: {a.profilo}\n\n| Data | Chi | Progetto | Formato | Categoria | Tipo | Dimensione | Richiesta | Situazione |\n"
                          "|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
        pulisci = lambda s: str(s).replace("|", "/").replace("\n", " ")
        with open(md, "a", encoding="utf-8") as f:
            f.write(f"| {ora.replace('T', ' ')} | {pulisci(a.chi)} | {pulisci(a.progetto)} | {pulisci(voce['formato'])} | {a.categoria} | "
                    f"{a.tipo} | {a.dimensione} | {pulisci(a.richiesta)} | {pulisci(a.situazione)} |\n")
        simili = [v for v in leggi(d) if v.get("tipo_voce") == "correzione" and v["categoria"] == a.categoria]
        progetti = {v["progetto"] for v in simili}
        info(f"Annotata. Correzioni '{a.categoria}' nel diario: {len(simili)} in {len(progetti)} lavori.")
        if len(progetti) >= 3:
            info("Questa categoria ritorna spesso: valuta con l'utente se trasformarla in una regola fissa del profilo.")
    elif a.azione == "versione":
        if not (a.progetto and a.piano and a.versione):
            errore("servono --progetto, --piano e --versione")
        scrivi(d, {"tipo_voce": "versione", "data": ora, "progetto": a.progetto, "piano": a.piano, "versione": a.versione})
        info(f"Registrata la versione {a.versione} di {a.progetto}/{a.piano}.")
    else:
        voci = leggi(d)
        lavori = defaultdict(lambda: {"versioni": set(), "correzioni": 0, "peso": 0, "data": ""})
        for v in voci:
            if v.get("tipo_voce") == "versione":
                k = (v["progetto"], v["piano"])
                lavori[k]["versioni"].add(v["versione"])
                lavori[k]["data"] = lavori[k]["data"] or v["data"]
            elif v.get("tipo_voce") == "correzione":
                k = next((kk for kk in lavori if kk[0] == v["progetto"] and (not v["formato"] or v["formato"] in kk[1] or kk[1] in v["formato"])),
                         (v["progetto"], v["formato"] or "?"))
                lavori[k]["correzioni"] += 1
                lavori[k]["peso"] += PESO.get(v["dimensione"], 1)
                lavori[k]["data"] = lavori[k]["data"] or v["data"]
        if not lavori:
            info("Il diario è ancora vuoto.")
            return
        info(f"Andamento del profilo {a.profilo} (dal lavoro più vecchio al più recente):")
        info("| Data | Lavoro | Revisioni | Correzioni | Peso |")
        info("|---|---|---|---|---|")
        ordinati = sorted(lavori.items(), key=lambda x: x[1]["data"])
        for (prog, piano), x in ordinati:
            rev = max(0, len(x["versioni"]) - 1)
            info(f"| {x['data'][:10]} | {prog}/{piano} | {rev} | {x['correzioni']} | {x['peso']} |")
        pesi = [x["peso"] for _, x in ordinati]
        if len(pesi) >= 4:
            meta = len(pesi) // 2
            prima, dopo = sum(pesi[:meta]) / meta, sum(pesi[meta:]) / (len(pesi) - meta)
            tendenza = "in calo: la skill sta imparando" if dopo < prima * 0.85 else ("in aumento: va corretto il profilo" if dopo > prima * 1.15 else "stabile")
            info(f"\nPeso medio delle correzioni: {prima:.1f} nella prima metà, {dopo:.1f} nella seconda ({tendenza}).")
        cat = Counter(v["categoria"] for v in voci if v.get("tipo_voce") == "correzione")
        info("\nCorrezioni per categoria: " + ", ".join(f"{k} {n}" for k, n in cat.most_common()))
        ricorrenti = defaultdict(set)
        for v in voci:
            if v.get("tipo_voce") == "correzione":
                ricorrenti[v["categoria"]].add(v["progetto"])
        cand = [k for k, p in ricorrenti.items() if len(p) >= 3]
        if cand:
            info("Ricorrenti in 3 o più lavori (candidate a regola fissa): " + ", ".join(cand))


if __name__ == "__main__":
    main()
