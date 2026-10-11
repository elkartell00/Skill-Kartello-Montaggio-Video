"""Controllo automatico di un video esportato: risoluzione, fps, durata, sincronia audio/video, volume.

uso:
  python controllo_finale.py video.mp4 [--larghezza 3840 --altezza 2160 --fps 30000/1001 --durata 612.4
                                        --loudness -14 --picco -1.5]

Stampa un riepilogo in italiano, salva controllo.json accanto al video ed esce con codice 1 se
qualcosa non va.
"""
import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import ffprobe, flusso_audio, flusso_video, scrivi_json, tc  # noqa: E402


def loudness(video):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    testo = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", testo)
    p = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", testo)
    return (float(i.group(1)) if i else None, float(p.group(1)) if p and p.group(1) != "-inf" else None)


def main():
    ap = argparse.ArgumentParser(description="Controllo finale del video")
    ap.add_argument("video")
    ap.add_argument("--larghezza", type=int)
    ap.add_argument("--altezza", type=int)
    ap.add_argument("--fps")
    ap.add_argument("--durata", type=float, help="durata attesa in secondi")
    ap.add_argument("--loudness", type=float, default=-14.0)
    ap.add_argument("--picco", type=float, default=-1.5)
    a = ap.parse_args()

    p = ffprobe(a.video)
    v, au = flusso_video(p), flusso_audio(p)
    esiti = []

    def esito(nome, ok, dettaglio):
        esiti.append({"controllo": nome, "ok": bool(ok), "dettaglio": dettaglio})

    if v is None:
        esito("video", False, "nessuna traccia video")
    else:
        w, h = int(v["width"]), int(v["height"])
        if a.larghezza and a.altezza:
            esito("risoluzione", (w, h) == (a.larghezza, a.altezza), f"{w}x{h} (attesa {a.larghezza}x{a.altezza})")
        if a.fps:
            reale = Fraction(v.get("avg_frame_rate", "0/1"))
            esito("fotogrammi al secondo", abs(float(reale) - float(Fraction(a.fps))) < 0.01, f"{float(reale):.3f} (attesi {float(Fraction(a.fps)):.3f})")
        esito("colori SDR Rec.709", v.get("color_transfer") in (None, "bt709") and v.get("color_primaries") in (None, "bt709"),
              f"transfer {v.get('color_transfer')}, primari {v.get('color_primaries')}")
    dur = float(p["format"].get("duration", 0))
    if a.durata:
        esito("durata", abs(dur - a.durata) < 0.25, f"{tc(dur)} (attesa {tc(a.durata)})")
    if au is None:
        esito("audio", False, "nessuna traccia audio")
    else:
        dv = float(v.get("duration", dur)) if v else dur
        da = float(au.get("duration", dur))
        esito("sincronia audio/video", abs(dv - da) < 0.1, f"video {dv:.3f} s, audio {da:.3f} s (differenza {abs(dv - da) * 1000:.0f} ms)")
        i, pk = loudness(a.video)
        if i is not None:
            esito("volume medio", abs(i - a.loudness) <= 1.0, f"{i:.1f} LUFS (obiettivo {a.loudness:.0f})")
        if pk is not None:
            esito("picchi", pk <= a.picco + 0.6, f"{pk:.1f} dBFS (massimo {a.picco})")

    tutto_ok = all(e["ok"] for e in esiti)
    print(f"\nControllo di {Path(a.video).name}: {'tutto a posto' if tutto_ok else 'CI SONO PROBLEMI'}")
    for e in esiti:
        print(f"  {'ok ' if e['ok'] else 'NO '} {e['controllo']}: {e['dettaglio']}")
    scrivi_json(Path(a.video).with_suffix(".controllo.json"), {"file": str(a.video), "ok": tutto_ok, "controlli": esiti})
    sys.exit(0 if tutto_ok else 1)


if __name__ == "__main__":
    main()
