#!/usr/bin/env bash
# Carga los datos de BIG'S Lawn Service (servicios, fotos, videos, reseñas, logo, español) en un sitio ya instalado.
#   Desde la raíz del repositorio creador-web:   sudo bash deploy/servidor/cargar-bigs.sh  [SLUG]
# Se puede volver a correr; las fotos y reseñas se reemplazan por las de la carpeta del cliente.
set -euo pipefail
SLUG="${1:-bigs}"
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
ENVF="/etc/sitios/$SLUG.env"
[ -f "$ENVF" ] || { echo "No existe $ENVF. Primero corre instalar-sitio.sh"; exit 1; }
set -a; . "$ENVF"; set +a
C="$SRC/clientes/bigs-lawn-service"
"/opt/sitios/$SLUG/venv/bin/python" "$C/setup_bigs.py" --url "http://127.0.0.1:$SITIO_PUERTO" \
  --logo "$C/logo.png" --photos "$C/fotos" --reviews
