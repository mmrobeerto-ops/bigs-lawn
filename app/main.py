"""Website + admin for a lawn care and lot clearing business (English UI, USD pricing).

Arranque:  JARDIN_ADMIN_TOKEN=... uvicorn app.main:app --host 0.0.0.0 --port 8090
"""
import hashlib
import hmac
import html
import json
import math
import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .db import DEFAULT_SETTINGS, Database

STATIC = Path(__file__).parent / "static"
DB_PATH = os.getenv("JARDIN_DB_PATH", "jardineria.db")
UPLOAD_DIR = Path(os.getenv("JARDIN_UPLOAD_DIR", Path(__file__).parent.parent / "uploads"))
NOINDEX = os.getenv("JARDIN_NOINDEX", "") == "1"   # vista previa: no aparecer en Google
TZ = ZoneInfo(os.getenv("JARDIN_TZ", "America/Los_Angeles"))   # Salem, OR = hora del Pacífico

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXT = {".mp4", ".webm", ".mov"}
MAX_PHOTO = 10 * 1024 * 1024
MAX_VIDEO = int(os.getenv("JARDIN_MAX_VIDEO_MB", 150)) * 1024 * 1024
STATUSES = ("pending", "confirmed", "done", "cancelled")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
             "diciembre"]
CONTACT = {"text": "Text message", "call": "Phone call", "whatsapp": "WhatsApp", "email": "Email"}
EST_KEYS = ("est_sizes", "est_conditions", "est_frequencies")


MSG = {
    "en": {"quote_hi": "Hi {biz}! I'd like a free quote.", "request": "Request", "name": "Name", "city": "City", "needs": "Needs",
           "about_yard": "About the yard", "book_hi": "Hi {biz}! I'd like to book a service.", "booking": "Booking",
           "service": "Service", "not_sure": "Not sure yet", "day": "Day", "lot": "Lot", "addons": "Add-ons",
           "estimate": "Online estimate", "address": "Address", "details": "Details",
           "book_end": "Please confirm my appointment. Thank you!"},
    "es": {"quote_hi": "¡Hola {biz}! Quiero una cotización gratis.", "request": "Solicitud", "name": "Nombre", "city": "Ciudad",
           "needs": "Necesito", "about_yard": "Sobre el jardín", "book_hi": "¡Hola {biz}! Quiero agendar un servicio.",
           "booking": "Reserva", "service": "Servicio", "not_sure": "Aún no sé", "day": "Día", "lot": "Terreno",
           "addons": "Extras", "estimate": "Estimado en línea", "address": "Dirección", "details": "Detalles",
           "book_end": "Por favor confírmenme la cita. ¡Gracias!"},
}


def clean_source(s: str) -> str:
    return re.sub(r"[^\w .:/+|@-]", "", s or "", flags=re.UNICODE).strip()[:120] or "Direct"


def admin_token() -> str:
    return os.getenv("JARDIN_ADMIN_TOKEN", "")


# --- acceso al panel: usuario y contraseña (sesión en cookie). El token Bearer queda solo para scripts.
SESSION_COOKIE = "jardin_session"
SESSION_DAYS = 30


def admin_user() -> str:
    return os.getenv("JARDIN_ADMIN_USER", "admin").strip().lower()


def admin_password() -> str:
    return os.getenv("JARDIN_ADMIN_PASSWORD", "") or admin_token()


def session_secret() -> bytes:
    base = os.getenv("JARDIN_SESSION_SECRET", "") or (admin_token() + "|" + admin_password())
    return hashlib.sha256(("jardin-session|" + base).encode()).digest()


def make_session(user: str) -> str:
    exp = int(time.time()) + SESSION_DAYS * 86400
    msg = f"{user}.{exp}"
    return msg + "." + hmac.new(session_secret(), msg.encode(), hashlib.sha256).hexdigest()


def valid_session(value: str) -> bool:
    try:
        user, exp, sig = value.rsplit(".", 2)
        good = hmac.new(session_secret(), f"{user}.{exp}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, good) and int(exp) > time.time() and user == admin_user()
    except (ValueError, AttributeError):
        return False


def require_admin(request: Request, authorization: str = Header(default="")):
    if not admin_password():
        raise HTTPException(401, "Admin access is not configured")
    if valid_session(request.cookies.get(SESSION_COOKIE, "")):
        return
    tok = authorization.removeprefix("Bearer ").strip()
    if tok and admin_token() and hmac.compare_digest(tok, admin_token()):
        return
    raise HTTPException(401, "Please sign in")


def today() -> date:
    return datetime.now(TZ).date()


def fmt_date(d: str, lang: str = "en") -> str:
    x = date.fromisoformat(d)
    if lang == "es":
        return f"{DAYS_ES[x.weekday()]} {x.day} de {MONTHS_ES[x.month - 1]}"
    return f"{DAYS[x.weekday()]}, {MONTHS[x.month - 1]} {x.day}"


def money(cents: int | None, sym: str = "$") -> str:
    if cents is None:
        return ""
    return f"{sym}{cents / 100:,.0f}" if cents % 100 == 0 else f"{sym}{cents / 100:,.2f}"


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def us_number(s: str) -> str:
    """Normaliza a E.164 asumiendo EE. UU./PR si tiene 10 dígitos."""
    d = digits(s)
    return "1" + d if len(d) == 10 else d


def wa_link(number: str, text: str) -> str:
    d = us_number(number)
    return f"https://wa.me/{d}?text={quote(text)}" if d else ""


def sms_link(number: str, text: str = "") -> str:
    d = us_number(number)
    if not d:
        return ""
    return f"sms:+{d}" + (f"?&body={quote(text)}" if text else "")   # "?&body=" funciona en iPhone y Android


def tel_link(number: str) -> str:
    d = us_number(number)
    return f"tel:+{d}" if d else ""


def youtube_id(url: str) -> str | None:
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/))([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def round5(cents: float) -> int:
    return int(math.ceil(cents / 500) * 500)   # redondea hacia arriba a $5


def parse_est(s: dict) -> dict:
    return {k: json.loads(s[k]) for k in EST_KEYS}


def zips(s: dict) -> list[str]:
    return [z for z in re.split(r"[\s,;]+", s.get("zip_codes", "")) if z]


DETAIL_LISTS = {"good_fit": 10, "how": 6, "price_factors": 8, "faqs": 10}


def clean_details(d: dict) -> dict:
    """Contenido de la página de cada servicio. Listas de textos o de {title,text} / {q,a}."""
    out = {"eyebrow": str(d.get("eyebrow", ""))[:80], "video_url": str(d.get("video_url", ""))[:200]}
    out["good_fit"] = [str(x)[:200] for x in d.get("good_fit", []) if str(x).strip()][:10]
    for k in ("how", "price_factors"):
        out[k] = [{"title": str(x.get("title", ""))[:80], "text": str(x.get("text", ""))[:800]}
                  for x in d.get(k, []) if isinstance(x, dict) and str(x.get("title", "")).strip()][:DETAIL_LISTS[k]]
    out["faqs"] = [{"q": str(x.get("q", ""))[:200], "a": str(x.get("a", ""))[:1000]}
                   for x in d.get("faqs", []) if isinstance(x, dict) and str(x.get("q", "")).strip()][:10]
    return out


def parse_details(raw) -> dict:
    try:
        d = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        d = {}
    d = clean_details(d if isinstance(d, dict) else {})
    vid = youtube_id(d["video_url"]) if d["video_url"] else None
    d["video_embed"] = f"https://www.youtube-nocookie.com/embed/{vid}" if vid else ""
    return d


# ------------------------------------------------------------------ modelos
class EstimateIn(BaseModel):
    package_id: int
    size: int = Field(default=1, ge=0, le=20)
    condition: int = Field(default=0, ge=0, le=20)
    frequency: int | None = Field(default=None, ge=0, le=20)
    addon_ids: list[int] = Field(default_factory=list, max_length=20)


class BookingIn(EstimateIn):
    package_id: int | None = None
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    email: str = Field(default="", max_length=120)
    address: str = Field(min_length=4, max_length=200)
    zip: str = Field(default="", max_length=10)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    contact_pref: Literal["text", "call", "whatsapp", "email"] = "text"
    notes: str = Field(default="", max_length=600)
    lang: Literal["en", "es"] = "en"
    source: str = Field(default="", max_length=120)   # de dónde llegó el cliente (Facebook, Google, volante...)
    website: str = Field(default="", max_length=0)   # trampa anti-spam: los humanos la dejan vacía

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v):
        d = re.sub(r"[^\d+]", "", v)
        if len(digits(d)) < 7:
            raise ValueError("Invalid phone number")
        return d

    @field_validator("email")
    @classmethod
    def clean_email(cls, v):
        v = v.strip()
        if v and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Invalid email")
        return v


class PackageIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=300)
    price_cents: int = Field(default=0, ge=0, le=10_000_000)
    price_note: str = Field(default="", max_length=30)
    features: list[str] = Field(default_factory=list, max_length=12)
    highlight: bool = False
    recurring: bool = False
    details: dict = Field(default_factory=dict)
    active: bool = True
    sort: int = 0


class AddonIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    price_cents: int = Field(default=0, ge=0, le=10_000_000)
    unit_note: str = Field(default="", max_length=30)
    active: bool = True
    sort: int = 0


class TestimonialIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    location: str = Field(default="", max_length=60)
    text: str = Field(min_length=1, max_length=600)
    rating: int = Field(default=5, ge=1, le=5)
    active: bool = True
    sort: int = 0


class FaqIn(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=1000)
    active: bool = True
    sort: int = 0


class QuoteIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    email: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=60)
    services: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=1000)
    contact_pref: Literal["text", "call", "whatsapp", "email"] = "text"
    page: str = Field(default="", max_length=100)
    lang: Literal["en", "es"] = "en"
    source: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=0)   # trampa anti-spam

    _phone = field_validator("phone")(BookingIn.clean_phone.__func__)
    _email = field_validator("email")(BookingIn.clean_email.__func__)


class VisitIn(BaseModel):
    path: str = Field(default="/", max_length=120)
    source: str = Field(default="", max_length=120)
    new_visitor: bool = False
    mobile: bool = False


BOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|headless|lighthouse|monitor|curl|wget|python|httpx", re.I)


class LoginIn(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=200)


class QuotePatch(BaseModel):
    status: Literal["new", "contacted", "won", "lost"] | None = None
    admin_note: str | None = Field(default=None, max_length=600)


class BookingPatch(BaseModel):
    status: Literal["pending", "confirmed", "done", "cancelled"] | None = None
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    price_cents: int | None = Field(default=None, ge=0)
    admin_note: str | None = Field(default=None, max_length=600)


class DayIn(BaseModel):
    capacity: int = Field(ge=0, le=50)
    note: str = Field(default="", max_length=80)


class MediaPatch(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    caption: str | None = Field(default=None, max_length=200)
    package_id: int | None = None
    featured: bool | None = None


# Tablas simples con CRUD genérico: (tabla, modelo, campos JSON, campos booleanos)
SIMPLE = {
    "addons": ("addons", AddonIn, (), ("active",)),
    "testimonials": ("testimonials", TestimonialIn, (), ("active",)),
    "faqs": ("faqs", FaqIn, (), ("active",)),
}


# ------------------------------------------------------------------ app
def create_app(db_path: str | None = None, upload_dir: Path | None = None) -> FastAPI:
    db = Database(db_path or DB_PATH)
    uploads = Path(upload_dir or UPLOAD_DIR)
    uploads.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Lawn care · website and admin", version="2.0.0")
    app.state.db = db

    if NOINDEX:
        @app.middleware("http")
        async def noindex(request, call_next):
            resp = await call_next(request)
            resp.headers["X-Robots-Tag"] = "noindex, nofollow"
            return resp
    app.mount("/media", StaticFiles(directory=uploads), name="media")
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")
    hits: dict[str, deque] = defaultdict(deque)

    def rate_limit(request: Request, limit=6, window=3600):
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
        q, now = hits[ip], time.time()
        while q and q[0] < now - window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "Too many requests. Please call or text us.")
        q.append(now)

    def packages(active_only=True):
        rows = db.all("SELECT * FROM packages " + ("WHERE active=1 " if active_only else "") + "ORDER BY sort, id")
        for r in rows:
            r["features"] = json.loads(r["features"])
            r["details"] = parse_details(r.get("details"))
            for k in ("highlight", "recurring", "active"):
                r[k] = bool(r[k])
        return rows

    def simple_rows(table, active_only=True):
        rows = db.all(f"SELECT * FROM {table} " + ("WHERE active=1 " if active_only else "") + "ORDER BY sort, id")
        for r in rows:
            r["active"] = bool(r["active"])
        return rows

    def media_list():
        rows = db.all("SELECT * FROM media ORDER BY featured DESC, created DESC")
        for r in rows:
            r["url"] = f"/media/{r['src']}" if r["kind"] != "youtube" else f"https://www.youtube-nocookie.com/embed/{r['src']}"
            r["after_url"] = f"/media/{r['after_src']}" if r.get("after_src") else ""
            r["featured"] = bool(r["featured"])
        return rows

    # ---------------------------------------------------------- cotizador
    def estimate(s: dict, body: EstimateIn) -> dict:
        pkg = db.one("SELECT * FROM packages WHERE id=? AND active=1", (body.package_id,))
        if not pkg:
            raise HTTPException(400, "Package not available")
        est = parse_est(s)
        pick = lambda lst, i: lst[min(i, len(lst) - 1)] if lst else {"label": "", "mult": 1}
        size, cond = pick(est["est_sizes"], body.size), pick(est["est_conditions"], body.condition)
        freq = pick(est["est_frequencies"], body.frequency if body.frequency is not None else 0) if pkg["recurring"] else None
        ids = list(dict.fromkeys(body.addon_ids))
        addons = db.all(f"SELECT * FROM addons WHERE active=1 AND id IN ({','.join('?' * len(ids))})", ids) if ids else []
        addon_total = sum(a["price_cents"] for a in addons)
        out = {"package": pkg["name"], "size": size["label"], "condition": cond["label"],
               "frequency": freq["label"] if freq else "", "recurring": bool(pkg["recurring"]),
               "addons": [a["name"] for a in addons], "addons_cents": addon_total, "low": None, "high": None, "custom": False}
        if size["mult"] is None or not pkg["price_cents"]:
            out["custom"] = True
            return out
        base = pkg["price_cents"] * size["mult"] * cond["mult"] * (freq["mult"] if freq else 1)
        r = int(s.get("est_range_pct") or 15) / 100
        out["low"] = round5(base * (1 - r)) + addon_total
        out["high"] = round5(base * (1 + r)) + addon_total
        out["first_visit_note"] = "Add-ons are charged once, on the first visit." if addons and freq else ""
        return out

    def estimate_text(e: dict, sym="$", lang="en") -> str:
        if e["custom"]:
            return "Cotización a medida" if lang == "es" else "Custom quote"
        per = (" por visita" if lang == "es" else " per visit") if e["recurring"] else ""
        return f"{money(e['low'], sym)}–{money(e['high'], sym)}{per}"

    # ---------------------------------------------------------- calendario
    def day_info(s: dict, start: date, days: int) -> list[dict]:
        work = s["work_days"]
        cap_default = int(s["daily_capacity"])
        first = today() + timedelta(days=int(s["min_notice_days"]))
        last = today() + timedelta(days=int(s["horizon_days"]))
        end = start + timedelta(days=days)
        ov = {r["date"]: r for r in db.all("SELECT * FROM day_overrides WHERE date>=? AND date<?",
                                           (start.isoformat(), end.isoformat()))}
        used = {r["date"]: r["n"] for r in db.all(
            "SELECT date, COUNT(*) n FROM bookings WHERE status IN ('pending','confirmed') AND date>=? AND date<? GROUP BY date",
            (start.isoformat(), end.isoformat()))}
        out = []
        for i in range(days):
            d = start + timedelta(days=i)
            k = d.isoformat()
            cap = ov[k]["capacity"] if k in ov else (cap_default if str(d.weekday()) in work else 0)
            bookable = first <= d <= last
            remaining = max(0, cap - used.get(k, 0)) if bookable else 0
            out.append({"date": k, "capacity": cap, "booked": used.get(k, 0), "remaining": remaining,
                        "open": remaining > 0, "note": ov[k]["note"] if k in ov else "",
                        "reason": "" if remaining else ("Closed" if cap == 0 else "Fully booked" if bookable else "Unavailable")})
        return out

    # ---------------------------------------------------------- páginas
    def business_ld(s: dict) -> dict:
        """Datos estructurados para Google (búsquedas locales tipo "lawn care Salem OR")."""
        ld = {"@type": "LocalBusiness", "name": s["business_name"], "description": s["about"], "priceRange": "$$",
              "address": {"@type": "PostalAddress", "addressLocality": s["city"], "addressRegion": s["region"], "addressCountry": "US"},
              "areaServed": s["zone"]}
        if s["phone_display"]:
            ld["telephone"] = "+" + us_number(s["phone_display"])
        if s["email"]:
            ld["email"] = s["email"]
        same = [u for u in (s["facebook"], s["instagram"], s["google_review_url"]) if u]
        if same:
            ld["sameAs"] = same
        return ld

    def render(file: str, title: str, description: str, ld: dict) -> HTMLResponse:
        page = (STATIC / file).read_text(encoding="utf-8")
        for mark, part in (("<!--#SPRITE-->", "_sprite.html"), ("<!--#TOP-->", "_top.html"), ("<!--#BOTTOM-->", "_bottom.html")):
            page = page.replace(mark, (STATIC / part).read_text(encoding="utf-8").rstrip("\n"))
        page = page.replace("{{TITLE}}", html.escape(title)).replace("{{DESCRIPTION}}", html.escape(description))
        page = page.replace("{{JSONLD}}", json.dumps({"@context": "https://schema.org", **ld}, ensure_ascii=False).replace("</", "<\\/"))
        return HTMLResponse(page)

    def place(s: dict) -> str:
        return ", ".join(x for x in (s["city"], s["region"]) if x)

    @app.get("/", include_in_schema=False)
    def home():
        s = db.settings()
        title = f"{s['business_name']} · {s['seo_services']}" + (f" in {place(s)}" if place(s) else "")
        return render("index.html", title, f"{s['about']} {s['zone']}", business_ld(s))

    @app.get("/services", include_in_schema=False)
    @app.get("/services/", include_in_schema=False)
    def services_index():
        return RedirectResponse("/#services", status_code=301)

    @app.get("/services/{slug}", include_in_schema=False)
    @app.get("/services/{slug}/", include_in_schema=False)
    def service_page(slug: str):
        s = db.settings()
        p = db.one("SELECT * FROM packages WHERE slug=? AND active=1", (slug,))
        if not p:
            return RedirectResponse("/#services", status_code=302)
        where = f" in {place(s)}" if place(s) else ""
        ld = {"@type": "Service", "name": p["name"], "description": p["description"], "serviceType": p["name"],
              "provider": business_ld(s), "areaServed": s["zone"]}
        if p["price_cents"]:
            ld["offers"] = {"@type": "Offer", "priceCurrency": "USD", "price": f"{p['price_cents'] / 100:.2f}",
                            "description": f"Starting at {money(p['price_cents'])} {p['price_note']}".strip()}
        return render("service.html", f"{p['name']}{where} · {s['business_name']}",
                      f"{p['description']} {s['business_name']} — {s['zone']}. Free estimates.", ld)

    @app.get("/robots.txt", include_in_schema=False)
    def robots(request: Request):
        if NOINDEX:
            return PlainTextResponse("User-agent: *\nDisallow: /\n")
        return PlainTextResponse(f"User-agent: *\nDisallow: /admin\nDisallow: /api/\nSitemap: {str(request.base_url).rstrip('/')}/sitemap.xml\n")

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap(request: Request):
        base = str(request.base_url).rstrip("/")
        urls = [f"{base}/"] + [f"{base}/services/{p['slug']}/" for p in db.all("SELECT slug FROM packages WHERE active=1 ORDER BY sort, id")]
        body = "".join(f"<url><loc>{html.escape(u)}</loc></url>" for u in urls)
        return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                        media_type="application/xml")

    @app.get("/admin", include_in_schema=False)
    def admin_page():
        return FileResponse(STATIC / "admin.html")

    # ---------------------------------------------------------- API pública
    @app.get("/api/site")
    def site():
        s = db.settings()
        public = {k: s[k] for k in ("business_name", "tagline", "about", "whatsapp", "phone_display", "email", "zone",
                                    "hours_text", "facebook", "instagram", "currency_symbol", "google_review_url", "city", "region",
                                    "promo_text", "payments_text", "top_bar_text", "rating_text", "owner_name", "about_long",
                                    "google_rating", "google_review_count", "google_maps_url", "meta_pixel_id",
                                    "legal_name", "license_text")}
        public["about_values"] = [v.strip() for v in s.get("about_values", "").split("|") if v.strip()]
        try:
            public["content_es"] = json.loads(s.get("content_es") or "{}")
        except ValueError:
            public["content_es"] = {}
        public["area_cities"] = [c.strip() for c in s["area_cities"].split("|") if c.strip()]
        public["trust_badges"] = [b.strip() for b in s["trust_badges"].split("|") if b.strip()]
        public["zip_codes"] = zips(s)
        public["whatsapp_link"] = wa_link(s["whatsapp"], f"Hi {s['business_name']}, I'd like a free estimate.")
        public["sms_link"] = sms_link(s["phone_display"], f"Hi {s['business_name']}, I'd like a free estimate.")
        public["tel_link"] = tel_link(s["phone_display"])
        public["logo_url"] = f"/media/{s['logo_src']}" if s.get("logo_src") else ""
        public["hero_url"] = f"/media/{s['hero_src']}" if s.get("hero_src") else ""
        return {"settings": public, "packages": packages(), "addons": simple_rows("addons"),
                "testimonials": simple_rows("testimonials"), "faqs": simple_rows("faqs"),
                "estimator": parse_est(s), "media": media_list()}

    @app.post("/api/estimate")
    def api_estimate(body: EstimateIn):
        s = db.settings()
        e = estimate(s, body)
        e["text"] = estimate_text(e, s["currency_symbol"])
        return e

    @app.get("/api/zip/{code}")
    def check_zip(code: str):
        z = zips(db.settings())
        return {"zip": code, "served": (not z) or code.strip() in z, "checked": bool(z)}

    @app.get("/api/availability")
    def availability(start: str | None = None, days: int = 42):
        s = db.settings()
        d0 = date.fromisoformat(start) if start else today()
        return day_info(s, d0, max(1, min(days, 120)))

    @app.post("/api/bookings")
    def create_booking(body: BookingIn, request: Request):
        rate_limit(request)
        s = db.settings()
        e = estimate(s, body) if body.package_id else None
        try:
            d = date.fromisoformat(body.date)
        except ValueError:
            raise HTTPException(400, "Invalid date")
        zip_ok = not zips(s) or not body.zip or body.zip.strip() in zips(s)
        bid = "R-" + secrets.token_hex(3).upper()
        with db.lock:  # comprobar cupo e insertar sin que otra reserva se cuele entre medio
            if not day_info(s, d, 1)[0]["open"]:
                raise HTTPException(409, "That day is no longer available. Please pick another one.")
            db.execute(
                "INSERT INTO bookings(id,name,phone,email,address,zip,date,package_id,package_name,size,condition,frequency,"
                "addons,contact_pref,estimate_low,estimate_high,notes,source,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (bid, body.name.strip(), body.phone, body.email, body.address.strip(), body.zip.strip(), body.date,
                 body.package_id if e else None, e["package"] if e else "", e["size"] if e else "",
                 e["condition"] if e else "", e["frequency"] if e else "", ", ".join(e["addons"]) if e else "",
                 body.contact_pref, e["low"] if e else None, e["high"] if e else None, body.notes.strip(),
                 clean_source(body.source), time.time()))
        L = MSG[body.lang]
        lines = [L["book_hi"].format(biz=s["business_name"]),
                 f"• {L['booking']}: {bid}",
                 f"• {L['service']}: {e['package'] if e else L['not_sure']}" + (f" ({e['frequency']})" if e and e["frequency"] else ""),
                 f"• {L['day']}: {fmt_date(body.date, body.lang)}"]
        if e:
            lines += [f"• {L['lot']}: {e['size']} · {e['condition']}"]
            if e["addons"]:
                lines.append(f"• {L['addons']}: {', '.join(e['addons'])}")
            lines.append(f"• {L['estimate']}: {estimate_text(e, s['currency_symbol'], body.lang)}")
        lines += [f"• {L['name']}: {body.name.strip()}",
                  f"• {L['address']}: {body.address.strip()}" + (f" {body.zip.strip()}" if body.zip.strip() else "")]
        if body.notes.strip():
            lines.append(f"• {L['details']}: {body.notes.strip()}")
        lines.append(L["book_end"])
        msg = "\n".join(lines)
        return {"id": bid, "date": body.date, "date_text": fmt_date(body.date), "zip_ok": zip_ok,
                "estimate_text": estimate_text(e, s["currency_symbol"]) if e else "",
                "whatsapp_url": wa_link(s["whatsapp"], msg), "sms_url": sms_link(s["phone_display"], msg),
                "tel_url": tel_link(s["phone_display"])}

    @app.post("/api/visit", status_code=204)
    def record_visit(body: VisitIn, request: Request):
        ua = request.headers.get("user-agent", "")
        if not ua or BOT_RE.search(ua) or request.headers.get("dnt") == "1":
            return Response(status_code=204)
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
        q, now = hits["visit:" + ip], time.time()
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= 30:                      # nadie navea 30 páginas por minuto: se ignora
            return Response(status_code=204)
        q.append(now)
        day = today().isoformat()
        path = re.sub(r"[^\w/.-]", "", body.path.split("?")[0])[:120] or "/"
        src, dev = clean_source(body.source), "mobile" if body.mobile else "desktop"
        rows = [("view", path, src, dev)] + ([("visitor", "", src, dev)] if body.new_visitor else [])
        for kind, pth, s_, d_ in rows:
            db.execute("INSERT INTO visits(day,kind,path,source,device,n) VALUES(?,?,?,?,?,1) "
                       "ON CONFLICT(day,kind,path,source,device) DO UPDATE SET n=n+1", (day, kind, pth, s_, d_))
        return Response(status_code=204)

    @app.post("/api/quotes")
    def create_quote(body: QuoteIn, request: Request):
        rate_limit(request)
        s = db.settings()
        names = [x.strip()[:60] for x in body.services if x.strip()][:20]
        qid = "Q-" + secrets.token_hex(3).upper()
        db.execute("INSERT INTO quotes(id,name,phone,email,city,services,notes,contact_pref,page,source,created)"
                   " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (qid, body.name.strip(), body.phone, body.email, body.city.strip(), ", ".join(names), body.notes.strip(),
                    body.contact_pref, body.page.strip(), clean_source(body.source), time.time()))
        L = MSG[body.lang]
        lines = [L["quote_hi"].format(biz=s["business_name"]), f"• {L['request']}: {qid}", f"• {L['name']}: {body.name.strip()}"]
        if body.city.strip():
            lines.append(f"• {L['city']}: {body.city.strip()}")
        if names:
            lines.append(f"• {L['needs']}: {', '.join(names)}")
        if body.notes.strip():
            lines.append(f"• {L['about_yard']}: {body.notes.strip()}")
        msg = "\n".join(lines)
        return {"id": qid, "sms_url": sms_link(s["phone_display"], msg), "whatsapp_url": wa_link(s["whatsapp"], msg),
                "tel_url": tel_link(s["phone_display"])}

    @app.get("/privacy", include_in_schema=False)
    def privacy():
        s = db.settings()
        return render("privacy.html", f"Privacy Policy · {s['business_name']}", f"How {s['business_name']} uses your information.",
                      business_ld(s))

    # ---------------------------------------------------------- inicio de sesión del panel
    login_hits: dict[str, deque] = defaultdict(deque)

    @app.post("/api/admin/login")
    def admin_login(body: LoginIn, request: Request, response: Response):
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
        q, now = login_hits[ip], time.time()
        while q and q[0] < now - 900:
            q.popleft()
        if len(q) >= 8:
            raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
        q.append(now)
        ok_user = hmac.compare_digest(body.username.strip().lower(), admin_user())
        ok_pass = bool(admin_password()) and hmac.compare_digest(body.password, admin_password())
        if not (ok_user and ok_pass):
            raise HTTPException(401, "Wrong username or password")
        secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie(SESSION_COOKIE, make_session(admin_user()), max_age=SESSION_DAYS * 86400, httponly=True,
                            samesite="strict", secure=secure, path="/")
        return {"ok": True}

    @app.post("/api/admin/logout")
    def admin_logout(response: Response):
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"ok": True}

    # ---------------------------------------------------------- administración
    admin = [Depends(require_admin)]

    @app.get("/api/admin/summary", dependencies=admin)
    def summary():
        t = today().isoformat()
        week = (today() + timedelta(days=7)).isoformat()
        month = t[:8] + "01"
        q = lambda sql, p=(): db.one(sql, p)["n"]
        return {
            "pending": q("SELECT COUNT(*) n FROM bookings WHERE status='pending'"),
            "today": q("SELECT COUNT(*) n FROM bookings WHERE status IN ('pending','confirmed') AND date=?", (t,)),
            "week": q("SELECT COUNT(*) n FROM bookings WHERE status IN ('pending','confirmed') AND date>=? AND date<?", (t, week)),
            "done_month": q("SELECT COUNT(*) n FROM bookings WHERE status='done' AND date>=?", (month,)),
            "revenue_month_cents": q("SELECT COALESCE(SUM(price_cents),0) n FROM bookings WHERE status='done' AND date>=?", (month,)),
            "pipeline_cents": q("SELECT COALESCE(SUM(COALESCE(price_cents,(estimate_low+estimate_high)/2)),0) n FROM bookings "
                                "WHERE status IN ('pending','confirmed') AND date>=?", (t,)),
            "new_quotes": q("SELECT COUNT(*) n FROM quotes WHERE status='new'"),
            "visitors_today": q("SELECT COALESCE(SUM(n),0) n FROM visits WHERE kind='visitor' AND day=?", (t,)),
            "recurring_leads": q("SELECT COUNT(*) n FROM bookings WHERE frequency NOT IN ('','One-time') AND status!='cancelled'"),
        }

    @app.get("/api/admin/visits", dependencies=admin)
    def visits_report(days: int = 30):
        days = max(1, min(days, 365))
        t = today()
        since = (t - timedelta(days=days - 1)).isoformat()
        q = lambda sql, p=(): db.all(sql, p)
        tot = lambda kind, d0: db.one("SELECT COALESCE(SUM(n),0) n FROM visits WHERE kind=? AND day>=?", (kind, d0))["n"]
        per_day = {r["day"]: r["n"] for r in q("SELECT day, SUM(n) n FROM visits WHERE kind='visitor' AND day>=? GROUP BY day", (since,))}
        day_list = [(t - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
        leads = db.one("SELECT COUNT(*) n FROM quotes WHERE created>=?", (time.time() - days * 86400,))["n"] + \
            db.one("SELECT COUNT(*) n FROM bookings WHERE created>=?", (time.time() - days * 86400,))["n"]
        visitors = tot("visitor", since)
        return {
            "days": days,
            "visitors_today": tot("visitor", t.isoformat()),
            "visitors_7": tot("visitor", (t - timedelta(days=6)).isoformat()),
            "visitors": visitors, "views": tot("view", since), "leads": leads,
            "conversion_pct": round(100 * leads / visitors, 1) if visitors else 0,
            "per_day": [{"day": d, "n": per_day.get(d, 0)} for d in day_list],
            "sources": q("SELECT source, SUM(n) n FROM visits WHERE kind='visitor' AND day>=? GROUP BY source ORDER BY n DESC LIMIT 12", (since,)),
            "pages": q("SELECT path, SUM(n) n FROM visits WHERE kind='view' AND day>=? GROUP BY path ORDER BY n DESC LIMIT 12", (since,)),
            "devices": q("SELECT device, SUM(n) n FROM visits WHERE kind='visitor' AND day>=? GROUP BY device ORDER BY n DESC", (since,)),
        }

    @app.get("/api/admin/settings", dependencies=admin)
    def get_settings():
        return db.settings()

    @app.put("/api/admin/settings", dependencies=admin)
    def put_settings(body: dict):
        for k, v in body.items():
            if k not in DEFAULT_SETTINGS:
                continue
            if k == "content_es":
                d = v if isinstance(v, dict) else json.loads(v or "{}")
                if not isinstance(d, dict) or not all(isinstance(a, str) and isinstance(b, str) for a, b in d.items()):
                    raise HTTPException(400, "Spanish translations must be a JSON object of text → text")
                v = json.dumps(d, ensure_ascii=False)
                if len(v) > 300_000:
                    raise HTTPException(400, "Spanish translations are too long")
                db.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
                continue
            if k in EST_KEYS:
                rows = v if isinstance(v, list) else json.loads(v)
                if not isinstance(rows, list) or not rows or len(rows) > 20:
                    raise HTTPException(400, f"Invalid {k}")
                clean = []
                for r in rows:
                    m = r.get("mult")
                    if m in ("", None):
                        m = None
                    else:
                        m = float(m)
                        if not 0 < m <= 50:
                            raise HTTPException(400, "Multipliers must be between 0 and 50")
                    clean.append({"label": str(r.get("label", ""))[:80], "mult": m})
                v = json.dumps(clean, ensure_ascii=False)
            else:
                v = str(v).strip()[:2000]
            if k == "work_days" and not re.fullmatch(r"[0-6]{0,7}", v):
                raise HTTPException(400, "Invalid work days")
            if k in ("daily_capacity", "horizon_days", "min_notice_days", "est_range_pct") and not (v.isdigit() and int(v) <= 365):
                raise HTTPException(400, f"Invalid value for {k}")
            if k == "meta_pixel_id" and v and not re.fullmatch(r"\d{6,20}", v):
                raise HTTPException(400, "The Meta Pixel ID is only numbers (e.g. 123456789012345)")
            if k == "whatsapp":
                v = digits(v)
            db.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
        return db.settings()

    # paquetes
    def pkg_values(b: PackageIn, pid: int | None = None):
        return (b.name, b.description, b.price_cents, b.price_note,
                json.dumps([f for f in b.features if f.strip()], ensure_ascii=False),
                int(b.highlight), int(b.recurring), int(b.active), b.sort, json.dumps(clean_details(b.details), ensure_ascii=False),
                db.unique_slug(b.name, pid))

    @app.get("/api/admin/packages", dependencies=admin)
    def list_packages():
        return packages(active_only=False)

    @app.post("/api/admin/packages", dependencies=admin)
    def add_package(body: PackageIn):
        cur = db.execute("INSERT INTO packages(name,description,price_cents,price_note,features,highlight,recurring,active,sort,"
                         "details,slug) VALUES(?,?,?,?,?,?,?,?,?,?,?)", pkg_values(body))
        return {"id": cur.lastrowid}

    @app.put("/api/admin/packages/{pid}", dependencies=admin)
    def edit_package(pid: int, body: PackageIn):
        cur = db.execute("UPDATE packages SET name=?,description=?,price_cents=?,price_note=?,features=?,highlight=?,recurring=?,"
                         "active=?,sort=?,details=?,slug=? WHERE id=?", (*pkg_values(body, pid), pid))
        if not cur.rowcount:
            raise HTTPException(404, "Not found")
        return {"ok": True}

    @app.delete("/api/admin/packages/{pid}", dependencies=admin)
    def del_package(pid: int):
        db.execute("DELETE FROM packages WHERE id=?", (pid,))
        return {"ok": True}

    # add-ons, reseñas y preguntas frecuentes (CRUD genérico)
    def register_simple(kind: str, table: str, model):
        fields = list(model.model_fields)

        def values(b):
            d = b.model_dump()
            return tuple(int(d[f]) if isinstance(d[f], bool) else d[f] for f in fields)

        @app.get(f"/api/admin/{kind}", dependencies=admin, name=f"list_{kind}")
        def _list():
            return simple_rows(table, active_only=False)

        @app.post(f"/api/admin/{kind}", dependencies=admin, name=f"add_{kind}")
        def _add(body: model):  # type: ignore[valid-type]
            cur = db.execute(f"INSERT INTO {table}({','.join(fields)}) VALUES({','.join('?' * len(fields))})", values(body))
            return {"id": cur.lastrowid}

        @app.put(f"/api/admin/{kind}/{{rid}}", dependencies=admin, name=f"edit_{kind}")
        def _edit(rid: int, body: model):  # type: ignore[valid-type]
            cur = db.execute(f"UPDATE {table} SET {','.join(f + '=?' for f in fields)} WHERE id=?", (*values(body), rid))
            if not cur.rowcount:
                raise HTTPException(404, "Not found")
            return {"ok": True}

        @app.delete(f"/api/admin/{kind}/{{rid}}", dependencies=admin, name=f"del_{kind}")
        def _del(rid: int):
            db.execute(f"DELETE FROM {table} WHERE id=?", (rid,))
            return {"ok": True}

    for kind, (table, model, _j, _b) in SIMPLE.items():
        register_simple(kind, table, model)

    # fotos y videos
    @app.post("/api/admin/media", dependencies=admin)
    async def add_media(file: UploadFile | None = File(default=None), youtube_url: str = Form(default=""),
                        title: str = Form(default=""), package_id: str = Form(default=""), featured: bool = Form(default=False),
                        after_file: UploadFile | None = File(default=None), caption: str = Form(default="")):
        pid = int(package_id) if package_id.isdigit() else None
        if pid is not None and not db.one("SELECT 1 FROM packages WHERE id=?", (pid,)):
            raise HTTPException(400, "That service no longer exists")
        if youtube_url:
            vid = youtube_id(youtube_url)
            if not vid:
                raise HTTPException(400, "YouTube link not recognized")
            kind, src = "youtube", vid
        elif file and file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext in PHOTO_EXT:
                kind, limit = "photo", MAX_PHOTO
            elif ext in VIDEO_EXT:
                kind, limit = "video", MAX_VIDEO
            else:
                raise HTTPException(400, "File type not allowed (photos: jpg, png, webp · videos: mp4, webm, mov)")
            src = secrets.token_hex(10) + ext
            path, size = uploads / src, 0
            with open(path, "wb") as f:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > limit:
                        f.close()
                        path.unlink(missing_ok=True)
                        raise HTTPException(413, f"File too large (max {limit // 1024 // 1024} MB)")
                    f.write(chunk)
        else:
            raise HTTPException(400, "Upload a file or paste a YouTube link")
        after = ""
        if kind == "photo" and after_file and after_file.filename:
            ext2 = Path(after_file.filename).suffix.lower()
            if ext2 not in PHOTO_EXT:
                (uploads / src).unlink(missing_ok=True)
                raise HTTPException(400, "The 'after' file must be a photo")
            data = await after_file.read(MAX_PHOTO + 1)
            if len(data) > MAX_PHOTO:
                (uploads / src).unlink(missing_ok=True)
                raise HTTPException(413, "File too large (max 10 MB)")
            after = secrets.token_hex(10) + ext2
            (uploads / after).write_bytes(data)
        cur = db.execute("INSERT INTO media(kind,src,after_src,title,caption,package_id,featured,created) VALUES(?,?,?,?,?,?,?,?)",
                         (kind, src, after, title.strip()[:100], caption.strip()[:200], pid, int(featured), time.time()))
        return {"id": cur.lastrowid, "kind": kind}

    @app.patch("/api/admin/media/{mid}", dependencies=admin)
    def edit_media(mid: int, body: MediaPatch):
        fields = body.model_dump(exclude_unset=True)
        if fields.get("package_id") is not None and not db.one("SELECT 1 FROM packages WHERE id=?", (fields["package_id"],)):
            raise HTTPException(400, "That service no longer exists")
        if "featured" in fields:
            fields["featured"] = int(bool(fields["featured"]))
        if fields:
            db.execute(f"UPDATE media SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), mid))
        return {"ok": True}

    # imágenes del sitio: logo, foto de fondo de la portada y foto del encabezado del panel
    SITE_IMAGES = {"logo": ("logo_src", 5), "hero": ("hero_src", 12), "banner": ("banner_src", 12)}

    async def save_site_image(kind: str, file: UploadFile):
        key, max_mb = SITE_IMAGES[kind]
        ext = Path(file.filename or "").suffix.lower()
        if ext not in PHOTO_EXT:
            raise HTTPException(400, "Image must be a PNG, JPG or WEBP file")
        data = await file.read(max_mb * 1024 * 1024 + 1)
        if len(data) > max_mb * 1024 * 1024:
            raise HTTPException(413, f"Image too large (max {max_mb} MB)")
        old = db.settings().get(key)
        src = f"{kind}_" + secrets.token_hex(6) + ext
        (uploads / src).write_bytes(data)
        db.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, src))
        if old:
            (uploads / Path(old).name).unlink(missing_ok=True)
        return {f"{kind}_url": f"/media/{src}"}

    def remove_site_image(kind: str):
        key = SITE_IMAGES[kind][0]
        old = db.settings().get(key)
        db.execute("UPDATE settings SET v='' WHERE k=?", (key,))
        if old:
            (uploads / Path(old).name).unlink(missing_ok=True)
        return {"ok": True}

    @app.post("/api/admin/logo", dependencies=admin)
    async def upload_logo(file: UploadFile = File(...)):
        return await save_site_image("logo", file)

    @app.delete("/api/admin/logo", dependencies=admin)
    def delete_logo():
        return remove_site_image("logo")

    @app.post("/api/admin/hero", dependencies=admin)
    async def upload_hero(file: UploadFile = File(...)):
        return await save_site_image("hero", file)

    @app.delete("/api/admin/hero", dependencies=admin)
    def delete_hero():
        return remove_site_image("hero")

    @app.post("/api/admin/banner", dependencies=admin)
    async def upload_banner(file: UploadFile = File(...)):
        return await save_site_image("banner", file)

    @app.delete("/api/admin/banner", dependencies=admin)
    def delete_banner():
        return remove_site_image("banner")

    @app.delete("/api/admin/media/{mid}", dependencies=admin)
    def del_media(mid: int):
        m = db.one("SELECT * FROM media WHERE id=?", (mid,))
        if m:
            db.execute("DELETE FROM media WHERE id=?", (mid,))
            if m["kind"] != "youtube":
                (uploads / Path(m["src"]).name).unlink(missing_ok=True)
            if m.get("after_src"):
                (uploads / Path(m["after_src"]).name).unlink(missing_ok=True)
        return {"ok": True}

    # reservas
    def decorate(s: dict, b: dict) -> dict:
        b["date_text"] = fmt_date(b["date"])
        b["contact_text"] = CONTACT.get(b["contact_pref"], b["contact_pref"])
        msg = client_message(s, b)
        b["wa_client"] = wa_link(b["phone"], msg)
        b["sms_client"] = sms_link(b["phone"], msg)
        b["tel_client"] = tel_link(b["phone"])
        b["review_client"] = sms_link(b["phone"], review_message(s, b)) if s["google_review_url"] else ""
        return b

    def review_message(s: dict, b: dict) -> str:
        return (f"Hi {b['name']}, thanks again for choosing {s['business_name']}! Would you mind leaving us a quick "
                f"Google review? It really helps a small business: {s['google_review_url']}")

    def client_message(s: dict, b: dict) -> str:
        sym = s["currency_symbol"]
        if b["status"] == "confirmed":
            txt = (f"Hi {b['name']}, you're all set! Your {b['package_name'] or 'lawn care'} service is confirmed "
                   f"for {fmt_date(b['date'])} at {b['address']}. Booking {b['id']}. — {s['business_name']}")
        elif b["status"] == "done":
            txt = f"Hi {b['name']}, your yard is done! Thank you for choosing {s['business_name']}."
            if s["google_review_url"]:
                txt += f" If you're happy with the work, a quick Google review would mean a lot: {s['google_review_url']}"
        elif b["status"] == "cancelled":
            txt = f"Hi {b['name']}, your booking {b['id']} for {fmt_date(b['date'])} has been cancelled. Text us anytime to reschedule."
        else:
            txt = (f"Hi {b['name']}, thanks for your request {b['id']} for {fmt_date(b['date'])}! "
                   f"We'll confirm your appointment and final price shortly.")
        if b.get("price_cents") and b["status"] in ("pending", "confirmed"):
            txt += f" Price: {money(b['price_cents'], sym)}."
        return txt

    @app.get("/api/admin/bookings", dependencies=admin)
    def list_bookings(status: str = "", upcoming: bool = False):
        sql, p = "SELECT * FROM bookings WHERE 1=1", []
        if status in STATUSES:
            sql += " AND status=?"
            p.append(status)
        if upcoming:
            sql += " AND date>=?"
            p.append(today().isoformat())
        sql += " ORDER BY date, created" if upcoming else " ORDER BY created DESC"
        s = db.settings()
        return [decorate(s, r) for r in db.all(sql + " LIMIT 300", p)]

    @app.patch("/api/admin/bookings/{bid}", dependencies=admin)
    def edit_booking(bid: str, body: BookingPatch):
        if not db.one("SELECT 1 FROM bookings WHERE id=?", (bid,)):
            raise HTTPException(404, "Booking not found")
        fields = body.model_dump(exclude_none=True)
        if "date" in fields:
            date.fromisoformat(fields["date"])
        if fields:
            db.execute(f"UPDATE bookings SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), bid))
        return decorate(db.settings(), db.one("SELECT * FROM bookings WHERE id=?", (bid,)))

    # solicitudes de cotización
    def decorate_quote(s: dict, r: dict) -> dict:
        r["contact_text"] = CONTACT.get(r["contact_pref"], r["contact_pref"])
        msg = f"Hi {r['name']}, this is {s['business_name']} about your free quote request {r['id']}."
        r["sms_client"], r["wa_client"], r["tel_client"] = sms_link(r["phone"], msg), wa_link(r["phone"], msg), tel_link(r["phone"])
        return r

    @app.get("/api/admin/quotes", dependencies=admin)
    def list_quotes(status: str = ""):
        s = db.settings()
        rows = db.all("SELECT * FROM quotes" + (" WHERE status=?" if status else "") + " ORDER BY created DESC, rowid DESC LIMIT 300",
                      (status,) if status else ())
        return [decorate_quote(s, r) for r in rows]

    @app.patch("/api/admin/quotes/{qid}", dependencies=admin)
    def edit_quote(qid: str, body: QuotePatch):
        fields = body.model_dump(exclude_none=True)
        if not db.one("SELECT 1 FROM quotes WHERE id=?", (qid,)):
            raise HTTPException(404, "Not found")
        if fields:
            db.execute(f"UPDATE quotes SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), qid))
        return decorate_quote(db.settings(), db.one("SELECT * FROM quotes WHERE id=?", (qid,)))

    # días
    @app.get("/api/admin/days", dependencies=admin)
    def admin_days(start: str | None = None, days: int = 42):
        return day_info(db.settings(), date.fromisoformat(start) if start else today(), max(1, min(days, 120)))

    @app.put("/api/admin/days/{d}", dependencies=admin)
    def set_day(d: str, body: DayIn):
        date.fromisoformat(d)
        db.execute("INSERT INTO day_overrides(date,capacity,note) VALUES(?,?,?) ON CONFLICT(date) DO UPDATE "
                   "SET capacity=excluded.capacity, note=excluded.note", (d, body.capacity, body.note))
        return {"ok": True}

    @app.delete("/api/admin/days/{d}", dependencies=admin)
    def reset_day(d: str):
        db.execute("DELETE FROM day_overrides WHERE date=?", (d,))
        return {"ok": True}

    return app


app = create_app()
