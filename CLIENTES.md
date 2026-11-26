# Clientes

Una fila por página web. Sin contraseñas aquí: esas van en el gestor de contraseñas.

| Cliente | Carpeta | Dominio | Servidor | Puerto | Estado |
|---|---|---|---|---|---|
| BIG'S Lawn Service LLC (Salem, OR) | `clientes/bigs-lawn-service` | bigslawn.com (GoDaddy) | DigitalOcean SFO2 "Bigs-pro" · 167.99.160.90 | 8101 | Activo |

## Cliente nuevo, paso a paso
1. Copia `clientes/bigs-lawn-service` a `clientes/<nombre>` y cambia los datos en su `setup_*.py` y `PERFIL.md`.
2. Agrega la fila arriba (usa el siguiente puerto libre: 8102, 8103…).
3. En el servidor: `sudo ADMIN_USER=<usuario> bash deploy/servidor/instalar-sitio.sh <slug> <dominio> <correo> <puerto>`.
4. Carga sus datos con su script y apunta el dominio (registro A) a la IP del servidor.
