"""Trova i battiti di una musica, per tagliare o far entrare grafiche e B-roll a tempo.

uso:
  python battiti.py musica.mp3 [--da 0] [--a 60] [--json battiti.json]

Stampa il tempo (BPM) e l'elenco dei battiti in secondi, con i battiti forti (inizio battuta, ogni 4).
Metodo: inviluppo degli attacchi (flusso spettrale), tempo per autocorrelazione tra 60 e 180 BPM,
fase scelta allineando la griglia agli attacchi più forti. Serve numpy.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import errore, info  # noqa: E402

SR, HOP, N = 22050, 512, 2048


def main():
    ap = argparse.ArgumentParser(description="Battiti di una musica")
    ap.add_argument("file")
    ap.add_argument("--da", type=float, default=0.0)
    ap.add_argument("--a", type=float, default=0.0, help="fine dell'analisi in secondi (0 = tutto)")
    ap.add_argument("--json", help="salva il risultato in questo file")
    a = ap.parse_args()
    try:
        import numpy as np
    except ImportError:
        errore("serve numpy: usa il Python della skill (montaggio-video/.strumenti/venv).")

    cmd = ["ffmpeg", "-v", "error", "-ss", str(a.da), "-i", a.file]
    if a.a:
        cmd += ["-t", str(a.a - a.da)]
    cmd += ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    if len(x) < SR * 4:
        errore("la musica è troppo corta per trovare il tempo (servono almeno 4 secondi).")
    fin = np.hanning(N).astype(np.float32)
    nfr = 1 + (len(x) - N) // HOP
    frames = np.lib.stride_tricks.as_strided(x, shape=(nfr, N), strides=(x.strides[0] * HOP, x.strides[0]))
    spec = np.log1p(np.abs(np.fft.rfft(frames * fin, axis=1)))
    flux = np.maximum(0, np.diff(spec, axis=0)).sum(axis=1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fr = SR / HOP
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    lmin, lmax = int(fr * 60 / 180), int(fr * 60 / 60)
    # Preferenza leggera per tempi attorno ai 120 BPM (riduce gli errori di raddoppio/dimezzamento).
    lags = np.arange(lmin, lmax + 1)
    peso = np.exp(-0.5 * (np.log2((60 * fr / lags) / 120) / 0.9) ** 2)
    li = int(lags[np.argmax(ac[lmin:lmax + 1] * peso)])
    # Picco affinato con un'interpolazione parabolica: il periodo non è un numero intero di fotogrammi.
    y0, y1, y2 = ac[li - 1], ac[li], ac[li + 1]
    lag = float(li) + 0.5 * float(y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
    # Il periodo esatto si ottiene meglio dai multipli lontani (meno errore relativo).
    k = max(1, int(len(flux) / lag) // 2)
    lo, hi = int(k * (lag - 1)), min(len(ac) - 2, int(k * (lag + 1)) + 1)
    lk = lo + int(np.argmax(ac[lo:hi + 1])) if hi > lo else int(round(lag * k))
    if 0 < lk and lk + 1 < len(ac):
        y0, y1, y2 = ac[lk - 1], ac[lk], ac[lk + 1]
        lag = float((lk + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)) / k)
    bpm = 60 * fr / lag
    pos = lambda f0, j: int(round(f0 + j * lag))
    nb = int((len(flux) - 1) / lag)
    fasi = [sum(flux[pos(f0, j)] for j in range(nb) if pos(f0, j) < len(flux)) for f0 in range(int(lag))]
    fase = int(np.argmax(fasi))
    battiti = [round(a.da + (fase + j * lag) / fr, 3) for j in range(nb + 1) if fase + j * lag < len(flux)]
    # Battito forte: tra le 4 posizioni possibili, quella con gli attacchi più forti.
    forza = [sum(flux[min(len(flux) - 1, pos(fase, j))] for j in range(o, len(battiti), 4)) for o in range(4)]
    o = int(np.argmax(forza))
    forti = battiti[o::4]
    res = {"bpm": round(float(bpm), 1), "battiti": battiti, "forti": forti}
    info(f"Tempo: {res['bpm']} BPM, {len(battiti)} battiti (forti ogni 4: primo a {forti[0] if forti else '-'} s)")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    else:
        print(json.dumps(res))


if __name__ == "__main__":
    main()
