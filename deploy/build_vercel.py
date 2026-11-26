"""Arma la carpeta lista para subir a Vercel:  python deploy/build_vercel.py  ->  deploy/out/bigs-lawn-service/

Después:  cd deploy/out/bigs-lawn-service && npx vercel deploy --prod -e JARDIN_ADMIN_TOKEN=<clave-del-panel>

Vercel detecta FastAPI por sí solo y usa `index.py` (en la raíz) como punto de entrada. El paquete de la app
se copia como `jardin/` para que Vercel no lo confunda con otro punto de entrada.
"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out" / "bigs-lawn-service"
CLIENT = ROOT / "clientes" / "bigs-lawn-service"

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
shutil.copytree(ROOT / "app", OUT / "jardin", ignore=shutil.ignore_patterns("__pycache__"))
(OUT / "seed").mkdir()
shutil.copy(CLIENT / "setup_bigs.py", OUT / "seed")
shutil.copy(CLIENT / "logo.png", OUT / "seed")
shutil.copy(CLIENT / "content_es.json", OUT / "seed")
(OUT / ".vercelignore").write_text(".env*\n.vercel\n")
shutil.copytree(CLIENT / "fotos", OUT / "seed" / "fotos")
shutil.copy(HERE / "vercel_index.py", OUT / "index.py")
# tzdata: los servidores de Vercel no traen la base de zonas horarias que usa zoneinfo
(OUT / "requirements.txt").write_text("fastapi>=0.100.0\npydantic>=2.0\npython-multipart>=0.0.6\nhttpx>=0.24.0\ntzdata\n")
(OUT / ".python-version").write_text("3.12\n")
print(OUT)
