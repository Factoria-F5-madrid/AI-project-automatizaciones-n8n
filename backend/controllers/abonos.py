"""CONTROLADOR · Abonos: consulta de abonos entre dos fechas."""

from datetime import date

from fastapi import APIRouter, Depends

from controllers.seguridad import exigir_clave
from models import abono
from schemas.abono import AbonoOut

router = APIRouter(prefix="/api/abonos", tags=["consultas"], dependencies=[Depends(exigir_clave)])


@router.get("", response_model=list[AbonoOut], summary="Abonos entre dos fechas (incluidas)")
def listar(desde: date | None = None, hasta: date | None = None):
    return abono.listar(desde, hasta)
