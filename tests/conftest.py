import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["JARDIN_DB_PATH"] = os.path.join(_tmp, "import.db")
os.environ["JARDIN_UPLOAD_DIR"] = os.path.join(_tmp, "up")
os.environ["JARDIN_ADMIN_TOKEN"] = "admintest"

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ADMIN = {"Authorization": "Bearer admintest"}


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "t.db"), tmp_path / "uploads")
    with TestClient(app) as c:
        c.db = app.state.db
        c.uploads = tmp_path / "uploads"
        yield c
