from datetime import timedelta
from urllib.parse import unquote

from app.main import today
from tests.conftest import ADMIN


def setup(c, **s):
    base = {"whatsapp": "1 (787) 555-0101", "phone_display": "(787) 555-0101", "work_days": "0123456", "daily_capacity": "2", "min_notice_days": "1"}
    r = c.put("/api/admin/settings", headers=ADMIN, json=base | s)
    assert r.status_code == 200, r.text


def tomorrow(n=1):
    return (today() + timedelta(days=n)).isoformat()


def book(c, d, **kw):
    return c.post("/api/bookings", json={"name": "Ana Rivera", "phone": "787-555-1234", "address": "Calle 5, Bayamón",
                                         "date": d, **kw}, headers={"x-forwarded-for": kw.pop("ip", "1.1.1.1")})


def test_home_has_defaults_and_title(client):
    r = client.get("/")
    assert r.status_code == 200 and "Your Lawn Care Co. · Lawn Care &amp; Lot Clearing in Salem, OR" in r.text and '"addressRegion": "OR"' in r.text
    site = client.get("/api/site").json()
    assert len(site["packages"]) == 3 and site["packages"][0]["highlight"] and site["packages"][0]["recurring"]
    assert len(site["addons"]) == 7 and len(site["faqs"]) == 7 and site["testimonials"] == []


def test_booking_flow_creates_whatsapp_and_fills_capacity(client):
    setup(client)
    pid = client.get("/api/site").json()["packages"][0]["id"]
    d = tomorrow(2)
    r = book(client, d, package_id=pid, notes="Patio grande")
    assert r.status_code == 200, r.text
    wa = r.json()["whatsapp_url"]
    assert wa.startswith("https://wa.me/17875550101?text=")
    msg = unquote(wa)
    assert "Lawn Mowing" in msg and r.json()["id"] in msg and "Patio grande" in msg
    assert book(client, d, ip="2.2.2.2").status_code == 200
    day = [x for x in client.get("/api/availability").json() if x["date"] == d][0]
    assert day["remaining"] == 0 and day["reason"] == "Fully booked"
    assert book(client, d, ip="3.3.3.3").status_code == 409
    # cancelar libera el cupo
    bid = r.json()["id"]
    client.patch(f"/api/admin/bookings/{bid}", headers=ADMIN, json={"status": "cancelled"})
    assert book(client, d, ip="3.3.3.3").status_code == 200


def test_closed_days_notice_and_horizon(client):
    setup(client, work_days="", horizon_days="10")
    assert book(client, tomorrow(2)).status_code == 409           # no trabaja ningún día
    setup(client)
    assert book(client, today().isoformat()).status_code == 409   # aviso mínimo 1 día
    assert book(client, tomorrow(30)).status_code == 409          # fuera del horizonte
    client.put(f"/api/admin/days/{tomorrow(3)}", headers=ADMIN, json={"capacity": 0, "note": "Feriado"})
    assert book(client, tomorrow(3)).status_code == 409
    client.delete(f"/api/admin/days/{tomorrow(3)}", headers=ADMIN)
    assert book(client, tomorrow(3)).status_code == 200


def test_spam_protection(client):
    setup(client)
    assert book(client, tomorrow(2), website="http://spam").status_code == 422
    setup(client, daily_capacity="20")
    codes = [book(client, tomorrow(2), ip="9.9.9.9").status_code for _ in range(7)]
    assert codes[-1] == 429


def test_admin_auth(client):
    assert client.get("/api/admin/bookings").status_code == 401
    assert client.get("/api/admin/bookings", headers={"Authorization": "Bearer x"}).status_code == 401


def test_packages_crud(client):
    r = client.post("/api/admin/packages", headers=ADMIN, json={"name": "Tree trimming", "price_cents": 8000,
                                                                "price_note": "from", "features": ["Trimming", "", "Cleanup"]})
    pid = r.json()["id"]
    p = [x for x in client.get("/api/site").json()["packages"] if x["id"] == pid][0]
    assert p["features"] == ["Trimming", "Cleanup"]
    client.put(f"/api/admin/packages/{pid}", headers=ADMIN, json={"name": "Trimming", "active": False})
    assert pid not in [x["id"] for x in client.get("/api/site").json()["packages"]]
    assert book(client, tomorrow(2), package_id=pid).status_code == 400


def test_media_upload_youtube_and_delete(client):
    r = client.post("/api/admin/media", headers=ADMIN, files={"file": ("antes.jpg", b"\xff\xd8fake", "image/jpeg")},
                    data={"title": "Antes y después", "featured": "true"})
    assert r.status_code == 200 and r.json()["kind"] == "photo"
    r2 = client.post("/api/admin/media", headers=ADMIN, data={"youtube_url": "https://youtube.com/shorts/abcdefghijk"})
    assert r2.json()["kind"] == "youtube"
    assert client.post("/api/admin/media", headers=ADMIN, files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 400
    media = client.get("/api/site").json()["media"]
    assert media[0]["featured"] and media[0]["url"].startswith("/media/")
    assert client.get(media[0]["url"]).status_code == 200
    assert any("youtube-nocookie.com/embed/abcdefghijk" in m["url"] for m in media)
    client.delete(f"/api/admin/media/{r.json()['id']}", headers=ADMIN)
    assert len(list(client.uploads.iterdir())) == 0


def test_admin_booking_messages_and_summary(client):
    setup(client)
    bid = book(client, tomorrow(1)).json()["id"]
    b = client.patch(f"/api/admin/bookings/{bid}", headers=ADMIN, json={"status": "confirmed", "price_cents": 4500}).json()
    msg = unquote(b["wa_client"])
    assert b["wa_client"].startswith("https://wa.me/17875551234") and b["sms_client"].startswith("sms:+17875551234") and "is confirmed" in msg and "$45" in msg
    up = client.get("/api/admin/bookings?upcoming=true", headers=ADMIN).json()
    assert up[0]["id"] == bid
    assert client.get("/api/admin/summary", headers=ADMIN).json()["week"] == 1


def test_settings_validation(client):
    assert client.put("/api/admin/settings", headers=ADMIN, json={"work_days": "89"}).status_code == 400
    s = client.put("/api/admin/settings", headers=ADMIN, json={"whatsapp": "+1 787-555-0000", "nope": "x"}).json()
    assert s["whatsapp"] == "17875550000" and "nope" not in s


def test_estimator_pricing(client):
    site = client.get("/api/site").json()
    mow = site["packages"][0]
    clear = [p for p in site["packages"] if p["name"] == "Blackberry & Brush Clearing"][0]
    e = client.post("/api/estimate", json={"package_id": mow["id"], "size": 1, "condition": 0, "frequency": 0}).json()
    assert (e["low"], e["high"]) == (4000, 5500) and e["text"] == "$40–$55 per visit"   # $45 ±15%, redondeado a $5
    one = client.post("/api/estimate", json={"package_id": mow["id"], "size": 1, "condition": 0, "frequency": 3}).json()
    assert one["low"] > e["low"] and one["frequency"] == "One-time"
    acre = client.post("/api/estimate", json={"package_id": clear["id"], "size": 4, "condition": 2,
                                              "addon_ids": [site["addons"][5]["id"]]}).json()
    assert acre["frequency"] == "" and acre["addons"] == ["Extra yard-debris load"]
    assert 120000 < acre["low"] < acre["high"] < 180000            # ~1 acre de zarzamora: $1,300–$1,700
    big = client.post("/api/estimate", json={"package_id": clear["id"], "size": 5}).json()
    assert big["custom"] and big["text"] == "Custom quote"


def test_booking_with_estimate_zip_and_sms(client):
    setup(client, zip_codes="00956, 00959")
    assert client.get("/api/zip/00956").json()["served"]
    assert not client.get("/api/zip/10001").json()["served"]
    mow = client.get("/api/site").json()["packages"][0]
    r = book(client, tomorrow(2), package_id=mow["id"], size=2, condition=1, frequency=1, zip="10001", contact_pref="call").json()
    assert r["zip_ok"] is False and r["sms_url"].startswith("sms:+17875550101?&body=")
    msg = unquote(r["sms_url"])
    assert "Every 2 weeks" in msg and "Online estimate: $" in msg and "per visit" in msg
    b = client.get("/api/admin/bookings", headers=ADMIN).json()[0]
    assert b["estimate_low"] and b["contact_text"] == "Phone call" and b["zip"] == "10001"
    s = client.get("/api/admin/summary", headers=ADMIN).json()
    assert s["pipeline_cents"] > 0 and s["recurring_leads"] == 1


def test_reviews_faq_addons_crud_and_review_request(client):
    r = client.post("/api/admin/testimonials", headers=ADMIN, json={"name": "Mike R.", "location": "Bayamón", "text": "Great job!", "rating": 5})
    tid = r.json()["id"]
    assert client.get("/api/site").json()["testimonials"][0]["name"] == "Mike R."
    client.put(f"/api/admin/testimonials/{tid}", headers=ADMIN, json={"name": "Mike R.", "text": "Great job!", "active": False})
    assert client.get("/api/site").json()["testimonials"] == []
    fid = client.get("/api/admin/faqs", headers=ADMIN).json()[0]["id"]
    client.delete(f"/api/admin/faqs/{fid}", headers=ADMIN)
    assert len(client.get("/api/site").json()["faqs"]) == 6
    assert client.post("/api/admin/addons", headers=ADMIN, json={"name": "Aeration", "price_cents": 9900}).status_code == 200
    setup(client, google_review_url="https://g.page/r/example/review")
    bid = book(client, tomorrow(1)).json()["id"]
    b = client.patch(f"/api/admin/bookings/{bid}", headers=ADMIN, json={"status": "done"}).json()
    assert "g.page/r/example/review" in unquote(b["wa_client"]) and b["review_client"].startswith("sms:")


def test_estimator_settings_validation(client):
    bad = client.put("/api/admin/settings", headers=ADMIN, json={"est_sizes": [{"label": "x", "mult": -1}]})
    assert bad.status_code == 400
    ok = client.put("/api/admin/settings", headers=ADMIN, json={"est_sizes": [{"label": "Tiny", "mult": "0.5"}, {"label": "Huge", "mult": ""}]})
    assert ok.status_code == 200
    assert client.get("/api/site").json()["estimator"]["est_sizes"][1]["mult"] is None


def test_migrates_old_database(tmp_path):
    import sqlite3
    from app.db import Database
    p = tmp_path / "old.db"
    c = sqlite3.connect(p)
    c.executescript("CREATE TABLE packages (id INTEGER PRIMARY KEY, name TEXT, description TEXT, price_cents INTEGER, price_note TEXT,"
                    " features TEXT, highlight INTEGER, active INTEGER, sort INTEGER);"
                    "CREATE TABLE bookings (id TEXT PRIMARY KEY, name TEXT, phone TEXT, address TEXT, date TEXT, package_id INTEGER,"
                    " package_name TEXT, notes TEXT, status TEXT, price_cents INTEGER, admin_note TEXT, created REAL);")
    c.close()
    db = Database(str(p))
    cols = {r["name"] for r in db.all("PRAGMA table_info(bookings)")}
    assert {"zip", "estimate_low", "contact_pref"} <= cols


def test_logo_upload_replace_and_remove(client):
    assert client.get("/api/site").json()["settings"]["logo_url"] == ""
    assert client.post("/api/admin/logo", headers=ADMIN, files={"file": ("x.gif", b"GIF89a", "image/gif")}).status_code == 400
    u1 = client.post("/api/admin/logo", headers=ADMIN, files={"file": ("logo.png", b"\x89PNG1", "image/png")}).json()["logo_url"]
    u2 = client.post("/api/admin/logo", headers=ADMIN, files={"file": ("logo.png", b"\x89PNG2", "image/png")}).json()["logo_url"]
    assert client.get("/api/site").json()["settings"]["logo_url"] == u2
    assert client.get(u1).status_code == 404 and client.get(u2).status_code == 200    # el anterior se borra
    client.delete("/api/admin/logo", headers=ADMIN)
    assert client.get("/api/site").json()["settings"]["logo_url"] == "" and client.get(u2).status_code == 404


def test_service_pages_slugs_seo_and_sitemap(client):
    pk = client.get("/api/site").json()["packages"]
    assert [p["slug"] for p in pk] == ["lawn-mowing", "fall-and-spring-cleanup", "blackberry-and-brush-clearing"]
    r = client.post("/api/admin/packages", headers=ADMIN, json={"name": "Yard Cleanup", "description": "Full reset.", "price_cents": 22500,
        "details": {"eyebrow": "One visit. Whole yard.", "good_fit": ["Selling the house", " "], "how": [{"title": "Clean", "text": "We haul it."}],
                    "price_factors": [{"title": "Size", "text": "How big"}], "faqs": [{"q": "How long?", "a": "One day."}],
                    "video_url": "https://youtu.be/abcdefghijk"}})
    pid = r.json()["id"]
    p = [x for x in client.get("/api/site").json()["packages"] if x["id"] == pid][0]
    assert p["slug"] == "yard-cleanup" and p["details"]["good_fit"] == ["Selling the house"]
    assert p["details"]["video_embed"].endswith("/embed/abcdefghijk")
    page = client.get("/services/yard-cleanup/")
    assert page.status_code == 200 and "Yard Cleanup in Salem, OR" in page.text and '"@type": "Service"' in page.text
    assert "<!--#TOP-->" not in page.text and 'id="burger"' in page.text
    assert client.get("/services/no-existe/", follow_redirects=False).status_code == 302
    # mismo nombre -> slug único; renombrar cambia el slug
    r2 = client.post("/api/admin/packages", headers=ADMIN, json={"name": "Yard Cleanup"}).json()["id"]
    assert [x for x in client.get("/api/admin/packages", headers=ADMIN).json() if x["id"] == r2][0]["slug"] == "yard-cleanup-2"
    sm = client.get("/sitemap.xml").text
    assert "/services/yard-cleanup/" in sm and "/services/yard-cleanup-2/" in sm
    assert "Disallow: /admin" in client.get("/robots.txt").text
    assert client.get("/privacy").status_code == 200


def test_quote_requests(client):
    setup(client)
    r = client.post("/api/quotes", json={"name": "Ann Lee", "phone": "503-555-0199", "city": "Keizer",
                                          "services": ["Yard Cleanup", "Leaf Cleanup"], "notes": "Back yard", "page": "/services/yard-cleanup/"},
                    headers={"x-forwarded-for": "5.5.5.5"})
    assert r.status_code == 200, r.text
    msg = unquote(r.json()["sms_url"])
    assert "Needs: Yard Cleanup, Leaf Cleanup" in msg and "City: Keizer" in msg and "photo" not in msg.lower()
    assert client.post("/api/quotes", json={"name": "x", "phone": "1"}).status_code == 422
    assert client.post("/api/quotes", json={"name": "Bot", "phone": "5035550000", "website": "spam"}).status_code == 422
    q = client.get("/api/admin/quotes", headers=ADMIN).json()
    assert len(q) == 1 and q[0]["sms_client"].startswith("sms:+15035550199")
    assert client.get("/api/admin/summary", headers=ADMIN).json()["new_quotes"] == 1
    client.patch(f"/api/admin/quotes/{q[0]['id']}", headers=ADMIN, json={"status": "won"})
    assert client.get("/api/admin/quotes?status=won", headers=ADMIN).json()[0]["id"] == q[0]["id"]


def test_before_after_media(client):
    r = client.post("/api/admin/media", headers=ADMIN, data={"title": "Front bed", "caption": "Fresh bark"},
                    files={"file": ("b.jpg", b"\xff\xd8b", "image/jpeg"), "after_file": ("a.jpg", b"\xff\xd8a", "image/jpeg")})
    m = client.get("/api/site").json()["media"][0]
    assert m["after_url"].startswith("/media/") and m["caption"] == "Fresh bark"
    client.delete(f"/api/admin/media/{r.json()['id']}", headers=ADMIN)
    assert list(client.uploads.iterdir()) == []


def test_media_with_unknown_service_is_rejected(client):
    r = client.post("/api/admin/media", headers=ADMIN, data={"package_id": "999"}, files={"file": ("b.jpg", b"\xff\xd8", "image/jpeg")})
    assert r.status_code == 400 and list(client.uploads.iterdir()) == []


def test_hero_background_upload(client):
    assert client.get("/api/site").json()["settings"]["hero_url"] == ""
    u = client.post("/api/admin/hero", headers=ADMIN, files={"file": ("hero.jpg", b"\xff\xd8hero", "image/jpeg")}).json()["hero_url"]
    assert client.get("/api/site").json()["settings"]["hero_url"] == u and client.get(u).status_code == 200
    client.delete("/api/admin/hero", headers=ADMIN)
    assert client.get(u).status_code == 404


def test_admin_banner_upload(client):
    assert client.get("/api/admin/settings", headers=ADMIN).json()["banner_src"] == ""
    u = client.post("/api/admin/banner", headers=ADMIN, files={"file": ("b.jpg", b"\xff\xd8banner", "image/jpeg")}).json()["banner_url"]
    assert client.get(u).status_code == 200
    assert client.get("/api/admin/settings", headers=ADMIN).json()["banner_src"] == u.removeprefix("/media/")
    assert client.post("/api/admin/banner", files={"file": ("b.jpg", b"\xff\xd8x", "image/jpeg")}).status_code == 401
    client.delete("/api/admin/banner", headers=ADMIN)
    assert client.get(u).status_code == 404


def test_admin_login_with_username_and_password(client, monkeypatch):
    monkeypatch.setenv("JARDIN_ADMIN_USER", "Martin")
    monkeypatch.setenv("JARDIN_ADMIN_PASSWORD", "green-lawn-2026")
    c2 = client  # misma app
    assert c2.get("/api/admin/summary").status_code == 401
    assert c2.post("/api/admin/login", json={"username": "martin", "password": "nope"}).status_code == 401
    r = c2.post("/api/admin/login", json={"username": "MARTIN", "password": "green-lawn-2026"})
    assert r.status_code == 200 and "httponly" in r.headers["set-cookie"].lower()
    assert c2.get("/api/admin/summary").status_code == 200          # la cookie de sesión basta
    c2.post("/api/admin/logout")
    c2.cookies.clear()
    assert c2.get("/api/admin/summary").status_code == 401
    c2.cookies.set("jardin_session", "martin.9999999999.deadbeef")  # cookie falsificada
    assert c2.get("/api/admin/summary").status_code == 401
    c2.cookies.clear()
    assert c2.get("/api/admin/summary", headers=ADMIN).status_code == 200   # scripts siguen con token
    for _ in range(8):
        c2.post("/api/admin/login", json={"username": "x", "password": "y"}, headers={"x-forwarded-for": "7.7.7.7"})
    assert c2.post("/api/admin/login", json={"username": "martin", "password": "green-lawn-2026"},
                   headers={"x-forwarded-for": "7.7.7.7"}).status_code == 429


def test_lead_source_and_meta_pixel(client):
    setup(client)
    r = client.post("/api/quotes", json={"name": "Ann Lee", "phone": "503-555-0199", "source": "facebook / cpc / fall<script>"},
                    headers={"x-forwarded-for": "8.8.8.8"})
    assert r.status_code == 200
    q = client.get("/api/admin/quotes", headers=ADMIN).json()[0]
    assert q["source"] == "facebook / cpc / fallscript"
    client.post("/api/quotes", json={"name": "Bob Ray", "phone": "503-555-0198"}, headers={"x-forwarded-for": "8.8.4.4"})
    assert client.get("/api/admin/quotes", headers=ADMIN).json()[0]["source"] == "Direct"
    bid = book(client, tomorrow(2), source="Google Ads").json()["id"]
    assert [b for b in client.get("/api/admin/bookings", headers=ADMIN).json() if b["id"] == bid][0]["source"] == "Google Ads"
    assert client.put("/api/admin/settings", headers=ADMIN, json={"meta_pixel_id": "abc"}).status_code == 400
    client.put("/api/admin/settings", headers=ADMIN, json={"meta_pixel_id": "123456789012345"})
    assert client.get("/api/site").json()["settings"]["meta_pixel_id"] == "123456789012345"


def test_visit_counter(client):
    ua = {"user-agent": "Mozilla/5.0 (iPhone) Safari", "x-forwarded-for": "9.1.1.1"}
    client.post("/api/visit", json={"path": "/", "source": "google / maps", "new_visitor": True, "mobile": True}, headers=ua)
    client.post("/api/visit", json={"path": "/services/yard-cleanup/", "source": "google / maps"}, headers=ua)
    client.post("/api/visit", json={"path": "/", "new_visitor": True}, headers={"user-agent": "Googlebot/2.1", "x-forwarded-for": "9.1.1.2"})
    r = client.get("/api/admin/visits", headers=ADMIN).json()
    assert r["visitors_today"] == 1 and r["views"] == 2
    assert r["sources"][0] == {"source": "google / maps", "n": 1} and r["devices"][0]["device"] == "mobile"
    assert client.get("/api/admin/summary", headers=ADMIN).json()["visitors_today"] == 1
    assert client.get("/api/admin/visits").status_code == 401
