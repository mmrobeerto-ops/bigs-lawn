# creador-web

Motor de páginas web para negocios de servicios y una carpeta por cliente. Lista de clientes en `CLIENTES.md`.

---

# Sitio web + administración para empresa de lawn care y lot clearing (EE. UU.)

Página para negocios de **lawn mowing, seasonal cleanup y lot & brush clearing**, pensada para clientes en
Estados Unidos (texto en inglés, precios en dólares), con un panel para que el dueño lo maneje todo desde el celular.

## Lo que ve el cliente (`/`)
- **Banner de promoción** de temporada y teléfono siempre visible (click-to-call).
- **Instant Estimate** en la portada: servicio + tamaño del lote (acres) + estado + frecuencia → rango de precio al momento.
- **Services & Pricing** con precio inicial, qué incluye y "Most popular"; lista de **add-ons** con precio.
- **Planes recurrentes** (weekly / every 2 weeks / monthly / one-time) mostrando cuánto ahorra cada uno.
- **Before & After**: fotos y videos de trabajos, filtrables por servicio.
- **Reseñas** (solo si el dueño agrega reales) y botón para dejar reseña en Google.
- **Reserva en 3 pasos**: el jardín (con add-ons y estimado), el día (calendario con cupos reales) y los datos
  (ZIP, forma de contacto preferida). Termina con botones **Text us / WhatsApp / Call** con el mensaje ya escrito.
- **Comprobador de ZIP code** de la zona de servicio, **FAQ** y barra fija en el celular: **Call · Text · Free Estimate**.

## Lo que maneja el dueño (`/admin`)
| Pestaña | Para qué |
|---|---|
| 📋 Bookings | Reservas por día con estimado, lote, estado, frecuencia y add-ons; botones Text / Call / WhatsApp con mensaje listo; confirmar, completar, precio final, cambiar día, notas; **pedir reseña de Google** al terminar |
| 📅 Availability | Cerrar días o cambiar cuántos trabajos acepta |
| 💲 Services | Servicios, precio inicial, si admite planes recurrentes, destacado |
| ➕ Add-ons | Extras con precio |
| 🧮 Estimator | Multiplicadores por tamaño, estado y frecuencia; margen del rango (±%) |
| 🎬 Photos & videos | Subir before/after o enlazar YouTube |
| ⭐ Reviews / ❓ FAQ | Reseñas reales y preguntas frecuentes |
| ⚙️ Business info | Nombre, teléfono, WhatsApp, ZIP codes, promo, badges, métodos de pago, link de reseñas, horario, días, cupos |

Indicadores: por confirmar, hoy, 7 días, **dinero agendado (pipeline)**, clientes recurrentes y cobrado en el mes.

## Configurado para Salem, Oregon
- Hora del Pacífico (`America/Los_Angeles`), ZIP codes de Salem y Keizer (97301–97306, 97307, 97317).
- Título y datos para Google ("LocalBusiness" en Salem, OR) para aparecer en búsquedas locales.
- Servicios y FAQ del Noroeste del Pacífico: temporada de corte marzo–noviembre, lluvia, zarzamora (Himalayan
  blackberry), moss, aeration y "bark dust".

| Servicio (1/4 acre) | Desde |
|---|---|
| Lawn Mowing | $45 / visita semanal · ~$50 cada 2 semanas · ~$55 mensual · ~$65 una sola vez |
| Fall & Spring Cleanup | $225 |
| Blackberry & Brush Clearing | $300 (1 acre muy enmontado ≈ $1,300–$1,700) |
| Add-ons | Aeration $95 · Overseeding $85 · Moss & dethatch $150 · Hedges $75 · Bark dust $95/yd³ · Debris load $110 · Gutters $150 |

Son puntos de partida típicos, **no un estudio del mercado de Salem**: compara con 3–4 competidores locales
(Google Maps, Nextdoor, Thumbtack) y ajústalos a tus costos desde el panel.

**Antes de operar en Oregon (verifícalo con las autoridades, esto no es asesoría legal):**
- Registrar el negocio con la Secretaría de Estado de Oregon (Corporation Division).
- El mantenimiento (cortar, podar, limpiar) normalmente no requiere licencia del Landscape Contractors Board (LCB),
  pero trabajos de instalación/paisajismo sí. Pregunta al LCB qué servicios ofreces exactamente.
- Aplicar herbicidas o productos para moss a clientes requiere licencia de pesticidas del Oregon Department of Agriculture.
- Seguro de responsabilidad civil; si contratas ayudantes, workers' comp.

## Probarlo
```bash
cd creador-web
pip install -r requirements.txt
JARDIN_ADMIN_TOKEN=elige-un-token-largo uvicorn app.main:app --port 8090
```
Página: http://localhost:8090 · Panel: http://localhost:8090/admin · Pruebas: `python -m pytest -q`

Variables: `JARDIN_ADMIN_TOKEN` (obligatoria), `JARDIN_TZ` (por defecto `America/Los_Angeles`, Salem OR),
`JARDIN_DB_PATH`, `JARDIN_UPLOAD_DIR`, `JARDIN_MAX_VIDEO_MB`.

## Notas
- Las reseñas empiezan vacías a propósito: solo se deben publicar reseñas reales. Lo mismo con "Licensed & insured".
- Una base de datos de la versión anterior se actualiza sola al arrancar.
- Protecciones: no se puede sobre-reservar un día, anti-spam y límite de solicitudes, solo fotos/videos, panel con token.
