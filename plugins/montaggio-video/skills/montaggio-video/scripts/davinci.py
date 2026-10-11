"""Progetto per DaVinci Resolve (FCPXML 1.9) collegato alle riprese originali.

uso:
  python davinci.py --progetto nome [--piano video-lungo] [--versione v03]

Crea in risultati/<progetto>/<piano>/vNN/davinci/:
  <progetto>-<piano>-vNN.fcpxml   la timeline: segmenti dagli originali sulla traccia principale, grafiche,
                                  animazioni e B-roll come clip separate sopra (trasparenti a piena risoluzione),
                                  musica ed effetti sonori sotto, con il loro volume
  sottotitoli.srt                 da importare a parte (File > Import > Subtitle)
  LEGGIMI.txt                     come importare e cosa sistemare a mano

Velocità, zoom, tremolio, transizioni, look colore e riinquadratura non passano in modo affidabile
nell'FCPXML: diventano marcatori sulla timeline con l'istruzione, così si rifanno in DaVinci in pochi clic.
In DaVinci si esporta una volta sola, dagli originali: nessuna perdita di qualità.
"""
import argparse
import shutil
import sys
from fractions import Fraction
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (calcola_timeline, cartelle_progetto, errore, ffprobe, flusso_audio, flusso_video, fps_nominale,  # noqa: E402
                    info, leggi_json, percorsi_piano, scegli_piano)


class Tempo:
    """Tempi FCPXML razionali, allineati ai fotogrammi della sequenza."""

    def __init__(self, fps):
        self.fd = 1 / Fraction(fps)  # durata di un fotogramma

    def __call__(self, secondi):
        n = round(Fraction(secondi).limit_denominator(1000000) / self.fd)
        v = n * self.fd
        return f"{v.numerator}/{v.denominator}s" if v.denominator != 1 else f"{v.numerator}s"


def url_file(p):
    return Path(p).resolve().as_uri()


def main():
    ap = argparse.ArgumentParser(description="Progetto DaVinci Resolve")
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--piano")
    ap.add_argument("--versione")
    a = ap.parse_args()

    c = cartelle_progetto(a.progetto, a.cartella)
    nome = scegli_piano(c, a.piano)
    P = percorsi_piano(c, nome)
    versioni = sorted((p for p in P["risultati"].glob("v[0-9]*") if p.is_dir()), key=lambda p: int(p.name[1:]))
    if not versioni:
        errore("nessuna versione esportata per questo piano.")
    vdir = P["risultati"] / a.versione if a.versione else versioni[-1]
    piano = leggi_json(vdir / "piano.json")
    analisi = {s["indice"]: s for s in leggi_json(c["lavoro"] / "analisi.json")["sorgenti"]}
    pezzi, mappa, durata = calcola_timeline(piano)
    W, H, fps = piano["larghezza"], piano["altezza"], piano["fps"]
    T = Tempo(fps)
    fr = Fraction(fps)
    base = c["root"]

    formati, risorse, asset_id = {}, [], {}
    prossimo = [1]

    def nuovo_id():
        prossimo[0] += 1
        return f"r{prossimo[0]}"

    def formato(w, h, f):
        k = (w, h, f)
        if k not in formati:
            fid = nuovo_id()
            fd = 1 / Fraction(f)
            formati[k] = fid
            risorse.append(f'<format id="{fid}" frameDuration="{fd.numerator}/{fd.denominator}s" width="{w}" height="{h}"/>')
        return formati[k]

    seq_fmt = "r1"
    fd = 1 / fr
    risorse.append(f'<format id="r1" name="Sequenza {W}x{H}" frameDuration="{fd.numerator}/{fd.denominator}s" width="{W}" height="{H}" colorSpace="1-1-1 (Rec. 709)"/>')

    def asset(percorso):
        percorso = str(Path(percorso).resolve())
        if percorso in asset_id:
            return asset_id[percorso]
        if not Path(percorso).exists():
            errore(f"non trovo {percorso}")
        pr = ffprobe(percorso)
        v, au = flusso_video(pr), flusso_audio(pr)
        dur = float(pr["format"].get("duration", 0) or 0)
        aid = nuovo_id()
        attr = [f'id="{aid}"', f"name={quoteattr(Path(percorso).name)}", 'start="0s"', f'duration="{T(dur)}"']
        if v:
            w, h = int(v["width"]), int(v["height"])
            for sd in v.get("side_data_list", []) or []:
                if abs(int(sd.get("rotation", 0))) in (90, 270):
                    w, h = h, w
            attr += ['hasVideo="1"', f'format="{formato(w, h, fps_nominale(v))}"']
        if au:
            attr += ['hasAudio="1"', 'audioSources="1"', f'audioChannels="{au.get("channels", 2)}"', f'audioRate="{au.get("sample_rate", 48000)}"']
        risorse.append(f"<asset {' '.join(attr)}><media-rep kind=\"original-media\" src={quoteattr(url_file(percorso))}/></asset>")
        asset_id[percorso] = (aid, dur, bool(v), bool(au))
        return asset_id[percorso]

    # Spine: un asset-clip per segmento (le transizioni diventano tagli netti + marcatore).
    spine, segclip = [], []
    t = 0.0
    for pz in pezzi:
        if pz["tipo"] != "segmento":
            continue
        seg = pz["seg"]
        src = analisi[seg["sorgente"]]
        aid, _, _, _ = asset(src["file"])
        inizio_t = mappa[seg["id"]][0]
        dur_src = seg["fine"] - seg["inizio"]
        marcatori = []
        v = seg.get("velocita", 1)
        if v != 1:
            marcatori.append(f"Velocità {v}x (in DaVinci: Retime > {int(v * 100)}%)")
        if seg.get("zoom"):
            z = seg["zoom"]
            marcatori.append(f"Zoom {z.get('tipo', 'scatto')} da {z.get('da', 1)} a {z.get('a')} dopo {z.get('inizio', 0)} s"
                             + (f" in {z.get('durata')} s" if z.get("durata") else ""))
        if seg.get("tremolio"):
            marcatori.append(f"Tremolio di camera intensità {seg['tremolio'].get('intensita')}")
        if seg.get("transizione"):
            tr = seg["transizione"]
            marcatori.append(f"Transizione in entrata: {tr.get('tipo', 'dissolvenza')} {tr.get('durata', 0.4)} s")
        if piano.get("riinquadratura", {}).get(str(seg["sorgente"])):
            marcatori.append("Riinquadratura che segue il soggetto: usa la posizione X (o Smart Reframe) per seguire il soggetto")
        # Con velocità diverse da 1 la durata sulla timeline cambia: si lascia la durata della ripresa e il marcatore.
        d_t = dur_src
        clip = {"aid": aid, "offset": t, "start": seg["inizio"], "dur": d_t, "nome": f"Segmento {seg['id']}", "marcatori": marcatori,
                "figli": [], "t_mappa": inizio_t}
        spine.append(clip)
        segclip.append(clip)
        t += d_t
    totale = t

    def clip_a(tt):
        for cl in spine:
            if cl["offset"] <= tt < cl["offset"] + cl["dur"]:
                return cl
        return spine[-1]

    # Il piano usa la timeline montata (con transizioni e velocità); qui le transizioni sono tagli netti,
    # quindi il tempo va riportato: si cerca il segmento che contiene il tempo e si mantiene la distanza.
    def riporta(tt):
        for cl, pz in zip(segclip, [p for p in pezzi if p["tipo"] == "segmento"]):
            t0 = pz["inizio_t"]
            if t0 <= tt < t0 + pz["durata"] + 1e-6:
                return cl["offset"] + (tt - cl["t_mappa"]) * pz["velocita"]
        return min(tt, totale)

    def collega(percorso, tt, dur, corsia, extra=""):
        aid, durf, _, _ = asset(percorso)
        pos = riporta(tt)
        cl = clip_a(pos)
        off_locale = cl["start"] + (pos - cl["offset"])
        cl["figli"].append(f'<asset-clip ref="{aid}" lane="{corsia}" offset="{T(off_locale)}" start="0s" duration="{T(dur)}" '
                           f'name={quoteattr(Path(percorso).name)}>{extra}</asset-clip>')

    for k, o in enumerate(sorted(piano.get("sovrapposizioni") or [], key=lambda x: x.get("livello", 0))):
        f = (base / o["file"]) if not Path(o["file"]).is_absolute() else Path(o["file"])
        _, durf, _, _ = asset(f)
        fine = o.get("fine") or (o["inizio"] + durf)
        extra = ""
        if o.get("modo") == "riquadro":
            x, y, w, h = o["riquadro"]
            # posizione FCPXML: centro rispetto al centro, in percentuale dell'altezza
            px = ((x + w / 2) - 0.5) * W / H * 100
            py = (0.5 - (y + h / 2)) * 100
            extra = f'<adjust-transform position="{px:.2f} {py:.2f}" scale="{w:.3f} {w:.3f}"/>'
        collega(f, o["inizio"], max(0.04, fine - o["inizio"]), 1 + int(o.get("livello", 0)), extra)
    audio = piano.get("audio") or {}
    for m in audio.get("musica") or []:
        f = (base / m["file"]) if not Path(m["file"]).is_absolute() else Path(m["file"])
        _, durf, _, _ = asset(f)
        fine = m.get("fine") or durata
        collega(f, m.get("inizio", 0), min(durf, fine - m.get("inizio", 0)), -1,
                f'<adjust-volume amount="{float(m.get("volume_db", -18)):.1f}dB"/>')
    for e in audio.get("effetti") or []:
        f = (base / e["file"]) if not Path(e["file"]).is_absolute() else Path(e["file"])
        _, durf, _, _ = asset(f)
        collega(f, e["inizio"], durf, -2, f'<adjust-volume amount="{float(e.get("volume_db", -6)):.1f}dB"/>')

    righe = []
    for cl in spine:
        interno = "".join(f'<marker start="{T(cl["start"])}" duration="{T(1 / float(fr))}" value={quoteattr(mk)}/>' for mk in cl["marcatori"])
        interno += "".join(cl["figli"])
        righe.append(f'<asset-clip ref="{cl["aid"]}" offset="{T(cl["offset"])}" start="{T(cl["start"])}" duration="{T(cl["dur"])}" '
                     f'name={quoteattr(cl["nome"])} format="{seq_fmt}" tcFormat="NDF">{interno}</asset-clip>')
    titolo = f"{a.progetto}-{nome}-{vdir.name}"
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.9">\n<resources>\n' + "\n".join(risorse) +
           f'\n</resources>\n<library>\n<event name={quoteattr(a.progetto)}>\n<project name={quoteattr(titolo)}>\n'
           f'<sequence format="{seq_fmt}" duration="{T(totale)}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">\n<spine>\n'
           + "\n".join(righe) + "\n</spine>\n</sequence>\n</project>\n</event>\n</library>\n</fcpxml>\n")
    out = vdir / "davinci"
    out.mkdir(exist_ok=True)
    (out / f"{titolo}.fcpxml").write_text(xml, encoding="utf-8")
    if P["srt"].exists():
        shutil.copy2(P["srt"], out / "sottotitoli.srt")
    note = []
    if any(p["tipo"] == "transizione" for p in pezzi):
        note.append("- Le transizioni sono tagli netti con un marcatore: aggiungile da Effects > Video Transitions.")
    if any(s.get("velocita", 1) != 1 for s in piano["segmenti"]):
        note.append("- I cambi di velocità sono indicati dai marcatori (Retime): applicali al clip e la timeline si sposta di conseguenza.")
    if piano.get("colore"):
        note.append(f"- Look colore del montaggio: {escape(str(piano['colore']))} (rifallo nella pagina Color o applica la LUT).")
    if any(s["hdr"]["hdr"] for s in analisi.values()):
        note.append("- Le riprese sono HDR: in Project Settings > Color Management usa DaVinci YRGB Color Managed con uscita Rec.709 "
                    "Gamma 2.4, oppure converti con una trasformazione HLG/PQ -> Rec.709 nella pagina Color.")
    (out / "LEGGIMI.txt").write_text(
        f"Progetto DaVinci Resolve per {titolo}\n\n"
        "1. DaVinci Resolve > File > Import > Timeline... e scegli il file .fcpxml di questa cartella.\n"
        "   Le riprese originali sono collegate dal loro percorso: se le hai spostate, usa Relink Media.\n"
        "2. File > Import > Subtitle... e scegli sottotitoli.srt, poi trascinalo sulla traccia dei sottotitoli.\n"
        "3. Le grafiche e i B-roll sono sulle tracce video superiori, la musica e gli effetti sulle tracce audio.\n"
        "4. I marcatori sui clip dicono cosa rifare a mano (velocità, zoom, transizioni, riinquadratura).\n"
        "5. Esporta da DaVinci: parte dagli originali, quindi una sola codifica.\n\n" + "\n".join(note) + "\n", encoding="utf-8")
    info(f"Progetto DaVinci: {out / (titolo + '.fcpxml')} ({len(spine)} segmenti, {len(asset_id)} file collegati)")


if __name__ == "__main__":
    main()
