"""CONTROLADOR · Apartados: recibe las peticiones HTTP, llama a los modelos y devuelve la respuesta."""

from fastapi import APIRouter, BackgroundTasks, Depends, Response

from controllers.seguridad import exigir_clave
from models import abono, apartado, vale
from schemas.abono import AbonoIn
from schemas.apartado import ApartadoDetalle, ApartadoIn, ApartadoOut, Resumen, Vencimiento
from services import n8n

router = APIRouter(prefix="/api/apartados", tags=["apartados"], dependencies=[Depends(exigir_clave)])


@router.get("", response_model=list[ApartadoOut], summary="Lista de apartados")
def listar(response: Response, estado: str | None = None, q: str = "", pagina: int | None = None, por_pagina: int = 25):
    """Filtra por `estado` (activo, liquidado o vencido) y busca con `q`. Sin `pagina` devuelve todos.
    El total de resultados va en la cabecera `X-Total-Count`."""
    limite = por_pagina if pagina else None
    apartados, total = apartado.listar(estado, q, limite, (max(pagina or 1, 1) - 1) * por_pagina)
    response.headers["X-Total-Count"] = str(total)
    return apartados


@router.get("/resumen", response_model=Resumen, summary="Cuántos apartados hay por estado")
def resumen():
    return apartado.contar_por_estado()


@router.get("/{apartado_id}", response_model=ApartadoDetalle, summary="Un apartado con sus abonos y su vale")
def ver(apartado_id: int):
    return apartado.obtener(apartado_id) | {"abonos": abono.de_apartado(apartado_id), "vale": vale.del_apartado(apartado_id)}


@router.post("", response_model=ApartadoOut, status_code=201, summary="Crear un apartado (con su abono inicial)")
def crear(datos: ApartadoIn, tareas: BackgroundTasks):
    nuevo = apartado.crear(**datos.model_dump())
    tareas.add_task(n8n.avisar, "apartado.creado", nuevo)
    return nuevo


@router.post("/{apartado_id}/abonos", response_model=ApartadoOut, status_code=201, summary="Registrar un abono")
def abonar(apartado_id: int, datos: AbonoIn, tareas: BackgroundTasks):
    actualizado = abono.registrar(apartado_id, **datos.model_dump())
    tareas.add_task(n8n.avisar, "abono.registrado", actualizado | {"importe": datos.importe})
    return actualizado


@router.post("/{apartado_id}/vencer", response_model=Vencimiento,
             summary="Marca un apartado fuera de plazo como vencido y genera el vale")
def vencer(apartado_id: int, tareas: BackgroundTasks):
    resultado = apartado.vencer(apartado_id)
    tareas.add_task(n8n.avisar, "apartado.vencido", resultado)
    return resultado
