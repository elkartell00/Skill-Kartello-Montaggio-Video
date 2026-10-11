"""Grafiche: preparazione degli strumenti e render con Remotion o con il motore di animazione.

uso:
  python grafiche.py prepara                                   # prima volta (e dopo un aggiornamento della skill)
  python grafiche.py remotion <Tipo> <props.json> <uscita.mov> # Titolo, Scritta, Freccia, Emoji, Barra, Sottotitoli o su misura
  python grafiche.py immagine <Tipo> <props.json> <uscita.png> [--secondo 1.5]   # immagine ferma (miniature, schede)
  python grafiche.py anima build <cartella_dist> <clip.html ...>
  python grafiche.py anima fogli <dist/clip.html> <foglio.png> t1 t2 ...
  python grafiche.py anima render <dist/clip.html> <uscita.mp4|mov> <fps>

Gli strumenti stanno in montaggio-video/.strumenti/grafiche/ (progetto Remotion + Playwright).
Le proprietà di Remotion (props.json) contengono sempre larghezza, altezza, fps (numero) e durata (s),
più quelle della grafica (vedi riferimenti/grafiche.md). Le grafiche Remotion escono in ProRes 4444
con trasparenza, a piena risoluzione: si sovrappongono al video e vanno anche nel progetto DaVinci.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import SKILL_DIR, cartella_lavoro, errore, info  # noqa: E402

MAC = platform.system() == "Darwin"


def cartella_strumenti():
    return cartella_lavoro() / ".strumenti" / "grafiche"


def npm():
    exe = shutil.which("npm") or shutil.which("npm.cmd")
    if not exe:
        errore("manca Node.js (npm). Su Mac: brew install node")
    return exe


def prepara():
    dest = cartella_strumenti()
    src = SKILL_DIR / "grafiche-remotion"
    dest.mkdir(parents=True, exist_ok=True)
    # Sorgenti sempre aggiornati dalla skill; node_modules resta.
    for nome in ("package.json", "tsconfig.json"):
        shutil.copy2(src / nome, dest / nome)
    # Sorgenti della skill aggiornati; la cartella su-misura/ (grafiche create nei progetti) resta com'è.
    su_misura = dest / "src" / "su-misura"
    salvata = None
    if su_misura.exists():
        salvata = dest / ".su-misura-tmp"
        if salvata.exists():
            shutil.rmtree(salvata)
        shutil.move(str(su_misura), str(salvata))
    if (dest / "src").exists():
        shutil.rmtree(dest / "src")
    shutil.copytree(src / "src", dest / "src")
    if salvata:
        shutil.rmtree(dest / "src" / "su-misura")
        shutil.move(str(salvata), str(su_misura))
    # Gli stili imparati dagli esempi (montaggio-video/stili/) entrano nel progetto Remotion.
    from stili import sincronizza
    sincronizza(silenzioso=True)
    fonts = dest / "public" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for f in (SKILL_DIR / "assets" / "fonts").glob("*.ttf"):
        shutil.copy2(f, fonts / f.name)
    if not (dest / "node_modules" / "remotion").exists() or not (dest / "node_modules" / "playwright").exists():
        info("Installo Remotion e Playwright (circa 300 MB, qualche minuto la prima volta) ...")
        r = subprocess.run([npm(), "install", "--no-audit", "--no-fund"], cwd=dest)
        if r.returncode != 0:
            errore("installazione delle librerie per le grafiche non riuscita. Controlla la connessione e riprova.")
    if not os.environ.get("MONTAGGIO_CHROMIUM"):
        info("Scarico il browser per il motore di animazione (Chromium) ...")
        subprocess.run([shutil.which("npx") or "npx", "playwright", "install", "chromium"], cwd=dest)
    info(f"Grafiche pronte in {dest}")


def controlla():
    d = cartella_strumenti()
    if not (d / "node_modules" / "remotion").exists():
        errore("gli strumenti per le grafiche non sono installati. Esegui: grafiche.py prepara (chiedi prima all'utente).")
    return d


def remotion(tipo, props, uscita):
    d = controlla()
    props = Path(props).resolve()
    dati = json.loads(props.read_text(encoding="utf-8"))
    for k in ("larghezza", "altezza", "fps", "durata"):
        if k not in dati:
            errore(f"in {props.name} manca '{k}' (servono sempre larghezza, altezza, fps e durata).")
    uscita = Path(uscita).resolve()
    uscita.parent.mkdir(parents=True, exist_ok=True)
    trasparente = uscita.suffix.lower() == ".mov"
    cmd = [shutil.which("npx") or "npx", "remotion", "render", "src/index.ts", tipo, str(uscita), f"--props={props}"]
    if trasparente:
        cmd += ["--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png"]
    else:
        cmd += ["--codec=h264", "--crf=14"]
    # Remotion scarica da solo il suo browser al primo render; questa variabile serve solo
    # dove il download non è possibile (ambienti senza rete).
    if os.environ.get("MONTAGGIO_REMOTION_BROWSER"):
        cmd += [f"--browser-executable={os.environ['MONTAGGIO_REMOTION_BROWSER']}"]
    info(f"Render {tipo} -> {uscita.name} ...")
    r = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        errore(f"render di {tipo} non riuscito:\n" + "\n".join((r.stderr or r.stdout).strip().splitlines()[-12:]))
    info(f"Creata {uscita}")


def immagine(tipo, props, uscita, secondo=None):
    d = controlla()
    props = Path(props).resolve()
    dati = json.loads(props.read_text(encoding="utf-8"))
    uscita = Path(uscita).resolve()
    uscita.parent.mkdir(parents=True, exist_ok=True)
    fotogramma = int(round(float(secondo if secondo is not None else max(0.0, dati.get("durata", 1) - 0.1)) * float(dati.get("fps", 30))))
    cmd = [shutil.which("npx") or "npx", "remotion", "still", "src/index.ts", tipo, str(uscita), f"--props={props}", f"--frame={fotogramma}"]
    if os.environ.get("MONTAGGIO_REMOTION_BROWSER"):
        cmd += [f"--browser-executable={os.environ['MONTAGGIO_REMOTION_BROWSER']}"]
    r = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        errore(f"immagine {tipo} non riuscita:\n" + "\n".join((r.stderr or r.stdout).strip().splitlines()[-12:]))
    info(f"Creata {uscita}")


def anima(azione, args):
    d = controlla()
    motore = SKILL_DIR / "motore-animazioni"
    env = dict(os.environ, NODE_PATH=str(d / "node_modules"))
    if azione == "build":
        cmd = [sys.executable, str(motore / "build.py"), *args]
    elif azione == "fogli":
        cmd = [shutil.which("node") or "node", str(motore / "beats.js"), *args]
    elif azione == "render":
        cmd = [shutil.which("node") or "node", str(motore / "render.js"), *args]
    else:
        errore(f"azione sconosciuta: {azione} (build, fogli, render)")
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        errore(f"motore di animazione: '{azione}' non riuscito.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "prepara":
        prepara()
    elif cmd == "remotion" and len(args) == 3:
        remotion(*args)
    elif cmd == "immagine" and len(args) in (3, 5):
        sec = float(args[4]) if len(args) == 5 and args[3] == "--secondo" else None
        immagine(args[0], args[1], args[2], sec)
    elif cmd == "anima" and args:
        anima(args[0], args[1:])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
