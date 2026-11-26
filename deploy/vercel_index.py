"""Punto de entrada para Vercel (vista previa de BIG'S Lawn Service).

Vercel no guarda archivos entre visitas: cada vez que arranca, se crea la base de datos en /tmp y se cargan
los datos, fotos, videos y reseñas de BIG'S. Los nombres de archivo se generan igual en todas las copias
del servidor para que las fotos funcionen sin importar qué copia responda.
"""
import os
import random
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "seed")]
os.environ.setdefault("JARDIN_DB_PATH", "/tmp/bigs.db")
os.environ.setdefault("JARDIN_UPLOAD_DIR", "/tmp/uploads")
os.environ.setdefault("JARDIN_TZ", "America/Los_Angeles")
os.environ.setdefault("JARDIN_NOINDEX", "1")

from fastapi.testclient import TestClient  # noqa: E402

import setup_bigs  # noqa: E402
from jardin.main import app  # noqa: E402


def _seed():
    db = app.state.db
    token = os.environ.get("JARDIN_ADMIN_TOKEN")
    if not token or db.one("SELECT 1 FROM settings WHERE k='_bigs_seeded'"):
        return
    rnd, original = random.Random(20261115), secrets.token_hex
    secrets.token_hex = lambda n=16: "%0*x" % (2 * n, rnd.getrandbits(8 * n))
    try:
        with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as c:
            setup_bigs.configure(c, logo=str(ROOT / "seed" / "logo.png"), photos=str(ROOT / "seed" / "fotos"), reviews=True)
    finally:
        secrets.token_hex = original
    db.execute("INSERT OR REPLACE INTO settings(k,v) VALUES('_bigs_seeded','1')")


_seed()
