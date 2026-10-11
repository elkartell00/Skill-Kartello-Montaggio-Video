"""Prepara la cartella di lavoro e registra le riprese di un progetto.

uso:
  python3 prepara_progetto.py --progetto nome [--profilo base] [--formati video-lungo,shorts-dal-lungo]
                              [--video file1.mov file2.mov ...]

Crea (se manca) dentro la cartella da cui è stata avviata la skill:
  montaggio-video/
    profili/base/              copiato dalla skill al primo avvio
    da-montare/<progetto>/     qui l'utente mette le riprese (mai modificate)
    media/<progetto>/          grafiche, B-roll, musica ed effetti del progetto
    risultati/<progetto>/      <piano>/v01, v02, ... una cartella per ogni versione
    .lavoro/<progetto>/        file intermedi (trascrizione, piano di montaggio, segmenti)

Le riprese possono stare anche altrove: con --video si registrano i percorsi senza copiarle.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (SKILL_DIR, FORMATI, cartelle_progetto, errore, impronta_file, info,  # noqa: E402
                    leggi_json, scrivi_json)

ESTENSIONI_VIDEO = {".mov", ".mp4", ".m4v", ".mkv", ".mts", ".avi", ".hevc"}


def prepara_root(root):
    (root / "profili").mkdir(parents=True, exist_ok=True)
    base_dest = root / "profili" / "base"
    if not base_dest.exists():
        shutil.copytree(SKILL_DIR / "profili" / "base", base_dest)
        info(f"Creato il profilo base in {base_dest}")
    for d in ("da-montare", "risultati", "media", ".lavoro"):
        (root / d).mkdir(exist_ok=True)
    leggimi = root / "LEGGIMI.txt"
    if not leggimi.exists():
        leggimi.write_text(
            "Cartella di lavoro della skill montaggio-video.\n\n"
            "da-montare/<progetto>/  metti qui le riprese: non vengono mai modificate\n"
            "risultati/<progetto>/   per ogni montaggio (video-lungo, short-1...) una cartella per versione (v01, v02...)\n"
            "media/<progetto>/       grafiche, B-roll generati, musica ed effetti: non cancellarli finché servono\n"
            "profili/                i profili di stile, con il diario delle revisioni\n"
            ".lavoro/                file intermedi: si possono cancellare a lavoro finito\n",
            encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Prepara un progetto di montaggio")
    ap.add_argument("--progetto", required=True, help="nome del progetto (es. tavolo-in-legno)")
    ap.add_argument("--profilo", default="base")
    ap.add_argument("--formati", default="video-lungo", help="formati separati da virgola")
    ap.add_argument("--video", nargs="*", help="riprese da registrare (altrimenti quelle in da-montare/<progetto>)")
    ap.add_argument("--cartella", help="cartella di lavoro (predefinita: ./montaggio-video)")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    prepara_root(c["root"])
    for k in ("da_montare", "lavoro", "risultati"):
        c[k].mkdir(parents=True, exist_ok=True)
    (c["root"] / "media" / a.progetto).mkdir(parents=True, exist_ok=True)

    formati = [f.strip() for f in a.formati.split(",") if f.strip()]
    for f in formati:
        if f not in FORMATI and "x" not in f:
            errore(f"formato sconosciuto: {f}. Formati: {', '.join(FORMATI)} oppure LARGHEZZAxALTEZZA (es. 1080x1080)")

    if not (c["root"] / "profili" / a.profilo).exists():
        errore(f"il profilo '{a.profilo}' non esiste in {c['root'] / 'profili'}. Chiedi all'utente se crearlo.")

    if a.video:
        video = [Path(v).expanduser().resolve() for v in a.video]
    else:
        video = sorted(p.resolve() for p in c["da_montare"].iterdir()
                       if p.suffix.lower() in ESTENSIONI_VIDEO and not p.name.startswith("."))
    if not video:
        errore(f"nessuna ripresa trovata. Mettile in {c['da_montare']} oppure indica i file con --video.")
    for v in video:
        if not v.exists():
            errore(f"non trovo la ripresa {v}")

    precedente = leggi_json(c["progetto"]) if c["progetto"].exists() else {}
    progetto = {
        "nome": a.progetto,
        "profilo": a.profilo,
        "formati": formati,
        "sorgenti": [{"indice": i, "file": str(v), "impronta": impronta_file(v)} for i, v in enumerate(video)],
        "creato": precedente.get("creato"),
    }
    if not progetto["creato"]:
        from datetime import datetime
        progetto["creato"] = datetime.now().isoformat(timespec="seconds")
    scrivi_json(c["progetto"], progetto)

    info(f"Progetto '{a.progetto}' pronto con {len(video)} riprese (profilo: {a.profilo}, formati: {', '.join(formati)}).")
    for s in progetto["sorgenti"]:
        info(f"  [{s['indice']}] {s['file']}")
    info(f"Risultati in: {c['risultati']}")


if __name__ == "__main__":
    main()
