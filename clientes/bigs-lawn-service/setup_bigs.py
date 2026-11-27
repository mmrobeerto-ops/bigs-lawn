"""Carga los datos de BIG'S Lawn Service LLC en una página ya en marcha (usa la API del panel).

    JARDIN_ADMIN_TOKEN=... python clientes/bigs-lawn-service/setup_bigs.py --url http://localhost:8090 [--logo logo.png]

OJO: precios PROVISIONALES y zonas por confirmar con el cliente (ver PERFIL.md).
Los textos son originales para BIG'S (no copiados de otras páginas).
"""
import argparse
import os
import sys

import json
from pathlib import Path

import httpx

SETTINGS = {
    "business_name": "BIG'S Lawn Service",
    "tagline": "Beautiful lawns, healthy landscapes.",
    "seo_services": "Lawn Care & Landscaping",
    "about": "Lawn care, yard cleanups and landscaping for homes in Salem and Keizer, Oregon.",
    # Basado en lo que dicen sus reseñas reales; falta la historia del negocio (desde cuándo, cómo empezó)
    "about_long": "BIG'S Lawn Service is run by its owner, Martin. Customers count on him to show up on time, answer "
                  "quickly and follow up afterward to make sure everything looks right. Every job ends the same way: "
                  "debris hauled off and the property left clean.",
    "owner_name": "Martin",
    "about_values": "Shows up on time|Professional & polite|Fast replies & follow-up|Fair, honest prices|"
                    "Attention to detail|Everything hauled away",
    "google_rating": "",                  # pendiente: calificación real de su perfil de Google
    "google_review_count": "",            # pendiente: número real de reseñas en Google
    "google_maps_url": "https://maps.app.goo.gl/okXsjKzeJbLh3smC9",   # su perfil en Google Maps
    "phone_display": "(971) 388-0768",
    "email": "Martin.90.gallardo@gmail.com",
    "whatsapp": "19713880768",            # mismo número que llamadas y textos
    "city": "Salem",
    "region": "OR",
    "zone": "Serving Salem, Keizer & nearby areas",
    "area_cities": "Salem, OR|Keizer, OR|West Salem, OR|South Salem, OR",          # pendiente de confirmar
    "zip_codes": "97301, 97302, 97303, 97304, 97305, 97306, 97307, 97317",        # pendiente de confirmar
    "top_bar_text": "Free estimates · Fully insured",
    "legal_name": "BIG'S Lawn Service LLC",
    "license_text": "",                  # pendiente: número de CCB/LCB si lo tienen
    "promo_text": "",
    "rating_text": "5-star reviews from Salem customers on Google",   # todas las reseñas recibidas son de 5 estrellas
    "trust_badges": "Fully insured|Free estimates|Upfront pricing",
    "payments_text": "Ask us about payment options",                              # pendiente
    "facebook": "",                       # pendiente: link de Facebook
    "google_review_url": "",
}

FREE = "Every estimate is free"


def svc(name, description, price, note, features, eyebrow, good_fit, how, factors, faqs, **kw):
    return {"name": name, "description": description, "price_cents": price, "price_note": note, "features": features,
            "details": {"eyebrow": eyebrow, "good_fit": good_fit,
                        "how": [{"title": t, "text": x} for t, x in how],
                        "price_factors": [{"title": t, "text": x} for t, x in factors],
                        "faqs": [{"q": q, "a": a} for q, a in faqs]}, **kw}


SIZE = ("Size", "How much lawn or yard we are working on.")
CONDITION = ("Condition", "A light tidy-up or a yard that got away from you.")
ACCESS = ("Access", "Gates, slopes and how close we can park.")
HAUL = ("Haul-away", "How much debris leaves your property.")

PACKAGES = [
    svc("Lawn Maintenance", "Regular mowing and upkeep so your lawn always looks its best.", 4500, "from / visit",
        ["Mowing at the right height for the season", "String-trimming around fences, trees and beds",
         "Edging along sidewalks and the driveway", "Clippings blown off walks, patios and driveways"],
        "Mowed, edged, blown clean. Every visit.",
        ["You want a sharp lawn without spending your weekends on it", "You're tired of chasing the grass every spring",
         "You're getting the house ready to sell or rent", "You want one crew you can count on all season"],
        [("Same crew, same standard", "We keep a regular schedule, so your yard is cared for by people who already know it: where the sprinkler heads are, which gate to use and how you like the edges."),
         ("We leave it clean", "Mowing is only half the job. Every visit ends with edges cut and every walkway, patio and driveway blown clean.")],
        [SIZE, ("How often", "Weekly visits cost less per visit than once a month."), CONDITION, ACCESS],
        [("How often should my lawn be mowed?", "In spring, when grass grows fastest, most lawns look best with weekly mowing. In the dry summer months many customers switch to every two weeks."),
         ("Do I need to sign a contract?", "No. You can pause or cancel your service anytime."),
         ("Do I need to be home?", "No. As long as we can get into the yard, we'll take care of it and let you know when we're done.")],
        recurring=True, highlight=True, sort=0),
    svc("Yard Cleanup", "A full cleanup for yards that got out of hand. Cleared, hauled away and left clean.", 22500, "from",
        ["Weeds pulled from beds, walkways and fence lines", "Overgrown shrubs and hedges cut back", "Beds edged and cleaned out",
         "Branches and storm debris picked up", "Walkways, patios and driveway blown clean", "Everything loaded up and hauled away"],
        "One visit. Whole yard. Hauled away.",
        ["You're getting the house ready to sell or rent", "You have guests coming and the yard needs help",
         "You just moved in and the yard came with problems", "You want it done once, done properly"],
        [("For yards that got ahead of you", "Busy months and rainy weekends happen. A full cleanup takes care of everything at once instead of one weekend at a time."),
         ("Clean, not just cut", "Cutting things down is the easy part. We load every pile, blow off every walkway and take the debris with us, so you're not left with a mountain of branches at the curb.")],
        [SIZE, CONDITION, HAUL, ACCESS],
        [("How do I get a price?", "Send us a quote request or give us a call. Estimates are free and we confirm your price before any work starts."),
         ("Do you haul everything away?", "Yes. We take the yard debris with us, and haul-away is included in your cleanup price."),
         ("How long does a cleanup take?", "Most home yards are done in a single day. Larger or very overgrown properties can take longer; we'll tell you up front.")],
        sort=1),
    svc("Leaf Cleanup", "Leaves raked, blown and hauled away before the fall rain turns them into mush.", 17500, "from",
        ["Leaves cleared from lawn, beds and hardscapes", "Fir needles and small branches picked up", "Leaves cleared along fences and under shrubs",
         "Everything bagged or hauled away", "Walkways and driveway blown clean"],
        "Every leaf, gone before the rain.",
        ["Your trees dropped more than you can keep up with", "Wet leaves are smothering your lawn",
         "You want one clean-up before winter", "You'd like a second visit after the last leaves fall"],
        [("Timing matters in the Willamette Valley", "Wet leaves left on the lawn block sunlight and invite moss. Clearing them before the heavy rain keeps your grass healthy through winter."),
         ("Gone, not just piled", "We clear lawns, beds and corners, then haul the leaves away so nothing ends up in the street.")],
        [SIZE, ("Number of trees", "Big maples and oaks mean more volume."), HAUL, ACCESS],
        [("When should I schedule leaf cleanup?", "Late October through December is our busiest time. Many customers book one visit mid-season and one after the last leaves drop."),
         ("Do you haul the leaves away?", "Yes, unless you'd like to keep them for compost.")],
        sort=2),
    svc("Tree & Shrub Pruning", "Healthier, better-looking trees and shrubs, shaped the right way.", 15000, "from",
        ["Tree pruning for shape and clearance", "Shrub and hedge shaping", "Dead and damaged branch removal",
         "Branches cleared from roofs, walkways and windows", "All trimmings cleaned up and hauled away"],
        "Shaped right. Cleaned up after.",
        ["Branches are rubbing the roof or blocking a walkway", "Your hedges have lost their shape",
         "You have dead or broken branches after a storm", "You want your landscape to look cared for"],
        [("The right cut at the right time", "Good pruning helps plants stay healthy and grow back the way you want. We shape for the long run, not just for today."),
         ("No mess left behind", "Every trimming is raked up and hauled off. Your yard looks finished when we leave.")],
        [("Number of plants", "A few shrubs or a whole hedge line."), ("Height", "Ground-level shrubs or taller trees."), HAUL, ACCESS],
        [("Do you remove trees?", "We handle pruning and small trees. For large tree removal we'll tell you honestly if it needs a certified arborist."),
         ("When is the best time to prune?", "It depends on the plant. Most shrubs do well in late winter or after they flower. We'll tell you the right time for yours.")],
        sort=3),
    svc("Gutter Cleaning", "Clear gutters and downspouts so the rain goes where it should.", 15000, "from",
        ["Leaves, needles and debris removed from gutters", "Downspouts checked and cleared", "Debris cleaned up from the ground below",
         "Quick look for loose or damaged sections"],
        "Ready for the rainy season.",
        ["Water spills over your gutters when it rains", "You have tall trees near the house",
         "You'd rather not be on a ladder yourself", "You want it done before winter"],
        [("Done safely", "We bring the right ladders and gear, and we clean up everything that comes out of the gutters."),
         ("Pairs with leaf cleanup", "Book it with a leaf cleanup and get the whole property ready for winter in one visit.")],
        [("Home size", "Single-story or two-story."), ("Length of gutters", "How many feet of gutter we're cleaning."), CONDITION],
        [("How often should gutters be cleaned?", "Homes with trees nearby usually need it at least once a year, ideally late fall.")],
        sort=4),
    svc("Mulch Application", "Fresh mulch or bark dust for clean, healthy-looking beds.", 9500, "per cu. yard",
        ["Beds weeded and edged first", "Mulch or bark dust spread evenly", "Clean lines along lawn and walkways", "Walks and driveway blown clean"],
        "Fresh beds, clean edges.",
        ["Your beds look tired or patchy", "You want fewer weeds this season",
         "You're getting the house ready to sell", "You want to hold moisture in during summer"],
        [("Prep makes the difference", "We weed and edge before mulching, so the new layer looks sharp and lasts longer."),
         ("The right depth", "Too thin and weeds come through; too thick and plants suffer. We spread it at the right depth for your beds.")],
        [("Yards of mulch", "How much material your beds need."), ("Bed prep", "How much weeding and edging comes first."), ACCESS],
        [("Mulch or bark dust?", "Both work. Bark dust is the classic Oregon look; we'll help you pick the color and type.")],
        sort=5),
    svc("Pressure Washing", "Driveways, walkways and patios cleaned of moss, grime and stains.", 15000, "from",
        ["Driveways and walkways", "Patios and pavers", "Moss and grime removed", "Surrounding areas rinsed clean"],
        "Like-new driveways and patios.",
        ["Moss and green film make your walkways slippery", "You're getting the house ready to sell",
         "Your patio needs a refresh before summer", "Your driveway is stained or dark"],
        [("Right pressure for the surface", "Concrete, pavers and wood each need a different approach. We clean without damaging the surface."),
         ("A big visual difference", "A clean driveway and walkway change how the whole property looks from the street.")],
        [("Square footage", "How much surface we're cleaning."), ("Surface type", "Concrete, pavers or wood."), CONDITION],
        [("Will it damage my pavers or concrete?", "No. We adjust pressure and technique to each surface.")],
        sort=6),
    svc("Landscaping", "New beds, plants and yard makeovers designed around how you use your space.", 0, "",
        ["Planting beds and new plants", "Bed borders and edging", "Rock and bark dust installation", "Yard makeovers and refreshes"],
        "Your yard, reimagined.",
        ["You want to refresh tired or empty beds", "You just bought a home and want to make it yours",
         "You want curb appeal before selling", "You have a project in mind and need a crew"],
        [("We start by listening", "We walk the yard with you, talk about what you want and your budget, then give you a clear written estimate."),
         ("Built to be easy to maintain", "We choose plants and materials that look great and are easy to keep up in the Oregon climate.")],
        [("Project size", "One bed or the whole yard."), ("Materials", "Plants, rock, bark and borders."), ACCESS],
        [("Do you give free estimates for projects?", "Yes. Every landscaping estimate is free.")],
        sort=7),
    svc("Irrigation Installation", "Sprinkler and drip systems that water your lawn and beds the right way.", 0, "",
        ["Sprinkler system installation", "Drip irrigation for beds", "Timers and controllers", "Repairs and adjustments"],
        "The right water, in the right place.",
        ["You're tired of dragging hoses all summer", "Parts of your lawn dry out while others stay soggy",
         "You're installing new beds or lawn", "Your current system needs repairs"],
        [("Planned around your yard", "We lay out zones for sun, shade, lawn and beds so every area gets what it needs."),
         ("Save water", "A well-set system and timer uses less water than hand watering.")],
        [("Number of zones", "How many areas need their own watering."), ("Lawn or drip", "Sprinkler heads, drip lines or both."), ACCESS],
        [("Can you repair an existing system?", "Yes. Tell us what's happening and we'll take a look.")],
        sort=8),
    svc("Fence Installation", "New fences and fence repairs for privacy, pets and curb appeal.", 0, "",
        ["New fence installation", "Fence repairs and replacement sections", "Gates", "Old fence removal and haul-away"],
        "Privacy, built to last.",
        ["You need privacy from the street or neighbors", "You have pets or kids to keep in",
         "Your old fence is leaning or broken", "You want a finished look for your yard"],
        [("Clear estimate first", "We measure, talk through materials and give you a written price before we start."),
         ("Clean job site", "Old fence boards and debris leave with us.")],
        [("Length", "How many feet of fence."), ("Material and height", "Wood type and fence height."), ("Gates", "How many gates and what size.")],
        [("Do you remove the old fence?", "Yes, we can remove and haul away your old fence as part of the job.")],
        sort=9),
]

ADDONS = [
    {"name": "Hedge trimming", "price_cents": 7500, "unit_note": "", "sort": 0},
    {"name": "Extra yard-debris load", "price_cents": 11000, "unit_note": "per load", "sort": 1},
]

# Fotos reales de trabajos (carpeta fotos/, sin datos GPS y con la placa del carro difuminada).
# (servicio, foto "antes" o única, foto "después" o None, título, descripción, destacada)
MEDIA = [
    # videos (el primero de cada servicio sale grande en su página)
    ("mulch-application", "video-front-bed-bark-dust.mp4", None, "Front bed refresh",
     "Weedy strip turned into a clean bed with fresh bark dust and a crisp edge.", True),
    ("mulch-application", "video-walkway-bark-dust.mp4", None, "Walkway beds", "Fresh bark dust along the walkway and a tidy front lawn.", False),
    ("yard-cleanup", "video-backyard-cleanup.mp4", None, "Backyard cleanup", "An overgrown backyard, from start to finish.", True),
    ("tree-and-shrub-pruning", "video-shrub-trimming.mp4", None, "Shrub shaping", "Martin shaping a row of rounded shrubs.", True),
    ("mulch-application", "video-mulch-after-walkthrough.mp4", None, "Bark dust job, walkthrough",
     "Front beds, tree ring and side yard finished with fresh bark dust.", True),
    ("yard-cleanup", "video-mulch-before-walkthrough.mp4", None, "Before we started",
     "The same yard before the cleanup: weeds, leaves and branches everywhere.", False),
    # trabajos de noviembre 2026 (pares de antes y después)
    ("mulch-application", "mulch2-front-before.jpg", "mulch2-front-after.jpg", "Front yard bark dust",
     "Bare front beds cleaned up and finished with fresh bark dust.", True),
    ("mulch-application", "mulch2-fence-before.jpg", "mulch2-fence-after.jpg", "Fence line bed",
     "Weedy fence line turned into a clean, defined bed.", True),
    ("yard-cleanup", "mulch2-box-before.jpg", "mulch2-box-after.jpg", "Leaves and weeds cleared",
     "Overgrown corner cleared and finished with bark dust.", True),
    ("leaf-cleanup", "mulch2-side-before.jpg", "mulch2-side-after.jpg", "Side yard leaf cleanup",
     "Leaves removed and the bed refreshed.", True),
    ("leaf-cleanup", "job3-fence-leaves-before.jpg", "job3-fence-leaves-after.jpg", "Backyard leaves gone",
     "Fall leaves cleared along the fence and the bed covered with new mulch.", True),
    ("yard-cleanup", "job3-raised-bed-before.jpg", "job3-raised-bed-after.jpg", "Raised bed reset", "Leaves out, fresh soil and mulch in.", False),
    ("yard-cleanup", "job3-corner-before.jpg", "job3-corner-after.jpg", "Backyard corner", "Debris removed and the corner covered.", False),
    ("mulch-application", "job3-side-path-before.jpg", "job3-side-path-after.jpg", "Side path", "Narrow side path cleaned and mulched.", False),
    ("mulch-application", "job3-deck-bed-before.jpg", "job3-deck-bed-after.jpg", "Beds by the deck", "Leaves cleared and the beds finished in dark mulch.", True),
    ("mulch-application", "job4-driveway-before.jpg", "job4-driveway-after.jpg", "Driveway beds", "Faded beds along the driveway refreshed.", False),
    ("mulch-application", "job4-deck-before.jpg", "job4-deck-after.jpg", "Backyard slope", "Leaves out and the whole slope re-mulched.", False),
    ("mulch-application", "job5-side-before.jpg", "job5-side-after.jpg", "Side yard refresh", "Old faded bark replaced with a fresh layer.", False),
    ("mulch-application", "job5-front-before.jpg", "job5-front-after.jpg", "Front yard refresh", "Front beds topped up with fresh bark dust.", False),
    # trabajos de noviembre 2026 (fotos sueltas)
    ("mulch-application", "job6-front-wide.jpg", None, "Front lawn and beds", "Tree ring and curved front beds finished.", True),
    ("mulch-application", "job6-front-curve.jpg", None, "Curved front bed", "Clean edges and fresh bark dust.", False),
    ("mulch-application", "job6-front-rocks.jpg", None, "Rock garden bed", "Bark dust around the rocks and ground cover.", False),
    ("mulch-application", "job6-back-fence.jpg", None, "Backyard bed", "Fresh bark dust along the fence.", False),
    ("mulch-application", "job7-yellow-shrubs.jpg", None, "Shrub bed", "New bark dust with clean brick edging.", False),
    ("mulch-application", "job5-circle-bed.jpg", None, "Circle bed", "Fresh mulch around the shrubs.", False),
    ("mulch-application", "job3-window-bed.jpg", None, "Bed by the window", "A small bed, finished clean.", False),
    ("mulch-application", "job3-back-of-house.jpg", None, "Along the house", "New mulch along the foundation.", False),
    ("mulch-application", "mulch2-tree-bed.jpg", None, "Tree ring", "Fresh bark dust around the tree.", False),
    ("mulch-application", "job4-hedge-edge.jpg", None, "Hedge line", "Mulch along the hedges and a clean lawn edge.", False),
    # fotos
    ("yard-cleanup", "parking-strip-before.jpg", "parking-strip-after.jpg", "Parking strip cleared",
     "Weeds and overgrowth pulled from the strip, left clean right up to the curb.", True),
    ("yard-cleanup", "front-bed-before.jpg", "front-yard-after.jpg", "Front yard reset",
     "Overgrown front beds cleared and the whole frontage cleaned up.", True),
    ("yard-cleanup", "cleanup-backyard-cleared.jpg", None, "Backyard cut back",
     "An overgrown backyard cut down and cleared behind a freshly renovated home.", False),
    ("yard-cleanup", "cleanup-trailer-haul.jpg", None, "Everything hauled away",
     "Every load leaves with us — no piles left at the curb.", False),
    ("tree-and-shrub-pruning", "shrubs-and-lawn.jpg", None, "Shrubs shaped, lawn finished",
     "A row of hedges shaped and the lawn cleaned up afterwards.", True),
    ("tree-and-shrub-pruning", "shrub-shaped.jpg", None, "Clean, rounded shape", "Overgrown shrub trimmed back into a tidy form.", False),
    ("tree-and-shrub-pruning", "hedge-line.jpg", None, "Long hedge line", "Hedges trimmed and shaped along the property line.", False),
    ("tree-and-shrub-pruning", "hedge-trimming.jpg", None, "Hedge trimming in progress", "Squaring up an overgrown hedge.", False),
    ("lawn-maintenance", "lawn-blowing.jpg", None, "Weekly upkeep", "Mowed, trimmed and blown clean on every visit.", False),
]

# Reseñas reales de Google (enviadas por el cliente). Nombre + inicial del apellido.
REVIEWS = [
    ("Roth P.", "Mr. Martin did a wonderful job cleaning my front yard. His work was very professional, thorough, and high quality. "
                "What I appreciate most about Mr. Martin is how responsive he is whenever I contact him. He always responds promptly "
                "and even follows up afterward to make sure everything looks good."),
    ("Becky R.", "AMAZING WORK! Words can not express how great of a job he did. My lawn was very overgrown and out of control. "
                 "It took him just over three hours. My place has never looked this good. The price is more than fair. "
                 "I would recommend him to everyone."),
    ("Darla M.", "I have been using Big's Lawn Service for several months now. Martin is wonderful! He does a great job, always shows "
                 "up on time and goes above and beyond. I would highly recommend him and his landscaping company."),
    ("Karolina L.", "I highly recommend Martin. He always does a great job cleaning up the yard, trimming the trees, and whatever else "
                    "needs to be done around the yard. The garden looks tidy, and healthy afterward. He is professional, polite, "
                    "reliable and shows up on time."),
    ("Jezzy R.", "I can't say enough good things about Big's Lawn Service. Martin has been helping take care of my yard and the "
                 "difference is amazing. Every time he finishes, my lawn looks beautiful, clean, and very well maintained. "
                 "On top of the great service, his prices are very fair and affordable compared to other lawn services in Salem."),
    ("Blanca V.", "I highly recommend Big's lawn care service. Martin is reliable, professional, and always do a great job keeping my "
                  "yard looking clean and well maintained. If you're looking for someone trustworthy to take care of your lawn, "
                  "I definitely recommend."),
    ("Michael B.", "Big's Lawn Service always meets or exceeds my expectations. They always show up, as needed, and keep my yard "
                   "looking sharp. I highly recommend their services."),
]

# Preguntas por defecto que no aplican a BIG'S (o que afirman cosas sin confirmar)
FAQ_REMOVE = ("Can you remove blackberries?", "How can I pay?")


def configure(c, logo=None, photos=None, reviews=False):
    """Carga todo usando un cliente HTTP ya autenticado (httpx.Client o TestClient)."""
    content_es = json.loads((Path(__file__).parent / "content_es.json").read_text(encoding="utf-8"))
    c.put("/api/admin/settings", json={**SETTINGS, "content_es": content_es}).raise_for_status()

    # Actualiza en su lugar (por nombre) para no perder las fotos ligadas a cada servicio
    existing = {p["name"]: p for p in c.get("/api/admin/packages").json()}
    for pkg in PACKAGES:
        old = existing.pop(pkg["name"], None)
        if old:
            c.put(f"/api/admin/packages/{old['id']}", json=pkg).raise_for_status()
        else:
            c.post("/api/admin/packages", json=pkg).raise_for_status()
    for old in existing.values():   # servicios por defecto que BIG'S no ofrece
        c.delete(f"/api/admin/packages/{old['id']}").raise_for_status()

    for old in c.get("/api/admin/addons").json():
        c.delete(f"/api/admin/addons/{old['id']}").raise_for_status()
    for add in ADDONS:
        c.post("/api/admin/addons", json=add).raise_for_status()

    for faq in c.get("/api/admin/faqs").json():
        if faq["question"] in FAQ_REMOVE:
            c.delete(f"/api/admin/faqs/{faq['id']}").raise_for_status()

    if logo:
        with open(logo, "rb") as f:
            c.post("/api/admin/logo", files={"file": (os.path.basename(logo), f)}).raise_for_status()

    if photos:
        slugs = {p["slug"]: p["id"] for p in c.get("/api/admin/packages").json()}
        for old in c.get("/api/site").json()["media"]:
            c.delete(f"/api/admin/media/{old['id']}").raise_for_status()
        for slug, before, after, title, caption, featured in reversed(MEDIA):   # la primera queda arriba
            mime = "video/mp4" if before.endswith(".mp4") else "image/jpeg"
            files = {"file": (before, open(os.path.join(photos, before), "rb"), mime)}
            if after:
                files["after_file"] = (after, open(os.path.join(photos, after), "rb"), "image/jpeg")
            c.post("/api/admin/media", files=files, data={"title": title, "caption": caption, "package_id": str(slugs[slug]),
                                                         "featured": "true" if featured else "false"}).raise_for_status()
        hero = os.path.join(photos, "hero.jpg")
        if os.path.exists(hero):
            with open(hero, "rb") as f:
                c.post("/api/admin/hero", files={"file": ("hero.jpg", f, "image/jpeg")}).raise_for_status()
        banner = os.path.join(photos, "shrubs-and-lawn.jpg")   # trabajo con los pinos de Oregón de fondo
        if os.path.exists(banner):
            with open(banner, "rb") as f:
                c.post("/api/admin/banner", files={"file": ("banner.jpg", f, "image/jpeg")}).raise_for_status()

    if reviews:
        for old in c.get("/api/admin/testimonials").json():
            c.delete(f"/api/admin/testimonials/{old['id']}").raise_for_status()
        for i, (name, text) in enumerate(REVIEWS):
            c.post("/api/admin/testimonials", json={"name": name, "location": "Google review", "text": text, "rating": 5,
                                                    "sort": i}).raise_for_status()



def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8090")
    p.add_argument("--logo", help="archivo PNG/JPG/WEBP del logo")
    p.add_argument("--photos", help="carpeta con las fotos (fotos/); REEMPLAZA las fotos y la foto de portada")
    p.add_argument("--reviews", action="store_true", help="REEMPLAZA las reseñas por las de REVIEWS")
    a = p.parse_args()
    token = os.environ.get("JARDIN_ADMIN_TOKEN")
    if not token:
        sys.exit("Falta JARDIN_ADMIN_TOKEN")
    c = httpx.Client(base_url=a.url, headers={"Authorization": f"Bearer {token}"}, timeout=30)

    configure(c, a.logo, a.photos, a.reviews)

    pages = [f"{a.url}/services/{p['slug']}/" for p in c.get("/api/admin/packages").json()]
    print("Listo: BIG'S Lawn Service configurado (precios PROVISIONALES). Páginas de servicios:")
    print("\n".join("  " + u for u in pages))


if __name__ == "__main__":
    main()
