"""Sottotitoli sulla timeline montata, a partire dalla trascrizione e dal piano di montaggio.

uso:
  python sottotitoli.py --progetto nome [--stile frase|parole] [--max-caratteri 42] [--max-righe 2]
                        [--parole-per-blocco 3] [--font Geist] [--dimensione 64] [--colore FFFFFF]
                        [--evidenzia FF5A1F] [--posizione 0.78] [--maiuscolo]

Scrive in .lavoro/<progetto>/:
  parole-timeline.json  ogni parola con i tempi sulla timeline montata (lo usano anche le grafiche)
  sottotitoli.srt       file da caricare su YouTube o da importare in DaVinci
  sottotitoli.ass       stesso testo con stile, da bruciare nel video (anteprima e shorts)

stile frase:  blocchi di 1-2 righe, per i video lunghi.
stile parole: pochi parole per volta, con la parola detta evidenziata (tipico di Shorts e Reels).
Le parole tagliate (intercalari, ripetizioni) non compaiono.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import cartelle_progetto, info, leggi_json, scrivi_json  # noqa: E402


def parole_sulla_timeline(piano, trascr):
    per_src = {s["indice"]: s["parole"] for s in trascr["sorgenti"]}
    out, t_out = [], 0.0
    for seg in piano["segmenti"]:
        for p in per_src.get(seg["sorgente"], []):
            if p.get("taglia"):
                continue
            centro = (p["inizio"] + p["fine"]) / 2
            if seg["inizio"] <= centro < seg["fine"]:
                ini = t_out + max(0.0, p["inizio"] - seg["inizio"])
                fin = t_out + min(seg["fine"], p["fine"]) - seg["inizio"]
                out.append({"w": p["w"], "inizio": round(ini, 3), "fine": round(max(fin, ini + 0.05), 3), "segmento": seg["id"]})
        t_out += seg["fine"] - seg["inizio"]
    return out


def blocchi_frase(parole, max_car, max_righe):
    blocchi, cur = [], []
    def lung(ws):
        return len(" ".join(x["w"] for x in ws))
    for i, p in enumerate(parole):
        if cur and (lung(cur + [p]) > max_car * max_righe or p["inizio"] - cur[-1]["fine"] > 0.8):
            blocchi.append(cur)
            cur = []
        cur.append(p)
        if p["w"].endswith((".", "?", "!")) and lung(cur) > max_car * 0.6:
            blocchi.append(cur)
            cur = []
    if cur:
        blocchi.append(cur)
    return blocchi


def blocchi_parole(parole, n):
    blocchi, cur = [], []
    for p in parole:
        if cur and (len(cur) >= n or p["inizio"] - cur[-1]["fine"] > 0.5 or cur[-1]["w"].endswith((".", "?", "!"))):
            blocchi.append(cur)
            cur = []
        cur.append(p)
    if cur:
        blocchi.append(cur)
    return blocchi


def a_righe(ws, max_car):
    righe, cur = [], ""
    for w in ws:
        prova = (cur + " " + w).strip()
        if len(prova) > max_car and cur:
            righe.append(cur)
            cur = w
        else:
            cur = prova
    if cur:
        righe.append(cur)
    return righe


def ts_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ts_ass(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def colore_ass(hex6, alpha="00"):
    hex6 = hex6.lstrip("#")
    return f"&H{alpha}{hex6[4:6]}{hex6[2:4]}{hex6[0:2]}"


def main():
    ap = argparse.ArgumentParser(description="Sottotitoli sulla timeline montata")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--stile", choices=["frase", "parole"], default="frase")
    ap.add_argument("--max-caratteri", type=int, default=42)
    ap.add_argument("--max-righe", type=int, default=2)
    ap.add_argument("--parole-per-blocco", type=int, default=3)
    ap.add_argument("--font", default="Geist")
    ap.add_argument("--dimensione", type=int, default=0, help="altezza del testo in pixel (0 = automatica)")
    ap.add_argument("--colore", default="FFFFFF")
    ap.add_argument("--evidenzia", default="FF5A1F", help="colore della parola detta (stile parole)")
    ap.add_argument("--contorno", default="0B0B0B")
    ap.add_argument("--posizione", type=float, default=0.0, help="altezza del testo, 0-1 dall'alto (0 = automatica)")
    ap.add_argument("--maiuscolo", action="store_true")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    piano = leggi_json(c["lavoro"] / "piano-montaggio.json")
    trascr = leggi_json(c["lavoro"] / "trascrizione.json")
    # Compaiono le parole che cadono nei segmenti del piano (anche se modificato a mano), tranne
    # gli intercalari. Le frasi ripetute sono già fuori dai segmenti.
    from pulizia import segna_intercalari
    pp = piano.get("parametri_pulizia", {})
    for s in trascr["sorgenti"]:
        segna_intercalari(s["parole"], not pp.get("intercalari", True))

    parole = parole_sulla_timeline(piano, trascr)
    scrivi_json(c["lavoro"] / "parole-timeline.json", {"fps": piano["fps"], "parole": parole})

    W, H = piano["larghezza"], piano["altezza"]
    verticale = H > W
    dim = a.dimensione or int(H * (0.045 if verticale else 0.05))
    pos = a.posizione or (0.70 if verticale else 0.88)
    max_car = a.max_caratteri if not verticale or a.max_caratteri != 42 else 24
    blocchi = blocchi_parole(parole, a.parole_per_blocco) if a.stile == "parole" else blocchi_frase(parole, max_car, a.max_righe)

    srt = []
    for i, b in enumerate(blocchi, 1):
        testo = "\n".join(a_righe([w["w"] for w in b], max_car))
        srt.append(f"{i}\n{ts_srt(b[0]['inizio'])} --> {ts_srt(b[-1]['fine'])}\n{testo}\n")
    (c["lavoro"] / "sottotitoli.srt").write_text("\n".join(srt), encoding="utf-8")

    margine_v = int(H * (1 - pos))
    ass = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Base,{a.font},{dim},{colore_ass(a.colore)},{colore_ass(a.evidenzia)},{colore_ass(a.contorno)},{colore_ass('000000', '80')},"
        f"1,0,0,0,100,100,0,0,1,{max(2, dim // 14)},0,2,{int(W * 0.06)},{int(W * 0.06)},{margine_v},1", "",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    up = (lambda s: s.upper()) if a.maiuscolo else (lambda s: s)
    for b in blocchi:
        if a.stile == "parole":
            # Un evento per parola: il blocco resta fermo e cambia solo la parola evidenziata.
            for k, w in enumerate(b):
                fine = b[k + 1]["inizio"] if k + 1 < len(b) else b[-1]["fine"]
                testo = " ".join((f"{{\\c{colore_ass(a.evidenzia)}}}{up(x['w'])}{{\\c{colore_ass(a.colore)}}}" if j == k else up(x["w"]))
                                 for j, x in enumerate(b))
                ass.append(f"Dialogue: 0,{ts_ass(w['inizio'])},{ts_ass(fine)},Base,,0,0,0,,{testo}")
        else:
            testo = "\\N".join(up(r) for r in a_righe([w["w"] for w in b], max_car))
            ass.append(f"Dialogue: 0,{ts_ass(b[0]['inizio'])},{ts_ass(b[-1]['fine'])},Base,,0,0,0,,{testo}")
    (c["lavoro"] / "sottotitoli.ass").write_text("\n".join(ass) + "\n", encoding="utf-8")
    info(f"{len(parole)} parole, {len(blocchi)} sottotitoli. File: sottotitoli.srt, sottotitoli.ass, parole-timeline.json")


if __name__ == "__main__":
    main()
