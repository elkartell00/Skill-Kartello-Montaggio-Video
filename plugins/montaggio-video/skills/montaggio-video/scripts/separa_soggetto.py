"""Separa un soggetto (persona, prodotto, mano) dallo sfondo, in locale con SAM 2.1 (Meta). Da object-separation (MIT).

uso:
  python separa_soggetto.py prepara                                         # installa (circa 2 GB, chiedi prima)
  python separa_soggetto.py griglia --progetto nome --ripresa 0 --tempo 12.3
  python separa_soggetto.py separa --progetto nome --ripresa 0 --da 12.3 --a 18.0 --punti "480,270,1;100,60,0"
                                   [--prova] [--ritaglio]

Passi:
1. griglia: salva il fotogramma con una griglia di coordinate (larghezza di lavoro 960 px). Guardalo e
   scegli 2-3 punti sul soggetto (etichetta 1) e punti su ciò che va escluso (etichetta 0: dita che
   tengono il prodotto, confezione, tavolo).
2. separa --prova: prova su circa 20 fotogrammi, controlla il verde, poi rilancia senza --prova.
3. Risultati in .lavoro/<progetto>/separazione/<ripresa>-<da>/:
     maschere/NNNNN.png   una maschera per fotogramma (bianco = soggetto), numerate come i fotogrammi
                          della ripresa: le usa riinquadra.py --metodo maschere
     verifica.mp4         il video con il soggetto evidenziato in verde, con l'audio originale
     ritaglio.mov         (con --ritaglio) solo il soggetto su sfondo trasparente, a piena risoluzione e
                          già convertito in SDR: messo sopra a una scritta crea l'effetto "testo dietro al soggetto"

Modello scelto in base al computer: Apple Silicon -> base-plus (323 MB), NVIDIA 12 GB+ -> large (898 MB),
solo CPU -> tiny (156 MB, lento: circa 5 s per fotogramma). Si scarica al primo uso e resta in
~/.cache/huggingface. Le maschere hanno bordi netti: ottime su oggetti e mani, meno sui capelli.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import (DECODIFICA_HW, cartella_lavoro, cartelle_progetto, errore, filtro_sdr, info,  # noqa: E402
                    leggi_json)

W = 960  # larghezza di lavoro: SAM 2 ridimensiona comunque a 1024, una larghezza minore NON è più veloce


def prepara():
    root = cartella_lavoro()
    venv = root / ".strumenti" / "venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        errore("manca l'ambiente Python della skill: esegui prima verifica_strumenti.py --installa")
    info("Installo PyTorch e transformers per la separazione (circa 2 GB) ...")
    r = subprocess.run([str(py), "-m", "pip", "install", "torch", "transformers", "opencv-python-headless<5", "pillow", "numpy"])
    if r.returncode != 0:
        errore("installazione non riuscita. Controlla la connessione e riprova.")
    info("Pronto. Il modello si scarica al primo utilizzo.")


def sorgente(c, indice):
    an = leggi_json(c["lavoro"] / "analisi.json")
    for s in an["sorgenti"]:
        if s["indice"] == indice:
            return s
    errore(f"nessuna ripresa con indice {indice}.")


def leggi_fotogrammi(src, a, b, fps):
    """Fotogrammi a..b (numeri di fotogramma della ripresa), RGB, larghezza 960, già in SDR."""
    import numpy as np
    h = int(round(W * src["altezza"] / src["larghezza"] / 2) * 2)
    vf = ",".join(x for x in [f"fps={fps}", f"scale={W}:{h}", filtro_sdr(src["hdr"], "mobius"), "format=rgb24"] if x)
    from fractions import Fraction
    F = float(Fraction(fps))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", *DECODIFICA_HW, "-ss", f"{a / F:.4f}", "-i", src["file"], "-vf", vf,
                          "-frames:v", str(b - a + 1), "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (W * h * 3)
    return list(np.frombuffer(raw[: n * W * h * 3], np.uint8).reshape(n, h, W, 3))


def griglia(c, src, tempo, out):
    import cv2
    from fractions import Fraction
    f = int(round(tempo * float(Fraction(src["fps"]))))
    im = cv2.cvtColor(leggi_fotogrammi(src, f, f, src["fps"])[0], cv2.COLOR_RGB2BGR)
    for x in range(0, im.shape[1], 80):
        cv2.line(im, (x, 0), (x, im.shape[0]), (0, 255, 255), 1)
        cv2.putText(im, str(x), (x + 2, 12), 0, 0.4, (0, 255, 255), 1)
    for y in range(0, im.shape[0], 60):
        cv2.line(im, (0, y), (im.shape[1], y), (0, 255, 255), 1)
        cv2.putText(im, str(y), (2, y - 2), 0, 0.4, (0, 255, 255), 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), im)
    info(f"Griglia salvata: {out} (fotogramma {f}, coordinate in pixel su larghezza {W})")


def modello():
    import platform
    import torch
    from transformers import Sam2VideoModel, Sam2VideoProcessor
    info(f"Sistema: {platform.system()} {platform.machine()}")
    if torch.cuda.is_available():
        gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        dev, nome = "cuda", "facebook/sam2.1-hiera-" + ("large" if gb >= 12 else "base-plus")
        info(f"Scheda video: {torch.cuda.get_device_name(0)} {gb:.0f} GB")
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        dev, nome = "mps", "facebook/sam2.1-hiera-base-plus"
    else:
        dev, nome = "cpu", "facebook/sam2.1-hiera-tiny"
    info(f"Uso {dev} con il modello {nome} (si scarica al primo utilizzo)")
    m = Sam2VideoModel.from_pretrained(nome).to(dev).eval()
    p = Sam2VideoProcessor.from_pretrained(nome)
    return m, p, dev


def separa_blocco(m, proc, dev, frames, punti=None, etichette=None, maschera=None):
    import numpy as np
    import torch
    H = frames[0].shape[0]
    s = proc.init_video_session(video=frames, inference_device=dev, video_storage_device="cpu",
                                inference_state_device="cpu", dtype=torch.float32)
    if maschera is None:
        proc.add_inputs_to_inference_session(inference_session=s, frame_idx=0, obj_ids=1,
                                             input_points=[[punti]], input_labels=[[etichette]])
    else:
        proc.add_inputs_to_inference_session(inference_session=s, frame_idx=0, obj_ids=1, input_masks=maschera.astype(np.uint8))
    res = {}
    with torch.inference_mode():
        m(inference_session=s, frame_idx=0)
        for o in m.propagate_in_video_iterator(s, start_frame_idx=0):
            mk = proc.post_process_masks([o.pred_masks], original_sizes=[[H, W]], binarize=True)[0]
            res[o.frame_idx] = mk.squeeze().cpu().numpy().astype(bool)
    return res


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "prepara":
        return prepara()
    ap = argparse.ArgumentParser(description="Separazione del soggetto con SAM 2.1")
    ap.add_argument("azione", choices=["griglia", "separa"])
    ap.add_argument("--progetto", required=True)
    ap.add_argument("--cartella")
    ap.add_argument("--ripresa", type=int, default=0)
    ap.add_argument("--tempo", type=float, help="griglia: tempo del fotogramma (s)")
    ap.add_argument("--da", type=float)
    ap.add_argument("--a", type=float)
    ap.add_argument("--punti", help="x,y,etichetta separati da ';' (coordinate sulla griglia larga 960)")
    ap.add_argument("--prova", action="store_true", help="solo circa 20 fotogrammi")
    ap.add_argument("--ritaglio", action="store_true", help="crea anche ritaglio.mov trasparente a piena risoluzione")
    a = ap.parse_args()
    try:
        import cv2
        import numpy as np
    except ImportError:
        errore("mancano le librerie: esegui separa_soggetto.py prepara (chiedi prima all'utente).")

    c = cartelle_progetto(a.progetto, a.cartella)
    src = sorgente(c, a.ripresa)
    from fractions import Fraction
    F = float(Fraction(src["fps"]))
    if a.azione == "griglia":
        if a.tempo is None:
            errore("indica --tempo")
        return griglia(c, src, a.tempo, c["lavoro"] / "separazione" / f"griglia-{a.ripresa:02d}-{a.tempo:.1f}.jpg")

    if a.da is None or a.a is None or not a.punti:
        errore("servono --da, --a e --punti")
    try:
        pts = [[float(x) for x in p.split(",")] for p in a.punti.split(";")]
        PTS, LBL = [[p[0], p[1]] for p in pts], [int(p[2]) for p in pts]
    except (ValueError, IndexError):
        errore("--punti va scritto così: \"480,270,1;100,60,0\"")
    inizio, fine = int(round(a.da * F)), int(round(a.a * F))
    if a.prova:
        fine = min(fine, inizio + 19)
    cart = c["lavoro"] / "separazione" / f"{a.ripresa:02d}-{a.da:.1f}"
    (cart / "maschere").mkdir(parents=True, exist_ok=True)

    m, proc, dev = modello()
    maschere, k, seme = {}, inizio, None
    while k <= fine:  # blocchi da 60 fotogrammi: la memoria resta bassa; ogni blocco parte dall'ultima maschera
        b = min(fine, k + 60)
        fr = leggi_fotogrammi(src, k, b, src["fps"])
        if not fr:
            break
        r = separa_blocco(m, proc, dev, fr, PTS, LBL) if seme is None else separa_blocco(m, proc, dev, fr, maschera=seme)
        for j, mk in r.items():
            maschere[k + j] = mk
        seme = r[len(fr) - 1]
        info(f"  fotogrammi {k}-{k + len(fr) - 1} fatti")
        if b == fine:
            break
        k = b
    for f, mk in maschere.items():
        cv2.imwrite(str(cart / "maschere" / f"{f:05d}.png"), mk.astype(np.uint8) * 255)

    # Verifica in verde, con l'audio originale.
    fr = leggi_fotogrammi(src, inizio, fine, src["fps"])
    h = fr[0].shape[0]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{h}", "-r", src["fps"], "-i", "-",
                           "-ss", f"{inizio / F:.4f}", "-t", f"{(fine - inizio + 1) / F:.4f}", "-i", src["file"],
                           "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                           str(cart / "verifica.mp4")], stdin=subprocess.PIPE)
    col = np.array([57, 255, 20], np.float32)  # verde (RGB)
    for j, img in enumerate(fr):
        mk = maschere.get(inizio + j)
        im = img.astype(np.float32)
        if mk is not None:
            mm = cv2.GaussianBlur(mk.astype(np.float32), (5, 5), 0)
            bordo = cv2.morphologyEx((mm > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((7, 7), np.uint8)).astype(np.float32)
            alone = np.clip(cv2.GaussianBlur(bordo, (37, 37), 0) * 2.5, 0, 1)[..., None]
            im = im * (1 - mm[..., None] * 0.35) + col * mm[..., None] * 0.35 + col * alone * 0.9
            im = im * (1 - bordo[..., None]) + np.array([200, 255, 220], np.float32) * bordo[..., None]
        ff.stdin.write(np.clip(im, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()
    info(f"Verifica: {cart / 'verifica.mp4'} (soggetto in verde). Maschere: {cart / 'maschere'}")
    info("Controlla l'inizio, la metà e i momenti in cui qualcosa passa davanti. Se il verde esce dal soggetto "
         "aggiungi un punto con etichetta 0 lì; se manca un pezzo, un punto con etichetta 1.")

    if a.ritaglio and not a.prova:
        # Soggetto a piena risoluzione su sfondo trasparente (maschera ingrandita e sfumata ai bordi).
        mdir = cart / "maschere"
        sdr = filtro_sdr(src["hdr"], "mobius")
        fc = (f"[0:v]fps={src['fps']}{',' + sdr if sdr else ''},format=yuv444p,trim=end_frame={fine - inizio + 1}[v];"
              f"[1:v]scale={src['larghezza']}:{src['altezza']}:flags=bicubic,gblur=sigma=1.5,format=gray,trim=end_frame={fine - inizio + 1}[m];"
              f"[v][m]alphamerge,format=yuva444p10le[o]")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *DECODIFICA_HW, "-ss", f"{inizio / F:.4f}", "-i", src["file"],
                        "-framerate", src["fps"], "-start_number", str(inizio), "-i", str(mdir / "%05d.png"),
                        "-filter_complex", fc, "-map", "[o]", "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le",
                        "-vendor", "apl0", str(cart / "ritaglio.mov")], check=True)
        info(f"Ritaglio trasparente: {cart / 'ritaglio.mov'}")


if __name__ == "__main__":
    main()
