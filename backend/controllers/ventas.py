"""CONTROLADOR · Ventas: consultar y registrar ventas directas."""

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Response

from controllers.seguridad import exigir_clave
from models import venta
from schemas.venta import VentaIn, VentaOut
from services import n8n

router = APIRouter(prefix="/api/ventas", tags=["consultas"], dependencies=[Depends(exigir_clave)])


@router.get("", response_model=list[VentaOut], summary="Ventas entre dos fechas (incluidas)")
def listar(response: Response, desde: date | None = None, hasta: date | None = None, orden: str = "asc",
           pagina: int | None = None, por_pagina: int = 25):
    """Sin `pagina` devuelve todas. `orden=desc` muestra primero las más recientes."""
    limite = por_pagina if pagina else None
    ventas, total = venta.listar(desde, hasta, orden == "desc", limite, (max(pagina or 1, 1) - 1) * por_pagina)
    response.headers["X-Total-Count"] = str(total)
    return ventas


@router.post("", response_model=VentaOut, status_code=201, summary="Registrar una venta")
def registrar(datos: VentaIn, tareas: BackgroundTasks):
    nueva = venta.registrar(**datos.model_dump())
    tareas.add_task(n8n.avisar, "venta.registrada", nueva)
    return nueva
