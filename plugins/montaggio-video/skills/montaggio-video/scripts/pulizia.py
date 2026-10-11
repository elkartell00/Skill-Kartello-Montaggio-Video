"""Pulizia automatica: crea il piano di montaggio tagliando pause, intercalari, false partenze e ripetizioni.

uso:
  python pulizia.py --progetto nome [--formato video-lungo] [--pausa-max 0.35] [--pausa-lascia 0.2]
                    [--margine 0.08] [--senza-ripetizioni] [--tieni-intercalari]

Logica:
- intercalari ("ehm", "uhm", "mmm"...): tagliati. "eh" solo se isolato da pause, perché in italiano
  spesso ha un senso ("eh sì").
- frasi ripetute e false partenze: se una frase è l'inizio di una delle due frasi successive, o le
  assomiglia molto, si tiene l'ultima ripresa (di solito la migliore) e si taglia la precedente.
- pause: quelle più lunghe di --pausa-max vengono accorciate a --pausa-lascia.
- ogni taglio cade su un fotogramma intero, con un piccolo margine prima e dopo la voce.

Scrive .lavoro/<progetto>/piano-montaggio.json (modificabile a mano o da Claude) e piano-montaggio.md
(riepilogo leggibile con ogni taglio e il motivo).
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import FORMATI, cartelle_progetto, errore, info, leggi_json, quantizza, scrivi_json, tc  # noqa: E402

INTERCALARI = {"ehm", "ehmm", "emh", "eem", "ehh", "ehhh", "uhm", "uhmm", "um", "umm", "uh", "uhh", "mmm", "mm",
               "mh", "mhm", "hmm", "hm", "ehmmm", "eeh", "eeeh", "aah", "ahm"}
INTERCALARI_SE_ISOLATI = {"eh", "ah", "ee", "eee"}
# Una pausa più lunga di così chiude una frase: serve a confrontare le frasi per trovare le ripetizioni.
PAUSA_FRASE = 0.6


def norm(w):
    return re.sub(r"[^\wàèéìíòóùú']", "", w.lower())


def segna_intercalari(parole, tieni):
    for i, p in enumerate(parole):
        n = norm(p["w"])
        p["taglia"] = None
        if tieni or not n:
            continue
        if n in INTERCALARI:
            p["taglia"] = "intercalare"
        elif n in INTERCALARI_SE_ISOLATI:
            prima = parole[i - 1]["fine"] if i > 0 else -9
            dopo = parole[i + 1]["inizio"] if i + 1 < len(parole) else 1e9
            if p["inizio"] - prima > 0.15 and dopo - p["fine"] > 0.15:
                p["taglia"] = "intercalare"


def raggruppa_frasi(parole):
    frasi, cur = [], []
    for i, p in enumerate(parole):
        if p["taglia"]:
            continue
        cur.append(i)
        fine = p["w"].endswith((".", "?", "!", "…"))
        succ = next((j for j in range(i + 1, len(parole)) if not parole[j]["taglia"]), None)
        pausa = succ is not None and parole[succ]["inizio"] - p["fine"] > PAUSA_FRASE
        if fine or pausa or succ is None:
            frasi.append(cur)
            cur = []
    if cur:
        frasi.append(cur)
    return frasi


def testo(parole, idx):
    return " ".join(norm(parole[i]["w"]) for i in idx).strip()


def segna_ripetizioni(parole, frasi):
    """Una frase seguita (entro 2 frasi) da una versione che la ripete o la completa viene tagliata."""
    for k, f in enumerate(frasi):
        a = testo(parole, f)
        if len(a.split()) < 2:
            continue
        for g in frasi[k + 1:k + 3]:
            b = testo(parole, g)
            if not b:
                continue
            testa = " ".join(b.split()[:len(a.split())])
            simile = difflib.SequenceMatcher(None, a, testa).ratio()
            if b.startswith(a) or simile >= 0.8:
                motivo = "falsa partenza" if len(b.split()) > len(a.split()) else "frase ripetuta"
                for i in f:
                    parole[i]["taglia"] = motivo
                break


def intervalli(parole, fps, pausa_max, pausa_lascia, margine, durata):
    """Intervalli da tenere (in tempo della ripresa), già su fotogrammi interi."""
    # Blocchi di parole tenute. Una parola tagliata spezza sempre il blocco, anche se le pause
    # attorno sono brevi, e fa da limite: il margine non può riportarla dentro.
    blocchi, cur, lim = [], None, None
    for p in parole:
        if p["taglia"]:
            if cur is not None:
                cur["dx"] = p["inizio"]
                blocchi.append(cur)
                cur = None
            lim = p["fine"]
            continue
        if cur is not None and p["inizio"] - cur["b"] <= pausa_max:
            cur["b"] = max(cur["b"], p["fine"])
        else:
            if cur is not None:
                blocchi.append(cur)
            cur = {"a": p["inizio"], "b": p["fine"], "sx": lim, "dx": None}
        lim = None
    if cur is not None:
        blocchi.append(cur)
    # Margine attorno alla voce, ma una pausa accorciata non supera mai pausa_lascia in totale.
    m = max(margine, 0.0)
    extra = max(0.0, pausa_lascia / 2 - m)
    out = []
    for i, bl in enumerate(blocchi):
        a2 = max(0.0, bl["a"] - m - (extra if i > 0 else 0))
        b2 = min(durata, bl["b"] + m + (extra if i + 1 < len(blocchi) else 0))
        if bl["sx"] is not None:
            a2 = max(a2, bl["sx"])
        if bl["dx"] is not None:
            b2 = min(b2, bl["dx"])
        if out and a2 <= out[-1][1]:
            out[-1][1] = b2
        else:
            out.append([a2, b2])
    q = []
    for a, b in out:
        a, b = quantizza(a, fps), quantizza(b, fps)
        if b > a:
            q.append([a, b])
    return q


def main():
    ap = argparse.ArgumentParser(description="Pulizia automatica e piano di montaggio")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--formato", default="video-lungo", help="video-lungo, shorts-indipendenti, reels, ... o LxA")
    ap.add_argument("--pausa-max", type=float, default=0.35, help="pause più lunghe di così vengono accorciate (s)")
    ap.add_argument("--pausa-lascia", type=float, default=0.2, help="quanta pausa lasciare dove si taglia (s)")
    ap.add_argument("--margine", type=float, default=0.08, help="margine prima e dopo la voce (s)")
    ap.add_argument("--senza-ripetizioni", action="store_true", help="non cercare frasi ripetute")
    ap.add_argument("--tieni-intercalari", action="store_true")
    ap.add_argument("--fps", help="fotogrammi al secondo dell'uscita (predefinito: quelli della prima ripresa)")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    prog = leggi_json(c["progetto"])
    analisi = leggi_json(c["lavoro"] / "analisi.json")
    trascr = leggi_json(c["lavoro"] / "trascrizione.json")
    if a.formato in FORMATI:
        W, H = FORMATI[a.formato]
    elif re.fullmatch(r"\d+x\d+", a.formato):
        W, H = map(int, a.formato.split("x"))
    else:
        errore(f"formato sconosciuto: {a.formato}")
    fps = a.fps or analisi["sorgenti"][0]["fps"]

    segmenti, tagli = [], []
    for src, tr in zip(analisi["sorgenti"], trascr["sorgenti"]):
        parole = tr["parole"]
        segna_intercalari(parole, a.tieni_intercalari)
        if not a.senza_ripetizioni:
            segna_ripetizioni(parole, raggruppa_frasi(parole))
        keep = intervalli(parole, fps, a.pausa_max, a.pausa_lascia, a.margine, src["durata"])
        if not parole:  # nessuna voce: si tiene tutta la ripresa
            keep = [[0.0, quantizza(src["durata"], fps)]]
        for ini, fin in keep:
            dentro = [p["w"] for p in parole if not p["taglia"] and p["inizio"] >= ini - 0.01 and p["fine"] <= fin + 0.01]
            segmenti.append({"id": len(segmenti) + 1, "sorgente": src["indice"], "inizio": ini, "fine": fin,
                             "testo": " ".join(dentro)})
        # Riepilogo dei tagli: parole tagliate per motivo + pause accorciate.
        gruppo = None
        for p in parole:
            if p["taglia"]:
                if gruppo and gruppo["motivo"] == p["taglia"] and p["inizio"] - gruppo["fine"] < 1.0:
                    gruppo["fine"], gruppo["testo"] = p["fine"], gruppo["testo"] + " " + p["w"]
                else:
                    gruppo = {"sorgente": src["indice"], "inizio": p["inizio"], "fine": p["fine"], "motivo": p["taglia"], "testo": p["w"]}
                    tagli.append(gruppo)
            else:
                gruppo = None
        for (a1, b1), (a2, b2) in zip(keep, keep[1:]):
            if a2 - b1 > 0.05 and not any(t["sorgente"] == src["indice"] and t["inizio"] >= b1 - 0.1 and t["fine"] <= a2 + 0.1 for t in tagli):
                tagli.append({"sorgente": src["indice"], "inizio": b1, "fine": a2, "motivo": "pausa", "testo": ""})
    tagli.sort(key=lambda t: (t["sorgente"], t["inizio"]))

    durata_orig = sum(s["durata"] for s in analisi["sorgenti"])
    durata_fin = sum(s["fine"] - s["inizio"] for s in segmenti)
    piano = {
        "schema": 1,
        "progetto": a.progetto,
        "profilo": prog.get("profilo", "base"),
        "formato": a.formato,
        "larghezza": W, "altezza": H, "fps": fps,
        "adattamento": "riempi",
        "parametri_pulizia": {"pausa_max": a.pausa_max, "pausa_lascia": a.pausa_lascia, "margine": a.margine,
                              "ripetizioni": not a.senza_ripetizioni, "intercalari": not a.tieni_intercalari},
        "segmenti": segmenti,
        "tagli": tagli,
        "sovrapposizioni": [],
        "audio": {},
        "note": [],
    }
    scrivi_json(c["lavoro"] / "piano-montaggio.json", piano)

    conta = {}
    for t in tagli:
        conta[t["motivo"]] = conta.get(t["motivo"], 0) + 1
    righe = [f"# Piano di montaggio: {a.progetto}", "",
             f"Formato {a.formato} {W}x{H}, {fps} fps. Durata: {tc(durata_orig)} -> {tc(durata_fin)} "
             f"({100 * (1 - durata_fin / max(durata_orig, 0.001)):.0f}% in meno), {len(segmenti)} segmenti.", "",
             "Tagli: " + ", ".join(f"{v} {k}" for k, v in sorted(conta.items())), "",
             "| Ripresa | Da | A | Motivo | Testo tagliato |", "|---|---|---|---|---|"]
    for t in tagli:
        righe.append(f"| {t['sorgente']:02d} | {tc(t['inizio'])} | {tc(t['fine'])} | {t['motivo']} | {t['testo']} |")
    (c["lavoro"] / "piano-montaggio.md").write_text("\n".join(righe) + "\n", encoding="utf-8")
    info(righe[2])
    info(righe[4])
    info(f"Piano salvato in {c['lavoro'] / 'piano-montaggio.json'} (riepilogo: piano-montaggio.md)")


if __name__ == "__main__":
    main()
