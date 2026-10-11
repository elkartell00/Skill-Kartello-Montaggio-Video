"""Esporta il montaggio rigenerandolo sempre dalle riprese originali.

uso:
  python esporta.py --progetto nome --modo anteprima|finale [--sottotitoli brucia|file|no]
                    [--tonemap mobius|hable|reinhard] [--encoder x264|videotoolbox] [--versione v03]
                    [--loudness -14] [--paralleli N]

Come funziona:
1. Ogni pezzo della timeline (segmento o transizione) viene ricavato direttamente dagli originali, mai
   da un video già esportato: riinquadratura (shorts), velocità, ridimensionamento, conversione HDR ->
   SDR, look colore, zoom, tremolio, fotogrammi al secondo costanti, micro dissolvenze audio sui tagli.
   I pezzi già fatti con le stesse impostazioni vengono riusati: le revisioni sono veloci e la qualità
   resta identica.
2. Unione dei pezzi, poi sovrapposizioni (grafiche trasparenti, B-roll, animazioni) e sottotitoli.
3. Audio: voce (con pulizia opzionale), musica abbassata sotto la voce, effetti sonori; volume finale
   -14 LUFS con normalizzazione in due passaggi.
4. Se ci sono sovrapposizioni o sottotitoli da bruciare, i pezzi si fanno in qualità intermedia quasi
   senza perdite e la codifica finale avviene una sola volta.

Il piano (.lavoro/<progetto>/piani/<piano>.json) descrive tutto: vedi riferimenti/piano.md.
Risultati in risultati/<progetto>/<piano>/vNN/.
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (DECODIFICA_HW, SKILL_DIR, TRANSIZIONI, adatta_dimensioni, avviso, calcola_timeline,  # noqa: E402
                    cartelle_progetto, errore, esegui, ffprobe, filtro_sdr, flusso_audio, flusso_video,
                    impronta, impronta_file, info, info_hdr, leggi_json, percorsi_piano, prossima_versione,
                    scegli_piano, scrivi_json, tc)

MAC = platform.system() == "Darwin"
COLORI_709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


# ------------------------------------------------------------------ codifica
def parametri_video(modo, encoder, intermedio):
    if modo == "anteprima":
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p"]
    if intermedio:  # quasi senza perdite: verrà ricodificato una sola volta
        return ["-c:v", "libx264", "-preset", "fast", "-crf", "10", "-pix_fmt", "yuv420p"]
    return parametri_finali(encoder)


def parametri_finali(encoder):
    if encoder == "videotoolbox":
        return ["-c:v", "hevc_videotoolbox", "-q:v", "70", "-tag:v", "hvc1", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p"]


def dimensioni_anteprima(W, H):
    k = 540 / min(W, H)
    return int(round(W * k / 2) * 2), int(round(H * k / 2) * 2)


# ------------------------------------------------------------------ catena video di un pezzo
def espressione_lineare(punti, var="t"):
    """[[t, valore], ...] -> espressione FFmpeg a tratti lineari."""
    if len(punti) == 1:
        return f"{punti[0][1]:.5f}"
    expr = f"{punti[-1][1]:.5f}"
    for (t0, v0), (t1, v1) in reversed(list(zip(punti, punti[1:]))):
        tratto = f"({v0:.5f}+({v1 - v0:.5f})*({var}-{t0:.4f})/{max(t1 - t0, 1e-4):.4f})"
        expr = f"if(lt({var},{t1:.4f}),{tratto},{expr})"
    return f"if(lt({var},{punti[0][0]:.4f}),{punti[0][1]:.5f},{expr})"


def filtro_riquadro(src, piano, inizio_src, out_w, out_h):
    """Riinquadratura (es. 16:9 -> 9:16) che segue il soggetto: piano['riinquadratura'][sorgente]."""
    r = (piano.get("riinquadratura") or {}).get(str(src["indice"]))
    if not r:
        return None
    W, H = src["larghezza"], src["altezza"]
    if out_w / out_h < W / H:
        cw, ch = int(round(H * out_w / out_h / 2) * 2), H
    else:
        cw, ch = W, int(round(W * out_h / out_w / 2) * 2)
    punti = [[p[0] - inizio_src, p[1]] for p in r["punti"]]
    cx = espressione_lineare(punti)
    x = f"max(0,min({W - cw},{cx}*{W}-{cw / 2}))"
    cy = r.get("cy", 0.5)
    y = f"max(0,min({H - ch},{cy * H - ch / 2}))"
    return f"crop={cw}:{ch}:x='{x}':y='{y}',scale={out_w}:{out_h}:flags=lanczos"


def filtro_colore(colore):
    if not colore:
        return ""
    parti = []
    if colore.get("lut"):
        lut = Path(colore["lut"]).expanduser()
        if not lut.exists():
            errore(f"non trovo il file LUT {lut}")
        parti.append(f"lut3d=file='{str(lut).replace(chr(92), '/').replace(':', chr(92) + ':')}'")
    eq = {k: colore[k] for k in ("contrasto", "luminosita", "saturazione", "gamma") if k in colore}
    if eq:
        parti.append("eq=" + ":".join(f"{n}={eq[k]}" for k, n in
                                       (("contrasto", "contrast"), ("luminosita", "brightness"), ("saturazione", "saturation"), ("gamma", "gamma")) if k in eq))
    return ",".join(parti)


def filtro_zoom(z, fps, W, H):
    """Zoom a scatto (punch-in) o lento. z = {tipo, da, a, inizio, durata, cx, cy} (tempi relativi al segmento)."""
    if not z:
        return ""
    F = float(Fraction(fps))
    z0, z1 = float(z.get("da", 1.0)), float(z.get("a", 1.15))
    t0, dur = float(z.get("inizio", 0)), float(z.get("durata", 0) or 0)
    tt = f"(on/{F:.5f})"
    if z.get("tipo", "scatto") == "scatto":
        zz = f"if(lt({tt},{t0:.3f}),{z0},{z1})"
    else:
        dur = dur or 3.0
        zz = f"({z0}+({z1 - z0})*min(1,max(0,({tt}-{t0:.3f})/{dur:.3f})))"
    cx, cy = float(z.get("cx", 0.5)), float(z.get("cy", 0.5))
    x = f"max(0,min(iw-iw/zoom,{cx}*iw-iw/zoom/2))"
    y = f"max(0,min(ih-ih/zoom,{cy}*ih-ih/zoom/2))"
    return f"zoompan=z='{zz}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={fps}"


def filtro_tremolio(tr, W, H):
    if not tr:
        return ""
    a = float(tr.get("intensita", 0.01))
    sw, sh = int(round(W * (1 + 2 * a) / 2) * 2), int(round(H * (1 + 2 * a) / 2) * 2)
    ax, ay = a * W, a * H
    return (f"scale={sw}:{sh},crop={W}:{H}:x='(iw-{W})/2+{ax:.1f}*sin(t*13.1)*cos(t*4.7)':"
            f"y='(ih-{H})/2+{ay:.1f}*sin(t*11.3+1.3)*cos(t*5.9)'")


def catena_video(src, piano, inizio_src, out_w, out_h, operatore, effetti=None, velocita=1.0):
    fps = piano["fps"]
    effetti = effetti or {}
    rq = filtro_riquadro(src, piano, inizio_src, out_w, out_h)
    parti = [
        rq,
        f"setpts=(PTS-STARTPTS)/{velocita}" if velocita != 1 else "",
        f"fps={fps}",
        None if rq else adatta_dimensioni(src["larghezza"], src["altezza"], out_w, out_h, piano.get("adattamento", "riempi")),
        filtro_sdr(src["hdr"], operatore),
        filtro_colore(piano.get("colore")),
        filtro_zoom(effetti.get("zoom"), fps, out_w, out_h),
        filtro_tremolio(effetti.get("tremolio"), out_w, out_h),
        "setsar=1", "format=yuv420p",
    ]
    return ",".join(p for p in parti if p)


def filtro_atempo(v):
    parti, r = [], v
    while r > 2.0:
        parti.append("atempo=2.0")
        r /= 2.0
    while r < 0.5:
        parti.append("atempo=0.5")
        r /= 0.5
    if abs(r - 1) > 1e-6:
        parti.append(f"atempo={r:.6f}")
    return ",".join(parti)


def catena_audio(dur, velocita=1.0, dissolvenza=0.01):
    fade = min(dissolvenza, dur / 4)
    parti = ["asetpts=PTS-STARTPTS", filtro_atempo(velocita) if velocita != 1 else "", "aresample=48000",
             "aformat=channel_layouts=stereo",
             f"afade=t=in:st=0:d={fade:.3f}", f"afade=t=out:st={max(0, dur - fade):.4f}:d={fade:.3f}",
             "apad", f"atrim=0:{dur:.6f}"]
    return ",".join(p for p in parti if p)


# ------------------------------------------------------------------ render dei pezzi
def ingresso(src, inizio, durata):
    cmd = [*DECODIFICA_HW, "-ss", f"{inizio:.6f}", "-t", f"{durata + 0.5:.6f}", "-i", src["file"]]
    return cmd


def render_segmento(pz, src, piano, W, H, vparams, operatore, dest):
    seg, v = pz["seg"], pz["velocita"]
    dur = pz["durata"]
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *ingresso(src, pz["da"], (pz["a"] - pz["da"]))]
    if not src["audio"]:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    effetti = {"zoom": seg.get("zoom"), "tremolio": seg.get("tremolio")}
    vf = catena_video(src, piano, pz["da"], W, H, operatore, effetti, v)
    af = catena_audio(dur, v)
    tmp = dest.with_name(dest.stem + ".tmp.mkv")
    cmd += ["-map", "0:v:0", "-map", "0:a:0" if src["audio"] else "1:a:0", "-vf", vf, "-af", af,
            "-frames:v", str(pz["fotogrammi"]), *vparams, *COLORI_709, "-c:a", "pcm_s16le", "-f", "matroska", str(tmp)]
    esegui(cmd, descrizione=f"segmento {seg['id']}")
    os.replace(tmp, dest)


def render_transizione(pz, src_a, src_b, piano, W, H, vparams, operatore, dest):
    d = pz["durata"]
    a, b = pz["da"], pz["a"]
    ia, ib = a["fine"] - d, b["inizio"]
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *ingresso(src_a, ia, d), *ingresso(src_b, ib, d)]
    sil = []
    for k, s in ((0, src_a), (1, src_b)):
        if not s["audio"]:
            sil.append(k)
    for _ in sil:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    aud = {0: "0:a:0", 1: "1:a:0"}
    for j, k in enumerate(sil):
        aud[k] = f"{2 + j}:a:0"
    va = catena_video(src_a, piano, ia, W, H, operatore)
    vb = catena_video(src_b, piano, ib, W, H, operatore)
    nome = TRANSIZIONI[pz["nome"]]
    fc = (f"[0:v]{va},trim=end_frame={pz['fotogrammi']},settb=AVTB[va];[1:v]{vb},trim=end_frame={pz['fotogrammi']},settb=AVTB[vb];"
          f"[va][vb]xfade=transition={nome}:duration={d:.6f}:offset=0,format=yuv420p[v];"
          f"[{aud[0]}]{catena_audio(d, 1.0, 0.0)}[aa];[{aud[1]}]{catena_audio(d, 1.0, 0.0)}[ab];"
          f"[aa][ab]acrossfade=d={d:.6f}:c1=tri:c2=tri,apad,atrim=0:{d:.6f}[a]")
    tmp = dest.with_name(dest.stem + ".tmp.mkv")
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-frames:v", str(pz["fotogrammi"]), *vparams, *COLORI_709,
            "-c:a", "pcm_s16le", "-f", "matroska", str(tmp)]
    esegui(cmd, descrizione=f"transizione verso il segmento {b['id']}")
    os.replace(tmp, dest)


# ------------------------------------------------------------------ sovrapposizioni e audio
def info_file(percorso, cache={}):
    if percorso not in cache:
        p = ffprobe(percorso)
        v, a = flusso_video(p), flusso_audio(p)
        cache[percorso] = {"video": v, "audio": a, "durata": float(p["format"].get("duration", 0) or 0),
                           "hdr": info_hdr(v) if v else {"hdr": False},
                           "alpha": bool(v and (v.get("pix_fmt") or "").startswith(("yuva", "rgba", "argb", "bgra", "abgr", "gbrap", "ya")))}
    return cache[percorso]


def risolvi(percorso, base):
    p = Path(percorso).expanduser()
    return p if p.is_absolute() else (base / p)


def grafo_sovrapposizioni(sovr, base, W, H, primo_indice, operatore):
    """Ingressi e filtri per le sovrapposizioni. Ogni voce: file, inizio, fine, modo (sopra|pieno|riquadro)."""
    ingressi, filtri, etichetta = [], [], "[vbase]"
    idx = primo_indice
    for k, o in enumerate(sorted(sovr, key=lambda x: (x.get("livello", 0), x["inizio"]))):
        f = risolvi(o["file"], base)
        if not f.exists():
            errore(f"non trovo il file della sovrapposizione {f}")
        inf = info_file(str(f))
        modo = o.get("modo", "sopra" if inf["alpha"] else "pieno")
        ini, fin = float(o["inizio"]), float(o.get("fine") or (float(o["inizio"]) + inf["durata"]))
        offs = float(o.get("inizio_file", 0))
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            ingressi += ["-loop", "1", "-t", f"{fin - ini + offs:.3f}", "-i", str(f)]
        else:
            ingressi += ["-i", str(f)]
        catena = [f"trim=start={offs:.3f}", "setpts=PTS-STARTPTS"]
        if inf["hdr"].get("hdr"):
            catena.append(filtro_sdr(inf["hdr"], operatore))
        if modo == "pieno":
            catena.append(f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}")
            catena.append("format=yuva420p")
        elif modo == "riquadro":
            x, y, w, h = o["riquadro"]  # frazioni 0-1
            catena.append(f"scale={int(w * W) // 2 * 2}:{int(h * H) // 2 * 2}:force_original_aspect_ratio=decrease:flags=lanczos,format=yuva420p")
        else:  # sopra: grafica trasparente a tutto fotogramma
            catena.append(f"scale={W}:{H}:flags=lanczos,format=yuva420p")
        if o.get("dissolvenza"):
            d = float(o["dissolvenza"])
            catena.append(f"fade=t=in:st=0:d={d}:alpha=1,fade=t=out:st={max(0, fin - ini - d):.3f}:d={d}:alpha=1")
        catena += ["tpad=stop_mode=clone:stop_duration=600", f"setpts=PTS+{ini:.4f}/TB"]
        filtri.append(f"[{idx}:v]{','.join(catena)}[o{k}]")
        if modo == "riquadro":
            x, y, w, h = o["riquadro"]
            pos = f"x={int(x * W)}:y={int(y * H)}"
        else:
            pos = "x=0:y=0"
        filtri.append(f"{etichetta}[o{k}]overlay={pos}:enable='between(t,{ini:.4f},{fin:.4f})':eof_action=pass[s{k}]")
        etichetta = f"[s{k}]"
        idx += 1
    return ingressi, filtri, etichetta


def grafo_audio(audio, base, primo_indice, durata):
    """Voce + musica (abbassata sotto la voce) + effetti sonori -> [amix]. Restituisce ingressi e filtri."""
    ingressi, filtri, mix = [], [], []
    voce = "[0:a]"
    if (audio.get("voce") or {}).get("pulizia"):
        filtri.append("[0:a]highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=10:release=200:makeup=2[voce]")
        voce = "[voce]"
    musiche = audio.get("musica") or []
    effetti = audio.get("effetti") or []
    ducking = any(m.get("abbassa_sotto_voce", True) for m in musiche)
    if ducking:
        filtri.append(f"{voce}asplit=2[vmix][vside]")
        voce, side = "[vmix]", "[vside]"
        if len([m for m in musiche if m.get("abbassa_sotto_voce", True)]) > 1:
            n = len([m for m in musiche if m.get("abbassa_sotto_voce", True)])
            filtri.append(f"[vside]asplit={n}" + "".join(f"[vs{i}]" for i in range(n)))
            sides = [f"[vs{i}]" for i in range(n)]
        else:
            sides = ["[vside]"]
    mix.append(voce)
    idx = primo_indice
    si = 0
    for k, m in enumerate(musiche):
        f = risolvi(m["file"], base)
        if not f.exists():
            errore(f"non trovo la musica {f}")
        ingressi += ["-stream_loop", "-1" if m.get("ripeti", False) else "0", "-i", str(f)]
        ini = float(m.get("inizio", 0))
        fin = float(m.get("fine") or durata)
        din, dout = float(m.get("dissolvenza_in", 1.0)), float(m.get("dissolvenza_out", 2.0))
        vol = float(m.get("volume_db", -18))
        c = (f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=start={float(m.get('inizio_file', 0)):.3f},"
             f"asetpts=PTS-STARTPTS,atrim=0:{fin - ini:.3f},afade=t=in:d={din}:st=0,afade=t=out:st={max(0, fin - ini - dout):.3f}:d={dout},"
             f"volume={vol}dB,adelay={int(ini * 1000)}:all=1")
        if m.get("abbassa_sotto_voce", True):
            filtri.append(f"{c}[m{k}pre]")
            filtri.append(f"[m{k}pre]{sides[si]}sidechaincompress=threshold=0.02:ratio=6:attack=30:release=500:makeup=1[m{k}]")
            si += 1
        else:
            filtri.append(f"{c}[m{k}]")
        mix.append(f"[m{k}]")
        idx += 1
    for k, e in enumerate(effetti):
        f = risolvi(e["file"], base)
        if not f.exists():
            errore(f"non trovo l'effetto sonoro {f}")
        ingressi += ["-i", str(f)]
        filtri.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume={float(e.get('volume_db', -6))}dB,"
                      f"adelay={int(float(e['inizio']) * 1000)}:all=1[e{k}]")
        mix.append(f"[e{k}]")
        idx += 1
    if len(mix) > 1:
        # duration=longest + taglio esatto: con duration=first il mixer chiudeva appena finiva la voce, perdendo
        # gli ultimi campioni ancora in viaggio nella compressione della musica (audio più corto del video).
        filtri.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=longest:normalize=0,apad,atrim=0:{durata:.6f}[amix]")
    else:
        filtri.append(f"{voce}apad,atrim=0:{durata:.6f}[amix]")
    return ingressi, filtri


# ------------------------------------------------------------------ principale
def main():
    ap = argparse.ArgumentParser(description="Esportazione dagli originali")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--piano", help="nome del piano (se il progetto ne ha più di uno)")
    ap.add_argument("--modo", choices=["anteprima", "finale"], required=True)
    ap.add_argument("--sottotitoli", choices=["brucia", "file", "no"], default="file",
                    help="brucia = scritti nel video; file = solo .srt a parte (nell'anteprima si vedono comunque)")
    ap.add_argument("--tonemap", default="mobius", help="conversione HDR: mobius, hable o reinhard")
    ap.add_argument("--encoder", choices=["x264", "videotoolbox"], default="x264")
    ap.add_argument("--versione", help="cartella di versione da usare (es. v03)")
    ap.add_argument("--loudness", type=float, default=-14.0)
    ap.add_argument("--picco", type=float, default=-1.5)
    ap.add_argument("--paralleli", type=int, default=0)
    ap.add_argument("--nome", help="nome del file finale (senza estensione)")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    nome_piano = scegli_piano(c, a.piano)
    P = percorsi_piano(c, nome_piano)
    piano = leggi_json(P["piano"])
    analisi = {s["indice"]: s for s in leggi_json(c["lavoro"] / "analisi.json")["sorgenti"]}
    if not piano["segmenti"]:
        errore("il piano di montaggio non ha segmenti.")
    if a.encoder == "videotoolbox" and not MAC:
        errore("la codifica videotoolbox esiste solo su Mac.")
    for s in analisi.values():
        if not Path(s["file"]).exists():
            errore(f"la ripresa originale {s['file']} non esiste più.")
    base = c["root"]  # i percorsi relativi nel piano partono dalla cartella montaggio-video/

    W, H, fps = piano["larghezza"], piano["altezza"], piano["fps"]
    if a.modo == "anteprima":
        W, H = dimensioni_anteprima(W, H)
    ass = P["ass"]
    brucia = a.sottotitoli == "brucia" or (a.modo == "anteprima" and a.sottotitoli == "file")
    if brucia and not ass.exists():
        avviso(f"non trovo {ass.name}: esporto senza sottotitoli. Esegui prima sottotitoli.py.")
        brucia = False
    sovr = piano.get("sovrapposizioni") or []
    audio = piano.get("audio") or {}
    serve_ricodifica = brucia or bool(sovr)
    intermedio = a.modo == "finale" and serve_ricodifica
    vparams = parametri_video(a.modo, a.encoder, intermedio)

    # Versione di destinazione.
    hash_piano = impronta(piano)
    if a.versione:
        versione = a.versione
    elif a.modo == "finale":
        ultime = sorted((p for p in P["risultati"].glob("v[0-9]*") if p.is_dir()), key=lambda p: int(p.name[1:]))
        stessa = ultime and (ultime[-1] / "piano.json").exists() and \
            impronta(leggi_json(ultime[-1] / "piano.json")) == hash_piano
        versione = ultime[-1].name if stessa else prossima_versione(P["risultati"])
    else:
        versione = prossima_versione(P["risultati"])
    vdir = P["risultati"] / versione
    vdir.mkdir(parents=True, exist_ok=True)
    scrivi_json(vdir / "piano.json", piano)

    # 1. Pezzi dagli originali (con cache).
    pezzi, _, durata_tot = calcola_timeline(piano)
    cache = c["lavoro"] / "segmenti" / ("anteprima" if a.modo == "anteprima" else ("intermedi" if intermedio else "finali"))
    cache.mkdir(parents=True, exist_ok=True)
    comune_chiave = [W, H, fps, piano.get("adattamento", "riempi"), piano.get("colore"), piano.get("riinquadratura"), a.tonemap, vparams]
    lavori = []
    for pz in pezzi:
        if pz["tipo"] == "segmento":
            src = analisi[pz["seg"]["sorgente"]]
            chiave = impronta("seg", src["file"], impronta_file(src["file"]), pz["da"], pz["a"], pz["velocita"],
                              pz["seg"].get("zoom"), pz["seg"].get("tremolio"), comune_chiave)
            lavori.append((pz, cache / f"{chiave}.mkv"))
        else:
            sa, sb = analisi[pz["da"]["sorgente"]], analisi[pz["a"]["sorgente"]]
            chiave = impronta("tr", sa["file"], sb["file"], pz["da"]["fine"], pz["a"]["inizio"], pz["durata"], pz["nome"], comune_chiave)
            lavori.append((pz, cache / f"{chiave}.mkv"))
    da_fare = [l for l in lavori if not l[1].exists()]
    paralleli = a.paralleli or max(1, (os.cpu_count() or 4) // (2 if a.modo == "anteprima" else 4))
    info(f"Versione {versione}, {a.modo} {W}x{H} @ {fps}: {len(lavori)} pezzi ({len(lavori) - len(da_fare)} già pronti), "
         f"{len(sovr)} sovrapposizioni.")

    def fai(pz, dest):
        if pz["tipo"] == "segmento":
            render_segmento(pz, analisi[pz["seg"]["sorgente"]], piano, W, H, vparams, a.tonemap, dest)
        else:
            render_transizione(pz, analisi[pz["da"]["sorgente"]], analisi[pz["a"]["sorgente"]], piano, W, H, vparams, a.tonemap, dest)

    with ThreadPoolExecutor(max_workers=paralleli) as ex:
        futuri = [ex.submit(fai, pz, dest) for pz, dest in da_fare]
        for i, f in enumerate(as_completed(futuri), 1):
            f.result()
            if i % 10 == 0 or i == len(futuri):
                info(f"  pezzi {i}/{len(futuri)}")

    lista = vdir / f".pezzi-{a.modo}.txt"
    lista.write_text("".join(f"file '{str(d).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for _, d in lavori),
                     encoding="utf-8")

    # 2-3. Grafo finale: video (sovrapposizioni, sottotitoli) + audio (mix, volume).
    ingressi = ["-f", "concat", "-safe", "0", "-i", str(lista)]
    filtri = []
    vi, vf, ultimo = grafo_sovrapposizioni(sovr, base, W, H, 1, a.tonemap)
    ultimo = ultimo.strip("[]")
    ingressi += vi
    ai, af = grafo_audio(audio, base, 1 + len(sovr), durata_tot)
    ingressi += ai
    filtri += af
    cwd = None
    if serve_ricodifica:
        filtri.insert(0, "[0:v]setpts=PTS-STARTPTS[vbase]")
        filtri += vf
        if brucia:
            fonts = ass.parent / "font"
            if not fonts.exists():
                shutil.copytree(SKILL_DIR / "assets" / "fonts", fonts)
            cwd = ass.parent  # il filtro dei sottotitoli lavora con percorsi relativi (niente problemi con spazi)
            filtri.append(f"[{ultimo}]subtitles={ass.name}:fontsdir=font,format=yuv420p[vout]")
        else:
            filtri.append(f"[{ultimo}]format=yuv420p[vout]")
        mappa_v = ["-map", "[vout]", *(parametri_finali(a.encoder) if a.modo == "finale" else vparams), *COLORI_709]
    else:
        mappa_v = ["-map", "0:v", "-c:v", "copy"]

    base_cmd = ["ffmpeg", "-hide_banner", "-nostats", *ingressi]
    # Primo passaggio: misura del volume del mix.
    grafo_audio_misura = ";".join(af) + f";[amix]loudnorm=I={a.loudness}:TP={a.picco}:LRA=11:print_format=json[aout]"
    r = subprocess.run(base_cmd + ["-filter_complex", grafo_audio_misura, "-map", "[aout]", "-f", "null", "-"],
                       capture_output=True, text=True, cwd=cwd)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if m:
        m = json.loads(m.group(0))
        ln = (f"loudnorm=I={a.loudness}:TP={a.picco}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    else:
        avviso("non riesco a misurare il volume: uso la normalizzazione in un solo passaggio.")
        ln = f"loudnorm=I={a.loudness}:TP={a.picco}:LRA=11"
    filtri.append(f"[amix]{ln},aresample=48000[aout]")

    nome = (a.nome or f"{a.progetto}-{nome_piano}-{versione}") + ".mp4" if a.modo == "finale" else "anteprima.mp4"
    out = vdir / nome
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *ingressi, "-filter_complex", ";".join(filtri), *mappa_v,
           "-map", "[aout]", "-c:a", "aac", "-b:a", "320k" if a.modo == "finale" else "160k",
           "-t", f"{durata_tot:.6f}", "-movflags", "+faststart", str(out)]
    info("Unione, grafiche e audio ...")
    if os.environ.get("MONTAGGIO_DEBUG"):
        (vdir / ".comando.json").write_text(json.dumps({"cmd": cmd, "cwd": str(cwd) if cwd else None}), encoding="utf-8")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        errore("unione finale non riuscita:\n" + "\n".join(r.stderr.strip().splitlines()[-15:]))
    if not os.environ.get("MONTAGGIO_DEBUG"):
        lista.unlink(missing_ok=True)

    for f, dest in ((P["srt"], "sottotitoli.srt"), (P["ass"], "sottotitoli.ass"), (P["riepilogo"], "riepilogo-tagli.md")):
        if f.exists():
            shutil.copy2(f, vdir / dest)

    info(f"Fatto: {out} (durata attesa {tc(durata_tot)})")
    controllo = Path(__file__).resolve().parent / "controllo_finale.py"
    subprocess.run([sys.executable, str(controllo), str(out), "--larghezza", str(W), "--altezza", str(H), "--fps", fps,
                    "--durata", f"{durata_tot:.3f}", "--loudness", str(a.loudness), "--picco", str(a.picco)])


if __name__ == "__main__":
    main()
