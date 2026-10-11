"""Analisi dei video di riferimento (shorts, reels, video lunghi che piacciono all'utente).

uso:
  python video_riferimento.py --profilo rossi [--cartella-video percorso] [--soglia 0.3]

Analizza ogni video in profili/<profilo>/riferimenti/ (o in --cartella-video) e misura:
  durata, formato, fps; tagli (cambi di inquadratura) e durata media delle inquadrature; tagli al minuto
  nei primi 5 secondi e nel resto (l'aggancio di solito è più veloce); volume medio; quanto parlato o silenzio.
Crea per ogni video:
  <nome>-aggancio.jpg   i primi 3 secondi, 6 fotogrammi: com'è fatto l'aggancio, testi in apertura
  <nome>-foglio.jpg     16 fotogrammi distribuiti: stile dei sottotitoli, grafiche, zoom, inquadrature
e un riepilogo in profili/<profilo>/riferimenti/analisi/analisi.json.
Guarda le immagini e scrivi tu le regole nel file del formato giusto del profilo (ritmo, aggancio, stile
dei sottotitoli, grafiche, zoom, musica, effetti). Ispirarsi sì, copiare loghi, sigle o grafiche no.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (cartella_lavoro, errore, ffprobe, filtro_sdr, flusso_audio, flusso_video, fps_nominale,  # noqa: E402
                    info, info_hdr, scrivi_json)

ESTENSIONI = {".mov", ".mp4", ".m4v", ".mkv", ".webm"}


def tagli(video, soglia, sdr):
    vf = ",".join(x for x in ["scale=320:-2", sdr, f"select='gt(scene,{soglia})'", "showinfo"] if x)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vf", vf, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(m.group(1)) for m in re.finditer(r"pts_time:([\d.]+)", r.stderr)]


def volume(video):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    t = r.stderr[r.stderr.rfind("Summary:"):]
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", t)
    return float(m.group(1)) if m else None


def silenzio(video, durata):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0", "-af", "silencedetect=noise=-35dB:d=0.3",
                        "-f", "null", "-"], capture_output=True, text=True)
    tot = sum(float(m.group(1)) for m in re.finditer(r"silence_duration: ([\d.]+)", r.stderr))
    return round(tot / durata, 3) if durata else None


def main():
    ap = argparse.ArgumentParser(description="Analisi dei video di riferimento")
    ap.add_argument("--profilo", required=True)
    ap.add_argument("--cartella-video")
    ap.add_argument("--soglia", type=float, default=0.3, help="sensibilità al cambio di inquadratura (0.2-0.5)")
    a = ap.parse_args()
    prof = cartella_lavoro() / "profili" / a.profilo
    if not prof.exists():
        errore(f"il profilo '{a.profilo}' non esiste.")
    src = Path(a.cartella_video).expanduser() if a.cartella_video else prof / "riferimenti"
    video = sorted(p for p in src.rglob("*") if p.suffix.lower() in ESTENSIONI and "analisi" not in p.parts)
    if not video:
        errore(f"nessun video in {src}. Chiedi all'utente di metterci i video che gli piacciono.")
    out = prof / "riferimenti" / "analisi"
    out.mkdir(parents=True, exist_ok=True)
    risultati = []
    for v in video:
        p = ffprobe(v)
        vs, au = flusso_video(p), flusso_audio(p)
        if not vs:
            continue
        dur = float(p["format"].get("duration", 0) or 0)
        w, h = int(vs["width"]), int(vs["height"])
        for sd in vs.get("side_data_list", []) or []:
            if abs(int(sd.get("rotation", 0))) in (90, 270):
                w, h = h, w
        sdr = filtro_sdr(info_hdr(vs), "mobius")
        info(f"Analizzo {v.name} ...")
        ct = tagli(v, a.soglia, sdr)
        inquadrature = [b - a_ for a_, b in zip([0.0] + ct, ct + [dur]) if b - a_ > 0.05]
        primi = [t for t in ct if t < 5]
        nome = re.sub(r"[^\w-]+", "-", v.stem)[:40]
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-t", "3", "-i", str(v), "-vf",
                        ",".join(x for x in ["fps=2", "scale=320:-2", sdr, "tile=6x1:padding=3"] if x), "-frames:v", "1",
                        str(out / f"{nome}-aggancio.jpg")])
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(v), "-vf",
                        ",".join(x for x in [f"fps=1/{max(dur / 16, 0.3):.3f}", "scale=320:-2", sdr, "tile=4x4:padding=3"] if x),
                        "-frames:v", "1", str(out / f"{nome}-foglio.jpg")])
        r = {"file": str(v), "durata": round(dur, 2), "formato": f"{w}x{h}", "orientamento": "verticale" if h > w else "orizzontale",
             "fps": fps_nominale(vs), "tagli": len(ct),
             "inquadratura_media_s": round(sum(inquadrature) / len(inquadrature), 2) if inquadrature else None,
             "inquadratura_mediana_s": round(sorted(inquadrature)[len(inquadrature) // 2], 2) if inquadrature else None,
             "tagli_al_minuto": round(len(ct) / dur * 60, 1) if dur else None,
             "tagli_al_minuto_primi_5s": round(len(primi) / min(5, dur) * 60, 1) if dur else None,
             "volume_lufs": volume(v) if au else None, "quota_silenzio": silenzio(v, dur) if au else None,
             "aggancio": str(out / f"{nome}-aggancio.jpg"), "foglio": str(out / f"{nome}-foglio.jpg")}
        risultati.append(r)
        info(f"   {r['durata']} s {r['formato']}: {r['tagli']} tagli, inquadratura media {r['inquadratura_media_s']} s, "
             f"{r['tagli_al_minuto']} tagli/min ({r['tagli_al_minuto_primi_5s']} nei primi 5 s), volume {r['volume_lufs']} LUFS")
    scrivi_json(out / "analisi.json", {"profilo": a.profilo, "video": risultati})
    info(f"Analisi in {out}. Guarda i fogli e scrivi le regole nel profilo, poi: profili.py salva --nome {a.profilo} --messaggio \"regole dai video di riferimento\"")


if __name__ == "__main__":
    main()
