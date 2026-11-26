# Montar páginas de clientes en tu servidor (y meterlas a la red TZANIX)

La idea es simple. Cada página de cliente vive en un servidor tuyo con nginx, y ese mismo servidor
se conecta al hub de TZANIX en Tokio. Así cada cliente nuevo es una página más y, de paso, un nodo
más de la red. Con dos o tres ya se empieza a ver el consenso funcionando con tráfico de verdad.

## Lo que necesitas

Un servidor Ubuntu (22.04 o 24.04) con acceso por SSH. Puede ser el de Tokio, que ya tiene nginx y
certbot, o uno nuevo. Para clientes de Salem, Oregon conviene uno de Vultr en Seattle: queda cerca
de los clientes y cuesta lo mismo que el de Tokio.

Y el dominio del cliente, con un registro A apuntando a la IP del servidor:

```
Tipo A   bigslawn.com       →  IP-DEL-SERVIDOR
Tipo A   www.bigslawn.com   →  IP-DEL-SERVIDOR
```

Si el dominio está en Cloudflare, deja la nube en gris (solo DNS) mientras se saca el certificado.

## Instalar la página

```bash
git clone git@github.com:mmrobeerto-ops/creador-web.git
cd creador-web
sudo ADMIN_USER=martin bash deploy/servidor/instalar-sitio.sh  bigs  bigslawn.com  tu@correo.com  8101
sudo bash deploy/servidor/cargar-bigs.sh  bigs
```

El primer comando deja la página corriendo, con HTTPS si el DNS ya apunta, y al final te muestra la
contraseña del panel. Guárdala. El segundo carga todo lo de BIG'S (servicios, fotos, videos,
reseñas, logo y el español).

Si el DNS todavía no estaba listo, cuando ya apunte vuelve a correr el primer comando y se activa el
HTTPS. No se pierde nada, porque los datos viven aparte.

Para otro cliente en el mismo servidor usa otro nombre y otro puerto, por ejemplo
`... instalar-sitio.sh  jose  joseslawn.com  tu@correo.com  8102`.

## Dónde queda cada cosa

La app está en `/opt/sitios/bigs`. Los datos (cotizaciones, reservas, fotos) están en
`/var/lib/sitios/bigs`, y eso es lo que importa respaldar. Hay una copia diaria a las 3:30 am en
`/var/backups/sitios/bigs` que guarda 14 días. La contraseña y las llaves están en
`/etc/sitios/bigs.env`, que solo root puede leer.

Comandos útiles:

```bash
systemctl status sitio-bigs              # ¿está corriendo?
journalctl -u sitio-bigs -n 50           # últimos mensajes si algo falla
sudo systemctl restart sitio-bigs        # reiniciarla
```

Para actualizar la página después de un cambio: `git pull` y vuelve a correr `instalar-sitio.sh`
con los mismos datos. No toca la contraseña ni los datos.

## Conectarla a TZANIX

nginx escribe también en `/var/log/nginx/access.log`, que es el que lee el vigilante. Si es un
servidor nuevo, instala el guard como lo hiciste en Tokio. Después, en Tokio, crea la llave del
nodo:

```bash
bash ~/tzanix/mesh/deploy/crear-llave.sh "bigs-seattle"
```

Y en el servidor nuevo, con la llave que te dio:

```bash
git clone https://github.com/mmrobeerto-ops/tzanix.git ~/tzanix
sudo bash ~/tzanix/mesh/deploy/install-agent.sh  https://202.182.96.167.nip.io  LA_LLAVE
```

Con eso ya son dos servidores reportando. En el `/stats` del hub `clientes_activos` debe subir a 2.

## Lo que no hace este script

No toca el firewall, porque de eso se encarga TZANIX. No instala el guard, que está en su propio
repositorio. Y no publica nada en Google: eso se hace en Search Console y en el perfil de Google
Business del cliente, poniendo la dirección nueva.
