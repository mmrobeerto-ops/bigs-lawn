"""Posts cuadrados de antes/después (1080x1080) con las fotos nuevas.  python generar_antes_despues.py CARPETA"""
import pathlib, sys, importlib.util
spec = importlib.util.spec_from_file_location("base", pathlib.Path(__file__).with_name("generar_piezas.py"))
base = importlib.util.module_from_spec(spec)
out = pathlib.Path(sys.argv[1]); sys.argv = [sys.argv[0], str(out / "_base")]
spec.loader.exec_module(base)
base.pieces.clear()
POSTS = [("mulch2-front-before.jpg", "mulch2-front-after.jpg", "Bark dust <span class=y>makeover</span>", "Front beds cleaned up and finished · Salem &amp; Keizer", "10-ad-bark-dust-frente"),
         ("job3-fence-leaves-before.jpg", "job3-fence-leaves-after.jpg", "Leaves gone. <span class=y>Beds fresh.</span>", "Fall cleanup + new mulch in one visit", "11-ad-hojas-cerca"),
         ("mulch2-fence-before.jpg", "mulch2-fence-after.jpg", "Weedy bed? <span class=y>Fixed.</span>", "Free estimates · Fully insured · 5-star Google reviews", "12-ad-cama-cerca"),
         ("job3-deck-bed-before.jpg", "job3-deck-bed-after.jpg", "Backyard <span class=y>refresh</span>", "Call, text or WhatsApp for a free quote", "13-ad-patio-deck")]
for args in POSTS:
    base.before_after(*args)
for name, (w, h, body) in base.pieces.items():
    (out / f"{name}.html").write_text(base.page(w, h, body), encoding="utf-8")
print("\n".join(base.pieces))
