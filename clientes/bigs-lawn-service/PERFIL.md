# Cliente: BIG'S Lawn Service LLC

Fuentes: flyer actual (`flyer-original.jpg`, 2026-11-15), logo enviado por el cliente (`logo-original.jpg`; versión
recortada con fondo transparente: `logo.png`) y página de referencia que les gusta (salemlawnservices.com, de otra empresa:
tomamos la **estructura y los botones**, no sus textos ni fotos).

## Datos confirmados
| Campo | Valor |
|---|---|
| Nombre | **BIG'S Lawn Service LLC** (en la página: "BIG'S Lawn Service") |
| Eslogan | *Beautiful Lawns, Healthy Landscapes* |
| Teléfono (llamadas y texto) | **(971) 388-0768** |
| Email | Martin.90.gallardo@gmail.com |
| Facebook | "BIG'S Lawn Service LLC" (falta el link exacto) |
| Google Maps | https://maps.app.goo.gl/okXsjKzeJbLh3smC9 |
| Seguro | Flyer: "We are insurance" → en la web: **"Fully insured"** |
| Zona | Salem, Oregon |
| Logo | ✅ recibido (verde oscuro + hojas verdes, fondo blanco) |

## Lo que pidieron (según la página de referencia)
- Página propia por servicio (`/services/<servicio>/`) con: ruta (Home / Services / …), frase corta, título
  "<Servicio> in Salem, OR", botones *Get a free quote* / *Call* / *Text us*, **What is included**, video,
  **A good fit if**, **How we work**, **What sets the price**, **Our work** (antes/después), **FAQ**,
  **Related services** y bloque **Request a free quote**.
- Formulario de cotización: nombre, teléfono, email, ciudad, servicios a elegir, notas, forma de contacto.
- **Sin** "mándanos fotos para cotizar" (lo pidieron quitar): no hay subida de fotos ni botón "Text photos".
- Barra superior, menú con servicios, menú hamburguesa en el celular, barra fija Call / Text / Free Quote,
  footer con Services / Service Areas / Company y política de privacidad.

## Servicios (10 páginas) — precios PROVISIONALES
| Página | Precio de arranque |
|---|---|
| Lawn Maintenance (semanal / cada 2 semanas / mensual) | $45 / visita |
| Yard Cleanup | $225 |
| Leaf Cleanup | $175 |
| Tree & Shrub Pruning | $150 |
| Gutter Cleaning | $150 |
| Mulch Application | $95 por yarda³ |
| Pressure Washing | $150 |
| Landscaping | Free quote |
| Irrigation Installation | Free quote |
| Fence Installation | Free quote |

Add-ons: Hedge trimming $75 · Extra yard-debris load $110.

## Pendiente de pedir al cliente
- [ ] **Precios reales** de cada servicio; precios semanal / cada 2 semanas / mensual / una vez.
- [ ] **Ciudades y ZIP codes** que cubren (¿Keizer? ¿Turner? ¿Silverton? ¿Woodburn?).
- [ ] Días, **horario** y cuántos trabajos por día.
- [ ] **Link** de Facebook y de Google Business Profile; si tienen reseñas en Google, la calificación real
      (ej. "4.9 stars from 40+ reviews") para mostrarla arriba.
- [x] Fotos de trabajos recibidas (12) + foto de portada. Faltan videos y más antes/después de otros servicios.
- [x] 7 reseñas reales de Google (todas de 5 estrellas) cargadas en la página.
- [ ] Formas de **pago** y si cobran al terminar o piden depósito (la sección de reservas dice "you pay after the job is done").
- [ ] Historia del negocio y nombre del dueño para la sección "About" (no asumimos "family-owned").
- [ ] ¿Usan WhatsApp?
- [x] Dominio comprado: **bigslawn.com** (GoDaddy, cuenta de Mario). Falta apuntarlo al servidor.

## Revisar con el cliente (importante)
1. **"We are insurance"** está mal dicho; lo correcto es **"We are insured"** / **"Fully insured"** (flyer, tarjetas, polos).
2. **Licencias en Oregon** (verificar con cada oficina; no es asesoría legal):
   *Landscaping* e *irrigation installation* normalmente requieren licencia del **Landscape Contractors Board (LCB)**;
   *fence installation*, del **Construction Contractors Board (CCB)**; aplicar herbicidas o productos para moss,
   licencia de pesticidas del **Oregon Department of Agriculture**. Si las tienen, se pone el número en la página;
   si no, conviene ocultar esos servicios (en el panel: Services → desmarcar "Show on website").
3. "Irrigation Installation" aparece dos veces en el flyer.

## Cargar estos datos en la página
```bash
JARDIN_ADMIN_TOKEN=... uvicorn app.main:app --port 8090 &
JARDIN_ADMIN_TOKEN=... python clientes/bigs-lawn-service/setup_bigs.py --url http://localhost:8090 \
    --logo clientes/bigs-lawn-service/logo.png
```
Reemplaza servicios (con el contenido de cada página), add-ons, quita preguntas que no aplican y sube el logo.
Después, todo se edita desde el panel `/admin`.

## Fotos (carpeta `fotos/`)
Procesadas antes de publicarlas: **sin datos GPS/EXIF** (las fotos de celular guardan la ubicación de la casa),
reducidas a 1600 px y con la **placa del carro difuminada** en `front-bed-before.jpg`.

| Servicio | Fotos |
|---|---|
| Yard Cleanup | Antes/después de la franja de banqueta · antes/después del frente · patio trasero · tráiler cargado |
| Tree & Shrub Pruning | Arbustos y pasto · arbusto redondeado · línea de setos · recorte en proceso |
| Lawn Maintenance | Soplado del pasto |
| Portada (fondo) | `hero.jpg` (pasto con arbustos redondos y pinos) |

No se usó `fence-bed-before.jpg` porque no hay foto "después" del mismo ángulo.

## Reseñas de Google
Cargadas a mano en la página (nombre + inicial del apellido): Roth P., Becky R., Darla M., Karolina L., Jezzy R.,
Blanca V., Michael B. Arriba de cada página de servicio se muestra "5-star reviews from Salem customers on Google".
Cuando lleguen reseñas nuevas, se agregan en el panel → Reviews.

### Conectar con Google (pasos para el cliente)
1. **Google Business Profile** → Editar perfil → *Website*: poner la dirección de la nueva página.
2. En el mismo perfil → *Ask for reviews* → copiar el enlace y ponerlo en el panel → Business info →
   *Google review link*. Así aparece el botón "Leave us a Google review" y el botón ⭐ en cada trabajo terminado.
3. **Google Search Console**: agregar el dominio y enviar `https://<dominio>/sitemap.xml` para que Google encuentre
   las 10 páginas de servicios.
4. (Opcional) **Reseñas automáticas**: con una clave de la Places API de Google (cuenta de Google Cloud con tarjeta),
   la página puede mostrar la calificación y las reseñas directamente desde Google. Esa API solo devuelve hasta
   5 reseñas y exige mostrar "Powered by Google".
