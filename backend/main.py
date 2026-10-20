"""Zapatería Paso Firme: apartados, abonos y ventas.

Estructura (MVC):
  models/       MODELO      los datos y las reglas del negocio (abono mínimo, plazo de 90 días...)
  schemas/                  la forma de los datos que entran y salen por la API (Pydantic)
  controllers/  CONTROLADOR las rutas HTTP: reciben la petición, llaman a los modelos y responden
  ../frontend/  VISTA       la interfaz (HTML, CSS y JavaScript), que usa la API como cualquier otro cliente

Este archivo solo junta las piezas. Las automatizaciones (avisos, recordatorios, cierres, informes) son
trabajo de n8n, que usa la API (documentada en /docs) y recibe eventos por webhook.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import config
import database
import seed
from controllers import abonos, apartados, paginas, utilidades, vales, ventas
from models.errores import NoEncontrado, ReglaDeNegocio

app = FastAPI(title="Zapatería Paso Firme", description="API para integrar n8n con la tienda.")


@app.exception_handler(ReglaDeNegocio)
def regla_rota(_: Request, error: ReglaDeNegocio):
    return JSONResponse({"detail": str(error)}, status_code=422)


@app.exception_handler(NoEncontrado)
def no_encontrado(_: Request, error: NoEncontrado):
    return JSONResponse({"detail": str(error)}, status_code=404)


for modulo in (apartados, abonos, ventas, vales, utilidades, paginas):
    app.include_router(modulo.router)
app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="frontend")

database.crear_tablas()
if config.SEED and database.esta_vacia():
    seed.cargar()
