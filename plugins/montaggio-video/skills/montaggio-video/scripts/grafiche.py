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
from comune import SKILL_DIR, avviso, cartella_lavoro, errore, info  # noqa: E402

MAC = platform.system() == "Darwin"


def cartella_strumenti():
    return cartella_lavoro() / ".strumenti" / "grafiche"


def npx():
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx"


def browser_playwright():
    """Il Chrome Headless Shell scaricato da Playwright (il più recente), o None."""
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if base and base != "0":
        cache = Path(base)
    elif MAC:
        cache = Path.home() / "Library" / "Caches" / "ms-playwright"
    elif os.name == "nt":
        cache = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"
    else:
        cache = Path.home() / ".cache" / "ms-playwright"
    nome = "chrome-headless-shell.exe" if os.name == "nt" else "chrome-headless-shell"
    trovati = []
    for exe in cache.glob(f"chromium_headless_shell-*/chrome-headless-shell-*/{nome}"):
        rev = exe.parent.parent.name.rsplit("-", 1)[-1]
        trovati.append((int(rev) if rev.isdigit() else 0, exe))
    return max(trovati)[1] if trovati else None


def file_browser_remotion():
    # Scritto da `prepara` quando Remotion non riesce a scaricare il suo browser e usa quello di Playwright.
    return cartella_strumenti() / "browser-remotion.txt"


def opzioni_browser_remotion():
    scelto = os.environ.get("MONTAGGIO_REMOTION_BROWSER")
    f = file_browser_remotion()
    if not scelto and f.exists():
        scelto = f.read_text(encoding="utf-8").strip()
        if not Path(scelto).exists():
            scelto = None
    return [f"--browser-executable={scelto}"] if scelto else []


def prova_playwright(dest):
    """Avvia e chiude il browser del motore di animazione: True se funziona."""
    codice = ("const o = process.env.MONTAGGIO_CHROMIUM ? {executablePath: process.env.MONTAGGIO_CHROMIUM} : {};"
              "require('playwright').chromium.launch(o).then(b => b.close())"
              ".catch(e => { console.error(e.message.split('\\n')[0]); process.exit(1); });")
    r = subprocess.run([shutil.which("node") or "node", "-e", codice], cwd=dest, capture_output=True, text=True)
    if r.returncode != 0:
        avviso((r.stderr or r.stdout).strip()[-400:])
    return r.returncode == 0


def prova_remotion(dest, opzioni):
    """Crea un fotogramma di prova: True se Remotion funziona con quel browser."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        props, png = Path(tmp) / "props.json", Path(tmp) / "prova.png"
        props.write_text(json.dumps({"larghezza": 320, "altezza": 180, "fps": 30, "durata": 1, "testo": "Prova"}),
                         encoding="utf-8")
        r = subprocess.run([npx(), "remotion", "still", "src/index.ts", "Titolo", str(png), f"--props={props}",
                            "--frame=15", "--timeout=60000", *opzioni], cwd=dest, capture_output=True, text=True)
        return r.returncode == 0 and png.exists()


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
    problemi = []
    # Browser del motore di animazione. Playwright prova più server; un errore di rete passeggero
    # interrompe il download a metà (resta Chromium ma non il Headless Shell), quindi si riprova.
    if not os.environ.get("MONTAGGIO_CHROMIUM"):
        info("Scarico il browser per il motore di animazione (Chromium) ...")
        for _ in range(3):
            subprocess.run([npx(), "playwright", "install", "chromium"], cwd=dest)
            if prova_playwright(dest):
                break
            avviso("il browser del motore di animazione non è completo, riprovo ...")
        else:
            problemi.append("il browser del motore di animazione (Playwright) non si è scaricato")
    elif not prova_playwright(dest):
        problemi.append("il browser indicato in MONTAGGIO_CHROMIUM non si avvia")
    # Browser di Remotion: lo scarica da remotion.media e si prova con un fotogramma vero. Se non si scarica
    # (rete, filtro DNS) o non funziona su questo computer (sul Mac la sua versione speciale può restare ferma
    # su "Waiting for root component to load"), Remotion usa il Headless Shell di Playwright, che va bene uguale.
    f = file_browser_remotion()
    if f.exists():
        f.unlink()
    if not os.environ.get("MONTAGGIO_REMOTION_BROWSER"):
        info("Preparo e provo il browser di Remotion ...")
        subprocess.run([npx(), "remotion", "browser", "ensure"], cwd=dest, capture_output=True, text=True)
        if not prova_remotion(dest, []):
            alternativo = browser_playwright()
            if alternativo and prova_remotion(dest, [f"--browser-executable={alternativo}"]):
                f.write_text(str(alternativo), encoding="utf-8")
                info(f"Il browser di Remotion non funziona qui: Remotion userà quello di Playwright ({alternativo}).")
            else:
                problemi.append("Remotion non riesce a creare le grafiche, né con il suo browser né con quello di Playwright")
    elif not prova_remotion(dest, opzioni_browser_remotion()):
        problemi.append("il browser indicato in MONTAGGIO_REMOTION_BROWSER non funziona con Remotion")
    if problemi:
        errore("grafiche non pronte: " + "; ".join(problemi) + ". Controlla la connessione e rilancia "
               "`grafiche.py prepara` (riprende da dove si è fermato).")
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
    cmd = [npx(), "remotion", "render", "src/index.ts", tipo, str(uscita), f"--props={props}"]
    if trasparente:
        cmd += ["--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png"]
    else:
        cmd += ["--codec=h264", "--crf=14"]
    # Browser: quello di Remotion, o quello scelto con MONTAGGIO_REMOTION_BROWSER, o quello di Playwright
    # se `prepara` ha visto che il browser di Remotion qui non funziona.
    cmd += opzioni_browser_remotion()
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
    cmd = [npx(), "remotion", "still", "src/index.ts", tipo, str(uscita), f"--props={props}", f"--frame={fotogramma}"]
    cmd += opzioni_browser_remotion()
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
