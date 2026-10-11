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

Scrive .lavoro/<progetto>/piani/<piano>.json (modificabile a mano o da Claude) e <piano>.md (riepilogo
leggibile con ogni taglio e il motivo). Il nome del piano predefinito è il formato (es. video-lungo).
Per più montaggi nello stesso progetto (es. shorts indipendenti da riprese diverse) usa --piano e --sorgenti.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (FORMATI, cartelle_progetto, errore, info, leggi_json, percorsi_piano, quantizza,  # noqa: E402
                    scrivi_json, tc)

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
    ap.add_argument("--fps", help="fotogrammi al secondo dell'uscita (predefinito: quelli della prima ripresa usata)")
    ap.add_argument("--piano", help="nome del piano (predefinito: il formato, es. video-lungo)")
    ap.add_argument("--sorgenti", help="riprese da usare, per indice (es. 0,2); predefinito: tutte")
    ap.add_argument("--intervalli", help="solo questi tratti, nell'ordine indicato: ripresa:da-a separati da virgola "
                    "(es. 0:125.3-172.8 oppure 0:301.2-305.0,0:125.3-172.8 per mettere prima l'aggancio)")
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
    usate = analisi["sorgenti"]
    if a.sorgenti:
        scelte = {int(x) for x in a.sorgenti.split(",")}
        usate = [s for s in usate if s["indice"] in scelte]
        if not usate:
            errore(f"nessuna ripresa con indice {a.sorgenti}.")
    fps = a.fps or usate[0]["fps"]
    nome = a.piano or (a.formato if a.formato in FORMATI else "personalizzato")
    P = percorsi_piano(c, nome)
    trascr_per = {t["indice"]: t for t in trascr["sorgenti"]}

    per_indice = {s["indice"]: s for s in analisi["sorgenti"]}
    if a.intervalli:
        tratti = []
        for parte in a.intervalli.split(","):
            m = re.fullmatch(r"\s*(\d+):([\d.]+)-([\d.]+)\s*", parte)
            if not m or int(m.group(1)) not in per_indice:
                errore(f"intervallo non valido: '{parte}' (formato ripresa:da-a, es. 0:125.3-172.8)")
            tratti.append((per_indice[int(m.group(1))], float(m.group(2)), float(m.group(3))))
        usate = [t[0] for t in tratti]
        fps = a.fps or usate[0]["fps"]
    else:
        tratti = [(s, 0.0, s["durata"]) for s in usate]

    segmenti, tagli = [], []
    for src, t_da, t_a in tratti:
        tr = trascr_per.get(src["indice"], {"parole": []})
        parole = [dict(p) for p in tr["parole"] if t_da <= (p["inizio"] + p["fine"]) / 2 < t_a]
        segna_intercalari(parole, a.tieni_intercalari)
        if not a.senza_ripetizioni:
            segna_ripetizioni(parole, raggruppa_frasi(parole))
        keep = intervalli(parole, fps, a.pausa_max, a.pausa_lascia, a.margine, src["durata"])
        keep = [[max(x, quantizza(t_da, fps)), min(y, quantizza(t_a, fps))] for x, y in keep]
        keep = [k for k in keep if k[1] > k[0]]
        if not parole:  # nessuna voce: si tiene tutto il tratto
            keep = [[quantizza(t_da, fps), quantizza(t_a, fps)]]
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
    if not a.intervalli:
        tagli.sort(key=lambda t: (t["sorgente"], t["inizio"]))

    durata_orig = sum(t_a - t_da for _, t_da, t_a in tratti)
    durata_fin = sum(s["fine"] - s["inizio"] for s in segmenti)
    piano = {
        "schema": 1,
        "progetto": a.progetto,
        "nome": nome,
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
    scrivi_json(P["piano"], piano)

    conta = {}
    for t in tagli:
        conta[t["motivo"]] = conta.get(t["motivo"], 0) + 1
    righe = [f"# Piano di montaggio: {a.progetto} / {nome}", "",
             f"Formato {a.formato} {W}x{H}, {fps} fps. Durata: {tc(durata_orig)} -> {tc(durata_fin)} "
             f"({100 * (1 - durata_fin / max(durata_orig, 0.001)):.0f}% in meno), {len(segmenti)} segmenti.", "",
             "Tagli: " + ", ".join(f"{v} {k}" for k, v in sorted(conta.items())), "",
             "| Ripresa | Da | A | Motivo | Testo tagliato |", "|---|---|---|---|---|"]
    for t in tagli:
        righe.append(f"| {t['sorgente']:02d} | {tc(t['inizio'])} | {tc(t['fine'])} | {t['motivo']} | {t['testo']} |")
    P["riepilogo"].write_text("\n".join(righe) + "\n", encoding="utf-8")
    info(righe[2])
    info(righe[4])
    info(f"Piano '{nome}' salvato in {P['piano']} (riepilogo: {P['riepilogo'].name})")


if __name__ == "__main__":
    main()
