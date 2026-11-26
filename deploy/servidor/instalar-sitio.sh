#!/usr/bin/env bash
# =============================================================================
#  instalar-sitio.sh — monta una página de cliente (jardineria) en un servidor Ubuntu con nginx.
#
#  Desde la carpeta raíz del repositorio creador-web, como root:
#     sudo bash deploy/servidor/instalar-sitio.sh  SLUG  DOMINIO  CORREO  [PUERTO]
#  Ejemplo:
#     sudo ADMIN_USER=martin bash deploy/servidor/instalar-sitio.sh  bigs  bigslawn.com  tu@correo.com  8101
#
#  Qué deja listo:
#   - la app en /opt/sitios/SLUG (con su propio entorno de Python)
#   - los datos (cotizaciones, reservas, fotos) en /var/lib/sitios/SLUG  ← esto es lo que se respalda
#   - un servicio systemd "sitio-SLUG" que arranca solo si el servidor se reinicia
#   - nginx sirviendo el dominio, y HTTPS con Let's Encrypt si el DNS ya apunta aquí
#   - copia de seguridad diaria (se guardan 14 días) en /var/backups/sitios/SLUG
#   - nginx también escribe en /var/log/nginx/access.log, que es el que lee el vigilante de TZANIX
#
#  Se puede volver a correr para actualizar la app: no toca los datos ni cambia la contraseña.
# =============================================================================
set -euo pipefail

SLUG="${1:-}"; DOMINIO="${2:-}"; CORREO="${3:-}"; PUERTO="${4:-8101}"
ADMIN_USER="${ADMIN_USER:-admin}"
TZ_SITIO="${TZ_SITIO:-America/Los_Angeles}"

if [ -z "$SLUG" ] || [ -z "$DOMINIO" ] || [ -z "$CORREO" ]; then
  echo "Uso: sudo [ADMIN_USER=usuario] bash $0 SLUG DOMINIO CORREO [PUERTO]"; exit 1
fi
[[ "$SLUG" =~ ^[a-z0-9-]+$ ]] || { echo "El SLUG solo puede llevar minúsculas, números y guiones."; exit 1; }
[[ "$PUERTO" =~ ^[0-9]+$ ]] || { echo "PUERTO debe ser un número."; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo "Córrelo con sudo."; exit 1; }

SRC="$(cd "$(dirname "$0")/../.." && pwd)"          # raíz del repositorio
[ -f "$SRC/app/main.py" ] || { echo "No encuentro $SRC/app/main.py"; exit 1; }
APP="/opt/sitios/$SLUG"; DATA="/var/lib/sitios/$SLUG"; ENVF="/etc/sitios/$SLUG.env"; BK="/var/backups/sitios/$SLUG"

echo "==> Paquetes (python, nginx, certbot, sqlite)"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv nginx certbot python3-certbot-nginx sqlite3 curl >/dev/null

echo "==> Usuario de sistema 'sitios' (sin acceso de login)"
id -u sitios >/dev/null 2>&1 || useradd --system --home-dir /var/lib/sitios --shell /usr/sbin/nologin sitios

echo "==> Copiando la app a $APP"
mkdir -p "$APP" "$DATA/uploads" /etc/sitios "$BK"
rm -rf "$APP/app.nuevo"
cp -r "$SRC/app" "$APP/app.nuevo"
find "$APP/app.nuevo" -name "__pycache__" -prune -exec rm -rf {} +
rm -rf "$APP/app"; mv "$APP/app.nuevo" "$APP/app"
cp "$SRC/requirements.txt" "$APP/requirements.txt"
[ -d "$APP/venv" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q --upgrade pip
"$APP/venv/bin/pip" install -q -r "$APP/requirements.txt" "uvicorn>=0.22"

if [ ! -f "$ENVF" ]; then
  echo "==> Creando $ENVF (contraseña y llaves nuevas)"
  rnd() { openssl rand -base64 32 | tr -d '/+=' | cut -c1-"$1"; }
  PASS="$(rnd 16)"
  cat > "$ENVF" <<EOF
SITIO_PUERTO=$PUERTO
JARDIN_DB_PATH=$DATA/sitio.db
JARDIN_UPLOAD_DIR=$DATA/uploads
JARDIN_TZ=$TZ_SITIO
JARDIN_ADMIN_USER=$ADMIN_USER
JARDIN_ADMIN_PASSWORD=$PASS
JARDIN_ADMIN_TOKEN=$(rnd 40)
JARDIN_SESSION_SECRET=$(rnd 48)
EOF
  NUEVA_PASS="$PASS"
else
  echo "==> $ENVF ya existe: se conserva la contraseña"
  NUEVA_PASS=""
fi
chmod 600 "$ENVF"; chown root:root "$ENVF"
chown -R sitios:sitios "$DATA"

echo "==> Servicio systemd sitio-$SLUG"
cat > "/etc/systemd/system/sitio-$SLUG.service" <<EOF
[Unit]
Description=Sitio web $SLUG ($DOMINIO)
After=network.target

[Service]
User=sitios
Group=sitios
EnvironmentFile=$ENVF
WorkingDirectory=$APP
ExecStart=$APP/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $PUERTO --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$DATA

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable "sitio-$SLUG" >/dev/null
systemctl restart "sitio-$SLUG"

echo "==> nginx para $DOMINIO"
CONF="/etc/nginx/sites-available/sitio-$SLUG.conf"
if [ ! -f "$CONF" ]; then
  cat > "$CONF" <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name __DOMINIO__ www.__DOMINIO__;

    client_max_body_size 160m;                 # videos de trabajos
    access_log /var/log/nginx/access.log;      # el vigilante de TZANIX lee este
    access_log /var/log/nginx/sitio-__SLUG__.access.log;

    location / {
        proxy_pass http://127.0.0.1:__PUERTO__;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;   # se reemplaza, no se suma: nadie puede falsificar su IP
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF
  sed -i "s/__DOMINIO__/$DOMINIO/g; s/__SLUG__/$SLUG/g; s/__PUERTO__/$PUERTO/g" "$CONF"
  ln -sf "$CONF" "/etc/nginx/sites-enabled/sitio-$SLUG.conf"
fi
nginx -t
systemctl reload nginx

echo "==> HTTPS"
MI_IP="$(curl -4 -s --max-time 8 https://api.ipify.org || true)"
DNS_IP="$(getent ahostsv4 "$DOMINIO" | awk 'NR==1{print $1}' || true)"
if [ -n "$MI_IP" ] && [ "$MI_IP" = "$DNS_IP" ]; then
  DOMS=(-d "$DOMINIO")
  WWW_IP="$(getent ahostsv4 "www.$DOMINIO" | awk 'NR==1{print $1}' || true)"
  [ "$WWW_IP" = "$MI_IP" ] && DOMS+=(-d "www.$DOMINIO")
  certbot --nginx "${DOMS[@]}" --redirect -m "$CORREO" --agree-tos -n
  URL="https://$DOMINIO"
else
  echo "   OJO: $DOMINIO todavía no apunta a este servidor ($MI_IP; DNS dice: ${DNS_IP:-nada})."
  echo "   Cuando el registro A esté listo, vuelve a correr este mismo comando y se activa HTTPS."
  URL="http://$DOMINIO"
fi

echo "==> Copia de seguridad diaria (3:30 am, se guardan 14 días)"
cat > "/etc/cron.d/sitio-$SLUG" <<EOF
30 3 * * * root sqlite3 $DATA/sitio.db ".backup '$BK/sitio-\$(date +\%F).db'" && tar czf $BK/uploads-\$(date +\%F).tgz -C $DATA uploads && find $BK -type f -mtime +14 -delete
EOF

sleep 2
if curl -s --max-time 5 -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PUERTO/" | grep -q 200; then
  echo "==> La app responde bien en 127.0.0.1:$PUERTO"
else
  echo "==> La app no responde todavía. Revisa:  journalctl -u sitio-$SLUG -n 50"
fi

echo
echo "LISTO."
echo "  Página:  $URL"
echo "  Panel:   $URL/admin"
echo "  Usuario: $ADMIN_USER"
if [ -n "$NUEVA_PASS" ]; then
  echo "  Contraseña: $NUEVA_PASS   ← guárdala, no se vuelve a mostrar (está en $ENVF)"
fi
