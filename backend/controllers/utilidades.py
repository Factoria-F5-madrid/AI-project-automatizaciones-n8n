"""CONTROLADOR · Utilidades: descargar los datos en Excel."""

import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

import database
from controllers.seguridad import exigir_clave
from models import apartado

router = APIRouter(prefix="/api", tags=["utilidades"], dependencies=[Depends(exigir_clave)])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/excel", summary="Descargar todos los datos en un Excel (una hoja por tabla)")
def excel():
    hojas = {
        "Apartados": (["id", "fecha", "cliente", "telefono", "email", "producto", "talla", "precio", "abonado",
                       "pendiente", "fecha_limite", "estado"], apartado.listar()[0]),
        "Abonos": (["id", "apartado_id", "fecha", "importe", "forma_pago"],
                   database.consultar("SELECT * FROM abonos ORDER BY fecha, id")),
        "Ventas": (["id", "fecha", "concepto", "importe", "forma_pago"],
                   database.consultar("SELECT * FROM ventas ORDER BY fecha, id")),
        "Vales": (["id", "codigo", "apartado_id", "fecha", "importe", "usado"],
                  database.consultar("SELECT * FROM vales ORDER BY fecha, id")),
    }
    libro = Workbook()
    libro.remove(libro.active)
    for nombre, (columnas, filas) in hojas.items():
        hoja = libro.create_sheet(nombre)
        hoja.append(columnas)
        for fila in filas:
            hoja.append([fila[c] for c in columnas])
    memoria = io.BytesIO()
    libro.save(memoria)
    memoria.seek(0)
    return StreamingResponse(memoria, media_type=XLSX,
                             headers={"Content-Disposition": f'attachment; filename="paso-firme-{date.today()}.xlsx"'})
