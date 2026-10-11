"""Riinquadratura automatica (es. da 16:9 a 9:16) che segue il soggetto principale.

uso:
  python riinquadra.py --progetto nome --piano short-1 [--metodo volto|maschere|centro] [--fluidita 0.6]
                       [--maschere cartella] [--anteprima]

Per ogni ripresa usata dal piano, solo nei tratti che servono:
- volto (predefinito): rileva il volto più grande 5 volte al secondo (OpenCV, funziona senza internet);
- maschere: usa le maschere di separa_soggetto.py (più preciso, per prodotti, mani o corpo intero);
- centro: inquadratura fissa al centro.
Il percorso viene ammorbidito: piccoli spostamenti ignorati (zona morta), velocità massima limitata,
nessuno scatto. Il risultato va nel piano (campo "riinquadratura") e lo usa esporta.py.
Con --anteprima crea un foglio con le inquadrature scelte su alcuni fotogrammi.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (DECODIFICA_HW, cartelle_progetto, errore, filtro_sdr, info, leggi_json, percorsi_piano,  # noqa: E402
                    scegli_piano, scrivi_json)

CAMPIONI = 5  # fotogrammi analizzati al secondo
LARGH = 640   # larghezza di analisi


def leggi_fotogrammi(src, da, a):
    import numpy as np
    h = int(round(LARGH * src["altezza"] / src["larghezza"] / 2) * 2)
    vf = ",".join(x for x in [f"fps={CAMPIONI}", f"scale={LARGH}:{h}", filtro_sdr(src["hdr"], "mobius"), "format=gray"] if x)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", *DECODIFICA_HW, "-ss", f"{da:.3f}", "-t", f"{a - da:.3f}", "-i", src["file"],
                          "-vf", vf, "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8)
    n = len(fr) // (LARGH * h)
    return fr[: n * LARGH * h].reshape(n, h, LARGH)


def centri_volto(frames):
    try:
        import cv2
    except ImportError:
        errore("serve OpenCV: python3 verifica_strumenti.py --installa (chiedi prima all'utente).")
    fronte = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    profilo = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    out = []
    for f in frames:
        h = f.shape[0]
        trovati = list(fronte.detectMultiScale(f, 1.1, 5, minSize=(h // 12, h // 12)))
        if not trovati:
            trovati = list(profilo.detectMultiScale(f, 1.1, 5, minSize=(h // 12, h // 12)))
            trovati += [(LARGH - x - w, y, w, hh) for (x, y, w, hh) in profilo.detectMultiScale(f[:, ::-1].copy(), 1.1, 5, minSize=(h // 12, h // 12))]
        if trovati:
            x, y, w, hh = max(trovati, key=lambda r: r[2] * r[3])
            out.append(((x + w / 2) / LARGH, (y + hh / 2) / h))
        else:
            out.append(None)
    return out


def centri_maschere(cartella, da, n, fps_src):
    import cv2
    import numpy as np
    out = []
    for k in range(n):
        idx = int(round((da + k / CAMPIONI) * fps_src))
        p = Path(cartella) / f"{idx:05d}.png"
        if not p.exists():
            out.append(None)
            continue
        m = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        ys, xs = np.nonzero(m > 127)
        out.append((xs.mean() / m.shape[1], ys.mean() / m.shape[0]) if len(xs) else None)
    return out


def ammorbidisci(valori, larghezza_finestra, fluidita):
    """Zona morta + velocità massima + media mobile: l'inquadratura segue senza ballare."""
    # Riempie i buchi (nessun soggetto trovato) con l'ultimo valore noto, o il centro.
    pieni, ultimo = [], None
    for v in valori:
        ultimo = v if v is not None else ultimo
        pieni.append(ultimo)
    primo = next((v for v in pieni if v is not None), 0.5)
    pieni = [v if v is not None else primo for v in pieni]
    zona = larghezza_finestra * 0.18 * (0.5 + fluidita)       # spostamenti piccoli ignorati
    vmax = larghezza_finestra * (1.2 - fluidita) / CAMPIONI    # spostamento massimo per campione
    cur, out = pieni[0], []
    for v in pieni:
        diff = v - cur
        if abs(diff) > zona:
            passo = diff - zona * (1 if diff > 0 else -1)
            cur += max(-vmax, min(vmax, passo))
        out.append(cur)
    k = max(1, int(CAMPIONI * (0.4 + fluidita)))
    liscio = [sum(out[max(0, i - k):i + k + 1]) / len(out[max(0, i - k):i + k + 1]) for i in range(len(out))]
    return liscio


def main():
    ap = argparse.ArgumentParser(description="Riinquadratura che segue il soggetto")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--piano")
    ap.add_argument("--metodo", choices=["volto", "maschere", "centro"], default="volto")
    ap.add_argument("--maschere", help="cartella delle maschere (metodo maschere)")
    ap.add_argument("--fluidita", type=float, default=0.6, help="0 = segue subito, 1 = molto morbido")
    ap.add_argument("--anteprima", action="store_true")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    P = percorsi_piano(c, scegli_piano(c, a.piano))
    piano = leggi_json(P["piano"])
    analisi = {s["indice"]: s for s in leggi_json(c["lavoro"] / "analisi.json")["sorgenti"]}
    W, H = piano["larghezza"], piano["altezza"]
    rq = {}
    for indice in sorted({s["sorgente"] for s in piano["segmenti"]}):
        src = analisi[indice]
        if W / H >= src["larghezza"] / src["altezza"] - 0.01:
            info(f"[{indice:02d}] la ripresa ha già il formato giusto: nessuna riinquadratura.")
            continue
        larghezza_finestra = (src["altezza"] * W / H) / src["larghezza"]
        segs = [s for s in piano["segmenti"] if s["sorgente"] == indice]
        da, fine = max(0.0, min(s["inizio"] for s in segs) - 0.5), max(s["fine"] for s in segs) + 0.5
        if a.metodo == "centro":
            rq[str(indice)] = {"punti": [[da, 0.5]], "cy": 0.5, "metodo": "centro"}
            continue
        info(f"[{indice:02d}] Cerco il soggetto tra {da:.1f} e {fine:.1f} s ({a.metodo}) ...")
        if a.metodo == "volto":
            frames = leggi_fotogrammi(src, da, fine)
            centri = centri_volto(frames)
        else:
            if not a.maschere:
                errore("con --metodo maschere indica la cartella con --maschere (da separa_soggetto.py).")
            from fractions import Fraction
            n = int((fine - da) * CAMPIONI)
            centri = centri_maschere(a.maschere, da, n, float(Fraction(src["fps"])))
        trovati = sum(1 for x in centri if x)
        info(f"     soggetto trovato in {trovati}/{len(centri)} campioni")
        if trovati == 0:
            info("     nessun soggetto: inquadratura al centro. Prova --metodo maschere.")
        cx = ammorbidisci([x[0] if x else None for x in centri], larghezza_finestra, a.fluidita)
        punti = [[round(da + k / CAMPIONI, 3), round(v, 4)] for k, v in enumerate(cx)][::2]  # un punto ogni 0,4 s
        rq[str(indice)] = {"punti": punti or [[da, 0.5]], "cy": 0.5, "metodo": a.metodo}
    piano["riinquadratura"] = rq
    scrivi_json(P["piano"], piano)
    info(f"Riinquadratura salvata nel piano {P['piano'].name}.")

    if a.anteprima and rq:
        out = c["lavoro"] / f"riinquadratura-{piano.get('nome', 'piano')}.jpg"
        indice = next(iter(rq))
        src = analisi[int(indice)]
        punti = rq[indice]["punti"]
        scelti = punti[:: max(1, len(punti) // 8)][:8]
        cw = src["altezza"] * W / H
        cmd = ["ffmpeg", "-loglevel", "error", "-y"]
        filtri = []
        for k, (t, x) in enumerate(scelti):
            cmd += ["-ss", f"{t:.2f}", "-i", src["file"]]
            x0 = max(0, min(src["larghezza"] - cw, x * src["larghezza"] - cw / 2))
            sdr = filtro_sdr(src["hdr"], "mobius")
            filtri.append(f"[{k}:v]trim=end_frame=1,scale=960:-2{',' + sdr if sdr else ''},"
                          f"drawbox=x={x0 * 960 / src['larghezza']:.0f}:y=0:w={cw * 960 / src['larghezza']:.0f}:h=ih:color=orange@0.9:t=6[f{k}]")
        hh = int(960 * src["altezza"] / src["larghezza"])  # 4 colonne: x = colonna*960, y = riga*altezza
        if len(scelti) > 1:
            filtri.append("".join(f"[f{k}]" for k in range(len(scelti))) + f"xstack=inputs={len(scelti)}:layout=" +
                          "|".join(f"{(k % 4) * 960}_{(k // 4) * hh}" for k in range(len(scelti))) + ":fill=black")
        else:
            filtri.append("[f0]null")
        cmd += ["-filter_complex", ";".join(filtri), "-frames:v", "1", "-update", "1", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            info(f"Anteprima delle inquadrature: {out}")


if __name__ == "__main__":
    main()
