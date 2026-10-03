"""Verifica que el test del diccionario no pase por vacuidad.

Si la conexion activa no tuviera esas columnas, el test pasaria sin comprobar nada.
Este script compara la respuesta con y sin los parametros de RBAC: si no difiere,
el test no esta probando el filtro.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: F401,E402
from app.core.database import SessionLocal  # noqa: E402
from app.modules.catalog.services.catalog_service import CatalogDomainService  # noqa: E402

BLOCKED = ("tarjeta_credito_token", "sueldo_mensual", "salario")
MASKED = ("rut_dni_cliente",)


def samples_for(blocked, masked):
    db = SessionLocal()
    try:
        resp = CatalogDomainService.get_data_dictionary(
            db, connection_id=None, blocked_columns=blocked, masked_columns=masked
        )
    finally:
        db.close()
    out = {}
    for table in resp.tables:
        for col in table.columns:
            out[col.name.lower()] = list(col.sample_values or [])
    return out


con_rbac = samples_for(set(BLOCKED), set(MASKED))
sin_rbac = samples_for(None, None)

print("estado de la conexion activa (con RBAC aplicado):")
for name in BLOCKED + MASKED:
    print(f"  {name:24} {con_rbac.get(name, 'AUSENTE')}")
print()
print("mismo endpoint SIN los parametros de RBAC (comportamiento previo):")
for name in BLOCKED + MASKED:
    print(f"  {name:24} {sin_rbac.get(name, 'AUSENTE')}")
print()

present = [n for n in BLOCKED + MASKED if sin_rbac.get(n)]
if not present:
    print("ATENCION: la conexion activa no tiene esas columnas; el test pasaria en vacio.")
    sys.exit(1)

fugas = [n for n in BLOCKED if con_rbac.get(n)]
no_enmascarado = [n for n in MASKED
                  if any(not str(v).startswith("*") for v in con_rbac.get(n, []))]
print(f"columnas con datos en la BD: {present}")
print(f"fugas BLOCKED con RBAC aplicado: {fugas or 'ninguna'}")
print(f"MASKED sin enmascarar:          {no_enmascarado or 'ninguna'}")
sys.exit(0 if not fugas and not no_enmascarado else 1)
