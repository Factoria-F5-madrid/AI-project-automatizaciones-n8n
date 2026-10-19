import os
import tempfile
from datetime import date, timedelta

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["API_KEY"] = "test"
os.environ["N8N_WEBHOOK_URL"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

c = TestClient(app, headers={"X-API-Key": "test"})
NUEVO = {"cliente": "Carmen Ruiz", "producto": "Botín piel marrón", "talla": "38", "precio": 89.9, "abono_inicial": 10}


def test_requiere_api_key():
    assert TestClient(app).get("/api/apartados").status_code == 401


def test_ciclo_completo_hasta_liquidar():
    a = c.post("/api/apartados", json=NUEVO).json()
    assert a["pendiente"] == 79.9 and a["estado"] == "activo"
    assert a["fecha_limite"] == (date.today() + timedelta(days=90)).isoformat()
    assert c.post(f"/api/apartados/{a['id']}/abonos", json={"importe": 100}).status_code == 422  # pagar de más
    a = c.post(f"/api/apartados/{a['id']}/abonos", json={"importe": 79.9}).json()
    assert a["pendiente"] == 0 and a["estado"] == "liquidado"
    assert c.post(f"/api/apartados/{a['id']}/abonos", json={"importe": 1}).status_code == 422


def test_abono_inicial_minimo():
    assert c.post("/api/apartados", json=NUEVO | {"abono_inicial": 4}).status_code == 422


def test_vencimiento_genera_vale():
    viejo = (date.today() - timedelta(days=100)).isoformat()
    a = c.post("/api/apartados", json=NUEVO | {"fecha": viejo}).json()
    nuevo = c.post("/api/apartados", json=NUEVO).json()
    assert c.post(f"/api/apartados/{nuevo['id']}/vencer").status_code == 422  # aún en plazo
    r = c.post(f"/api/apartados/{a['id']}/vencer").json()
    assert r["apartado"]["estado"] == "vencido" and r["vale"]["importe"] == 10


def test_ventas_por_fecha_y_excel():
    c.post("/api/ventas", json={"concepto": "Crema calzado", "importe": 4.5})
    hoy = date.today().isoformat()
    assert len(c.get(f"/api/ventas?desde={hoy}&hasta={hoy}").json()) == 1
    assert c.get("/excel").content[:2] == b"PK"  # xlsx es un zip


def test_pantallas():
    assert c.get("/").status_code == 200
    r = c.post("/apartados", data=NUEVO | {"abono_inicial": 2, "forma_pago": "efectivo"}, follow_redirects=True)
    assert "abono inicial mínimo" in r.text
