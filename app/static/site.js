// Partes comunes del sitio: barra superior, menú (con hamburguesa), footer, barra móvil y formulario de cotización.
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const svcUrl = p => `/services/${p.slug}/`;
let SITE = null;

// ------------------------------------------------------------------ idioma (inglés / español)
const LANG = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "es" || q === "en") { try { localStorage.setItem("lang", q); } catch {} return q; }
  try { const v = localStorage.getItem("lang"); if (v === "es" || v === "en") return v; } catch {}
  return (navigator.language || "").toLowerCase().startsWith("es") ? "es" : "en";
})();
document.documentElement.lang = LANG;
let DICT = {}, DICT_LC = {};
const ES_DAYS = {Monday: "lunes", Tuesday: "martes", Wednesday: "miércoles", Thursday: "jueves", Friday: "viernes", Saturday: "sábado", Sunday: "domingo"};
const ES_MONTHS = {January: "enero", February: "febrero", March: "marzo", April: "abril", May: "mayo", June: "junio", July: "julio",
  August: "agosto", September: "septiembre", October: "octubre", November: "noviembre", December: "diciembre"};
const DAY_RE = Object.keys(ES_DAYS).join("|"), MONTH_RE = Object.keys(ES_MONTHS).join("|");
const lower = s => s.charAt(0).toLowerCase() + s.slice(1);
function tr(s) {
  if (LANG !== "es" || !s) return s;
  if (DICT[s] !== undefined) return DICT[s];
  const lc = DICT_LC[s.toLowerCase()];
  if (lc !== undefined) return lc;
  for (const [re, fn] of PATTERNS) { const m = s.match(re); if (m) return fn(m); }
  return s;
}
const svc = s => lower(tr(s)).toLowerCase();
const PATTERNS = [
  [new RegExp(`^(.+) in ([A-Z][\\w .'-]+, [A-Z]{2})$`), m => `${tr(m[1])} en ${m[2]}`],
  [/^(.+), done right\.$/, m => `${tr(m[1])}`],
  [/^Price my (.+) →$/, m => `Cotizar ${svc(m[1])} →`],
  [/^Real (.+) jobs$/, m => `Trabajos reales de ${svc(m[1])}`],
  [/^(.+) questions$/, m => `Preguntas sobre ${svc(m[1])}`],
  [/^Get your (.+) price\.$/, m => `Obtenga su precio de ${svc(m[1])}.`],
  [/^Starting at (\$[\d,.]+)\s*(.*)$/, m => `Desde ${m[1]}${m[2] ? " " + tr(m[2]) : ""}`],
  [/^Save (\d+%)$/, m => `Ahorre ${m[1]}`],
  [/^Thanks, (.+)!$/, m => `¡Gracias, ${m[1]}!`],
  [/^Call or text (.+)$/, m => `Llame o escriba al ${m[1]}`],
  [/^Call (\(?\d[\d() .-]+)$/, m => `Llamar al ${m[1]}`],
  [/^Serving (.+) and nearby areas$/, m => `Servimos en ${m[1]} y alrededores`],
  [/^✓ Yes, we work in (.+)\.$/, m => `✓ Sí trabajamos en ${m[1]}.`],
  [/^(\S+) is outside our usual area\. Book anyway and we'll let you know if we can make it \(a travel fee may apply\)\.$/,
    m => `${m[1]} está fuera de nuestra zona habitual. Reserve de todos modos y le avisamos si podemos ir (puede haber un cargo por traslado).`],
  [new RegExp(`^(📅 )?(${DAY_RE}), (${MONTH_RE}) (\\d{1,2})$`), m => `${m[1] || ""}${ES_DAYS[m[2]]} ${m[4]} de ${ES_MONTHS[m[3]]}`],
  [new RegExp(`^(${MONTH_RE}) (\\d{4})$`), m => `${ES_MONTHS[m[1]]} de ${m[2]}`],
  [/^— (.+), owner$/, m => `— ${m[1]}, dueño`],
  [/^(\d+)\+ Google reviews$/, m => `Más de ${m[1]} reseñas en Google`],
  [/^Based on (\d+) Google reviews$/, m => `Según ${m[1]} reseñas en Google`],
];

function translateText(node) {
  const raw = node.nodeValue, t = raw.trim();
  if (!t) return;
  const out = tr(t);
  if (out !== t) node.nodeValue = raw.replace(t, out);
}
function translateTree(root) {
  if (LANG !== "es") return;
  if (root.nodeType === 3) { if (!root.parentElement?.closest(".review p, .review b, script, style, [data-notr]")) translateText(root); return; }
  if (root.nodeType !== 1 || root.closest?.(".review p, .review b, script, style, [data-notr]")) return;
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (w.nextNode()) nodes.push(w.currentNode);
  nodes.forEach(n => { if (!n.parentElement.closest(".review p, .review b, script, style, [data-notr]")) translateText(n); });
  const els = root.querySelectorAll ? [root, ...root.querySelectorAll("[placeholder],[aria-label]")] : [];
  els.forEach(el => ["placeholder", "aria-label"].forEach(a => { const v = el.getAttribute?.(a); if (v) { const o = tr(v.trim()); if (o !== v.trim()) el.setAttribute(a, o); } }));
}
function startTranslating() {
  translateTree(document.body);
  document.title = document.title.split(" · ").map(tr).join(" · ");
  new MutationObserver(ms => ms.forEach(m => {
    if (m.type === "characterData") translateTree(m.target);
    m.addedNodes.forEach(translateTree);
  })).observe(document.body, {childList: true, subtree: true, characterData: true});
}
function setupLangToggle() {
  $$("[data-lang-toggle]").forEach(b => {
    b.textContent = LANG === "es" ? "EN" : "ES";
    b.setAttribute("aria-label", LANG === "es" ? "View in English" : "Ver en español");
    b.onclick = () => {
      try { localStorage.setItem("lang", LANG === "es" ? "en" : "es"); } catch {}
      const u = new URL(location.href); u.searchParams.delete("lang"); location.href = u.toString();
    };
  });
}

// ------------------------------------------------------------------ de dónde llegó el cliente
// Se guarda la primera vez y se reemplaza solo si llega de una campaña nueva (utm, fbclid, gclid).
const SOURCE = (() => {
  const q = new URLSearchParams(location.search), get = k => (q.get(k) || "").trim();
  let src = "";
  if (get("utm_source")) src = [get("utm_source"), get("utm_medium"), get("utm_campaign")].filter(Boolean).join(" / ");
  else if (get("fbclid")) src = "Facebook / Instagram (ad)";
  else if (get("gclid") || get("gbraid") || get("wbraid")) src = "Google Ads";
  if (!src) {
    let saved = "";
    try { saved = localStorage.getItem("lead_source") || ""; } catch {}
    if (saved) return saved;
    let host = "";
    try { host = document.referrer ? new URL(document.referrer).hostname : ""; } catch {}
    if (host && host !== location.hostname) {
      src = /google\./.test(host) ? "Google (search / Maps)" : /facebook|fb\.|messenger/.test(host) ? "Facebook"
        : /instagram/.test(host) ? "Instagram" : /nextdoor/.test(host) ? "Nextdoor" : /bing\./.test(host) ? "Bing"
        : /yelp\./.test(host) ? "Yelp" : host;
    } else src = "Direct";
  }
  try { localStorage.setItem("lead_source", src); } catch {}
  return src;
})();

// ------------------------------------------------------------------ Pixel de Meta (solo si el negocio lo configuró)
function track(evt, data) { try { if (window.fbq) window.fbq("track", evt, data || {}); } catch {} }
function setupPixel(id) {
  if (!/^\d{6,20}$/.test(id || "")) return;
  !function (f, b, e, v, n, t, s) { if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
    if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0"; n.queue = []; t = b.createElement(e); t.async = !0; t.src = v;
    s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s); }(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
  window.fbq("init", id);
  window.fbq("track", "PageView");
  document.addEventListener("click", e => {
    const a = e.target.closest("a[href]"); if (!a) return;
    const h = a.getAttribute("href");
    if (/^(tel:|sms:|https:\/\/wa\.me)/.test(h)) track("Contact", {method: h.startsWith("tel:") ? "call" : h.startsWith("sms:") ? "text" : "whatsapp"});
  }, true);
}

async function loadSite() {
  const [site, ui] = await Promise.all([
    fetch("/api/site").then(r => r.json()),
    LANG === "es" ? fetch("/assets/i18n/es.json").then(r => r.json()).catch(() => ({})) : Promise.resolve({}),
  ]);
  SITE = site;
  if (LANG === "es") {
    DICT = Object.assign({}, ui, site.settings.content_es || {});
    for (const [k, v] of Object.entries(DICT)) DICT_LC[k.toLowerCase()] = v;
    startTranslating();
  }
  setupLangToggle();
  setupPixel(site.settings.meta_pixel_id);
  try {
    const day = new Date().toISOString().slice(0, 10);
    let first = false;
    try { first = localStorage.getItem("seen_day") !== day; localStorage.setItem("seen_day", day); } catch { first = true; }
    fetch("/api/visit", {method: "POST", headers: {"Content-Type": "application/json"}, keepalive: true,
      body: JSON.stringify({path: location.pathname, source: SOURCE, new_visitor: first, mobile: matchMedia("(max-width: 760px)").matches})});
  } catch {}
  return SITE;
}

function renderChrome(site, opts = {}) {
  const s = site.settings, quoteHref = opts.quoteHref || "/#book";
  $$("[data-s]").forEach(el => el.textContent = s[el.dataset.s] || "");
  $$("[data-tel]").forEach(a => { if (s.tel_link) { a.href = s.tel_link; a.hidden = false; } else a.style.display = "none"; });
  $$("[data-sms]").forEach(a => {
    const l = s.sms_link || s.whatsapp_link;
    if (l) { a.href = l; a.hidden = false; } else a.style.display = "none";
  });
  $$("[data-sms-only]").forEach(a => { if (s.sms_link) { a.href = s.sms_link; a.hidden = false; } else a.hidden = true; });
  $$("[data-wa]").forEach(a => { if (s.whatsapp_link) { a.href = s.whatsapp_link; a.hidden = false; } else a.hidden = true; });
  $$("[data-quote]").forEach(a => a.href = quoteHref);
  if (s.logo_url) $$(".brand").forEach(b => b.classList.add("has-logo"));
  if (s.logo_url) $$("[data-mark]").forEach(m => m.outerHTML = `<img class="logo" src="${esc(s.logo_url)}" alt="${esc(s.business_name)} logo">`);
  $$("[data-mark-footer]").forEach(m => { if (s.logo_url) m.outerHTML = `<img class="f-logo" src="${esc(s.logo_url)}" alt="">`; });
  if ($("#year")) $("#year").textContent = new Date().getFullYear();
  if ($("#f-place")) $("#f-place").textContent = [s.seo_services_text || "Lawn care & landscaping", [s.city, s.region].filter(Boolean).join(", ")].filter(Boolean).join(" · ");
  if ($("#f-legal")) $("#f-legal").textContent = s.legal_name || s.business_name;
  if ($("#f-license")) { if (s.license_text) $("#f-license").textContent = s.license_text; else $("#f-license").previousSibling.remove(); }
  if (s.promo_text && $("#promo")) { $("#promo").textContent = s.promo_text; $("#promo").hidden = false; }

  // menú de servicios (escritorio + hamburguesa + footer)
  const links = site.packages.map(p => `<a href="${svcUrl(p)}">${esc(p.name)}</a>`).join("");
  $$("[data-svc-menu]").forEach(el => el.innerHTML = links + `<a href="/#services" class="all">All services →</a>`);
  if ($("#f-services")) $("#f-services").innerHTML = links + `<a href="/#services">All services</a>`;
  if ($("#f-areas")) $("#f-areas").innerHTML = s.area_cities.map(c => `<span>${esc(c)}</span>`).join("") + `<a href="/#area">All areas</a>`;

  const c = [];
  if (s.phone_display) c.push(`Call or text <a href="${esc(s.tel_link)}">${esc(s.phone_display)}</a>`);
  if (s.email) c.push(`<a href="mailto:${esc(s.email)}">${esc(s.email)}</a>`);
  if (s.whatsapp_link) c.push(`<a href="${esc(s.whatsapp_link)}" target="_blank" rel="noopener">WhatsApp</a>`);
  if ($("#contact")) $("#contact").innerHTML = c.join("<br>");
  if ($("#social")) $("#social").innerHTML = [s.facebook && `<a href="${esc(s.facebook)}" target="_blank" rel="noopener">Facebook</a>`,
    s.instagram && `<a href="${esc(s.instagram)}" target="_blank" rel="noopener">Instagram</a>`,
    s.google_review_url && `<a href="${esc(s.google_review_url)}" target="_blank" rel="noopener">Google Reviews</a>`].filter(Boolean).join(" · ");

  // hamburguesa
  const burger = $("#burger"), drawer = $("#drawer");
  if (burger && drawer) {
    const set = open => { drawer.hidden = !open; burger.setAttribute("aria-expanded", open); document.body.classList.toggle("menu-open", open); };
    burger.onclick = () => set(drawer.hidden);
    drawer.addEventListener("click", e => { if (e.target.closest("a")) set(false); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") set(false); });
  }
  // desplegable "Services" en escritorio
  $$(".dd > button").forEach(b => b.onclick = () => { const open = b.getAttribute("aria-expanded") !== "true"; b.setAttribute("aria-expanded", open); });
  document.addEventListener("click", e => { if (!e.target.closest(".dd")) $$(".dd > button").forEach(b => b.setAttribute("aria-expanded", "false")); });
}

// Reseñas: calificación grande + botón a Google + carrusel con flechas
function renderReviews(box, site) {
  const s = site.settings, t = site.testimonials;
  if (!box || (!t.length && !s.google_rating)) { if (box) box.hidden = true; return; }
  const rating = s.google_rating ? parseFloat(s.google_rating) : t.reduce((a, r) => a + r.rating, 0) / t.length;
  const count = parseInt(s.google_review_count, 10);
  const countText = count ? `${count}+ Google reviews` : `Based on ${t.length} Google reviews`;
  const maps = s.google_maps_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([s.business_name, s.city, s.region].filter(Boolean).join(" "))}`;
  const full = Math.round(rating);
  box.hidden = false;
  box.innerHTML = `<div class="wrap">
    <div class="eyebrow">Reviews</div><h2 class="cond rev-h">What neighbors say</h2>
    <div class="rev-sum"><span class="rev-num">${rating.toFixed(1)}</span>
      <div><div class="stars" aria-label="${rating.toFixed(1)} out of 5 stars">${"★".repeat(full)}${"☆".repeat(5 - full)}</div><div class="muted">${esc(countText)}</div></div></div>
    <div class="rev-btns"><a class="btn dark" href="${esc(maps)}" target="_blank" rel="noopener">Read them on Google</a>
      ${s.google_review_url ? `<a class="btn line" href="${esc(s.google_review_url)}" target="_blank" rel="noopener">Leave us a Google review</a>` : ""}</div>
    ${t.length ? `<div class="rev-track" tabindex="0" aria-label="Customer reviews">${t.map(r => `<figure class="review">
        <div class="stars" aria-label="${r.rating} out of 5 stars">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</div>
        <blockquote><p>“${esc(r.text)}”</p></blockquote><figcaption><b>${esc(r.name)}</b> <span class="muted">${esc(r.location)}</span></figcaption></figure>`).join("")}</div>
      <div class="rev-nav"><button type="button" class="rev-prev" aria-label="Previous review">‹</button><button type="button" class="rev-next" aria-label="Next review">›</button></div>` : ""}
  </div>`;
  const track = box.querySelector(".rev-track");
  if (track) {
    const step = () => (track.querySelector(".review")?.offsetWidth || 300) + 16;
    box.querySelector(".rev-prev").onclick = () => track.scrollBy({left: -step(), behavior: "smooth"});
    box.querySelector(".rev-next").onclick = () => track.scrollBy({left: step(), behavior: "smooth"});
    const upd = () => {
      box.querySelector(".rev-prev").disabled = track.scrollLeft < 8;
      box.querySelector(".rev-next").disabled = track.scrollLeft + track.clientWidth > track.scrollWidth - 8;
      box.querySelector(".rev-nav").hidden = track.scrollWidth <= track.clientWidth + 8;
    };
    track.addEventListener("scroll", upd, {passive: true}); addEventListener("resize", upd); setTimeout(upd, 50);
  }
}

// Formulario "Request a free quote"
function renderQuoteForm(box, site, opts = {}) {
  const s = site.settings, pre = new Set(opts.preselect || []);
  box.innerHTML = `<form class="qform" novalidate>
    <h3 class="cond">Request a free quote</h3>
    <label class="f" for="q-name">Name</label><input id="q-name" name="name" autocomplete="name" required>
    <label class="f" for="q-phone">Phone</label><input id="q-phone" name="phone" type="tel" autocomplete="tel" inputmode="tel" required>
    <label class="f" for="q-email">Email (optional)</label><input id="q-email" name="email" type="email" autocomplete="email">
    <label class="f" for="q-city">City</label><input id="q-city" name="city" autocomplete="address-level2" placeholder="${esc(s.city || "")}">
    <span class="f">What needs doing?</span>
    <div class="pills">${site.packages.map(p => `<label class="pill"><input type="checkbox" name="svc" value="${esc(p.name)}" ${pre.has(p.name) ? "checked" : ""}><span>${esc(p.name)}</span></label>`).join("")}</div>
    <label class="f" for="q-notes">Tell us about the yard</label>
    <textarea id="q-notes" name="notes" placeholder="Front and back yard, leaves along the fence, beds need weeding…"></textarea>
    <label class="f" for="q-pref">Best way to reach you</label>
    <select id="q-pref" name="contact_pref"><option value="text">Text</option><option value="call">Phone call</option>${s.whatsapp ? `<option value="whatsapp">WhatsApp</option>` : ""}<option value="email">Email</option></select>
    <input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
    <button class="btn sun block" style="margin-top:16px">Send my quote request →</button>
    <div class="err" role="alert"></div>
    <p class="fine">We only use your info to reply to this request. See our <a href="/privacy">privacy policy</a>.</p>
  </form>`;
  const f = box.querySelector("form"), err = box.querySelector(".err"), btn = f.querySelector("button");
  f.onsubmit = async e => {
    e.preventDefault();
    const d = new FormData(f);
    const body = {name: d.get("name"), phone: d.get("phone"), email: d.get("email"), city: d.get("city"), notes: d.get("notes"),
      contact_pref: d.get("contact_pref"), services: d.getAll("svc").map(tr), page: opts.page || location.pathname, website: d.get("website"), lang: LANG, source: SOURCE};
    if (!body.name.trim() || !body.phone.trim()) { err.textContent = "Please add your name and phone number."; return; }
    btn.disabled = true; btn.textContent = "Sending…"; err.textContent = "";
    try {
      const r = await fetch("/api/quotes", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
      const j = await r.json();
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "Please check your name, phone and email.");
      const b = [];
      if (j.sms_url) b.push(`<a class="btn sun block" href="${esc(j.sms_url)}">Text us now</a>`);
      if (j.tel_url) b.push(`<a class="btn line block" href="${esc(j.tel_url)}">Call ${esc(s.phone_display)}</a>`);
      track("Lead", {content_name: body.services.join(", ")});
      box.innerHTML = `<div class="qdone"><div class="eyebrow">Request sent</div><h3 class="cond">Thanks, ${esc(body.name.split(" ")[0])}!</h3>
        <p>We got your request <b>${esc(j.id)}</b> and will reach out soon to set up your free estimate.</p>
        ${b.length ? `<p class="muted">Want a faster answer? Reach us directly:</p><div class="btns">${b.join("")}</div>` : ""}</div>`;
    } catch (x) { err.textContent = x.message; btn.disabled = false; btn.textContent = "Send my quote request →"; }
  };
}
