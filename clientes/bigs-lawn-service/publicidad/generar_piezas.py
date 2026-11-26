"""Genera piezas de publicidad de BIG'S (HTML -> PNG con Playwright)."""
import base64
import io
import pathlib
import sys

import qrcode

F = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)


def b64(p, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def qr(url):
    img = qrcode.make(url, border=1, box_size=12)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


PH = lambda n: b64(F / "fotos" / n)
LOGO = b64(F / "logo.png", "image/png")
PHONE = "(971) 388-0768"

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Inter:wght@500;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,sans-serif;background:#123d24}
.c{position:relative;overflow:hidden;background:#123d24;color:#fff}
.bc{font-family:"Barlow Condensed",sans-serif;text-transform:uppercase;line-height:.92;font-weight:900}
.y{color:#f4c430}
.logo{background:#fff;border-radius:22px;padding:14px 20px;display:inline-block;box-shadow:0 10px 30px rgba(0,0,0,.35)}
.logo img{display:block}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#fff}
.pair .ph{position:relative;background-size:cover;background-position:center}
.tag{position:absolute;top:22px;left:22px;font:800 30px Inter;letter-spacing:.06em;padding:8px 20px;border-radius:99px}
.tb{background:#111a14;color:#fff}.ta{background:#f4c430;color:#2a2200}
.bar{background:#f4c430;color:#1a1600;display:flex;align-items:center;justify-content:space-between;padding:0 54px}
.pill{display:inline-flex;align-items:center;gap:12px;background:rgba(255,255,255,.12);border:2px solid rgba(255,255,255,.3);border-radius:99px;padding:10px 24px;font:700 28px Inter}
.ck::before{content:"✓";color:#f4c430;font-weight:900;margin-right:12px}
.ov{position:absolute;inset:0;background-size:cover;background-position:center}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(9,32,18,.45) 0%,rgba(9,32,18,.1) 25%,rgba(9,32,18,.82) 42%,rgba(9,32,18,.95) 70%)}
</style>"""


def page(w, h, body):
    return f"<!doctype html><html><head><meta charset=utf-8>{CSS}</head><body><div class=c style='width:{w}px;height:{h}px'>{body}</div></body></html>"


pieces = {}

# 1 · Antes/después cuadrado (franja de banqueta)
def before_after(before, after, title, sub, name):
    pieces[name] = (1080, 1080, f"""
<div style="height:150px;display:flex;align-items:center;justify-content:space-between;padding:0 54px">
  <div class=logo><img src="{LOGO}" style="height:96px"></div>
  <div class="bc" style="font-size:64px;text-align:right">Before <span class=y>&amp;</span> After</div></div>
<div class=pair style="height:660px">
  <div class=ph style="background-image:url('{PH(before)}')"><span class="tag tb">BEFORE</span></div>
  <div class=ph style="background-image:url('{PH(after)}')"><span class="tag ta">AFTER</span></div></div>
<div style="padding:26px 54px 0;height:150px">
  <div class="bc" style="font-size:62px">{title}</div>
  <div style="font:600 28px Inter;opacity:.9;margin-top:8px">{sub}</div></div>
<div class=bar style="position:absolute;bottom:0;left:0;right:0;height:120px">
  <div class=bc style="font-size:66px">📞 {PHONE}</div><div style="font:800 34px Inter">bigslawn.com</div></div>""")


before_after("parking-strip-before.jpg", "parking-strip-after.jpg", "Overgrown strip? <span class=y>Gone.</span>",
             "Weeds pulled, edges clean, debris hauled away · Salem &amp; Keizer", "01-antes-despues-banqueta")
before_after("front-bed-before.jpg", "front-yard-after.jpg", "Yard cleanup <span class=y>in one visit</span>",
             "Free estimates · Fully insured · 5-star Google reviews", "02-antes-despues-frente")

# 3 · Historia vertical: limpieza de otoño
pieces["03-historia-otono"] = (1080, 1920, f"""
<div class=ov style="background-image:url('{PH('shrubs-and-lawn.jpg')}')"></div><div class=shade></div>
<div style="position:absolute;top:70px;left:0;right:0;text-align:center"><div class=logo><img src="{LOGO}" style="height:150px"></div></div>
<div style="position:absolute;left:64px;right:64px;bottom:150px">
  <div style="font:800 34px Inter;letter-spacing:.14em" class=y>FALL SEASON · SALEM, OR</div>
  <div class="bc" style="font-size:170px;margin:14px 0 26px">Leaf<br>cleanup<br><span class=y>time.</span></div>
  <div style="display:grid;gap:14px;font:700 38px Inter">
    <div class=ck>Leaves &amp; needles cleared</div><div class=ck>Beds &amp; walkways cleaned</div><div class=ck>Everything hauled away</div></div>
  <div style="margin-top:44px;background:#f4c430;color:#1a1600;border-radius:24px;padding:30px 36px">
    <div style="font:800 30px Inter">Book your spot · Free estimate</div>
    <div class=bc style="font-size:96px;margin-top:6px">{PHONE}</div>
    <div style="font:800 32px Inter">Call · Text · WhatsApp · bigslawn.com</div></div></div>""")

# 4 · Servicios (cuadrado)
pieces["04-servicios"] = (1080, 1080, f"""
<div class=ov style="background-image:url('{PH('hedge-line.jpg')}');background-position:center 30%"></div>
<div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(9,32,18,.95) 0%,rgba(9,32,18,.82) 55%,rgba(9,32,18,.25) 100%)"></div>
<div style="position:absolute;left:60px;top:60px;right:60px">
  <div class=logo><img src="{LOGO}" style="height:100px"></div>
  <div class="bc" style="font-size:96px;margin:40px 0 30px">Beautiful lawns,<br><span class=y>healthy landscapes.</span></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px 30px;font:700 34px Inter;max-width:820px">
    <div class=ck>Lawn maintenance</div><div class=ck>Yard cleanup</div><div class=ck>Leaf cleanup</div><div class=ck>Tree &amp; shrub pruning</div>
    <div class=ck>Mulch / bark dust</div><div class=ck>Gutter cleaning</div><div class=ck>Pressure washing</div><div class=ck>Landscaping</div></div>
  <div style="display:flex;gap:14px;margin-top:40px;flex-wrap:wrap"><span class=pill>⭐ 5-star on Google</span><span class=pill>Free estimates</span><span class=pill>Fully insured</span></div></div>
<div class=bar style="position:absolute;bottom:0;left:0;right:0;height:120px">
  <div class=bc style="font-size:66px">📞 {PHONE}</div><div style="font:800 34px Inter">bigslawn.com</div></div>""")

# 5 · Reseña (cuadrado)
pieces["05-resena"] = (1080, 1080, f"""
<div class=ov style="background-image:url('{PH('shrub-shaped.jpg')}')"></div>
<div style="position:absolute;inset:0;background:rgba(9,32,18,.78)"></div>
<div style="position:absolute;left:70px;right:70px;top:80px">
  <div style="font-size:70px;letter-spacing:8px;color:#f4c430">★★★★★</div>
  <div style="font:700 52px/1.32 Inter;margin-top:34px">“My lawn was very overgrown and out of control. My place has never looked this good. The price is more than fair.”</div>
  <div style="font:700 34px Inter;margin-top:30px" class=y>— Becky R., Google review</div></div>
<div style="position:absolute;left:70px;bottom:170px" class=logo><img src="{LOGO}" style="height:96px"></div>
<div class=bar style="position:absolute;bottom:0;left:0;right:0;height:120px">
  <div class=bc style="font-size:66px">📞 {PHONE}</div><div style="font:800 34px Inter">bigslawn.com</div></div>""")

# 6 · Volante tamaño carta con QR (para imprimir)
QR = qr("https://bigslawn.com/?utm_source=flyer&utm_medium=print")
pieces["06-volante-con-qr"] = (1275, 1650, f"""
<div style="background:#fff;height:260px;display:flex;align-items:center;justify-content:center"><img src="{LOGO}" style="height:200px"></div>
<div class=pair style="height:620px">
  <div class=ph style="background-image:url('{PH('parking-strip-before.jpg')}')"><span class="tag tb">BEFORE</span></div>
  <div class=ph style="background-image:url('{PH('parking-strip-after.jpg')}')"><span class="tag ta">AFTER</span></div></div>
<div style="padding:44px 70px 0;display:grid;grid-template-columns:1fr 330px;gap:40px;align-items:start">
  <div><div class=bc style="font-size:96px">Lawn care &amp; <span class=y>yard cleanup</span></div>
    <div style="display:grid;gap:12px;font:700 34px Inter;margin-top:26px"><div class=ck>Free estimates</div><div class=ck>Fully insured</div><div class=ck>5-star Google reviews</div><div class=ck>Hablamos español</div></div></div>
  <div style="background:#fff;border-radius:24px;padding:22px;text-align:center;color:#123d24">
    <img src="{QR}" style="width:100%;display:block"><div style="font:800 26px Inter;margin-top:10px">Scan for a free quote</div></div></div>
<div class=bar style="position:absolute;bottom:0;left:0;right:0;height:180px;flex-direction:column;justify-content:center;gap:6px">
  <div class=bc style="font-size:104px">{PHONE}</div><div style="font:800 38px Inter">bigslawn.com · Call · Text · WhatsApp</div></div>""")

for name, (w, h, body) in pieces.items():
    (OUT / f"{name}.html").write_text(page(w, h, body), encoding="utf-8")
print("\n".join(pieces))
