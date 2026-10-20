"""CONTROLADOR · Vales de compra generados al vencer un apartado."""

from fastapi import APIRouter, Depends

from controllers.seguridad import exigir_clave
from models import vale
from schemas.vale import ValeOut

router = APIRouter(prefix="/api/vales", tags=["consultas"], dependencies=[Depends(exigir_clave)])


@router.get("", response_model=list[ValeOut], summary="Vales de compra generados")
def listar():
    return vale.listar()
