"""Trascrizione parola per parola con i tempi, in locale con Whisper.

uso:
  python trascrivi.py --progetto nome [--lingua it] [--modello turbo|large|small] [--srt file.srt ...]

Motore: mlx-whisper sui Mac con chip Apple (molto più veloce), faster-whisper altrove.
Il prompt iniziale contiene intercalari ("ehm", "cioè"...) per spingere Whisper a trascriverli
invece di ripulirli: servono per poterli tagliare.

Con --srt (uno per ripresa, nello stesso ordine) non usa Whisper: stima i tempi delle parole
distribuendo ogni sottotitolo sui caratteri (precisione circa ±0,2 s, metodo di motion-broll).

Scrive in .lavoro/<progetto>/:
  trascrizione.json   parole con inizio, fine e probabilità, per ogni ripresa
  trascrizione.txt    testo leggibile con i tempi, una frase per riga
"""
import argparse
import platform
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import cartelle_progetto, errore, info, leggi_json, scrivi_json, tc  # noqa: E402

MODELLI = {
    "mlx_whisper": {"turbo": "mlx-community/whisper-large-v3-turbo", "large": "mlx-community/whisper-large-v3-mlx",
                    "small": "mlx-community/whisper-small-mlx"},
    "faster_whisper": {"turbo": "large-v3-turbo", "large": "large-v3", "small": "small"},
}

PROMPT_INIZIALE = {
    "it": "Ehm, allora... cioè, praticamente, ehm, sì. Uhm, va bene, quindi... ehm, ecco.",
    "en": "Um, so... uh, like, you know, um, yeah. Uh, okay, so... um, right.",
}


def scegli_backend(richiesto):
    if richiesto != "auto":
        return richiesto
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper  # noqa: F401
            return "mlx_whisper"
        except ImportError:
            pass
    try:
        import faster_whisper  # noqa: F401
        return "faster_whisper"
    except ImportError:
        errore("Whisper non è installato. Esegui: python3 verifica_strumenti.py --installa")


def trascrivi_mlx(wav, modello, lingua):
    import mlx_whisper
    r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=modello, language=lingua, word_timestamps=True,
                               initial_prompt=PROMPT_INIZIALE.get(lingua), condition_on_previous_text=False)
    parole = []
    for seg in r.get("segments", []):
        for w in seg.get("words", []):
            parole.append({"w": w["word"].strip(), "inizio": round(w["start"], 3), "fine": round(w["end"], 3),
                           "prob": round(float(w.get("probability", 1.0)), 3)})
    return parole


def trascrivi_faster(wav, modello, lingua):
    from faster_whisper import WhisperModel
    try:
        import ctranslate2
        cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        cuda = False
    m = WhisperModel(modello, device="cuda" if cuda else "cpu", compute_type="float16" if cuda else "int8")
    segs, _ = m.transcribe(str(wav), language=lingua, word_timestamps=True, initial_prompt=PROMPT_INIZIALE.get(lingua),
                           condition_on_previous_text=False, vad_filter=False, beam_size=5)
    parole = []
    for seg in segs:
        for w in seg.words or []:
            parole.append({"w": w.word.strip(), "inizio": round(w.start, 3), "fine": round(w.end, 3),
                           "prob": round(float(w.probability), 3)})
    return parole


def parole_da_srt(srt):
    """Stima i tempi delle parole da un SRT (da motion-broll/words.py)."""
    def ts(x):
        hh, mm, r = x.strip().split(":")
        s, ms = r.replace(".", ",").split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(s) + int(ms) / 1000
    parole = []
    testo = Path(srt).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    for blk in testo.strip().split("\n\n"):
        L = blk.strip().split("\n")
        idx = next((i for i, l in enumerate(L) if "-->" in l), None)
        if idx is None:
            continue
        a, b = [ts(x) for x in L[idx].split("-->")]
        words = re.sub(r"<[^>]+>", "", " ".join(L[idx + 1:])).split()
        n = sum(len(w) + 1 for w in words) or 1
        c = 0
        for w in words:
            ini = a + (b - a) * c / n
            c += len(w) + 1
            parole.append({"w": w, "inizio": round(ini, 3), "fine": round(a + (b - a) * (c - 1) / n, 3), "prob": None})
    return parole


def frasi(parole, pausa=0.7):
    """Raggruppa le parole in frasi: punteggiatura finale o pausa lunga."""
    out, cur = [], []
    for i, p in enumerate(parole):
        cur.append(p)
        fine_frase = p["w"].endswith((".", "?", "!", "…"))
        pausa_lunga = i + 1 < len(parole) and parole[i + 1]["inizio"] - p["fine"] > pausa
        if fine_frase or pausa_lunga or i == len(parole) - 1:
            out.append(cur)
            cur = []
    return out


def main():
    ap = argparse.ArgumentParser(description="Trascrizione con Whisper")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--lingua", default="it")
    ap.add_argument("--modello", default="turbo", help="turbo (consigliato), large, small o il nome completo di un modello")
    ap.add_argument("--backend", default="auto", choices=["auto", "mlx_whisper", "faster_whisper"])
    ap.add_argument("--srt", nargs="*", help="sottotitoli già pronti, uno per ripresa (salta Whisper)")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    analisi = leggi_json(c["lavoro"] / "analisi.json")
    sorgenti = analisi["sorgenti"]
    if a.srt and len(a.srt) != len(sorgenti):
        errore(f"servono {len(sorgenti)} file SRT (uno per ripresa), ne ho ricevuti {len(a.srt)}.")

    backend = "srt" if a.srt else scegli_backend(a.backend)
    modello = MODELLI.get(backend, {}).get(a.modello, a.modello) if backend != "srt" else None
    risultato = {"lingua": a.lingua, "backend": backend, "modello": modello, "sorgenti": []}

    for i, s in enumerate(sorgenti):
        n = f"{s['indice']:02d}"
        t0 = time.time()
        if a.srt:
            parole = parole_da_srt(a.srt[i])
        elif not s.get("audio_wav"):
            info(f"[{n}] nessun audio: salto.")
            parole = []
        else:
            info(f"[{n}] Trascrivo con {backend} ({modello}) ... (la prima volta scarica il modello)")
            try:
                parole = (trascrivi_mlx if backend == "mlx_whisper" else trascrivi_faster)(s["audio_wav"], modello, a.lingua)
            except Exception as e:  # di solito: modello non scaricabile (rete) o memoria insufficiente
                errore(f"la trascrizione non è riuscita ({type(e).__name__}: {str(e)[:200]}). "
                       "Se è il primo utilizzo, serve internet per scaricare il modello (circa 1,5 GB) da HuggingFace. "
                       "Con poca memoria prova --modello small.")
        risultato["sorgenti"].append({"indice": s["indice"], "file": s["file"], "parole": parole})
        info(f"     {len(parole)} parole in {time.time() - t0:.0f} s")

    scrivi_json(c["lavoro"] / "trascrizione.json", risultato)
    righe = []
    for s in risultato["sorgenti"]:
        righe.append(f"## Ripresa {s['indice']:02d}: {Path(s['file']).name}")
        for fr in frasi(s["parole"]):
            righe.append(f"[{tc(fr[0]['inizio'])} - {tc(fr[-1]['fine'])}] " + " ".join(p["w"] for p in fr))
        righe.append("")
    (c["lavoro"] / "trascrizione.txt").write_text("\n".join(righe), encoding="utf-8")
    info(f"Trascrizione salvata in {c['lavoro'] / 'trascrizione.json'} e trascrizione.txt")


if __name__ == "__main__":
    main()
