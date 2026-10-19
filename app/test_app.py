import os
import tempfile
from datetime import date, timedelta

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["API_KEY"] = "test"
os.environ["N8N_WEBHOOK_URL"] = ""
os.environ["SEED"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from main import app, con_dias  # noqa: E402

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
    r = c.post("/apartados", data=NUEVO | {"abono_inicial": 2, "forma_pago": "efectivo"})
    assert r.status_code == 422 and "abono inicial mínimo" in r.text and "Carmen Ruiz" in r.text  # no se pierde lo escrito
    assert c.get("/apartados/nuevo").status_code == 200
    assert c.get("/?estado=&q=Carmen&pagina=99").status_code == 200
    assert c.get("/ventas?pagina=2").status_code == 200


def test_datos_de_ejemplo():
    import main
    from seed import seed

    main.DB_PATH = os.path.join(tempfile.mkdtemp(), "seed.db")
    with main.db() as con:
        con.executescript(main.SCHEMA)
    seed(main.crear_apartado, main.registrar_abono, main.registrar_venta, main.vencer_apartado)
    activos = c.get("/api/apartados?estado=activo").json()
    hoy = date.today()
    limites = {date.fromisoformat(a["fecha_limite"]) - hoy for a in activos}
    assert {timedelta(days=7), timedelta(days=1)} <= limites  # recordatorios
    assert any(d < timedelta(0) for d in limites)  # fuera de plazo pendientes de vencer
    assert c.get("/api/apartados?estado=liquidado").json() and c.get("/api/vales").json()
    assert c.get(f"/api/ventas?desde={hoy}&hasta={hoy}").json() or hoy.weekday() == 6
    # Los correos de data/correos/ cuentan con estos apartados de ejemplo.
    por_id = {a["id"]: con_dias(a) for a in c.get("/api/apartados").json()}
    assert por_id[1]["cliente"] == "Carmen Ruiz" and por_id[1]["pendiente"] >= 10
    assert por_id[3]["cliente"] == "Lucía Gómez" and por_id[3]["pendiente"] == 12  # liquida
    assert por_id[12]["cliente"] == "Laura Ortega" and por_id[12]["pendiente"] < 15  # paga de más
    assert por_id[16]["cliente"] == "Paula Ramos" and por_id[16]["dias"] < 0  # fuera de plazo
    assert por_id[24]["cliente"] == "Silvia Cortés" and por_id[24]["pendiente"] >= 5


def test_swagger_muestra_authorize():
    esquemas = TestClient(app).get("/openapi.json").json()["components"]["securitySchemes"]
    assert any(e["type"] == "apiKey" and e["name"] == "X-API-Key" for e in esquemas.values())
