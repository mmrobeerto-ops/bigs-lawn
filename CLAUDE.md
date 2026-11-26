# creador-web

Motor de páginas web para negocios de servicios (lawn care, limpieza, etc.) + una carpeta por cliente.

- `app/` — el motor (FastAPI + SQLite + HTML/JS sin framework). Igual para todos los clientes.
- `clientes/<cliente>/` — datos, fotos, logo, publicidad y script de carga de cada cliente.
- `deploy/servidor/` — instalador para Ubuntu (nginx + certbot + systemd). `deploy/build_vercel.py` solo para vistas previas.
- `CLIENTES.md` — lista de clientes, dominios, servidores y puertos.

Reglas:
- Pruebas: `python -m pytest -q` (deben pasar antes de cada commit).
- Fotos de clientes: quitar EXIF/GPS y difuminar números de casa y placas antes de subirlas.
- Nunca guardar contraseñas, tokens ni llaves en el repositorio.
- El usuario habla español; textos de las páginas en inglés con traducción en `app/static/i18n/es.json` y `clientes/*/content_es.json`.
