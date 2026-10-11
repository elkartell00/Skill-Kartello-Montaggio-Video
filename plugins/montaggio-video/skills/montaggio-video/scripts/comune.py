"""Funzioni condivise dagli script della skill montaggio-video.

Tutti i messaggi per l'utente sono in italiano. Gli script usano solo la libreria
standard di Python (più numpy dove indicato), così funzionano con qualsiasi Python 3.9+.
"""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# Sul Mac la decodifica HEVC 4K passa dal chip video (VideoToolbox): molto più veloce.
DECODIFICA_HW = ["-hwaccel", "videotoolbox"] if platform.system() == "Darwin" else []

# Fotogrammi al secondo standard: le riprese iPhone sono a frequenza variabile,
# quindi il valore misurato va riportato al valore nominale più vicino.
FPS_STANDARD = ["24000/1001", "24", "25", "30000/1001", "30", "50", "60000/1001", "60", "120"]

# Dimensioni di uscita predefinite per formato (larghezza, altezza).
FORMATI = {
    "video-lungo": (3840, 2160),
    "shorts-dal-lungo": (1080, 1920),
    "shorts-indipendenti": (1080, 1920),
    "reels": (1080, 1920),
}


def errore(messaggio, codice=1):
    """Ferma lo script con un messaggio chiaro in italiano."""
    print(f"ERRORE: {messaggio}", file=sys.stderr)
    sys.exit(codice)


def avviso(messaggio):
    print(f"ATTENZIONE: {messaggio}", file=sys.stderr)


def info(messaggio):
    print(messaggio, flush=True)


def cartella_lavoro(base=None):
    """La cartella 'montaggio-video' dentro la cartella da cui è stata avviata la skill."""
    if base:
        return Path(base).expanduser().resolve()
    env = os.environ.get("MONTAGGIO_VIDEO_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / "montaggio-video").resolve()


def cartelle_progetto(nome, base=None):
    """Percorsi standard di un progetto. Non crea nulla."""
    root = cartella_lavoro(base)
    return {
        "root": root,
        "da_montare": root / "da-montare" / nome,
        "lavoro": root / ".lavoro" / nome,
        "risultati": root / "risultati" / nome,
        "progetto": root / ".lavoro" / nome / "progetto.json",
    }


def leggi_json(percorso):
    percorso = Path(percorso)
    if not percorso.exists():
        errore(f"non trovo il file {percorso}")
    with open(percorso, encoding="utf-8") as f:
        return json.load(f)


def scrivi_json(percorso, dati):
    percorso = Path(percorso)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    tmp = percorso.with_suffix(percorso.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)
    os.replace(tmp, percorso)


def richiedi(programma, suggerimento):
    if shutil.which(programma) is None:
        errore(f"manca {programma}. {suggerimento}")


def esegui(cmd, cattura=False, descrizione=None):
    """Esegue un comando (lista di argomenti, mai una stringa di shell)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        errore(f"non trovo il programma {cmd[0]}. Esegui verifica_strumenti.py per controllare l'installazione.")
    if r.returncode != 0:
        dettaglio = (r.stderr or r.stdout or "").strip().splitlines()[-15:]
        errore(f"{descrizione or 'comando'} non riuscito ({cmd[0]}):\n" + "\n".join(dettaglio))
    return r.stdout if cattura else r


def ffprobe(percorso):
    richiedi("ffprobe", "Installa FFmpeg (su Mac: brew install ffmpeg).")
    out = esegui(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format",
                  str(percorso)], cattura=True, descrizione=f"lettura di {Path(percorso).name}")
    return json.loads(out)


def flusso_video(probe):
    for s in probe.get("streams", []):
        if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0:
            return s
    return None


def flusso_audio(probe):
    for s in probe.get("streams", []):
        if s.get("codec_type") == "audio":
            return s
    return None


def fps_nominale(stream):
    """Riporta la frequenza misurata al valore standard più vicino (le riprese iPhone sono VFR)."""
    def frac(v):
        try:
            f = Fraction(v)
            return f if f > 0 else None
        except (ValueError, ZeroDivisionError, TypeError):
            return None
    misurato = frac(stream.get("avg_frame_rate")) or frac(stream.get("r_frame_rate")) or Fraction(30)
    return min(FPS_STANDARD, key=lambda s: abs(float(Fraction(s)) - float(misurato)))


def is_vfr(stream):
    try:
        return Fraction(stream.get("avg_frame_rate", "0/1")) != Fraction(stream.get("r_frame_rate", "0/1"))
    except (ValueError, ZeroDivisionError):
        return False


def info_hdr(stream):
    """Riconosce HLG, PQ (HDR10) e Dolby Vision (anche il profilo 8.4 dell'iPhone, che ha base HLG)."""
    trc = stream.get("color_transfer", "")
    dovi = any("DOVI" in (sd.get("side_data_type", "") or "").upper() or "dolby vision" in (sd.get("side_data_type", "") or "").lower()
               for sd in stream.get("side_data_list", []) or [])
    tipo = None
    if trc == "arib-std-b67":
        tipo = "HLG"
    elif trc == "smpte2084":
        tipo = "PQ"
    if dovi:
        tipo = f"Dolby Vision ({tipo or 'base sconosciuta'})"
    return {"hdr": tipo is not None, "tipo": tipo, "transfer": trc,
            "primaries": stream.get("color_primaries", ""), "matrix": stream.get("color_space", "")}


# Operatori di mappatura dei toni disponibili nel filtro tonemap di FFmpeg.
OPERATORI_TONEMAP = {
    "mobius": "tonemap=mobius:param=0.3:desat=0",
    "hable": "tonemap=hable:desat=0",
    "reinhard": "tonemap=reinhard:param=0.6:desat=0",
}


def filtro_sdr(hdr, operatore="mobius", npl=100):
    """Catena di filtri HDR -> SDR Rec.709. Vuota se il video è già SDR.

    Passa in luce lineare a virgola mobile, converte i primari BT.2020 -> BT.709,
    applica la mappatura dei toni e torna in BT.709. Senza questi passaggi i colori
    escono slavati (il classico errore di chi converte solo il formato pixel).
    """
    if not hdr.get("hdr"):
        return ""
    tin = "arib-std-b67" if hdr.get("transfer") == "arib-std-b67" else "smpte2084"
    tm = OPERATORI_TONEMAP.get(operatore)
    if tm is None:
        errore(f"operatore di mappatura dei toni sconosciuto: {operatore}. Valori possibili: {', '.join(OPERATORI_TONEMAP)}")
    return (f"zscale=tin={tin}:pin=bt2020:min=bt2020nc:t=linear:npl={npl},format=gbrpf32le,"
            f"zscale=p=bt709,{tm},zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def adatta_dimensioni(w_in, h_in, w_out, h_out, modo="riempi"):
    """Filtro per portare il video a w_out x h_out.

    riempi: scala e ritaglia al centro (nessuna banda nera).
    contieni: scala e aggiunge bande nere.
    """
    if (w_in, h_in) == (w_out, h_out):
        return ""
    if modo == "contieni":
        return (f"scale={w_out}:{h_out}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={w_out}:{h_out}:(ow-iw)/2:(oh-ih)/2")
    return (f"scale={w_out}:{h_out}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={w_out}:{h_out}")


def quantizza(t, fps):
    """Arrotonda un tempo al fotogramma più vicino."""
    f = float(Fraction(fps))
    return round(round(t * f) / f, 6)


def prossima_versione(cartella_risultati):
    cartella_risultati = Path(cartella_risultati)
    esistenti = []
    if cartella_risultati.exists():
        for p in cartella_risultati.iterdir():
            if p.is_dir() and p.name.startswith("v") and p.name[1:].isdigit():
                esistenti.append(int(p.name[1:]))
    return f"v{(max(esistenti) + 1) if esistenti else 1:02d}"


def impronta(*parti):
    h = hashlib.sha1()
    for p in parti:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()[:16]


def impronta_file(percorso):
    """Dimensione + data di modifica: serve a controllare che un originale non sia cambiato."""
    st = Path(percorso).stat()
    return {"dimensione": st.st_size, "modificato": int(st.st_mtime)}


def tc(t):
    """Secondi -> m:ss.cc per i riepiloghi."""
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{t % 60:05.2f}"


# ------------------------------------------------------------------ timeline
# Transizioni disponibili (nome nel piano -> transizione xfade di FFmpeg).
TRANSIZIONI = {
    "dissolvenza": "fade", "flash": "fadewhite", "nero": "fadeblack", "glitch": "pixelize",
    "scorri-sinistra": "slideleft", "scorri-destra": "slideright", "scorri-su": "slideup", "scorri-giu": "slidedown",
    "frusta": "smoothleft", "zoom": "zoomin", "cerchio": "circleopen", "sfocatura": "hblur", "tendina": "wipeleft",
}


def n_fotogrammi(secondi, fps):
    return max(1, round(secondi * float(Fraction(fps))))


def calcola_timeline(piano):
    """Pezzi da renderizzare in ordine (segmenti e transizioni) e posizione di ogni segmento sulla timeline.

    Una transizione di durata d tra A e B usa gli ultimi d secondi di A e i primi d di B sovrapposti:
    la timeline si accorcia di d. Le transizioni valgono solo tra segmenti a velocità normale e
    abbastanza lunghi; le altre vengono ignorate con un avviso.
    Restituisce (pezzi, mappa, durata_totale). mappa[id_segmento] = (tempo sulla timeline che
    corrisponde a seg.inizio, velocità): per portare un tempo della ripresa sulla timeline.
    """
    fps = piano["fps"]
    f = float(Fraction(fps))
    segs = piano["segmenti"]
    n = len(segs)
    d_in = [0.0] * (n + 1)
    for i in range(1, n):
        tr = segs[i].get("transizione")
        if not tr:
            continue
        nome = tr.get("tipo", "dissolvenza")
        if nome not in TRANSIZIONI:
            avviso(f"transizione sconosciuta '{nome}' nel segmento {segs[i]['id']}: ignorata. Valori: {', '.join(TRANSIZIONI)}")
            continue
        d = n_fotogrammi(tr.get("durata", 0.4), fps) / f
        a, b = segs[i - 1], segs[i]
        if a.get("velocita", 1) != 1 or b.get("velocita", 1) != 1:
            avviso(f"transizione nel segmento {b['id']} ignorata: non si combina con un cambio di velocità.")
            continue
        if (a["fine"] - a["inizio"]) - d_in[i - 1] < d + 2 / f or (b["fine"] - b["inizio"]) < d + 2 / f:
            avviso(f"transizione nel segmento {b['id']} ignorata: segmenti troppo corti.")
            continue
        d_in[i] = d
    pezzi, mappa, t = [], {}, 0.0
    for i, s in enumerate(segs):
        v = float(s.get("velocita", 1) or 1)
        if d_in[i]:
            nf = n_fotogrammi(d_in[i], fps)
            pezzi.append({"tipo": "transizione", "da": segs[i - 1], "a": s, "nome": s["transizione"].get("tipo", "dissolvenza"),
                          "fotogrammi": nf, "durata": nf / f, "inizio_t": t})
            t += nf / f
        mappa[s["id"]] = (t - d_in[i], v)
        da, a = s["inizio"] + d_in[i], s["fine"] - d_in[i + 1]
        nf = n_fotogrammi((a - da) / v, fps)
        pezzi.append({"tipo": "segmento", "seg": s, "da": da, "a": a, "velocita": v, "fotogrammi": nf, "durata": nf / f, "inizio_t": t})
        t += nf / f
    return pezzi, mappa, t


# ------------------------------------------------------------------ piani
# Un progetto può avere più montaggi (video lungo, short-1, short-2, reel-1...): uno per piano.
def nome_piano_valido(nome):
    import re as _re
    if not _re.fullmatch(r"[a-z0-9][a-z0-9-]*", nome or ""):
        errore(f"nome del piano non valido: '{nome}'. Usa lettere minuscole, numeri e trattini (es. short-1).")
    return nome


def percorsi_piano(cartelle, nome):
    nome_piano_valido(nome)
    lav = cartelle["lavoro"]
    return {
        "piano": lav / "piani" / f"{nome}.json",
        "riepilogo": lav / "piani" / f"{nome}.md",
        "srt": lav / "sottotitoli" / f"{nome}.srt",
        "ass": lav / "sottotitoli" / f"{nome}.ass",
        "parole": lav / "sottotitoli" / f"{nome}-parole.json",
        "risultati": cartelle["risultati"] / nome,
        "segmenti": lav / "segmenti",
    }


def piani_del_progetto(cartelle):
    d = cartelle["lavoro"] / "piani"
    return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []


def scegli_piano(cartelle, nome=None):
    """Il piano indicato, oppure l'unico del progetto."""
    if nome:
        return nome_piano_valido(nome)
    piani = piani_del_progetto(cartelle)
    if len(piani) == 1:
        return piani[0]
    if not piani:
        errore("il progetto non ha ancora un piano di montaggio: esegui prima pulizia.py.")
    errore(f"il progetto ha più piani ({', '.join(piani)}): indica quale con --piano.")
