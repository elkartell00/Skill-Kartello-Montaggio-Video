"""Controlla che ci siano gli strumenti necessari e, se richiesto, installa quelli Python.

uso:
  python3 verifica_strumenti.py                 # solo controllo, stampa cosa manca
  python3 verifica_strumenti.py --installa      # crea l'ambiente Python della skill e installa Whisper

L'ambiente Python (venv) sta in montaggio-video/.strumenti/venv, dentro la cartella di lavoro:
cancellando quella cartella si rimuove tutto. Gli altri script vanno eseguiti con quel Python.
"""
import argparse
import json
import os
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


# Whisper, OpenCV e PyTorch vogliono Python 3.10+; le versioni appena uscite spesso non hanno ancora i
# pacchetti pronti, quindi si preferiscono quelle collaudate. Sul Mac `python3` è spesso il 3.9 di Xcode.
PYTHON_PREFERITI = [(3, 12), (3, 13), (3, 11), (3, 10)]
PYTHON_MINIMO = (3, 10)


def python_venv(root):
    venv = root / ".strumenti" / "venv"
    return venv / ("Scripts/python.exe" if WINDOWS else "bin/python"), venv


def versione_python(exe):
    try:
        out = subprocess.run([str(exe), "-c", "import sys; print(*sys.version_info[:2])"],
                             capture_output=True, text=True, timeout=30).stdout.split()
        return tuple(int(x) for x in out[:2]) if len(out) >= 2 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def scegli_python():
    """Il Python con cui creare l'ambiente della skill, o None se non ce n'è uno adatto."""
    cartelle = ["/opt/homebrew/bin", "/usr/local/bin"] if MAC else []
    for v in PYTHON_PREFERITI:
        nome = f"python{v[0]}.{v[1]}"
        for exe in [shutil.which(nome)] + [os.path.join(c, nome) for c in cartelle]:
            if exe and os.path.isfile(exe) and versione_python(exe) == v:
                return exe
    if sys.version_info[:2] >= PYTHON_MINIMO:
        return sys.executable
    return None


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
        "ffmpeg_percorso": shutil.which("ffmpeg"),
        "venv": py.exists(),
        "python_venv": str(py),
        "versione_venv": versione_python(py) if py.exists() else None,
        "numpy": modulo_in(py, "numpy"),
        "whisper": modulo_in(py, backend_whisper()),
        "opencv": modulo_in(py, "cv2"),
        "git": shutil.which("git") is not None,
        "grafiche": (root / ".strumenti" / "grafiche" / "node_modules" / "remotion").exists(),
        "separazione": modulo_in(py, "transformers") and modulo_in(py, "torchvision"),
        "backend_whisper": backend_whisper(),
    }
    return stato


def stampa(stato):
    ok = lambda b: "ok" if b else "MANCA"
    print(f"Sistema: {stato['sistema']}")
    print(f"- FFmpeg / ffprobe: {ok(stato['ffmpeg'] and stato['ffprobe'])}  ({stato['ffmpeg_percorso'] or '-'})")
    for f in ["zscale", "tonemap", "loudnorm", "silencedetect", "ebur128", "subtitles", "xfade"]:
        print(f"  - filtro {f}: {ok(stato['filtri'][f])}")
    print(f"  - ProRes con trasparenza (prores_ks): {ok(stato['prores'])}")
    if MAC:
        print(f"  - codifica hardware del Mac (VideoToolbox): {ok(stato['videotoolbox'])}")
    print(f"- Node.js (grafiche): {ok(stato['node'])}")
    v = stato["versione_venv"]
    print(f"- Ambiente Python della skill: {ok(stato['venv'])}  ({stato['python_venv']}"
          + (f", Python {v[0]}.{v[1]})" if v else ")"))
    print(f"  - numpy: {ok(stato['numpy'])}")
    print(f"  - Whisper ({stato['backend_whisper']}): {ok(stato['whisper'])}")
    print(f"  - OpenCV (riinquadratura): {ok(stato['opencv'])}")
    print(f"- git (storico dei profili): {ok(stato['git'])}")
    print(f"- Grafiche (Remotion e motore di animazione): {ok(stato['grafiche'])}  -> grafiche.py prepara")
    print(f"- Separazione del soggetto (facoltativa, ~2 GB): {ok(stato['separazione'])}  -> separa_soggetto.py prepara")

    consigli = []
    if not stato["ffmpeg"] or not stato["ffprobe"]:
        consigli.append("Installa FFmpeg: su Mac `brew install ffmpeg-full` (serve Homebrew: https://brew.sh).")
    else:
        mancano = [f for f in ("zscale", "tonemap", "subtitles") if not stato["filtri"][f]]
        if mancano:
            consigli.append(f"Il tuo FFmpeg non ha {', '.join(mancano)} (servono per l'HDR e i sottotitoli bruciati). "
                            "Su Mac: `brew install ffmpeg-full`; gli script lo usano da soli, anche se resta "
                            "installato il normale ffmpeg.")
    if not stato["node"]:
        consigli.append("Installa Node.js (serve dalla tappa delle grafiche): su Mac `brew install node`.")
    if v and v < PYTHON_MINIMO:
        consigli.append(f"L'ambiente Python usa Python {v[0]}.{v[1]}, troppo vecchio: rilancia con --installa "
                        "per ricrearlo (su Mac prima `brew install python@3.12`).")
    elif not (stato["venv"] and stato["numpy"] and stato["whisper"] and stato["opencv"]):
        consigli.append("Manca l'ambiente Python con Whisper: rilancia questo script con --installa (chiedi prima all'utente).")
    if consigli:
        print("\nDa fare:")
        for c in consigli:
            print(f"- {c}")
    else:
        print("\nTutto pronto.")


def installa(root):
    py, venv = python_venv(root)
    if py.exists():
        v = versione_python(py)
        if v and v < PYTHON_MINIMO:
            print(f"L'ambiente Python esistente usa Python {v[0]}.{v[1]}, troppo vecchio: lo ricreo.")
            shutil.rmtree(venv)
    if not py.exists():
        base = scegli_python()
        if not base:
            print("ERRORE: serve Python 3.10 o più recente (consigliato 3.12). Su Mac: `brew install python@3.12`, "
                  "poi rilancia.", file=sys.stderr)
            sys.exit(1)
        print(f"Creo l'ambiente Python in {venv} con {base} ...")
        venv.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([base, "-m", "venv", str(venv)])
        if r.returncode != 0:
            print("ERRORE: non riesco a creare l'ambiente Python. Su Mac installa Python con `brew install python@3.12`.", file=sys.stderr)
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
