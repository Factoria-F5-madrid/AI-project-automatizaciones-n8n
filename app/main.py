"""Zapatería Paso Firme: registro de apartados, abonos y ventas.

La app guarda los datos y aplica las reglas del apartado.
Las automatizaciones (avisos, recordatorios, cierres, informes) son trabajo de n8n,
que se integra por la API (/api, documentada en /docs) y recibe eventos por webhook.
"""

import io
import json
import logging
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import date, timedelta

from fastapi import BackgroundTasks, Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "tienda.db")
API_KEY = os.getenv("API_KEY", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
ABONO_MINIMO = 5
PLAZO_DIAS = 90
FORMAS_PAGO = ["efectivo", "tarjeta", "bizum"]

log = logging.getLogger("tienda")
app = FastAPI(title="Zapatería Paso Firme", description="API para integrar n8n con la tienda.")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS apartados (
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, cliente TEXT NOT NULL, telefono TEXT, email TEXT,
  producto TEXT NOT NULL, talla TEXT, precio REAL NOT NULL, fecha_limite TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'liquidado', 'vencido')));
CREATE TABLE IF NOT EXISTS abonos (
  id INTEGER PRIMARY KEY, apartado_id INTEGER NOT NULL REFERENCES apartados(id),
  fecha TEXT NOT NULL, importe REAL NOT NULL CHECK (importe > 0), forma_pago TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ventas (
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, concepto TEXT NOT NULL,
  importe REAL NOT NULL CHECK (importe > 0), forma_pago TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS vales (
  id INTEGER PRIMARY KEY, codigo TEXT UNIQUE NOT NULL, apartado_id INTEGER NOT NULL REFERENCES apartados(id),
  fecha TEXT NOT NULL, importe REAL NOT NULL, usado INTEGER NOT NULL DEFAULT 0);
"""

APARTADOS_SQL = """
SELECT a.*, ROUND(COALESCE(SUM(b.importe), 0), 2) AS abonado,
       ROUND(a.precio - COALESCE(SUM(b.importe), 0), 2) AS pendiente
FROM apartados a LEFT JOIN abonos b ON b.apartado_id = a.id
"""


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


with db() as con:
    con.executescript(SCHEMA)


def rows(sql, *args):
    with db() as con:
        return [dict(r) for r in con.execute(sql, args)]


def get_apartado(apartado_id):
    found = rows(APARTADOS_SQL + " WHERE a.id = ? GROUP BY a.id", apartado_id)
    if not found:
        raise HTTPException(404, "Apartado no encontrado")
    return found[0]


def notify(evento, datos):
    """Envía el evento a n8n. Si n8n no responde, la tienda sigue funcionando."""
    if not N8N_WEBHOOK_URL:
        return
    body = json.dumps({"evento": evento, "datos": datos}, default=str).encode()
    req = urllib.request.Request(N8N_WEBHOOK_URL, body, {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log.warning("No se pudo avisar a n8n (%s): %s", evento, e)


# --- Reglas del negocio -------------------------------------------------------

def crear_apartado(cliente, telefono, email, producto, talla, precio, abono_inicial, forma_pago, fecha=None):
    fecha = fecha or date.today()
    if precio <= 0:
        raise ValueError("El precio debe ser mayor que 0")
    if abono_inicial < ABONO_MINIMO:
        raise ValueError(f"El abono inicial mínimo es de {ABONO_MINIMO} €")
    if abono_inicial > precio:
        raise ValueError("El abono inicial no puede superar el precio")
    if forma_pago not in FORMAS_PAGO:
        raise ValueError(f"Forma de pago no válida: {forma_pago}")
    with db() as con:
        cur = con.execute(
            "INSERT INTO apartados (fecha, cliente, telefono, email, producto, talla, precio, fecha_limite)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (fecha.isoformat(), cliente.strip(), telefono, email, producto.strip(), talla, precio,
             (fecha + timedelta(days=PLAZO_DIAS)).isoformat()))
        apartado_id = cur.lastrowid
        con.execute("INSERT INTO abonos (apartado_id, fecha, importe, forma_pago) VALUES (?, ?, ?, ?)",
                    (apartado_id, fecha.isoformat(), abono_inicial, forma_pago))
        if abono_inicial == precio:
            con.execute("UPDATE apartados SET estado = 'liquidado' WHERE id = ?", (apartado_id,))
    return get_apartado(apartado_id)


def registrar_abono(apartado_id, importe, forma_pago, fecha=None):
    fecha = fecha or date.today()
    apartado = get_apartado(apartado_id)
    if apartado["estado"] != "activo":
        raise ValueError(f"El apartado está {apartado['estado']} y no admite abonos")
    if fecha.isoformat() > apartado["fecha_limite"]:
        raise ValueError("El plazo del apartado ha vencido")
    if importe <= 0:
        raise ValueError("El importe debe ser mayor que 0")
    if importe > apartado["pendiente"]:
        raise ValueError(f"El importe supera lo pendiente ({apartado['pendiente']} €)")
    if forma_pago not in FORMAS_PAGO:
        raise ValueError(f"Forma de pago no válida: {forma_pago}")
    with db() as con:
        con.execute("INSERT INTO abonos (apartado_id, fecha, importe, forma_pago) VALUES (?, ?, ?, ?)",
                    (apartado_id, fecha.isoformat(), importe, forma_pago))
        if round(apartado["pendiente"] - importe, 2) == 0:
            con.execute("UPDATE apartados SET estado = 'liquidado' WHERE id = ?", (apartado_id,))
    return get_apartado(apartado_id)


def vencer_apartado(apartado_id):
    apartado = get_apartado(apartado_id)
    if apartado["estado"] != "activo":
        raise ValueError(f"El apartado ya está {apartado['estado']}")
    if date.today().isoformat() <= apartado["fecha_limite"]:
        raise ValueError(f"El apartado no vence hasta el {apartado['fecha_limite']}")
    with db() as con:
        con.execute("UPDATE apartados SET estado = 'vencido' WHERE id = ?", (apartado_id,))
        con.execute("INSERT INTO vales (codigo, apartado_id, fecha, importe) VALUES (?, ?, ?, ?)",
                    (f"VALE-{apartado_id:05d}", apartado_id, date.today().isoformat(), apartado["abonado"]))
    return {"apartado": get_apartado(apartado_id), "vale": rows("SELECT * FROM vales WHERE apartado_id = ?", apartado_id)[0]}


def registrar_venta(concepto, importe, forma_pago, fecha=None):
    fecha = fecha or date.today()
    if importe <= 0:
        raise ValueError("El importe debe ser mayor que 0")
    if forma_pago not in FORMAS_PAGO:
        raise ValueError(f"Forma de pago no válida: {forma_pago}")
    with db() as con:
        cur = con.execute("INSERT INTO ventas (fecha, concepto, importe, forma_pago) VALUES (?, ?, ?, ?)",
                          (fecha.isoformat(), concepto.strip(), importe, forma_pago))
    return rows("SELECT * FROM ventas WHERE id = ?", cur.lastrowid)[0]


if os.getenv("SEED", "1") != "0" and not rows("SELECT 1 FROM apartados LIMIT 1"):
    from seed import seed
    seed(crear_apartado, registrar_abono, registrar_venta, vencer_apartado)


# --- API para n8n --------------------------------------------------------------

def check_key(x_api_key: str = Header("")):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(401, "Falta la cabecera X-API-Key o no es válida")


api = Depends(check_key)


def run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(422, str(e))


class ApartadoIn(BaseModel):
    cliente: str
    telefono: str | None = None
    email: str | None = None
    producto: str
    talla: str | None = None
    precio: float = Field(gt=0)
    abono_inicial: float
    forma_pago: str = "efectivo"
    fecha: date | None = Field(None, description="Solo para migrar datos antiguos. Por defecto, hoy.")


class AbonoIn(BaseModel):
    importe: float
    forma_pago: str = "efectivo"
    fecha: date | None = None


class VentaIn(BaseModel):
    concepto: str
    importe: float
    forma_pago: str = "efectivo"
    fecha: date | None = None


def date_filter(col, desde, hasta):
    return f" WHERE {col} BETWEEN ? AND ?", (str(desde or "0000-01-01"), str(hasta or "9999-12-31"))


@app.get("/api/apartados", dependencies=[api], tags=["apartados"])
def api_apartados(estado: str | None = None):
    if estado:
        return rows(APARTADOS_SQL + " WHERE a.estado = ? GROUP BY a.id ORDER BY a.fecha_limite", estado)
    return rows(APARTADOS_SQL + " GROUP BY a.id ORDER BY a.fecha_limite")


@app.get("/api/apartados/{apartado_id}", dependencies=[api], tags=["apartados"])
def api_apartado(apartado_id: int):
    return get_apartado(apartado_id) | {"abonos": rows("SELECT * FROM abonos WHERE apartado_id = ? ORDER BY fecha", apartado_id)}


@app.post("/api/apartados", dependencies=[api], tags=["apartados"], status_code=201)
def api_crear_apartado(body: ApartadoIn, tasks: BackgroundTasks):
    apartado = run(crear_apartado, **body.model_dump())
    tasks.add_task(notify, "apartado.creado", apartado)
    return apartado


@app.post("/api/apartados/{apartado_id}/abonos", dependencies=[api], tags=["apartados"], status_code=201)
def api_abono(apartado_id: int, body: AbonoIn, tasks: BackgroundTasks):
    apartado = run(registrar_abono, apartado_id, **body.model_dump())
    tasks.add_task(notify, "abono.registrado", apartado | {"importe": body.importe})
    return apartado


@app.post("/api/apartados/{apartado_id}/vencer", dependencies=[api], tags=["apartados"],
          summary="Marca un apartado fuera de plazo como vencido y genera el vale")
def api_vencer(apartado_id: int, tasks: BackgroundTasks):
    result = run(vencer_apartado, apartado_id)
    tasks.add_task(notify, "apartado.vencido", result)
    return result


@app.get("/api/abonos", dependencies=[api], tags=["consultas"], summary="Abonos entre dos fechas (incluidas)")
def api_abonos(desde: date | None = None, hasta: date | None = None):
    where, args = date_filter("fecha", desde, hasta)
    return rows("SELECT * FROM abonos" + where + " ORDER BY fecha", *args)


@app.get("/api/ventas", dependencies=[api], tags=["consultas"], summary="Ventas entre dos fechas (incluidas)")
def api_ventas(desde: date | None = None, hasta: date | None = None):
    where, args = date_filter("fecha", desde, hasta)
    return rows("SELECT * FROM ventas" + where + " ORDER BY fecha", *args)


@app.post("/api/ventas", dependencies=[api], tags=["consultas"], status_code=201)
def api_crear_venta(body: VentaIn, tasks: BackgroundTasks):
    venta = run(registrar_venta, **body.model_dump())
    tasks.add_task(notify, "venta.registrada", venta)
    return venta


@app.get("/api/vales", dependencies=[api], tags=["consultas"])
def api_vales():
    return rows("SELECT * FROM vales ORDER BY fecha")


# --- Pantallas de la tienda ---------------------------------------------------
# ponytail: sin login, pensada para usarse en el ordenador de la tienda. Añadir auth si se publica.

POR_PAGINA = 25
ESTADOS = ["activo", "liquidado", "vencido"]


def page(request, name, status_code=200, **ctx):
    ctx = {"formas_pago": FORMAS_PAGO, "error": "", "ok": request.query_params.get("ok", "")} | ctx
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def con_dias(apartado):
    """Añade cuántos días quedan hasta la fecha límite (negativo si ya pasó)."""
    return apartado | {"dias": (date.fromisoformat(apartado["fecha_limite"]) - date.today()).days}


def paginar(total, pagina):
    paginas = max(1, -(-total // POR_PAGINA))
    pagina = min(max(1, pagina), paginas)
    return pagina, paginas, (pagina - 1) * POR_PAGINA


@app.get("/", include_in_schema=False)
def ui_apartados(request: Request, estado: str = "activo", q: str = "", pagina: int = 1):
    where, args = [], []
    if estado in ESTADOS:
        where.append("a.estado = ?")
        args.append(estado)
    if q.strip():
        where.append("(a.cliente LIKE ? OR a.producto LIKE ? OR a.telefono LIKE ? OR CAST(a.id AS TEXT) = ?)")
        args += [f"%{q.strip()}%"] * 3 + [q.strip().lstrip("#")]
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = rows("SELECT COUNT(*) AS n FROM apartados a" + filtro, *args)[0]["n"]
    pagina, paginas, offset = paginar(total, pagina)
    apartados = rows(APARTADOS_SQL + filtro + f" GROUP BY a.id ORDER BY a.fecha_limite LIMIT {POR_PAGINA} OFFSET {offset}", *args)
    conteo = {r["estado"]: r["n"] for r in rows("SELECT estado, COUNT(*) AS n FROM apartados GROUP BY estado")}
    return page(request, "apartados.html", apartados=[con_dias(a) for a in apartados], estado=estado, q=q,
                conteo=conteo | {"": sum(conteo.values())}, total=total, pagina=pagina, paginas=paginas)


@app.get("/apartados/nuevo", include_in_schema=False)
def ui_nuevo_apartado(request: Request):
    return page(request, "nuevo_apartado.html", form={})


@app.post("/apartados", include_in_schema=False)
async def ui_crear_apartado(request: Request, tasks: BackgroundTasks):
    form = dict(await request.form())
    try:
        apartado = crear_apartado(form.get("cliente", ""), form.get("telefono", ""), form.get("email", ""),
                                  form.get("producto", ""), form.get("talla", ""), float(form.get("precio") or 0),
                                  float(form.get("abono_inicial") or 0), form.get("forma_pago", ""))
    except ValueError as e:
        # Se vuelve a mostrar el formulario con lo que se había escrito, para no perderlo.
        return page(request, "nuevo_apartado.html", 422, form=form, error=str(e))
    tasks.add_task(notify, "apartado.creado", apartado)
    return RedirectResponse(f"/apartados/{apartado['id']}?ok=Apartado+creado", 303)


@app.get("/apartados/{apartado_id}", include_in_schema=False)
def ui_apartado(request: Request, apartado_id: int, error: str = ""):
    return page(request, "apartado.html", a=con_dias(get_apartado(apartado_id)), error=error,
                abonos=rows("SELECT * FROM abonos WHERE apartado_id = ? ORDER BY fecha DESC, id DESC", apartado_id),
                vale=(rows("SELECT * FROM vales WHERE apartado_id = ?", apartado_id) or [None])[0])


@app.post("/apartados/{apartado_id}/abonos", include_in_schema=False)
def ui_abono(apartado_id: int, tasks: BackgroundTasks, importe: float = Form(), forma_pago: str = Form()):
    try:
        apartado = registrar_abono(apartado_id, importe, forma_pago)
    except ValueError as e:
        return RedirectResponse(f"/apartados/{apartado_id}?error={urllib.parse.quote(str(e))}", 303)
    tasks.add_task(notify, "abono.registrado", apartado | {"importe": importe})
    ok = "Apartado liquidado: ya puede recoger sus zapatos" if apartado["estado"] == "liquidado" else "Abono registrado"
    return RedirectResponse(f"/apartados/{apartado_id}?ok={urllib.parse.quote(ok)}", 303)


@app.get("/ventas", include_in_schema=False)
def ui_ventas(request: Request, error: str = "", pagina: int = 1):
    total = rows("SELECT COUNT(*) AS n FROM ventas")[0]["n"]
    pagina, paginas, offset = paginar(total, pagina)
    ventas = rows(f"SELECT * FROM ventas ORDER BY fecha DESC, id DESC LIMIT {POR_PAGINA} OFFSET {offset}")
    return page(request, "ventas.html", ventas=ventas, error=error, total=total, pagina=pagina, paginas=paginas)


@app.post("/ventas", include_in_schema=False)
def ui_crear_venta(tasks: BackgroundTasks, concepto: str = Form(), importe: float = Form(), forma_pago: str = Form()):
    try:
        venta = registrar_venta(concepto, importe, forma_pago)
    except ValueError as e:
        return RedirectResponse(f"/ventas?error={urllib.parse.quote(str(e))}", 303)
    tasks.add_task(notify, "venta.registrada", venta)
    return RedirectResponse("/ventas?ok=Venta+registrada", 303)


@app.get("/excel", include_in_schema=False)
def excel():
    """Descarga todos los datos en un Excel, una hoja por tabla."""
    wb = Workbook()
    wb.remove(wb.active)
    sheets = {
        "Apartados": rows(APARTADOS_SQL + " GROUP BY a.id ORDER BY a.id"),
        "Abonos": rows("SELECT * FROM abonos ORDER BY fecha, id"),
        "Ventas": rows("SELECT * FROM ventas ORDER BY fecha, id"),
        "Vales": rows("SELECT * FROM vales ORDER BY fecha, id"),
    }
    columns = {"Apartados": ["id", "fecha", "cliente", "telefono", "email", "producto", "talla", "precio",
                             "abonado", "pendiente", "fecha_limite", "estado"]}
    for name, data in sheets.items():
        ws = wb.create_sheet(name)
        cols = columns.get(name) or (list(data[0]) if data else [])
        ws.append(cols)
        for r in data:
            ws.append([r[c] for c in cols])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="paso-firme-{date.today()}.xlsx"'})
