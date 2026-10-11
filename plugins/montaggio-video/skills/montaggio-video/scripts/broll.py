"""B-roll: indice delle riprese extra dell'utente e ricerca negli archivi gratuiti.

uso:
  python broll.py indice --progetto nome [--cartella-broll percorso]
  python broll.py archivi --progetto nome --cerca "wood planks" [--archivio pexels|pixabay] [--orientamento orizzontale|verticale] [--quanti 5]

indice:  analizza le riprese extra (dettagli, lavorazioni, timelapse, prodotti) che l'utente mette in
         da-montare/<progetto>/broll/ (o in --cartella-broll): durata, risoluzione, fps, HDR e un foglio di
         4 fotogrammi per clip. Scrive .lavoro/<progetto>/broll/indice.json e i fogli broll-NN.jpg: guardali
         per capire cosa mostra ogni clip e abbinarla al punto giusto del parlato.
archivi: solo se il profilo prevede gli archivi gratuiti. Cerca video su Pexels o Pixabay e scarica i
         migliori in media/<progetto>/broll/archivio/. Serve la chiave gratuita dell'utente nella variabile
         d'ambiente PEXELS_API_KEY o PIXABAY_API_KEY (non chiederla in chat: si imposta nel terminale).
         Ogni file scaricato ha accanto un .txt con autore e pagina d'origine.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (cartelle_progetto, errore, esegui, ffprobe, filtro_sdr, flusso_video, fps_nominale, info,  # noqa: E402
                    info_hdr, scrivi_json, tc)

ESTENSIONI = {".mov", ".mp4", ".m4v", ".mkv", ".mts"}


def indice(a):
    c = cartelle_progetto(a.progetto, a.cartella)
    cart = Path(a.cartella_broll).expanduser() if a.cartella_broll else c["da_montare"] / "broll"
    if not cart.exists():
        errore(f"non trovo la cartella dei B-roll {cart}. Chiedi all'utente dove sono le riprese extra.")
    clip = sorted(p for p in cart.rglob("*") if p.suffix.lower() in ESTENSIONI and not p.name.startswith("."))
    if not clip:
        errore(f"nessun video in {cart}.")
    out = c["lavoro"] / "broll"
    out.mkdir(parents=True, exist_ok=True)
    voci = []
    for i, f in enumerate(clip):
        p = ffprobe(f)
        v = flusso_video(p)
        if not v:
            continue
        dur = float(p["format"].get("duration", 0) or 0)
        hdr = info_hdr(v)
        w, h = int(v["width"]), int(v["height"])
        for sd in v.get("side_data_list", []) or []:
            if abs(int(sd.get("rotation", 0))) in (90, 270):
                w, h = h, w
        foglio = out / f"broll-{i:02d}.jpg"
        vf = ",".join(x for x in [f"fps=4/{max(dur, 0.5):.3f}", "scale=360:-2", filtro_sdr(hdr, "mobius"), "tile=4x1:padding=2"] if x)
        esegui(["ffmpeg", "-loglevel", "error", "-y", "-i", str(f), "-vf", vf, "-frames:v", "1", str(foglio)], descrizione=f"foglio di {f.name}")
        voci.append({"indice": i, "file": str(f.resolve()), "durata": round(dur, 2), "larghezza": w, "altezza": h,
                     "orientamento": "verticale" if h > w else "orizzontale", "fps": fps_nominale(v), "hdr": hdr["tipo"],
                     "foglio": str(foglio), "descrizione": ""})
        info(f"[{i:02d}] {f.name}: {tc(dur)}, {w}x{h}, {hdr['tipo'] or 'SDR'}")
    scrivi_json(out / "indice.json", {"cartella": str(cart), "clip": voci})
    info(f"Indice in {out / 'indice.json'}. Guarda i fogli broll-NN.jpg e scrivi in 'descrizione' cosa mostra ogni clip.")


def scarica_json(url, intestazioni=None):
    req = urllib.request.Request(url, headers={"User-Agent": "montaggio-video", **(intestazioni or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def archivi(a):
    c = cartelle_progetto(a.progetto, a.cartella)
    dest = c["root"] / "media" / a.progetto / "broll" / "archivio"
    dest.mkdir(parents=True, exist_ok=True)
    orient = "portrait" if a.orientamento == "verticale" else "landscape"
    risultati = []
    if a.archivio == "pexels":
        chiave = os.environ.get("PEXELS_API_KEY")
        if not chiave:
            errore("manca la chiave di Pexels. L'utente la crea gratis su pexels.com/api e la imposta nel terminale: "
                   "export PEXELS_API_KEY=...  (poi riapre Claude Code).")
        d = scarica_json(f"https://api.pexels.com/videos/search?{urllib.parse.urlencode({'query': a.cerca, 'orientation': orient, 'per_page': a.quanti})}",
                         {"Authorization": chiave})
        for v in d.get("videos", []):
            files = sorted((f for f in v.get("video_files", []) if f.get("width")), key=lambda f: f["width"] * f["height"], reverse=True)
            if files:
                risultati.append({"id": v["id"], "url": files[0]["link"], "w": files[0]["width"], "h": files[0]["height"],
                                  "durata": v.get("duration"), "autore": v.get("user", {}).get("name"), "pagina": v.get("url")})
    else:
        chiave = os.environ.get("PIXABAY_API_KEY")
        if not chiave:
            errore("manca la chiave di Pixabay. L'utente la crea gratis su pixabay.com/api/docs e la imposta nel terminale: "
                   "export PIXABAY_API_KEY=...  (poi riapre Claude Code).")
        d = scarica_json(f"https://pixabay.com/api/videos/?{urllib.parse.urlencode({'key': chiave, 'q': a.cerca, 'per_page': max(3, a.quanti)})}")
        for v in d.get("hits", [])[: a.quanti]:
            best = max((x for x in v.get("videos", {}).values() if x.get("url")), key=lambda x: x.get("width", 0) * x.get("height", 0), default=None)
            if best:
                risultati.append({"id": v["id"], "url": best["url"], "w": best.get("width"), "h": best.get("height"),
                                  "durata": v.get("duration"), "autore": v.get("user"), "pagina": v.get("pageURL")})
    if not risultati:
        errore(f"nessun risultato per '{a.cerca}'. Prova parole diverse, in inglese.")
    for r in risultati:
        nome = f"{a.archivio}-{r['id']}.mp4"
        f = dest / nome
        if not f.exists():
            info(f"Scarico {nome} ({r['w']}x{r['h']}, {r['durata']} s) ...")
            req = urllib.request.Request(r["url"], headers={"User-Agent": "montaggio-video"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(f, "wb") as out:
                while True:
                    blocco = resp.read(1 << 20)
                    if not blocco:
                        break
                    out.write(blocco)
        f.with_suffix(".txt").write_text(f"Archivio: {a.archivio}\nAutore: {r['autore']}\nPagina: {r['pagina']}\nRicerca: {a.cerca}\n",
                                         encoding="utf-8")
    info(f"Scaricati {len(risultati)} video in {dest}. Guardali prima di usarli (anche con broll.py indice --cartella-broll).")


def main():
    ap = argparse.ArgumentParser(description="B-roll")
    ap.add_argument("azione", choices=["indice", "archivi"])
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--cartella-broll")
    ap.add_argument("--cerca")
    ap.add_argument("--archivio", choices=["pexels", "pixabay"], default="pexels")
    ap.add_argument("--orientamento", choices=["orizzontale", "verticale"], default="orizzontale")
    ap.add_argument("--quanti", type=int, default=5)
    a = ap.parse_args()
    if a.azione == "indice":
        indice(a)
    else:
        if not a.cerca:
            errore("indica cosa cercare con --cerca (meglio in inglese)")
        archivi(a)


if __name__ == "__main__":
    main()
