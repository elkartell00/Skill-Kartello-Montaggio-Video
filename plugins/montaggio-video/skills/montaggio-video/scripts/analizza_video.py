"""Analisi delle riprese di un progetto: dati tecnici, HDR, foglio di anteprime, layout, silenzi, audio per Whisper.

uso:
  python analizza_video.py --progetto nome [--soglia-silenzio -35] [--silenzio-min 0.35]

Scrive in .lavoro/<progetto>/:
  analisi.json             dati di ogni ripresa (risoluzione, fps, HDR, durata, silenzi, sezioni)
  contatto-NN.jpg          foglio di 16 fotogrammi per guardare cosa si vede (già convertito in SDR)
  hdr-confronto-NN.jpg     solo per riprese HDR: lo stesso fotogramma con i 3 operatori di conversione
  audio/NN.wav             audio mono 16 kHz per la trascrizione

Il riconoscimento delle sezioni con riquadro (picture-in-picture) viene dalla skill motion-broll.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (DECODIFICA_HW, OPERATORI_TONEMAP, avviso, cartelle_progetto, errore, esegui, ffprobe,  # noqa: E402
                    filtro_sdr, flusso_audio, flusso_video, fps_nominale, impronta_file, info,
                    info_hdr, is_vfr, leggi_json, scrivi_json, tc)


def silenzi(video, soglia_db, durata_min):
    """Intervalli di silenzio dell'audio (silencedetect di FFmpeg)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0", "-af",
                        f"silencedetect=noise={soglia_db}dB:d={durata_min}", "-f", "null", "-"],
                       capture_output=True, text=True)
    out, inizio = [], None
    for line in r.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            inizio = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and inizio is not None:
            out.append([round(inizio, 3), round(float(m.group(1)), 3)])
            inizio = None
    return out


def sezioni_layout(video, sdr, w, h):
    """Sezioni a schermo pieno o con riquadro (PiP) e spazio vuoto per i pannelli. Da motion-broll."""
    try:
        import numpy as np
    except ImportError:
        avviso("numpy non disponibile: salto il riconoscimento del layout.")
        return []
    vf = ",".join(x for x in ["fps=4,scale=96:54", sdr, "format=gray"] if x)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", *DECODIFICA_HW, "-i", str(video), "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    if not raw:
        return []
    fr = np.frombuffer(raw, np.uint8)
    fr = fr[: len(fr) // (54 * 96) * (54 * 96)].reshape(-1, 54, 96)
    sections, prev, start = [], None, 0
    for i, f in enumerate(fr):
        dark = f[:, 60:].mean() < 8 or f[:, :36].mean() < 8
        if dark != prev:
            if prev is not None:
                sections.append({"da": start / 4, "a": i / 4, "layout": "pip" if prev else "pieno"})
            start, prev = i, dark
    sections.append({"da": start / 4, "a": len(fr) / 4, "layout": "pip" if prev else "pieno"})
    for s in sections:
        if s["layout"] != "pip":
            continue
        boxes = []
        for i in range(int(s["da"] * 4), int(s["a"] * 4)):
            f = fr[i]
            cols, rows = np.where(f.max(0) > 20)[0], np.where(f.max(1) > 20)[0]
            if len(cols) == 0:
                continue
            boxes.append((i / 4, [int(cols.min() * w / 96), int(rows.min() * h / 54),
                                  int((cols.max() + 1) * w / 96), int((rows.max() + 1) * h / 54)]))
        if not boxes:
            continue
        s["riquadro_soggetto"] = [min(b[1][0] for b in boxes), min(b[1][1] for b in boxes),
                                  max(b[1][2] for b in boxes), max(b[1][3] for b in boxes)]
        cambi, ref = [], boxes[0][1]
        for t, b in boxes:
            if max(abs(b[k] - ref[k]) for k in range(4)) > 2 * w / 96:
                cambi.append({"a": t, "riquadro": b})
                ref = b
        s["cambi_riquadro"] = cambi
        if cambi:
            avviso(f"il riquadro del soggetto cambia dimensione o posizione nella sezione {tc(s['da'])}-{tc(s['a'])}: "
                   "i pannelli vanno tenuti lontani dal riquadro più grande, oppure chiedi se il cambio è voluto.")
    return sections


def main():
    ap = argparse.ArgumentParser(description="Analisi delle riprese")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--soglia-silenzio", type=float, default=-35.0, help="dB sotto cui l'audio è silenzio")
    ap.add_argument("--silenzio-min", type=float, default=0.35, help="durata minima di un silenzio (s)")
    ap.add_argument("--senza-layout", action="store_true", help="salta il riconoscimento delle sezioni PiP")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    prog = leggi_json(c["progetto"])
    (c["lavoro"] / "audio").mkdir(parents=True, exist_ok=True)
    analisi = {"progetto": a.progetto, "sorgenti": []}

    for s in prog["sorgenti"]:
        v = Path(s["file"])
        if not v.exists():
            errore(f"la ripresa {v} non esiste più. È stata spostata?")
        if impronta_file(v) != s["impronta"]:
            avviso(f"la ripresa {v.name} risulta cambiata da quando è stata registrata nel progetto.")
        n = f"{s['indice']:02d}"
        info(f"[{n}] Analizzo {v.name} ...")
        p = ffprobe(v)
        vs, aud = flusso_video(p), flusso_audio(p)
        if vs is None:
            errore(f"{v.name} non contiene video.")
        w, h = int(vs["width"]), int(vs["height"])
        rot = 0
        for sd in vs.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        if abs(rot) in (90, 270):
            w, h = h, w
        hdr = info_hdr(vs)
        dur = float(p["format"].get("duration", vs.get("duration", 0)))
        sdr = filtro_sdr(hdr, "mobius")

        # Foglio di anteprime: 16 fotogrammi distribuiti sulla durata.
        passo = max(0.5, dur / 16)
        vf = ",".join(x for x in [f"fps=1/{passo:.3f}", "scale=480:-2", sdr, "tile=4x4:padding=4"] if x)
        esegui(["ffmpeg", "-loglevel", "error", "-y", *DECODIFICA_HW, "-i", str(v), "-vf", vf, "-frames:v", "1",
                str(c["lavoro"] / f"contatto-{n}.jpg")], descrizione="foglio di anteprime")

        # Confronto degli operatori HDR sullo stesso fotogramma: l'utente sceglie quello che preferisce.
        if hdr["hdr"]:
            t = dur / 3
            files = []
            for op in OPERATORI_TONEMAP:
                out = c["lavoro"] / f"hdr-{op}-{n}.jpg"
                esegui(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(v), "-vf",
                        f"scale=960:-2,{filtro_sdr(hdr, op)}", "-frames:v", "1", str(out)], descrizione=f"anteprima HDR {op}")
                files.append(out)
            cmd = ["ffmpeg", "-loglevel", "error", "-y"]
            for f in files:
                cmd += ["-i", str(f)]
            cmd += ["-filter_complex", f"hstack=inputs={len(files)}", str(c["lavoro"] / f"hdr-confronto-{n}.jpg")]
            esegui(cmd, descrizione="confronto HDR")

        sil = silenzi(v, a.soglia_silenzio, a.silenzio_min) if aud else []
        sezioni = [] if a.senza_layout else sezioni_layout(v, sdr, w, h)

        wav = c["lavoro"] / "audio" / f"{n}.wav"
        if aud:
            esegui(["ffmpeg", "-loglevel", "error", "-y", "-i", str(v), "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", str(wav)], descrizione="estrazione audio")

        voce = {
            "indice": s["indice"], "file": str(v), "durata": round(dur, 3),
            "larghezza": w, "altezza": h, "orientamento": "verticale" if h > w else "orizzontale",
            "rotazione": rot, "codec": vs.get("codec_name"), "pix_fmt": vs.get("pix_fmt"),
            "fps": fps_nominale(vs), "fps_misurato": vs.get("avg_frame_rate"), "vfr": is_vfr(vs),
            "hdr": hdr, "audio": bool(aud),
            "audio_canali": int(aud.get("channels", 0)) if aud else 0,
            "audio_wav": str(wav) if aud else None,
            "silenzi": sil, "sezioni": sezioni,
            "contatto": str(c["lavoro"] / f"contatto-{n}.jpg"),
            "hdr_confronto": str(c["lavoro"] / f"hdr-confronto-{n}.jpg") if hdr["hdr"] else None,
        }
        analisi["sorgenti"].append(voce)
        info(f"     {w}x{h} {voce['orientamento']}, {voce['fps']} fps{' (VFR)' if voce['vfr'] else ''}, "
             f"{tc(dur)}, {hdr['tipo'] or 'SDR'}, {len(sil)} silenzi")

    scrivi_json(c["lavoro"] / "analisi.json", analisi)
    if any(s["hdr"]["hdr"] for s in analisi["sorgenti"]):
        info("Riprese HDR: guarda hdr-confronto-NN.jpg (da sinistra: " + ", ".join(OPERATORI_TONEMAP) +
             ") e chiedi all'utente quale conversione preferisce, se il profilo non lo dice già.")
    info(f"Analisi salvata in {c['lavoro'] / 'analisi.json'}")


if __name__ == "__main__":
    main()
