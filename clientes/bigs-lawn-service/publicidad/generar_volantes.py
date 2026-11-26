"""Volantes de BIG'S para imprimir (PNG a 300 dpi + PDF al tamaño exacto).

    python generar_volantes.py CARPETA_SALIDA      # luego: node render.js CARPETA_SALIDA && python generar_volantes.py --pdf CARPETA_SALIDA

Cada pieza lleva su propio QR con utm_source distinto, así el panel cuenta cuántos clientes trae cada una.
"""
import base64
import io
import pathlib
import sys

import qrcode

F = pathlib.Path(__file__).resolve().parent.parent
PHONE = "(971) 388-0768"
DPI = 300

# nombre: (ancho_pulgadas, alto_pulgadas)
SIZES = {"07-door-hanger": (4.25, 11), "08-volante-otono-media-carta": (5.5, 8.5), "09-volante-espanol-carta": (8.5, 11)}


def b64(p, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def qr(url):
    img = qrcode.make(url, border=1, box_size=14, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


PH = lambda n: b64(F / "fotos" / n)
LOGO = b64(F / "logo.png", "image/png")

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Inter:wght@500;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}body{font-family:Inter,sans-serif}
.c{position:relative;overflow:hidden;background:#123d24;color:#fff}
.bc{font-family:"Barlow Condensed",sans-serif;text-transform:uppercase;line-height:.92;font-weight:900}
.y{color:#f4c430}.ck::before{content:"✓";color:#f4c430;font-weight:900;margin-right:.45em}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;background:#fff}
.pair .ph{position:relative;background-size:cover;background-position:center}
.tag{position:absolute;top:26px;left:26px;font:800 40px Inter;letter-spacing:.06em;padding:10px 26px;border-radius:99px}
.tb{background:#111a14;color:#fff}.ta{background:#f4c430;color:#2a2200}
.qrbox{background:#fff;border-radius:30px;padding:26px;text-align:center;color:#123d24}
.qrbox img{width:100%;display:block}
.bar{background:#f4c430;color:#1a1600;text-align:center}
</style>"""


def page(w, h, body):
    return f"<!doctype html><html><head><meta charset=utf-8>{CSS}</head><body><div class=c style='width:{w}px;height:{h}px'>{body}</div></body></html>"


def px(name):
    w, h = SIZES[name]
    return int(w * DPI), int(h * DPI)


pieces = {}

# ---- Door hanger 4.25 x 11 in: hueco para la manija arriba
w, h = px("07-door-hanger")
pieces["07-door-hanger"] = page(w, h, f"""
<div style="background:#fff;height:620px;position:relative">
  <div style="position:absolute;left:50%;top:110px;width:380px;height:380px;margin-left:-190px;border-radius:50%;border:6px dashed #c9c9c9"></div>
  <div style="position:absolute;left:50%;top:0;width:6px;height:110px;margin-left:-3px;border-left:6px dashed #c9c9c9"></div></div>
<div style="background:#fff;text-align:center;padding:10px 0 50px"><img src="{LOGO}" style="height:330px"></div>
<div style="padding:70px 80px 0">
  <div style="font:800 52px Inter;letter-spacing:.14em" class=y>HELLO NEIGHBOR!</div>
  <div class=bc style="font-size:150px;margin:24px 0 30px">We just worked<br>on your <span class=y>street.</span></div>
  <div style="font:600 50px/1.35 Inter;opacity:.95">Want your yard looking this sharp too? Ask about our neighbor discount.</div>
  <div style="display:grid;gap:22px;font:700 54px Inter;margin-top:56px">
    <div class=ck>Lawn mowing &amp; edging</div><div class=ck>Leaf &amp; yard cleanup</div><div class=ck>Hedge &amp; shrub pruning</div>
    <div class=ck>Bark dust &amp; mulch</div><div class=ck>Gutter cleaning</div></div></div>
<div style="position:absolute;left:80px;right:80px;bottom:520px;display:grid;grid-template-columns:1fr 520px;gap:50px;align-items:center">
  <div><div style="font:800 60px/1.25 Inter">Free estimates<br>Fully insured<br><span class=y>★★★★★</span> on Google</div></div>
  <div class=qrbox><img src="{qr('https://bigslawn.com/?utm_source=doorhanger&utm_medium=print')}"><div style="font:800 40px Inter;margin-top:16px">Scan for a free quote</div></div></div>
<div class=bar style="position:absolute;left:0;right:0;bottom:0;height:440px;padding-top:70px">
  <div class=bc style="font-size:170px">{PHONE}</div>
  <div style="font:800 58px Inter;margin-top:20px">Call · Text · WhatsApp</div><div style="font:800 58px Inter">bigslawn.com</div></div>""")

# ---- Volante de otoño 5.5 x 8.5 in
w, h = px("08-volante-otono-media-carta")
pieces["08-volante-otono-media-carta"] = page(w, h, f"""
<div style="position:absolute;inset:0;background:url('{PH('cleanup-trailer-haul.jpg')}') center/cover"></div>
<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(9,32,18,.5) 0%,rgba(9,32,18,.2) 22%,rgba(9,32,18,.9) 45%,rgba(9,32,18,.97) 100%)"></div>
<div style="position:absolute;top:70px;left:0;right:0;text-align:center"><div style="display:inline-block;background:#fff;border-radius:34px;padding:22px 40px"><img src="{LOGO}" style="height:230px;display:block"></div></div>
<div style="position:absolute;left:90px;right:90px;top:1000px">
  <div style="font:800 56px Inter;letter-spacing:.14em" class=y>FALL CLEANUP · SALEM &amp; KEIZER</div>
  <div class=bc style="font-size:210px;margin:20px 0 40px">Leaves gone<br><span class=y>before the rain.</span></div>
  <div style="display:grid;gap:22px;font:700 58px Inter;max-width:930px">
    <div class=ck>Leaves, needles &amp; branches</div><div class=ck>Beds &amp; walkways cleaned</div><div class=ck>Gutters cleared</div><div class=ck>Everything hauled away</div></div></div>
<div style="position:absolute;left:90px;right:90px;bottom:440px;display:grid;grid-template-columns:1fr 480px;gap:60px;align-items:end">
  <div style="font:800 66px/1.25 Inter">Spots fill fast.<br><span class=y>Book yours today.</span></div>
  <div class=qrbox><img src="{qr('https://bigslawn.com/services/leaf-cleanup/?utm_source=flyer-fall&utm_medium=print')}"><div style="font:800 42px Inter;margin-top:16px">Free quote</div></div></div>
<div class=bar style="position:absolute;left:0;right:0;bottom:0;height:380px;padding-top:60px">
  <div class=bc style="font-size:180px">{PHONE}</div><div style="font:800 60px Inter;margin-top:14px">bigslawn.com · Call · Text · WhatsApp</div></div>""")

# ---- Volante en español, carta 8.5 x 11 in
w, h = px("09-volante-espanol-carta")
pieces["09-volante-espanol-carta"] = page(w, h, f"""
<div style="background:#fff;height:620px;display:flex;align-items:center;justify-content:center"><img src="{LOGO}" style="height:470px"></div>
<div class=pair style="height:1000px">
  <div class=ph style="background-image:url('{PH('front-bed-before.jpg')}')"><span class="tag tb" style="font-size:64px">ANTES</span></div>
  <div class=ph style="background-image:url('{PH('front-yard-after.jpg')}')"><span class="tag ta" style="font-size:64px">DESPUÉS</span></div></div>
<div style="padding:70px 120px 0;display:grid;grid-template-columns:1fr 640px;gap:70px">
  <div><div class=bc style="font-size:165px">Jardines bonitos,<br><span class=y>paisajes sanos.</span></div>
    <div style="display:grid;gap:18px;font:700 60px Inter;margin-top:40px">
      <div class=ck>Corte y mantenimiento de césped</div><div class=ck>Limpieza de patios y hojas</div>
      <div class=ck>Poda de arbustos y árboles</div><div class=ck>Corteza (bark dust) y mulch</div>
      <div class=ck>Cotización gratis</div><div class=ck>Hablamos español</div></div></div>
  <div class=qrbox style="align-self:center"><img src="{qr('https://bigslawn.com/?lang=es&utm_source=volante-es&utm_medium=print')}"><div style="font:800 56px Inter;margin-top:20px">Escanee para cotizar gratis</div></div></div>
<div class=bar style="position:absolute;left:0;right:0;bottom:0;height:460px;padding-top:60px">
  <div class=bc style="font-size:240px">{PHONE}</div><div style="font:800 80px Inter;margin-top:20px">bigslawn.com · Llamada · Mensaje · WhatsApp</div></div>""")


def to_pdf(folder):
    from PIL import Image
    for name in SIZES:
        img = Image.open(folder / f"{name}.png").convert("RGB")
        img.save(folder / f"{name}.pdf", resolution=DPI)
        print("PDF", name, SIZES[name], "in")


if __name__ == "__main__":
    if sys.argv[1] == "--pdf":
        to_pdf(pathlib.Path(sys.argv[2]))
    else:
        out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
        for name, html in pieces.items():
            (out / f"{name}.html").write_text(html, encoding="utf-8")
        print("\n".join(pieces))
