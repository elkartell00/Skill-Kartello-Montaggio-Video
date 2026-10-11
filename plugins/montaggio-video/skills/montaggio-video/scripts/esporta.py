"""Esporta il montaggio rigenerandolo sempre dalle riprese originali.

uso:
  python esporta.py --progetto nome --modo anteprima|finale [--sottotitoli brucia|file|no]
                    [--tonemap mobius|hable|reinhard] [--encoder x264|videotoolbox] [--versione v03]
                    [--loudness -14] [--paralleli N]

Come funziona:
1. Ogni segmento del piano viene ricavato direttamente dall'originale (mai da un video già esportato):
   conversione HDR -> SDR se serve, adattamento al formato, fotogrammi al secondo costanti, micro
   dissolvenze audio di 10 ms per non sentire "click" sui tagli. I segmenti già fatti con le stesse
   impostazioni vengono riusati, così le revisioni sono veloci e la qualità resta identica.
2. I segmenti vengono uniti; l'audio viene portato al livello di YouTube/Instagram (-14 LUFS, picchi
   sotto -1,5 dBTP) con una normalizzazione in due passaggi.
3. Se vanno bruciati i sottotitoli (o, dalle tappe successive, grafiche), i segmenti si fanno in una
   qualità intermedia molto alta e la codifica finale avviene una sola volta.

anteprima: bassa risoluzione (lato corto 540 px), veloce, sottotitoli visibili.
finale:    risoluzione piena del formato (video lungo 3840x2160, verticali 1080x1920).

Ogni anteprima crea una nuova versione risultati/<progetto>/vNN. L'export finale va nella versione
più recente se il piano non è cambiato, altrimenti in una nuova.
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (DECODIFICA_HW, SKILL_DIR, adatta_dimensioni, avviso, cartelle_progetto, errore, esegui,  # noqa: E402
                    filtro_sdr, impronta, impronta_file, info, leggi_json, prossima_versione,
                    scrivi_json, tc)

MAC = platform.system() == "Darwin"


def parametri_video(modo, encoder, intermedio):
    """Codifica dei segmenti."""
    if modo == "anteprima":
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p"]
    if intermedio:  # qualità intermedia: quasi senza perdite, perché verrà ricodificata una volta
        return ["-c:v", "libx264", "-preset", "fast", "-crf", "10", "-pix_fmt", "yuv420p"]
    return parametri_finali(encoder)


def parametri_finali(encoder):
    if encoder == "videotoolbox":
        return ["-c:v", "hevc_videotoolbox", "-q:v", "70", "-tag:v", "hvc1", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p"]


COLORI_709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def dimensioni_anteprima(W, H):
    k = 540 / min(W, H)
    return int(round(W * k / 2) * 2), int(round(H * k / 2) * 2)


def render_segmento(seg, src, out_w, out_h, fps, vparams, adattamento, operatore, dest):
    n_frame = max(1, round((seg["fine"] - seg["inizio"]) * float(Fraction(fps))))
    dur = n_frame / float(Fraction(fps))
    # Prima i fotogrammi al secondo e il ridimensionamento, poi la conversione HDR: se l'uscita è più
    # piccola dell'originale la conversione (pesante, in virgola mobile) lavora su meno pixel.
    vf = ",".join(x for x in [
        f"fps={fps}",
        adatta_dimensioni(src["larghezza"], src["altezza"], out_w, out_h, adattamento),
        filtro_sdr(src["hdr"], operatore),
        "setsar=1", "format=yuv420p"] if x)
    fade = min(0.01, dur / 4)
    af = (f"aresample=48000,aformat=channel_layouts=stereo,afade=t=in:st=0:d={fade:.3f},"
          f"afade=t=out:st={max(0, dur - fade):.4f}:d={fade:.3f},apad,atrim=0:{dur:.6f}")
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *DECODIFICA_HW]
    cmd += ["-ss", f"{seg['inizio']:.6f}", "-i", src["file"]]
    if src["audio"]:
        amap = "0:a:0"
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        amap = "1:a:0"
    tmp = dest.with_name(dest.stem + ".tmp.mkv")
    cmd += ["-map", "0:v:0", "-map", amap, "-vf", vf, "-af", af, "-frames:v", str(n_frame), *vparams, *COLORI_709,
            "-c:a", "pcm_s16le", "-f", "matroska", str(tmp)]
    esegui(cmd, descrizione=f"segmento {seg['id']}")
    os.replace(tmp, dest)
    return dest


def misura_loudness(lista, target, tp):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "concat", "-safe", "0", "-i", str(lista), "-map", "0:a",
                        "-af", f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        avviso("non riesco a misurare il volume: uso la normalizzazione in un solo passaggio.")
        return None
    import json
    return json.loads(m.group(0))


def main():
    ap = argparse.ArgumentParser(description="Esportazione dagli originali")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--modo", choices=["anteprima", "finale"], required=True)
    ap.add_argument("--sottotitoli", choices=["brucia", "file", "no"], default="file",
                    help="brucia = scritti nel video; file = solo .srt a parte (nell'anteprima si vedono comunque)")
    ap.add_argument("--tonemap", default="mobius", help="conversione HDR: mobius, hable o reinhard")
    ap.add_argument("--encoder", choices=["x264", "videotoolbox"], default="x264",
                    help="videotoolbox = codifica hardware del Mac, molto più veloce, qualità leggermente inferiore")
    ap.add_argument("--versione", help="cartella di versione da usare (es. v03)")
    ap.add_argument("--loudness", type=float, default=-14.0, help="volume medio in LUFS (YouTube/Instagram: -14)")
    ap.add_argument("--picco", type=float, default=-1.5, help="picco massimo in dBTP")
    ap.add_argument("--paralleli", type=int, default=0, help="segmenti codificati insieme (0 = automatico)")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    piano = leggi_json(c["lavoro"] / "piano-montaggio.json")
    analisi = {s["indice"]: s for s in leggi_json(c["lavoro"] / "analisi.json")["sorgenti"]}
    if not piano["segmenti"]:
        errore("il piano di montaggio non ha segmenti.")
    if a.encoder == "videotoolbox" and not MAC:
        errore("la codifica videotoolbox esiste solo su Mac.")
    for s in analisi.values():
        if not Path(s["file"]).exists():
            errore(f"la ripresa originale {s['file']} non esiste più.")

    W, H, fps = piano["larghezza"], piano["altezza"], piano["fps"]
    if a.modo == "anteprima":
        W, H = dimensioni_anteprima(W, H)
    ass = c["lavoro"] / "sottotitoli.ass"
    brucia = a.sottotitoli == "brucia" or (a.modo == "anteprima" and a.sottotitoli == "file")
    if brucia and not ass.exists():
        avviso("non trovo sottotitoli.ass: esporto senza sottotitoli. Esegui prima sottotitoli.py.")
        brucia = False
    intermedio = a.modo == "finale" and brucia
    vparams = parametri_video(a.modo, a.encoder, intermedio)

    # Versione di destinazione.
    hash_piano = impronta(piano)
    if a.versione:
        versione = a.versione
    elif a.modo == "finale":
        ultime = sorted(p for p in c["risultati"].glob("v[0-9]*") if p.is_dir())
        stessa = ultime and (ultime[-1] / "piano-montaggio.json").exists() and \
            impronta(leggi_json(ultime[-1] / "piano-montaggio.json")) == hash_piano
        versione = ultime[-1].name if stessa else prossima_versione(c["risultati"])
    else:
        versione = prossima_versione(c["risultati"])
    vdir = c["risultati"] / versione
    vdir.mkdir(parents=True, exist_ok=True)
    scrivi_json(vdir / "piano-montaggio.json", piano)

    # 1. Segmenti dagli originali (con cache).
    cache = c["lavoro"] / "segmenti" / ("anteprima" if a.modo == "anteprima" else ("intermedi" if intermedio else "finali"))
    cache.mkdir(parents=True, exist_ok=True)
    lavori = []
    for seg in piano["segmenti"]:
        src = analisi[seg["sorgente"]]
        chiave = impronta(src["file"], impronta_file(src["file"]), seg["inizio"], seg["fine"], W, H, fps,
                          piano.get("adattamento", "riempi"), a.tonemap, vparams)
        lavori.append((seg, src, cache / f"{chiave}.mkv"))
    da_fare = [l for l in lavori if not l[2].exists()]
    paralleli = a.paralleli or max(1, (os.cpu_count() or 4) // (2 if a.modo == "anteprima" else 4))
    info(f"Versione {versione}, {a.modo} {W}x{H} @ {fps}: {len(lavori)} segmenti ({len(lavori) - len(da_fare)} già pronti).")
    with ThreadPoolExecutor(max_workers=paralleli) as ex:
        futuri = [ex.submit(render_segmento, seg, src, W, H, fps, vparams, piano.get("adattamento", "riempi"), a.tonemap, dest)
                  for seg, src, dest in da_fare]
        for i, f in enumerate(as_completed(futuri), 1):
            f.result()
            if i % 10 == 0 or i == len(futuri):
                info(f"  segmenti {i}/{len(futuri)}")

    lista = vdir / f".segmenti-{a.modo}.txt"
    lista.write_text("".join(f"file '{str(d).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for _, _, d in lavori),
                     encoding="utf-8")

    # 2. Audio: misura del volume (primo passaggio di loudnorm).
    m = misura_loudness(lista, a.loudness, a.picco)
    if m:
        ln = (f"loudnorm=I={a.loudness}:TP={a.picco}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    else:
        ln = f"loudnorm=I={a.loudness}:TP={a.picco}:LRA=11"
    af = f"{ln},aresample=48000"

    # 3. Unione finale.
    nome = f"{a.progetto}-{piano['formato']}-{versione}.mp4" if a.modo == "finale" else "anteprima.mp4"
    out = vdir / nome
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-map", "0:v", "-map", "0:a"]
    cwd = None
    if brucia:
        # Il filtro dei sottotitoli lavora con percorsi relativi: niente problemi con spazi o accenti.
        fonts = c["lavoro"] / "font"
        if not fonts.exists():
            shutil.copytree(SKILL_DIR / "assets" / "fonts", fonts)
        cwd = c["lavoro"]
        cmd += ["-vf", "subtitles=sottotitoli.ass:fontsdir=font", *(parametri_finali(a.encoder) if a.modo == "finale" else vparams)]
    else:
        cmd += ["-c:v", "copy"]
    cmd += [*COLORI_709, "-af", af, "-c:a", "aac", "-b:a", "320k" if a.modo == "finale" else "160k",
            "-movflags", "+faststart", str(out)]
    info("Unione e audio ...")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        errore("unione finale non riuscita:\n" + "\n".join(r.stderr.strip().splitlines()[-15:]))
    lista.unlink(missing_ok=True)

    for f in ("sottotitoli.srt", "sottotitoli.ass", "piano-montaggio.md"):
        if (c["lavoro"] / f).exists():
            shutil.copy2(c["lavoro"] / f, vdir / f)

    durata_attesa = sum(round((s["fine"] - s["inizio"]) * float(Fraction(fps))) for s in piano["segmenti"]) / float(Fraction(fps))
    info(f"Fatto: {out} (durata attesa {tc(durata_attesa)})")
    # 4. Controllo automatico del file.
    controllo = Path(__file__).resolve().parent / "controllo_finale.py"
    subprocess.run([sys.executable, str(controllo), str(out), "--larghezza", str(W), "--altezza", str(H), "--fps", fps,
                    "--durata", f"{durata_attesa:.3f}", "--loudness", str(a.loudness), "--picco", str(a.picco)])


if __name__ == "__main__":
    main()
