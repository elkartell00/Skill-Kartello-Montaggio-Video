"""Controllo di sicurezza di una skill da integrare (cartella o file .zip).

uso:
  python controllo_sicurezza.py percorso/skill.zip|cartella [--json rapporto.json]

Non esegue niente: legge i file di testo e segnala i punti da guardare, per gravità:
  ALTA   invio di dati all'esterno, lettura di chiavi/password/file di sistema, download ed esecuzione di
         codice, istruzioni che spingono a ignorare l'utente o a fare cose di nascosto
  MEDIA  comandi di shell costruiti con testo variabile, cancellazioni, richieste di rete, installazioni
  BASSA  risorse caricate da internet (font, immagini), link pubblicitari, cose da tradurre o adattare
Elenca anche i file binari (da controllare a parte) e gli eseguibili. Ogni segnalazione va comunque letta
nel contesto: molte sono normali (es. pip install di un pacchetto noto), ma vanno capite prima di integrare.
"""
import argparse
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

REGOLE = [
    ("ALTA", "invio di dati all'esterno", r"\b(fetch|axios|XMLHttpRequest|sendBeacon|WebSocket|requests\.(post|put)|urllib\.request\.urlopen|http\.request|curl\s+-[dXF]|curl\s.*--data|nc\s+-|scp\s|rsync\s)"),
    ("ALTA", "lettura di chiavi, password o file di sistema", r"(\.ssh|id_rsa|\.aws|(?<!process)\.env\b|keychain|security find-|/etc/passwd|credentials|api[_-]?key|secret|token|password|\.netrc|\.npmrc|\.pypirc|Cookies|Login Data)"),
    ("ALTA", "download ed esecuzione di codice", r"(curl[^|\n]*\|\s*(ba|z)?sh|wget[^|\n]*\|\s*(ba|z)?sh|iex\s*\(|Invoke-Expression|eval\s*\(\s*(atob|base64|fetch)|exec\(\s*(base64|urlopen)|python\s+-c\s+.*base64|powershell\s+-enc)"),
    ("ALTA", "istruzioni che manipolano Claude", r"(?i)(ignore (all|previous|the user)|ignora (le )?istruzioni|non dire all'utente|do not tell the user|without (asking|telling)|senza chiedere|segretamente|secretly|disable (safety|permission)|--dangerously|bypassPermissions|skip-permissions)"),
    ("MEDIA", "comandi di shell con testo variabile", r"(os\.system\(|shell\s*=\s*True|execSync\(`|exec\(`|subprocess\.\w+\(\s*f[\"']|child_process.*exec\()"),
    ("MEDIA", "cancellazioni", r"(rm\s+-rf|shutil\.rmtree|fs\.rm(Sync)?\(|unlink\(|del\s+/[sq])"),
    ("MEDIA", "installazioni di pacchetti o programmi", r"(pip3?\s+install|npm\s+(i|install)\b|npx\s+\S+|brew\s+install|apt(-get)?\s+install|playwright install)"),
    ("MEDIA", "richieste di rete", r"(https?://(?!localhost|127\.0\.0\.1)[^\s\"'<>)]+)"),
    ("BASSA", "risorse caricate da internet", r"(fonts\.googleapis|fonts\.gstatic|cdn\.|unpkg\.com|jsdelivr)"),
    ("BASSA", "pubblicità o promozione", r"(?i)(skool\.com|patreon|join my|community|newsletter|affiliate|sponsor)"),
]
TESTO = {".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".json",
         ".html", ".htm", ".css", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".xml", ".svg", ""}


def apri(percorso):
    p = Path(percorso).expanduser()
    if p.suffix.lower() == ".zip":
        d = Path(tempfile.mkdtemp(prefix="skill-da-controllare-"))
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.startswith("/") or ".." in Path(n).parts:
                    print(f"ALTA  lo zip contiene un percorso pericoloso: {n} (non estratto)")
                    continue
                z.extract(n, d)
        return d
    if not p.is_dir():
        print(f"ERRORE: {p} non è né una cartella né uno zip", file=sys.stderr)
        sys.exit(1)
    return p


def main():
    ap = argparse.ArgumentParser(description="Controllo di sicurezza di una skill")
    ap.add_argument("percorso")
    ap.add_argument("--json")
    a = ap.parse_args()
    radice = apri(a.percorso)
    trovati, binari, link = [], [], []
    for f in sorted(radice.rglob("*")):
        if f.is_symlink():
            trovati.append({"gravita": "ALTA", "tipo": "collegamento simbolico", "file": str(f.relative_to(radice)), "riga": 0, "testo": str(f.readlink())})
            continue
        if not f.is_file():
            continue
        rel = str(f.relative_to(radice))
        if f.suffix.lower() not in TESTO or f.stat().st_size > 2_000_000:
            binari.append(f"{rel} ({f.stat().st_size // 1024} KB)")
            continue
        try:
            righe = f.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            binari.append(f"{rel} (non testo)")
            continue
        for i, r in enumerate(righe, 1):
            for grav, tipo, rx in REGOLE:
                m = re.search(rx, r)
                if m:
                    trovati.append({"gravita": grav, "tipo": tipo, "file": rel, "riga": i, "testo": r.strip()[:160]})
    ordine = {"ALTA": 0, "MEDIA": 1, "BASSA": 2}
    trovati.sort(key=lambda x: (ordine[x["gravita"]], x["file"], x["riga"]))
    print(f"Controllo di {a.percorso}: {len(trovati)} punti da guardare, {len(binari)} file non di testo.\n")
    for t in trovati:
        print(f"{t['gravita']:5} {t['tipo']}: {t['file']}:{t['riga']}  {t['testo']}")
    if binari:
        print("\nFile non di testo (controlla cosa sono, non vanno eseguiti):")
        for b in binari:
            print(f"  {b}")
    if a.json:
        Path(a.json).write_text(json.dumps({"punti": trovati, "binari": binari, "cartella": str(radice)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nFile estratti in: {radice}")


if __name__ == "__main__":
    main()
