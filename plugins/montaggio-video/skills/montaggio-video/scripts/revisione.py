"""Revisione scena per scena nel player (da Motion OS, MIT): prepara reel.json per una versione.

uso:
  python revisione.py --progetto nome [--piano video-lungo] [--versione v03] [--scena 30]

Crea risultati/<progetto>/<piano>/reel.json, che descrive l'anteprima della versione per il player:
  - scene: blocchi del montaggio di circa --scena secondi (shorts: 6), tagliati tra un segmento e l'altro;
  - per ogni segmento: "Nel montaggio" (tieni/togli) e "Zoom" (nessuno/scatto/lento);
  - per ogni frase dei sottotitoli: il testo, correggibile (gli errori di trascrizione si correggono qui);
  - per ogni sovrapposizione (grafica, B-roll, animazione): tempi, posizione e dimensione, e i testi delle
    grafiche Remotion (se nel piano la sovrapposizione ha "remotion": {"tipo", "props"}).
Poi avvia il player (in background) con:
  node $SKILL/revisione-player/serve.mjs risultati/<progetto>/<piano>
Il player legge reel.json ogni pochi secondi: rigenerandolo per una nuova versione si ricarica da solo.
"""
import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (SKILL_DIR, calcola_timeline, cartelle_progetto, errore, info, leggi_json, percorsi_piano,  # noqa: E402
                    scegli_piano, scrivi_json)


def main():
    ap = argparse.ArgumentParser(description="Prepara la revisione scena per scena")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--piano")
    ap.add_argument("--versione")
    ap.add_argument("--scena", type=float, default=0, help="durata indicativa di una scena in secondi")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    nome = scegli_piano(c, a.piano)
    P = percorsi_piano(c, nome)
    versioni = sorted((p for p in P["risultati"].glob("v[0-9]*") if (p / "anteprima.mp4").exists()), key=lambda p: int(p.name[1:]))
    if not versioni:
        errore("nessuna anteprima per questo piano: esporta prima l'anteprima.")
    vdir = P["risultati"] / a.versione if a.versione else versioni[-1]
    if not (vdir / "anteprima.mp4").exists():
        errore(f"in {vdir.name} manca anteprima.mp4.")
    piano = leggi_json(vdir / "piano.json")
    pezzi, mappa, durata = calcola_timeline(piano)
    W, H = piano["larghezza"], piano["altezza"]
    verticale = H > W
    lung_scena = a.scena or (6.0 if verticale else 30.0)
    parole = leggi_json(P["parole"])["parole"] if P["parole"].exists() else []

    # Scene: si chiude una scena al primo confine di segmento dopo lung_scena secondi.
    confini, inizio = [], 0.0
    for pz in pezzi:
        if pz["tipo"] != "segmento":
            continue
        fine = pz["inizio_t"] + pz["durata"]
        if fine - inizio >= lung_scena or pz is pezzi[-1]:
            confini.append((inizio, fine))
            inizio = fine
    if not confini or confini[-1][1] < durata - 0.01:
        confini.append((inizio, durata))

    def testo_tra(t0, t1):
        return " ".join(p["w"] for p in parole if t0 <= p["inizio"] < t1)

    scene = []
    for k, (t0, t1) in enumerate(confini, 1):
        prime = testo_tra(t0, t1).split()[:3]
        scene.append({"id": f"S{k}", "name": " ".join(prime) + ("…" if prime else "") or f"Scena {k}", "t": [round(t0, 3), round(t1, 3)], "els": []})

    def scena_di(t):
        return next((s for s in scene if t < s["t"][1] - 1e-6), scene[-1])

    # Segmenti.
    for pz in pezzi:
        if pz["tipo"] != "segmento":
            continue
        seg = pz["seg"]
        t0, t1 = pz["inizio_t"], pz["inizio_t"] + pz["durata"]
        z = (seg.get("zoom") or {}).get("tipo", "nessuno") if seg.get("zoom") else "nessuno"
        scena_di(t0)["els"].append({
            "id": f"seg-{seg['id']}", "label": f"Segmento {seg['id']}", "t": [round(t0, 3), round(t1, 3)], "box": None,
            "src": f"piano:segmenti[id={seg['id']}] ripresa {seg['sorgente']} {seg['inizio']:.2f}-{seg['fine']:.2f}",
            "props": {
                "tieni": {"type": "choice", "label": "Nel montaggio", "options": ["tieni", "togli"], "v": "tieni"},
                "zoom": {"type": "choice", "label": "Zoom", "options": ["nessuno", "scatto", "lento"], "v": z},
                "motion": {"type": "motion", "label": "Altro (ritmo, taglio, effetti)", "v": seg.get("testo", "")[:120]},
            }})

    # Frasi dei sottotitoli.
    if parole:
        frase, n = [], 0
        def chiudi(fr):
            nonlocal n
            if not fr:
                return
            n += 1
            t0, t1 = fr[0]["inizio"], fr[-1]["fine"]
            box = [6, 62, 88, 14] if verticale else [8, 80, 84, 14]
            scena_di(t0)["els"].append({
                "id": f"sub-{n}", "label": f"Sottotitolo {n}", "t": [round(t0, 3), round(t1, 3)], "box": box,
                "src": "sottotitoli (correzioni -> piano.sostituzioni)",
                "props": {"text": {"type": "text", "label": "Testo", "v": " ".join(p["w"] for p in fr)}}})
        for p in parole:
            if frase and (p["inizio"] - frase[-1]["fine"] > 0.6 or len(frase) >= 14):
                chiudi(frase)
                frase = []
            frase.append(p)
            if p["w"].endswith((".", "?", "!")):
                chiudi(frase)
                frase = []
        chiudi(frase)

    # Sovrapposizioni.
    base = c["root"]
    for k, o in enumerate(piano.get("sovrapposizioni") or [], 1):
        f = Path(o["file"])
        fine = o.get("fine") or (o["inizio"] + 3)
        modo = o.get("modo", "sopra")
        if modo == "riquadro":
            x, y, w, h = o["riquadro"]
            box = [x * 100, y * 100, w * 100, h * 100]
        else:
            box = [0, 0, 100, 100]
        props = {}
        rem = o.get("remotion")
        if rem:
            pf = (base / rem["props"]) if not Path(rem["props"]).is_absolute() else Path(rem["props"])
            if pf.exists():
                dati = json.loads(pf.read_text(encoding="utf-8"))
                for campo in ("testo", "sottotitolo", "emoji"):
                    if campo in dati:
                        props[campo] = {"type": "text", "label": campo.capitalize(), "v": dati[campo]}
                if "x" in dati and "y" in dati:
                    box = [max(0, dati["x"] * 100 - 15), max(0, dati["y"] * 100 - 5), 30, 10]
        props["motion"] = {"type": "motion", "label": "Movimento", "v": o.get("nota", "")}
        scena_di(o["inizio"])["els"].append({
            "id": f"ov-{k}", "label": o.get("nota") or f.stem, "t": [round(o["inizio"], 3), round(fine, 3)], "box": box,
            "src": f"piano:sovrapposizioni[{k - 1}] {o['file']}" + (f" · props {rem['props']}" if rem else ""),
            "props": props})

    for s in scene:
        s["els"].sort(key=lambda e: e["t"][0])
    reel = {
        "id": f"{a.progetto}-{nome}", "title": f"{a.progetto} · {nome}", "version": int(vdir.name[1:]),
        "path": str(vdir), "src": f"{vdir.name}/anteprima.mp4",
        "w": W, "h": H, "fps": round(float(Fraction(piano["fps"])), 3), "duration": round(durata, 3),
        "brand": {"colors": [{"id": "accento", "name": "Accento", "v": "#FF5A1F"}, {"id": "testo", "name": "Testo", "v": "#0B0B0B"},
                             {"id": "fondo", "name": "Fondo", "v": "#FFFFFF"}],
                  "fonts": [{"id": "testi", "name": "Testi", "v": "Geist"}], "logo": None},
        "audio": {"music": None, "bpm": 0, "drop": 0, "musicVol": 0.6, "sfxVol": 0.8},
        "assets": [], "scenes": scene, "notes": [],
    }
    scrivi_json(P["risultati"] / "reel.json", reel)
    info(f"Revisione pronta per {nome} {vdir.name}: {len(scene)} scene. Avvia il player in background con:")
    info(f'  node "{SKILL_DIR / "revisione-player" / "serve.mjs"}" "{P["risultati"]}"')


if __name__ == "__main__":
    main()
