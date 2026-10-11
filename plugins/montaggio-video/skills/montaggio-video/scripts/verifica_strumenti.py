"""Controlla che ci siano gli strumenti necessari e, se richiesto, installa quelli Python.

uso:
  python3 verifica_strumenti.py                 # solo controllo, stampa cosa manca
  python3 verifica_strumenti.py --installa      # crea l'ambiente Python della skill e installa Whisper

L'ambiente Python (venv) sta in montaggio-video/.strumenti/venv, dentro la cartella di lavoro:
cancellando quella cartella si rimuove tutto. Gli altri script vanno eseguiti con quel Python.
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import cartella_lavoro  # noqa: E402

MAC = platform.system() == "Darwin"
APPLE_SILICON = MAC and platform.machine() == "arm64"
WINDOWS = platform.system() == "Windows"


def python_venv(root):
    venv = root / ".strumenti" / "venv"
    return venv / ("Scripts/python.exe" if WINDOWS else "bin/python"), venv


def ha_filtri(nomi):
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return {n: False for n in nomi}
    presenti = {line.split()[1] for line in out.splitlines() if len(line.split()) > 2}
    return {n: n in presenti for n in nomi}


def ha_encoder(nome):
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return False
    return any(len(l.split()) > 1 and l.split()[1] == nome for l in out.splitlines())


def modulo_in(py, modulo):
    if not Path(py).exists():
        return False
    r = subprocess.run([str(py), "-c", f"import {modulo}"], capture_output=True)
    return r.returncode == 0


def backend_whisper():
    return "mlx_whisper" if APPLE_SILICON else "faster_whisper"


def pacchetto_whisper():
    return "mlx-whisper" if APPLE_SILICON else "faster-whisper"


def controlla(root):
    py, venv = python_venv(root)
    filtri = ha_filtri(["zscale", "tonemap", "loudnorm", "silencedetect", "ebur128", "subtitles", "xfade", "libplacebo"])
    stato = {
        "sistema": f"{platform.system()} {platform.machine()}",
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "filtri": filtri,
        "prores": ha_encoder("prores_ks"),
        "videotoolbox": ha_encoder("hevc_videotoolbox"),
        "node": shutil.which("node") is not None,
        "venv": py.exists(),
        "python_venv": str(py),
        "numpy": modulo_in(py, "numpy"),
        "whisper": modulo_in(py, backend_whisper()),
        "backend_whisper": backend_whisper(),
    }
    return stato


def stampa(stato):
    ok = lambda b: "ok" if b else "MANCA"
    print(f"Sistema: {stato['sistema']}")
    print(f"- FFmpeg / ffprobe: {ok(stato['ffmpeg'] and stato['ffprobe'])}")
    for f in ["zscale", "tonemap", "loudnorm", "silencedetect", "ebur128", "subtitles", "xfade"]:
        print(f"  - filtro {f}: {ok(stato['filtri'][f])}")
    print(f"  - ProRes con trasparenza (prores_ks): {ok(stato['prores'])}")
    if MAC:
        print(f"  - codifica hardware del Mac (VideoToolbox): {ok(stato['videotoolbox'])}")
    print(f"- Node.js (grafiche): {ok(stato['node'])}")
    print(f"- Ambiente Python della skill: {ok(stato['venv'])}  ({stato['python_venv']})")
    print(f"  - numpy: {ok(stato['numpy'])}")
    print(f"  - Whisper ({stato['backend_whisper']}): {ok(stato['whisper'])}")

    consigli = []
    if not stato["ffmpeg"] or not stato["ffprobe"]:
        consigli.append("Installa FFmpeg: su Mac `brew install ffmpeg` (serve Homebrew: https://brew.sh).")
    elif not (stato["filtri"]["zscale"] and stato["filtri"]["tonemap"]):
        consigli.append("Il tuo FFmpeg non ha i filtri per convertire l'HDR (zscale/tonemap). Su Mac: `brew reinstall ffmpeg`.")
    if not stato["node"]:
        consigli.append("Installa Node.js (serve dalla tappa delle grafiche): su Mac `brew install node`.")
    if not (stato["venv"] and stato["numpy"] and stato["whisper"]):
        consigli.append("Manca l'ambiente Python con Whisper: rilancia questo script con --installa (chiedi prima all'utente).")
    if consigli:
        print("\nDa fare:")
        for c in consigli:
            print(f"- {c}")
    else:
        print("\nTutto pronto.")


def installa(root):
    py, venv = python_venv(root)
    if not py.exists():
        print(f"Creo l'ambiente Python in {venv} ...")
        venv.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, "-m", "venv", str(venv)])
        if r.returncode != 0:
            print("ERRORE: non riesco a creare l'ambiente Python. Su Mac installa Python con `brew install python`.", file=sys.stderr)
            sys.exit(1)
    # OpenCV 4.x: la 5 non ha più il rilevatore di volti classico (serve per la riinquadratura).
    pacchetti = ["numpy", "opencv-python-headless<5", pacchetto_whisper()]
    print(f"Installo: {', '.join(pacchetti)} (la prima volta può richiedere qualche minuto) ...")
    r = subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
    r = subprocess.run([str(py), "-m", "pip", "install", *pacchetti])
    if r.returncode != 0:
        print("ERRORE: installazione non riuscita. Controlla la connessione e riprova.", file=sys.stderr)
        sys.exit(1)
    print("Fatto. Il modello di Whisper (circa 1,5 GB) si scarica al primo utilizzo.")


def main():
    ap = argparse.ArgumentParser(description="Controllo strumenti della skill montaggio-video")
    ap.add_argument("--installa", action="store_true", help="crea l'ambiente Python e installa Whisper")
    ap.add_argument("--cartella", help="cartella di lavoro (predefinita: ./montaggio-video)")
    ap.add_argument("--json", action="store_true", help="stampa lo stato in JSON")
    a = ap.parse_args()
    root = cartella_lavoro(a.cartella)
    if a.installa:
        installa(root)
    stato = controlla(root)
    if a.json:
        print(json.dumps(stato, ensure_ascii=False, indent=2))
    else:
        stampa(stato)


if __name__ == "__main__":
    main()
