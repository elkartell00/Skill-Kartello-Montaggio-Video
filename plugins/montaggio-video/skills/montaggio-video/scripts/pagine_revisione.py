"""Pagine di revisione per una versione: confronto prima/dopo e visore delle clip (da motion-broll, MIT).

uso:
  python pagine_revisione.py --progetto nome [--piano video-lungo] [--versione v03]

Crea in risultati/<progetto>/<piano>/vNN/:
  confronto.html  anteprima affiancata, sovrapposta o a tendina rispetto alla versione precedente
                  (o all'originale se è la prima), sincronizzate, con i punti delle grafiche sulla timeline
  clip.html       le grafiche, i B-roll e le animazioni della versione, una per una
  TEMPI.md        ogni sovrapposizione con entrata, uscita e cosa copre

Le pagine funzionano aprendole nel browser, senza internet (font inclusi).
"""
import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import SKILL_DIR, cartelle_progetto, errore, info, leggi_json, percorsi_piano, scegli_piano, tc  # noqa: E402


def font_css():
    f = SKILL_DIR / "motore-animazioni" / "fonts"
    b64 = lambda p: base64.b64encode(p.read_bytes()).decode()
    return ("@font-face{font-family:'Geist';src:url(data:font/woff2;base64," + b64(f / "Geist-Variable.woff2") +
            ") format('woff2');font-weight:100 900}@font-face{font-family:'Geist Mono';src:url(data:font/woff2;base64," +
            b64(f / "GeistMono-Medium.woff2") + ") format('woff2');font-weight:100 900}")


def main():
    ap = argparse.ArgumentParser(description="Pagine di revisione")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--versione")
    ap.add_argument("--piano")
    a = ap.parse_args()
    c = cartelle_progetto(a.progetto, a.cartella)
    nome_piano = scegli_piano(c, a.piano)
    P = percorsi_piano(c, nome_piano)
    versioni = sorted((p for p in P["risultati"].glob("v[0-9]*") if p.is_dir()), key=lambda p: int(p.name[1:]))
    if not versioni:
        errore("nessuna versione esportata.")
    vdir = P["risultati"] / a.versione if a.versione else versioni[-1]
    prev = next((v for v in reversed(versioni) if int(v.name[1:]) < int(vdir.name[1:]) and (v / "anteprima.mp4").exists()), None)
    ante = vdir / "anteprima.mp4"
    if not ante.exists():
        errore(f"in {vdir.name} manca anteprima.mp4: esporta prima l'anteprima.")
    piano = leggi_json(vdir / "piano.json")
    base = c["root"]
    font = font_css()
    titolo = f"{a.progetto} · {nome_piano} · {vdir.name}"

    # Confronto: con la versione precedente, oppure con la prima ripresa originale (ridotta per il browser).
    if prev:
        orig = os.path.relpath(prev / "anteprima.mp4", vdir)
        sotto = f"Sinistra o sopra: {prev.name}. Destra o sotto: {vdir.name}."
    else:
        indice = piano["segmenti"][0]["sorgente"]
        an = next(s for s in leggi_json(c["lavoro"] / "analisi.json")["sorgenti"] if s["indice"] == indice)
        rid = vdir / "originale-ridotto.mp4"
        if not rid.exists():
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", an["file"], "-vf", "scale=-2:540,format=yuv420p",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "128k", str(rid)])
        orig = rid.name
        sotto = "Sinistra o sopra: la ripresa originale. Destra o sotto: il montaggio."
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ante)],
                               capture_output=True, text=True).stdout.strip() or 0)
    sovr = piano.get("sovrapposizioni") or []
    marks = [[o["inizio"], o.get("fine") or o["inizio"] + 3, str(i + 1), Path(o["file"]).stem] for i, o in enumerate(sovr)]
    tpl = (SKILL_DIR / "modelli-pagine" / "compare.html").read_text(encoding="utf-8")
    html = (tpl.replace("/*FONTS*/", font).replace("/*DUR*/0", f"{dur:.2f}").replace("/*MARKS*/[]", json.dumps(marks, ensure_ascii=False))
            .replace("/*ORIG*/", orig).replace("/*BROLL*/", ante.name).replace("/*TITLE*/", titolo).replace("/*SUB*/", sotto))
    (vdir / "confronto.html").write_text(html, encoding="utf-8")

    # Visore delle clip.
    clips = [{"n": "▶", "full": True, "t": "Anteprima completa", "tc": "tutto il video", "q": "Per la revisione.", "f": ante.name, "src": ante.name}]
    for i, o in enumerate(sovr, 1):
        f = (base / o["file"]) if not Path(o["file"]).is_absolute() else Path(o["file"])
        src = os.path.relpath(f, vdir)
        alpha = f.suffix.lower() == ".mov"
        if alpha:  # i browser non leggono il ProRes: copia su nero per la pagina
            pv = vdir / f"clip-{i:02d}.mp4"
            if not pv.exists():
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=black:s=1920x1080", "-i", str(f),
                                "-filter_complex", "[1]scale=1920:1080[o];[0][o]overlay=shortest=1", "-c:v", "libx264", "-crf", "22",
                                "-pix_fmt", "yuv420p", str(pv)])
            src = pv.name
        fine = o.get("fine") or o["inizio"]
        clips.append({"n": f"{i:02d}", "t": Path(o["file"]).stem, "tc": f"{tc(o['inizio'])} – {tc(fine)}", "q": o.get("nota", ""),
                      "f": f.name, "src": src, **({"alpha": True} if alpha else {})})
    v = (SKILL_DIR / "modelli-pagine" / "viewer.html").read_text(encoding="utf-8")
    v = (v.replace("/*FONTS*/", font).replace("/*CLIPS*/[]", json.dumps(clips, ensure_ascii=False)).replace("/*TITLE*/", titolo)
         .replace("/*SUB*/", f"{len(sovr)} sovrapposizioni + anteprima"))
    (vdir / "clip.html").write_text(v, encoding="utf-8")

    righe = ["| # | File | Entra | Esce | Modo | Nota |", "|---|---|---|---|---|---|"]
    for i, o in enumerate(sovr, 1):
        righe.append(f"| {i:02d} | {Path(o['file']).name} | {tc(o['inizio'])} | {tc(o.get('fine') or o['inizio'])} | {o.get('modo', 'auto')} | {o.get('nota', '')} |")
    (vdir / "TEMPI.md").write_text(f"# Sovrapposizioni di {titolo}\n\n" + "\n".join(righe) + "\n", encoding="utf-8")
    info(f"Pagine pronte: {vdir / 'confronto.html'} e {vdir / 'clip.html'}")


if __name__ == "__main__":
    main()
