"""Gestione dei profili di stile: elenco, creazione, copia, rinomina, eliminazione, storico e annullamento.

uso:
  python profili.py elenca
  python profili.py crea --nome rossi [--da base]
  python profili.py copia --da rossi --a rossi-reels
  python profili.py rinomina --da rossi --a cliente-rossi
  python profili.py elimina --nome rossi                 # va nel cestino (profili/.cestino), recuperabile
  python profili.py salva --nome rossi --messaggio "sottotitoli più piccoli negli shorts"
  python profili.py storico --nome rossi
  python profili.py annulla --nome rossi [--modifica <id>] # annulla l'ultima modifica (o quella indicata)

I profili stanno in montaggio-video/profili/<nome>/: profilo.md, un file per formato, diario-revisioni.md,
brand/ (logo, materiali del brand), riferimenti/ (video di riferimento e loro analisi).
Ogni modifica si salva con data e descrizione (`salva`): con git se c'è (cartella profili/ come
repository), altrimenti con copie datate in profili/.storico/. Così ogni cambio si può annullare.
Il profilo "base" non si modifica: per cambiarlo, crea un profilo nuovo partendo da lui.
"""
import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import SKILL_DIR, cartella_lavoro, errore, info  # noqa: E402

FORMATI = ["video-lungo", "shorts-dal-lungo", "shorts-indipendenti", "reels"]


def radice():
    r = cartella_lavoro() / "profili"
    r.mkdir(parents=True, exist_ok=True)
    if not (r / "base").exists():
        shutil.copytree(SKILL_DIR / "profili" / "base", r / "base")
    return r


def nome_valido(n):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", n or ""):
        errore(f"nome di profilo non valido: '{n}'. Usa minuscole, numeri e trattini (es. cliente-rossi).")
    return n


def git_ok(r):
    if shutil.which("git") is None:
        return False
    if not (r / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=r)
        subprocess.run(["git", "config", "user.name", "montaggio-video"], cwd=r)
        subprocess.run(["git", "config", "user.email", "montaggio-video@localhost"], cwd=r)
        (r / ".gitignore").write_text(".cestino/\n.storico/\n*.mp4\n*.mov\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=r)
        subprocess.run(["git", "commit", "-q", "-m", "Profili: stato iniziale"], cwd=r)
    return True


def salva(r, messaggio, nome=None):
    data = datetime.now().strftime("%Y-%m-%d %H:%M")
    if git_ok(r):
        subprocess.run(["git", "add", "-A"], cwd=r)
        res = subprocess.run(["git", "commit", "-q", "-m", f"[{data}] {nome or 'profili'}: {messaggio}"], cwd=r, capture_output=True, text=True)
        if res.returncode != 0 and "nothing to commit" not in (res.stdout + res.stderr):
            errore("salvataggio della modifica non riuscito: " + (res.stderr or res.stdout)[-300:])
    elif nome:
        dest = r / ".storico" / nome / datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copytree(r / nome, dest)
        (dest / "MODIFICA.txt").write_text(f"{data}: {messaggio}\n", encoding="utf-8")
    info(f"Salvato [{data}]: {messaggio}")


def crea(r, nome, da):
    nome_valido(nome)
    if (r / nome).exists():
        errore(f"il profilo '{nome}' esiste già.")
    if not (r / da).exists():
        errore(f"il profilo di partenza '{da}' non esiste.")
    shutil.copytree(r / da, r / nome, ignore=shutil.ignore_patterns("diario-revisioni.md", "diario.jsonl"))
    p = r / nome / "profilo.md"
    if p.exists():
        testo = p.read_text(encoding="utf-8")
        testo = re.sub(r"^# Profilo: .*$", f"# Profilo: {nome}", testo, count=1, flags=re.M)
        testo = testo.replace("Profilo neutro e curato, usato quando non ne viene indicato un altro. Non si modifica con\n"
                              "l'apprendimento: le preferenze imparate vanno nei profili dell'utente (si può partire da una copia di questo).",
                              f"Creato il {datetime.now():%d/%m/%Y} partendo da '{da}'.")
        p.write_text(testo, encoding="utf-8")
    for d in ("brand", "riferimenti"):
        (r / nome / d).mkdir(exist_ok=True)
    (r / nome / "diario-revisioni.md").write_text(
        f"# Diario delle revisioni: {nome}\n\nOgni correzione dell'utente, per imparare il suo gusto (vedi riferimenti/profili.md).\n\n"
        "| Data | Chi | Progetto | Formato | Categoria | Tipo | Dimensione | Richiesta | Situazione |\n|---|---|---|---|---|---|---|---|---|\n",
        encoding="utf-8")
    salva(r, f"creato da '{da}'", nome)


def main():
    ap = argparse.ArgumentParser(description="Profili di stile")
    ap.add_argument("azione", choices=["elenca", "crea", "copia", "rinomina", "elimina", "salva", "storico", "annulla"])
    ap.add_argument("--nome")
    ap.add_argument("--da", default=None)
    ap.add_argument("--a")
    ap.add_argument("--messaggio")
    ap.add_argument("--modifica", help="id della modifica da annullare (da 'storico')")
    a = ap.parse_args()
    r = radice()

    if a.azione == "elenca":
        for p in sorted(x for x in r.iterdir() if x.is_dir() and not x.name.startswith(".")):
            formati = [f for f in FORMATI if (p / f"{f}.md").exists()]
            righe_diario = 0
            if (p / "diario.jsonl").exists():
                righe_diario = sum(1 for x in open(p / "diario.jsonl", encoding="utf-8") if '"correzione"' in x)
            info(f"- {p.name}: formati {', '.join(formati) or 'nessuno'}; {righe_diario} correzioni nel diario")
        sopra = [p.name for p in r.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if sopra == ["base"]:
            info("C'è solo il profilo base: è il primo utilizzo, chiedi all'utente se vuole creare i suoi profili.")
    elif a.azione == "crea":
        crea(r, a.nome, a.da or "base")
    elif a.azione == "copia":
        crea(r, a.a, a.da)
    elif a.azione == "rinomina":
        nome_valido(a.a)
        if a.da == "base":
            errore("il profilo base non si rinomina: crea una copia.")
        if not (r / a.da).exists() or (r / a.a).exists():
            errore("profilo di partenza inesistente o nome nuovo già usato.")
        (r / a.da).rename(r / a.a)
        salva(r, f"rinominato da '{a.da}'", a.a)
    elif a.azione == "elimina":
        if a.nome == "base":
            errore("il profilo base non si elimina.")
        if not (r / a.nome).exists():
            errore(f"il profilo '{a.nome}' non esiste.")
        dest = r / ".cestino" / f"{a.nome}-{datetime.now():%Y%m%d-%H%M%S}"
        dest.parent.mkdir(exist_ok=True)
        shutil.move(str(r / a.nome), str(dest))
        salva(r, "eliminato (copia nel cestino)", a.nome)
        info(f"Il profilo è recuperabile da {dest}")
    elif a.azione == "salva":
        if not a.messaggio:
            errore("indica cosa è cambiato con --messaggio")
        if a.nome == "base":
            errore("il profilo base non si modifica: crea un profilo nuovo partendo da base.")
        salva(r, a.messaggio, a.nome)
    elif a.azione == "storico":
        if git_ok(r):
            out = subprocess.run(["git", "log", "--pretty=format:%h  %s", "--", a.nome or "."], cwd=r, capture_output=True, text=True).stdout
            info(out or "Nessuna modifica registrata.")
        else:
            d = r / ".storico" / (a.nome or "")
            for x in sorted(d.glob("*/MODIFICA.txt")) if d.exists() else []:
                info(f"{x.parent.name}  {x.read_text(encoding='utf-8').strip()}")
    elif a.azione == "annulla":
        if not a.nome:
            errore("indica il profilo con --nome")
        if git_ok(r):
            rif = a.modifica or subprocess.run(["git", "log", "-1", "--pretty=%h", "--", a.nome], cwd=r, capture_output=True, text=True).stdout.strip()
            if not rif:
                errore("nessuna modifica da annullare.")
            res = subprocess.run(["git", "revert", "--no-edit", rif], cwd=r, capture_output=True, text=True)
            if res.returncode != 0:
                subprocess.run(["git", "revert", "--abort"], cwd=r)
                errore("non riesco ad annullare automaticamente (modifiche successive sugli stessi file). Mostra lo storico all'utente.")
            info(f"Annullata la modifica {rif}.")
        else:
            snap = sorted((r / ".storico" / a.nome).glob("*")) if (r / ".storico" / a.nome).exists() else []
            if len(snap) < 2:
                errore("non c'è una versione precedente da ripristinare.")
            shutil.rmtree(r / a.nome)
            shutil.copytree(snap[-2], r / a.nome, ignore=shutil.ignore_patterns("MODIFICA.txt"))
            info(f"Ripristinata la versione del {snap[-2].name}.")


if __name__ == "__main__":
    main()
