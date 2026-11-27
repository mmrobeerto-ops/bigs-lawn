"""Base de datos SQLite: un solo archivo, sin servidor aparte."""
import json
import re
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL DEFAULT 0,   -- precio base: 1/4 de acre, terreno mantenido (y semanal si es recurrente)
    price_note TEXT NOT NULL DEFAULT '',      -- "from", "per visit"...
    features TEXT NOT NULL DEFAULT '[]',
    highlight INTEGER NOT NULL DEFAULT 0,
    recurring INTEGER NOT NULL DEFAULT 0,     -- admite plan semanal / quincenal / mensual
    slug TEXT NOT NULL DEFAULT '',            -- URL de su página: /services/<slug>/
    details TEXT NOT NULL DEFAULT '',         -- texto largo de la página del servicio
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS addons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL DEFAULT 0,
    unit_note TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS testimonials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 5,
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('photo','video','youtube')),
    src TEXT NOT NULL,
    after_src TEXT NOT NULL DEFAULT '',       -- foto "después" (si la hay, se muestra antes/después)
    title TEXT NOT NULL DEFAULT '',
    caption TEXT NOT NULL DEFAULT '',
    package_id INTEGER REFERENCES packages(id) ON DELETE SET NULL,
    featured INTEGER NOT NULL DEFAULT 0,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS day_overrides (
    date TEXT PRIMARY KEY,
    capacity INTEGER NOT NULL,                -- 0 = cerrado
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL,
    zip TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL,
    package_id INTEGER REFERENCES packages(id) ON DELETE SET NULL,
    package_name TEXT NOT NULL DEFAULT '',
    size TEXT NOT NULL DEFAULT '',
    condition TEXT NOT NULL DEFAULT '',
    frequency TEXT NOT NULL DEFAULT '',
    addons TEXT NOT NULL DEFAULT '',
    contact_pref TEXT NOT NULL DEFAULT 'text',
    estimate_low INTEGER,
    estimate_high INTEGER,
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',   -- pending|confirmed|done|cancelled
    price_cents INTEGER,
    admin_note TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date, status);
-- Visitas: solo conteos por día (sin IP, sin cookies, sin datos personales)
CREATE TABLE IF NOT EXISTS visits (
    day TEXT NOT NULL,            -- AAAA-MM-DD (hora local del negocio)
    kind TEXT NOT NULL,           -- 'view' (página vista) o 'visitor' (visitante nuevo ese día)
    path TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    device TEXT NOT NULL DEFAULT '',
    n INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, kind, path, source, device)
);
CREATE TABLE IF NOT EXISTS quotes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    services TEXT NOT NULL DEFAULT '',        -- lista separada por comas
    notes TEXT NOT NULL DEFAULT '',
    contact_pref TEXT NOT NULL DEFAULT 'text',
    page TEXT NOT NULL DEFAULT '',            -- desde qué página llegó
    status TEXT NOT NULL DEFAULT 'new',       -- new|contacted|won|lost
    admin_note TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL
);
"""

# Columnas añadidas después de la primera versión (para bases de datos ya existentes)
MIGRATIONS = {
    "quotes": {"source": "TEXT NOT NULL DEFAULT ''"},
    "media": {"after_src": "TEXT NOT NULL DEFAULT ''", "caption": "TEXT NOT NULL DEFAULT ''"},
    "packages": {"recurring": "INTEGER NOT NULL DEFAULT 0", "slug": "TEXT NOT NULL DEFAULT ''", "details": "TEXT NOT NULL DEFAULT ''"},
    "bookings": {"email": "TEXT NOT NULL DEFAULT ''", "zip": "TEXT NOT NULL DEFAULT ''", "size": "TEXT NOT NULL DEFAULT ''",
                 "condition": "TEXT NOT NULL DEFAULT ''", "frequency": "TEXT NOT NULL DEFAULT ''",
                 "addons": "TEXT NOT NULL DEFAULT ''", "contact_pref": "TEXT NOT NULL DEFAULT 'text'",
                 "estimate_low": "INTEGER", "estimate_high": "INTEGER", "source": "TEXT NOT NULL DEFAULT ''"},
}

# Multiplicadores del cotizador. El precio base de cada paquete = 1/4 acre, terreno mantenido, servicio semanal.
EST_SIZES = [
    {"label": "Small — up to 1/8 acre (≈5,000 sq ft)", "mult": 0.8},
    {"label": "Standard — 1/4 acre (≈10,000 sq ft)", "mult": 1.0},
    {"label": "Large — 1/2 acre (≈22,000 sq ft)", "mult": 1.6},
    {"label": "3/4 acre (≈33,000 sq ft)", "mult": 2.1},
    {"label": "1 acre (≈43,500 sq ft)", "mult": 2.6},
    {"label": "More than 1 acre", "mult": None},          # None = cotización a medida
]
EST_CONDITIONS = [
    {"label": "Well maintained", "mult": 1.0},
    {"label": "Overgrown (6–12 in. grass)", "mult": 1.35},
    {"label": "Very overgrown / brush & weeds", "mult": 1.8},
]
EST_FREQUENCIES = [
    {"label": "Weekly", "mult": 1.0},
    {"label": "Every 2 weeks", "mult": 1.1},
    {"label": "Monthly", "mult": 1.25},
    {"label": "One-time", "mult": 1.4},
]

DEFAULT_SETTINGS = {
    "business_name": "Your Lawn Care Co.",
    "tagline": "Salem lawn care & lot clearing done right.",
    "about": "Local, owner-operated crew serving Salem and Keizer. We show up when we say we will, do the job right, and leave your property spotless.",
    "whatsapp": "",              # con código de país, solo números: 15035551234
    "phone_display": "",         # se usa para llamar y para SMS
    "email": "",
    "seo_services": "Lawn Care & Lot Clearing",   # va en el título de la pestaña y en Google
    "city": "Salem",
    "region": "OR",
    "zone": "Serving Salem, Keizer, West Salem & South Salem",
    "zip_codes": "97301, 97302, 97303, 97304, 97305, 97306, 97307, 97317",
    "hours_text": "Mon–Sat · 8:00 AM – 6:00 PM",
    "facebook": "",
    "instagram": "",
    "google_review_url": "",
    "top_bar_text": "Free estimates.",
    "rating_text": "",           # p. ej. "4.9 stars from 40+ Google reviews" — solo si es real
    "area_cities": "Salem, OR|Keizer, OR|West Salem, OR|South Salem, OR",
    "owner_name": "",
    "about_long": "",
    "promo_text": "Fall leaf cleanup season is here — book early, spots fill fast",
    "trust_badges": "Free estimates|Upfront pricing|Satisfaction guaranteed|Clean-up included",
    "payments_text": "Cash, Zelle, Venmo, and all major cards",
    "currency_symbol": "$",
    "google_rating": "",        # p. ej. "4.9" (de su perfil de Google). Vacío = se calcula con las reseñas cargadas
    "google_review_count": "",  # p. ej. "130". Vacío = cantidad de reseñas cargadas
    "legal_name": "",           # razón social (pie de página), p. ej. "BIG'S Lawn Service LLC"
    "license_text": "",         # p. ej. "Oregon CCB #123456" — solo si es real
    "meta_pixel_id": "",        # Pixel de Meta (Facebook/Instagram) para medir campañas. Vacío = apagado
    "google_maps_url": "",      # enlace a su perfil en Google Maps ("Léelos en Google"). Vacío = búsqueda en Maps
    "about_values": "",         # tarjetas de "Sobre nosotros", separadas por |
    "content_es": "{}",        # traducciones al español del contenido del negocio {"texto en inglés": "texto en español"}
    "hero_src": "",            # foto de fondo de la portada
    "banner_src": "",          # foto de un trabajo para el encabezado del panel de administración
    "logo_src": "",            # archivo del logo en uploads/ (se sube desde el panel)
    "work_days": "012345",
    "daily_capacity": "4",
    "horizon_days": "45",
    "min_notice_days": "1",
    "est_range_pct": "15",
    "est_sizes": json.dumps(EST_SIZES, ensure_ascii=False),
    "est_conditions": json.dumps(EST_CONDITIONS, ensure_ascii=False),
    "est_frequencies": json.dumps(EST_FREQUENCIES, ensure_ascii=False),
}

# Precios de referencia para Salem, OR (USD, 1/4 acre). El dueño los ajusta en el panel.
DEFAULT_PACKAGES = [
    ("Lawn Mowing", "Weekly or bi-weekly mowing, March through November.", 4500, "from / visit",
     ["Mow at the right height for PNW grass", "String-trim around obstacles", "Edge sidewalks & driveway", "Blow clippings off hard surfaces"], 1, 1),
    ("Fall & Spring Cleanup", "Leaves, fir needles and storm debris — a full yard reset.", 22500, "from",
     ["Leaf & needle removal", "Bed weeding & edging", "Shrub shaping", "Yard debris haul-away included"], 0, 0),
    ("Blackberry & Brush Clearing", "Overgrown lots, Himalayan blackberry, ivy and fence lines.", 30000, "from",
     ["Blackberry & bramble removal", "Tall grass & brush cutting", "Ivy and vine pull-down", "Debris pickup & haul-away available"], 0, 0),
]
DEFAULT_ADDONS = [
    ("Core aeration", 9500, ""), ("Overseeding", 8500, ""), ("Moss raking & dethatching", 15000, ""),
    ("Hedge & shrub trimming", 7500, ""), ("Bark dust installation", 9500, "per cu. yard"),
    ("Extra yard-debris load", 11000, "per load"), ("Gutter cleaning", 15000, "single-story"),
]
DEFAULT_FAQS = [
    ("Which areas do you serve?", "Salem, Keizer, West Salem and South Salem. Check your ZIP code above — if you're just outside, ask us anyway."),
    ("When is mowing season?", "Grass grows here from about March through November. Most customers go weekly in spring and every two weeks in the dry summer months. Fall and winter we focus on leaf cleanups and brush clearing."),
    ("Do you work in the rain?", "Light Oregon drizzle doesn't stop us. In heavy rain we'd rather not tear up your lawn, so we'll move your visit to the next available day and text you."),
    ("Can you remove blackberries?", "Yes — Himalayan blackberry is one of our most common jobs. We cut it down, pull what we can by the root and haul it away. Regrowth is normal, so we recommend a follow-up visit."),
    ("How do you price a job?", "By lot size, how overgrown it is, and how often we come. Use the instant estimate on this page, then we'll confirm your exact price before any work starts — no surprises."),
    ("Do I have to sign a contract?", "No contracts. Recurring plans can be paused or cancelled anytime."),
    ("How can I pay?", "We accept cash, Zelle, Venmo and all major cards. You pay after the job is done."),
]


def slugify(name: str) -> str:
    s = name.lower().replace("&", " and ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.lock = threading.RLock()
        self._migrate()
        self._seed()
        self._fill_slugs()

    def _migrate(self):
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in self.all(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    self.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

    def _seed(self):
        for k, v in DEFAULT_SETTINGS.items():
            self.execute("INSERT OR IGNORE INTO settings(k,v) VALUES(?,?)", (k, v))
        if self.one("SELECT 1 FROM settings WHERE k='_seeded_v2'"):
            return
        if not self.one("SELECT 1 FROM packages LIMIT 1"):
            for i, (n, d, p, note, f, h, rec) in enumerate(DEFAULT_PACKAGES):
                self.execute("INSERT INTO packages(name,description,price_cents,price_note,features,highlight,recurring,sort)"
                             " VALUES(?,?,?,?,?,?,?,?)", (n, d, p, note, json.dumps(f, ensure_ascii=False), h, rec, i))
        if not self.one("SELECT 1 FROM addons LIMIT 1"):
            for i, (n, p, u) in enumerate(DEFAULT_ADDONS):
                self.execute("INSERT INTO addons(name,price_cents,unit_note,sort) VALUES(?,?,?,?)", (n, p, u, i))
        if not self.one("SELECT 1 FROM faqs LIMIT 1"):
            for i, (q, a) in enumerate(DEFAULT_FAQS):
                self.execute("INSERT INTO faqs(question,answer,sort) VALUES(?,?,?)", (q, a, i))
        self.execute("INSERT OR IGNORE INTO settings(k,v) VALUES('_seeded_v2','1')")

    def unique_slug(self, name: str, exclude_id: int | None = None) -> str:
        base = slugify(name) or "service"
        slug, n = base, 2
        while self.one("SELECT 1 FROM packages WHERE slug=? AND id IS NOT ?", (slug, exclude_id)):
            slug, n = f"{base}-{n}", n + 1
        return slug

    def _fill_slugs(self):
        for p in self.all("SELECT id, name FROM packages WHERE slug=''"):
            self.execute("UPDATE packages SET slug=? WHERE id=?", (self.unique_slug(p["name"], p["id"]), p["id"]))

    def execute(self, sql, params=()):
        with self.lock:
            return self.conn.execute(sql, params)

    def all(self, sql, params=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        with self.lock:
            r = self.conn.execute(sql, params).fetchone()
            return dict(r) if r else None

    def settings(self) -> dict:
        return {r["k"]: r["v"] for r in self.all("SELECT k,v FROM settings WHERE k NOT LIKE '\\_%' ESCAPE '\\'")}
