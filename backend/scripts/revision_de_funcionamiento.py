"""Revision de funcionamiento: recorre los flujos reales contra la app montada.

No mira codigo. Levanta FastAPI con TestClient, se autentica de verdad contra las
cuentas demo y ejercita los endpoints que se corrigieron hoy, verificando el
comportamiento observable y no solo el codigo de status.
"""
import warnings

warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient

from main import app  # noqa: F401

OK, FAIL = [], []


def check(name, condition, detail=""):
    (OK if condition else FAIL).append(name)
    print(f"  [{'OK ' if condition else 'FALLA'}] {name}{(' -> ' + detail) if detail else ''}")


def main():
    c = TestClient(app)
    print("REVISION DE FUNCIONAMIENTO\n")

    # --- Autenticacion real ---
    print("1. Autenticacion")
    r = c.post("/api/v1/auth/login", json={"username": "economista", "password": "economista123"})
    check("login con credenciales validas", r.status_code == 200, f"{r.status_code}")
    eco = r.json().get("access_token", "")
    check("devuelve token", bool(eco))

    r_bad = c.post("/api/v1/auth/login", json={"username": "economista", "password": "incorrecta"})
    check("login con password incorrecta es 401", r_bad.status_code == 401, f"{r_bad.status_code}")

    r_adm = c.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    adm = r_adm.json().get("access_token", "")
    check("login admin", r_adm.status_code == 200, f"{r_adm.status_code}")

    E = {"Authorization": f"Bearer {eco}"}
    A = {"Authorization": f"Bearer {adm}"}

    # --- Autorizacion (lo corregido hoy) ---
    print("\n2. Autorizacion de endpoints de administracion")
    check("GET /auth/users sin token -> 401",
          c.get("/api/v1/auth/users").status_code == 401)
    check("GET /auth/users como economista -> 403",
          c.get("/api/v1/auth/users", headers=E).status_code == 403)
    check("GET /auth/users como admin -> 200",
          c.get("/api/v1/auth/users", headers=A).status_code == 200)
    check("GET /auth/roles sin token -> 401",
          c.get("/api/v1/auth/roles").status_code == 401)

    # --- Salud (corregido hoy) ---
    print("\n3. Salud del sistema")
    r = c.get("/api/v1/system/health", headers=E)
    check("GET /system/health responde 200", r.status_code == 200, f"{r.status_code}")
    body = r.json()
    check("declara un estado global", bool(body.get("status")), str(body.get("status"))[:30])

    r = c.get("/api/v1/system/anomalies", headers=E)
    check("GET /system/anomalies responde 200", r.status_code == 200, f"{r.status_code}")
    anoms = r.json().get("anomalies", [])
    payload = str(anoms)
    check("anomalias no filtran columnas sensibles",
          not any(k in payload for k in ("tarjeta_credito", "rut_dni", "sueldo", "api_key")))

    # --- Diccionario de datos (corregido hoy) ---
    print("\n4. Diccionario de datos (enmascarado)")
    r = c.get("/api/v1/catalog/data-dictionary", headers=E)
    check("responde 200", r.status_code == 200, f"{r.status_code}")
    samples, descriptions = {}, ""
    for t in r.json().get("tables", []):
        for col in t.get("columns", []):
            n = col["name"].lower()
            if col.get("sample_values"):
                samples[n] = col["sample_values"]
            descriptions += str(col.get("description") or "")
    for name in ("tarjeta_credito_token", "sueldo_mensual", "salario"):
        check(f"BLOCKED {name} sin muestras para economista",
              not samples.get(name), str(samples.get(name, "[]"))[:40])
    if samples.get("rut_dni_cliente"):
        check("RUT enmascarado en muestras",
              all(str(v).startswith("*") for v in samples["rut_dni_cliente"]),
              str(samples["rut_dni_cliente"][:2]))
    else:
        check("RUT sin muestras (nada que enmascarar)", True)
    check("description no contiene valores reales",
          "Muestra:" not in descriptions and "TOK-" not in descriptions)

    # --- Hilos (IDOR corregido hoy) ---
    print("\n5. Aislamiento de hilos")
    tid = "rev-func-thread"
    payload_thread = {
        "id": tid, "title": "Revision funcional", "connection_id": 1,
        "results": [{"data_rows": [{"monto": "999999"}], "summary_text": "privado"}],
    }
    r = c.post("/api/v1/chat/threads", json=payload_thread, headers=E)
    check("crear hilo propio -> 200", r.status_code == 200, f"{r.status_code}")
    r = c.get(f"/api/v1/chat/threads/{tid}", headers=E)
    check("leer hilo propio -> 200", r.status_code == 200, f"{r.status_code}")
    r = c.get(f"/api/v1/chat/threads/shared/{tid}", headers=E)
    check("hilo no compartido no es legible como compartido", r.status_code == 404, f"{r.status_code}")
    adm_threads = c.get("/api/v1/chat/threads", headers=A)
    listed = adm_threads.json()
    listed = listed.get("threads", []) if isinstance(listed, dict) else listed
    check("otro usuario no ve el hilo en su listado",
          tid not in [t["id"] for t in listed])

    # --- Validador AST ---
    print("\n6. Guardrail de SQL")
    from app.modules.chat_engine.ast_validator import ASTValidator, ASTValidationError
    try:
        out = ASTValidator.validate_and_secure_sql("SELECT * FROM dim_clientes", is_admin=False,
                                                   allowed_tables=["dim_clientes"], table_columns=None)
        check("SELECT * sin columnas -> denegado", False, f"paso: {out[1][:50]}")
    except ASTValidationError:
        check("SELECT * sin columnas -> denegado (fail-closed)", True)
    out = ASTValidator.validate_and_secure_sql("SELECT id FROM fact_ventas LIMIT 501",
                                               is_admin=True, allowed_tables=None)
    check("LIMIT 501 acotado a 500 sin crashear", "LIMIT 500" in out[1], out[1])
    out = ASTValidator.validate_and_secure_sql("SELECT id FROM fact_ventas LIMIT 5",
                                               is_admin=True, allowed_tables=None)
    check("LIMIT 5 se preserva (techo, no piso)", "LIMIT 5" in out[1], out[1])
    try:
        ASTValidator.validate_and_secure_sql("DROP TABLE fact_ventas", is_admin=True, allowed_tables=None)
        check("DROP bloqueado", False, "paso")
    except ASTValidationError:
        check("DROP bloqueado", True)

    # --- Enmascarado ---
    print("\n7. Enmascarado de columnas MASKED")
    from app.core.security import mask_value, sanitize_spreadsheet_value
    check("RUT enmascarado con ultimos 4 digitos",
          mask_value("12.345.678-9") == "*******678-9", mask_value("12.345.678-9"))
    check("sin digitos suficientes -> fail-closed",
          mask_value("texto") == "*" * 5, mask_value("texto"))
    check("formula de hoja de calculo neutralizada",
          sanitize_spreadsheet_value("=1+1").startswith("'"))

    # --- .sql rechazado ---
    print("\n8. Importacion de datasets")
    from app.modules.admin_catalog.importers.postgres_importer import import_sql_script_to_postgres
    try:
        import_sql_script_to_postgres("x.sql", None)
        check("script .sql rechazado", False, "se ejecuto")
    except ValueError:
        check("script .sql rechazado", True)

    print(f"\n{'=' * 46}\nOK: {len(OK)}   FALLAS: {len(FAIL)}")
    if FAIL:
        print("Fallaron:")
        for f in FAIL:
            print("  -", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
