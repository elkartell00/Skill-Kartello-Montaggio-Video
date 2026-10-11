"""Libreria degli stili: imparare motion graphics, effetti e modi di montare dagli esempi dell'utente.

uso:
  python stili.py elenca
  python stili.py analizza --nome titoli-pop --video esempio.mp4 [--da 12.0 --a 18.5] [--fps 8]
  python stili.py confronta --nome titoli-pop --video riproduzione.mov [--esempio altro.mp4] [--punti 8]
  python stili.py sincronizza          # porta gli stili nel progetto Remotion (lo fa anche grafiche.py prepara)
  python stili.py indice               # rigenera stili/INDICE.md
  python stili.py salva --nome titoli-pop --messaggio "imparato dall'esempio del canale X"

La libreria sta in montaggio-video/stili/ ed è comune a tutti i profili: ogni esempio che l'utente dà
diventa uno stile riutilizzabile (o una variante di uno stile esistente), che poi si applica con i colori,
il brand e i contenuti del profilo. Struttura di uno stile:

  stili/<nome>/
    stile.md          scheda: cosa lo caratterizza, come riprodurlo, quando usarlo, cosa non copiare,
                      giudizio dell'utente, dove è stato usato
    esempio/          copia ridotta dell'esempio, fogli di fotogrammi, curva del movimento, palette
    componenti/       codice che lo riproduce: index.tsx (Remotion, esporta COMPOSIZIONI) ed eventuali
                      clip-modello.html del motore di animazione
    prove/            render di prova (con i colori originali e con quelli del brand)

analizza:  estrae dall'esempio fogli di fotogrammi fitti (8 al secondo: si vedono le fasi del movimento),
           i tagli, la curva del movimento con gli istanti in cui le animazioni partono e si fermano (durate
           tipiche e tipo di accelerazione), la palette dei colori. Il resto lo fai tu guardando i fogli.
confronta: mette affiancati esempio e riproduzione agli stessi istanti relativi, per controllare che lo
           stile sia uguale (il colore può essere diverso).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (DECODIFICA_HW, cartella_lavoro, errore, ffprobe, filtro_sdr, flusso_video, info,  # noqa: E402
                    info_hdr, scrivi_json)


def radice():
    r = cartella_lavoro() / "stili"
    r.mkdir(parents=True, exist_ok=True)
    return r


def nome_valido(n):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", n or ""):
        errore(f"nome di stile non valido: '{n}'. Usa minuscole, numeri e trattini (es. titoli-pop).")
    return n


def leggi_fotogrammi(video, da, a, fps, larghezza, sdr):
    import numpy as np
    p = ffprobe(video)
    v = flusso_video(p)
    w, h = int(v["width"]), int(v["height"])
    hh = int(round(larghezza * h / w / 2) * 2)
    vf = ",".join(x for x in [f"fps={fps}", f"scale={larghezza}:{hh}", sdr, "format=rgb24"] if x)
    cmd = ["ffmpeg", "-loglevel", "error", *DECODIFICA_HW, "-ss", f"{da:.3f}"]
    if a:
        cmd += ["-t", f"{a - da:.3f}"]
    raw = subprocess.run(cmd + ["-i", str(video), "-vf", vf, "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (larghezza * hh * 3)
    return np.frombuffer(raw[: n * larghezza * hh * 3], np.uint8).reshape(n, hh, larghezza, 3)


def palette(frames, k=6):
    """Colori principali (k-means semplice sui pixel campionati)."""
    import numpy as np
    px = frames[:, ::4, ::4].reshape(-1, 3).astype(np.float32)
    if len(px) > 40000:
        px = px[np.linspace(0, len(px) - 1, 40000).astype(int)]
    centri = px[np.linspace(0, len(px) - 1, k).astype(int)].copy()
    for _ in range(12):
        d = ((px[:, None, :] - centri[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            sel = px[lab == j]
            if len(sel):
                centri[j] = sel.mean(0)
    quote = np.bincount(lab, minlength=k) / len(lab)
    ordine = np.argsort(-quote)
    return [{"colore": "#%02X%02X%02X" % tuple(int(c) for c in centri[j]), "quota": round(float(quote[j]), 3)} for j in ordine]


def movimento(frames, fps):
    """Curva del movimento (differenza tra fotogrammi) e raffiche di animazione con durata e accelerazione."""
    import numpy as np
    g = frames.mean(-1)
    diff = np.abs(np.diff(g, axis=0)).mean((1, 2))
    if not len(diff):
        return [], []
    soglia = max(0.4, float(np.percentile(diff, 60)) * 1.2)
    raffiche, ini = [], None
    for i, d in enumerate(list(diff) + [0.0]):
        if d > soglia and ini is None:
            ini = i
        elif d <= soglia and ini is not None:
            pezzo = diff[ini:i]
            if len(pezzo) >= 2:
                picco = int(np.argmax(pezzo))
                pos = picco / max(1, len(pezzo) - 1)
                tipo = "parte veloce e frena (ease-out)" if pos < 0.35 else ("parte piano e accelera (ease-in)" if pos > 0.65 else "morbido in entrata e uscita (ease-in-out)")
                raffiche.append({"da": round(ini / fps, 3), "a": round(i / fps, 3), "durata": round((i - ini) / fps, 3),
                                 "fotogrammi_a_30fps": round((i - ini) / fps * 30), "andamento": tipo})
            ini = None
    return [round(float(x), 2) for x in diff], raffiche


def tagli(video, da, a, sdr):
    vf = ",".join(x for x in ["scale=320:-2", sdr, "select='gt(scene,0.35)'", "showinfo"] if x)
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{da:.3f}"]
    if a:
        cmd += ["-t", f"{a - da:.3f}"]
    r = subprocess.run(cmd + ["-i", str(video), "-vf", vf, "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [round(float(m.group(1)), 3) for m in re.finditer(r"pts_time:([\d.]+)", r.stderr)]


def fogli(video, da, a, fps, sdr, dest, per_foglio=48):
    """Fogli 8x6 di fotogrammi fitti; restituisce l'elenco dei fogli con i tempi di ogni casella."""
    durata = (a or (da + 3600)) - da
    out, k, t = [], 0, 0.0
    passo = per_foglio / fps
    while t < durata - 1e-3:
        f = dest / f"foglio-{k:02d}.jpg"
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{da + t:.3f}", "-t", f"{min(passo, durata - t):.3f}", "-i", str(video),
               "-vf", ",".join(x for x in [f"fps={fps}", "scale=240:-2", sdr, "tile=8x6:padding=3:color=white"] if x),
               "-frames:v", "1", str(f)]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0 or not f.exists():
            break
        out.append({"file": f.name, "da": round(da + t, 3), "passo": round(1 / fps, 4), "caselle": per_foglio})
        k += 1
        t += passo
        if not a and k > 20:
            break
    return out


def analizza(a):
    nome_valido(a.nome)
    v = Path(a.video).expanduser().resolve()
    if not v.exists():
        errore(f"non trovo l'esempio {v}")
    p = ffprobe(v)
    vs = flusso_video(p)
    if not vs:
        errore("l'esempio non contiene video.")
    dur = float(p["format"].get("duration", 0) or 0)
    da, fine = a.da or 0.0, a.a or dur
    sdr = filtro_sdr(info_hdr(vs), "mobius")
    d = radice() / a.nome
    es = d / "esempio"
    es.mkdir(parents=True, exist_ok=True)
    for sub in ("componenti", "prove"):
        (d / sub).mkdir(exist_ok=True)
    info(f"Analizzo {v.name} da {da:.2f} a {fine:.2f} s ...")
    # Copia ridotta del tratto, per i confronti successivi (l'esempio originale resta dov'è).
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{da:.3f}", "-t", f"{fine - da:.3f}", "-i", str(v),
                    "-vf", ",".join(x for x in ["scale=-2:720", sdr, "format=yuv420p"] if x), "-c:v", "libx264", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k", str(es / "esempio.mp4")], check=True)
    frames = leggi_fotogrammi(v, da, fine, a.fps, 160, sdr)
    curva, raffiche = movimento(frames, a.fps)
    pal = palette(leggi_fotogrammi(v, da, fine, 2, 320, sdr))
    ct = tagli(v, da, fine, sdr)
    fg = fogli(v, da, fine, a.fps, sdr, es)
    w, h = int(vs["width"]), int(vs["height"])
    analisi = {"esempio": str(v), "da": da, "a": fine, "durata": round(fine - da, 3), "formato": f"{w}x{h}",
               "fps_analisi": a.fps, "tagli": ct, "raffiche_di_movimento": raffiche, "palette": pal, "fogli": fg,
               "curva_movimento": curva, "creato": datetime.now().isoformat(timespec="minutes")}
    scrivi_json(es / "analisi.json", analisi)
    scheda = d / "stile.md"
    if not scheda.exists():
        scheda.write_text(MODELLO_SCHEDA.format(nome=a.nome, esempio=v.name, da=da, a=fine, data=datetime.now().strftime("%d/%m/%Y")),
                          encoding="utf-8")
    info(f"  {len(fg)} fogli di fotogrammi ({a.fps} al secondo), {len(ct)} tagli, {len(raffiche)} raffiche di movimento")
    if raffiche:
        durate = sorted(r["durata"] for r in raffiche)
        info(f"  durata tipica di un'animazione: {durate[len(durate) // 2]:.2f} s; andamenti: "
             + ", ".join(sorted({r['andamento'] for r in raffiche})))
    info("  palette dell'esempio: " + ", ".join(f"{c['colore']} ({c['quota'] * 100:.0f}%)" for c in pal))
    info(f"Ora guarda i fogli in {es} (ogni casella = 1/{a.fps} s, da sinistra a destra e dall'alto in basso), compila "
         f"{scheda} e scrivi la riproduzione in {d / 'componenti'}.")


MODELLO_SCHEDA = """# Stile: {nome}

Imparato il {data} da `{esempio}` ({da:.2f}–{a:.2f} s).

## In una frase
(cosa lo rende riconoscibile)

## Tipo
(titoli / scritte / sottotitoli / transizioni / B-roll animato / schede / grafici / intro / chiusura / effetti di montaggio / ...)

## Scomposizione
- **Elementi:** (forme, testi, icone, linee, maschere, sfondi)
- **Entrate e uscite:** (come appare e sparisce ogni elemento; direzione, scala, sfocatura, maschera)
- **Tempi:** (durate in fotogrammi a 30 fps, sfasamenti tra elementi, pause)
- **Andamento:** (molla, ease-out, ease-in-out, lineare; rimbalzo sì/no)
- **Tipografia:** (peso, maiuscolo, dimensione rispetto all'altezza, spaziatura, allineamento)
- **Impaginazione:** (posizione, margini, griglia, rapporto con il soggetto)
- **Colore:** (ruoli: fondo, testo, accento; contrasto) -> nella riproduzione si usano i colori del profilo
- **Effetti e suono:** (motion blur, grana, glitch, whoosh, pop...)
- **Montaggio:** (se l'esempio insegna anche un modo di tagliare: ritmo, zoom, transizioni)

## Riproduzione
- Componenti: `componenti/index.tsx` (id delle composizioni e proprietà)
- Proprietà principali: (testo, colori dal profilo, durata...)

## Quando usarlo
(che tipo di frase o momento, quali formati)

## Cosa non copiare
Loghi, marchi, sigle, grafiche identiche, musiche e personaggi dell'esempio: si prende lo stile, non il contenuto.

## Giudizio dell'utente e uso
- (data) (progetto) (cosa ha detto l'utente)
"""


def confronta(a):
    import numpy as np  # noqa: F401
    d = radice() / nome_valido(a.nome)
    es = Path(a.esempio).expanduser() if a.esempio else d / "esempio" / "esempio.mp4"
    rip = Path(a.video).expanduser()
    for f in (es, rip):
        if not f.exists():
            errore(f"non trovo {f}")
    durate = [float(ffprobe(f)["format"].get("duration", 0) or 0) for f in (es, rip)]
    out = d / "prove" / f"confronto-{rip.stem}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    n = max(2, a.punti)
    tmp = Path(tempfile.mkdtemp(prefix="confronto-"))
    righe = []
    for k in range(n):
        frac = (k + 0.5) / n
        celle = []
        for j, (f, dur) in enumerate(((es, durate[0]), (rip, durate[1]))):
            c = tmp / f"{k:02d}-{j}.png"
            # Ogni fotogramma su fondo grigio 480x270, così esempio e riproduzione hanno la stessa cornice.
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{frac * dur:.3f}", "-i", str(f), "-frames:v", "1",
                            "-vf", "scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2:color=0x222222",
                            str(c)], capture_output=True)
            if not c.exists():
                errore(f"non riesco a leggere un fotogramma di {f.name}")
            celle.append(c)
        righe.append(celle)
    cmd = ["ffmpeg", "-loglevel", "error", "-y"]
    for celle in righe:
        for c in celle:
            cmd += ["-i", str(c)]
    filtri = [f"[{2 * k}:v][{2 * k + 1}:v]hstack=2[r{k}]" for k in range(n)]
    filtri.append("".join(f"[r{k}]" for k in range(n)) + f"vstack={n}[o]")
    r = subprocess.run(cmd + ["-filter_complex", ";".join(filtri), "-map", "[o]", "-frames:v", "1", "-update", "1", str(out)],
                       capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        errore("confronto non riuscito:\n" + r.stderr[-500:])
    info(f"Confronto: {out} (a sinistra l'esempio, a destra la riproduzione, {n} istanti alla stessa posizione relativa)")


def sincronizza(silenzioso=False):
    """Copia i componenti di ogni stile nel progetto Remotion e genera il registro src/stili/index.tsx."""
    dest = cartella_lavoro() / ".strumenti" / "grafiche" / "src" / "stili"
    if not dest.parent.exists():
        if not silenzioso:
            info("Gli strumenti per le grafiche non sono ancora installati: lo farà grafiche.py prepara.")
        return
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    voci = []
    for s in sorted(p for p in radice().iterdir() if p.is_dir() and not p.name.startswith(".")):
        comp = s / "componenti"
        if not (comp / "index.tsx").exists():
            continue
        shutil.copytree(comp, dest / s.name, ignore=shutil.ignore_patterns("*.html", "*.md"))
        voci.append(s.name)
    righe = ["// Generato da stili.py sincronizza: non modificare a mano (la fonte è montaggio-video/stili/<nome>/componenti/).",
             "import type {SuMisura} from '../su-misura';"]
    righe += [f"import {{COMPOSIZIONI as C{i}}} from './{n}/index';" for i, n in enumerate(voci)]
    righe.append(f"export const STILI: SuMisura[] = [{', '.join(f'...C{i}' for i in range(len(voci)))}];")
    (dest / "index.tsx").write_text("\n".join(righe) + "\n", encoding="utf-8")
    if not silenzioso:
        info(f"Stili nel progetto Remotion: {', '.join(voci) or 'nessuno con componenti'}")


def indice():
    r = radice()
    righe = ["# Libreria degli stili", "",
             "Stili imparati dagli esempi dell'utente. Si applicano con i colori, il brand e i contenuti del profilo.", "",
             "| Stile | In una frase | Tipo | Quando usarlo | Composizioni |", "|---|---|---|---|---|"]
    for s in sorted(p for p in r.iterdir() if p.is_dir() and not p.name.startswith(".")):
        testo = (s / "stile.md").read_text(encoding="utf-8") if (s / "stile.md").exists() else ""
        def sezione(titolo):
            m = re.search(rf"## {titolo}\n(.*?)(\n## |\Z)", testo, re.S)
            v = (m.group(1).strip() if m else "").replace("\n", " ")
            return "" if v.startswith("(") else v[:140].replace("|", "/")
        comp = ""
        idx = s / "componenti" / "index.tsx"
        if idx.exists():
            comp = ", ".join(re.findall(r"id:\s*'([^']+)'", idx.read_text(encoding="utf-8")))
        righe.append(f"| [{s.name}]({s.name}/stile.md) | {sezione('In una frase')} | {sezione('Tipo')} | {sezione('Quando usarlo')} | {comp} |")
    (r / "INDICE.md").write_text("\n".join(righe) + "\n", encoding="utf-8")
    info(f"Indice aggiornato: {r / 'INDICE.md'}")


def main():
    ap = argparse.ArgumentParser(description="Libreria degli stili")
    ap.add_argument("azione", choices=["elenca", "analizza", "confronta", "sincronizza", "indice", "salva"])
    ap.add_argument("--nome")
    ap.add_argument("--video")
    ap.add_argument("--esempio")
    ap.add_argument("--da", type=float)
    ap.add_argument("--a", type=float)
    ap.add_argument("--fps", type=int, default=8)
    ap.add_argument("--punti", type=int, default=8)
    ap.add_argument("--messaggio")
    a = ap.parse_args()
    try:
        import numpy  # noqa: F401
    except ImportError:
        errore("serve numpy: usa il Python della skill (montaggio-video/.strumenti/venv).")
    if a.azione == "elenca":
        stili = sorted(p for p in radice().iterdir() if p.is_dir() and not p.name.startswith("."))
        if not stili:
            info("La libreria è vuota: dai alla skill un esempio di video o di motion graphic che ti piace.")
        for s in stili:
            pronto = "riproduzione pronta" if (s / "componenti" / "index.tsx").exists() or list((s / "componenti").glob("*.html")) else "da riprodurre"
            info(f"- {s.name} ({pronto})")
    elif a.azione == "analizza":
        if not (a.nome and a.video):
            errore("servono --nome e --video")
        analizza(a)
    elif a.azione == "confronta":
        if not (a.nome and a.video):
            errore("servono --nome e --video (la riproduzione)")
        confronta(a)
    elif a.azione == "sincronizza":
        sincronizza()
    elif a.azione == "indice":
        indice()
    else:
        if not (a.nome and a.messaggio):
            errore("servono --nome e --messaggio")
        from profili import salva
        indice()
        salva(radice(), a.messaggio, a.nome)


if __name__ == "__main__":
    main()
