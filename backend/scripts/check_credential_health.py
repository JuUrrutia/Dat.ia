"""Diagnostico: cuantas credenciales de conector quedaron ilegibles.

Rotar SECRET_KEY y setear una FERNET_KEY nueva invalida todo lo que estaba cifrado
con la clave derivada del SECRET_KEY anterior. Este script informa el alcance SIN
imprimir ningun secreto.
"""
import warnings

warnings.filterwarnings("ignore")

from main import app  # noqa: F401
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import decrypt_credential


def main() -> int:
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "SELECT id, name, db_type, username, encrypted_password "
            "FROM corporate_connections ORDER BY id"
        )).fetchall()

        ok = broken = empty = 0
        for r in rows:
            if not r.encrypted_password:
                empty += 1
                state = "sin password (SQLite/demo)"
            else:
                try:
                    value = decrypt_credential(r.encrypted_password)
                    if value:
                        ok += 1
                        state = "descifra OK"
                    else:
                        broken += 1
                        state = "ILEGIBLE (devuelve vacio)"
                except Exception as exc:
                    broken += 1
                    state = f"ILEGIBLE ({type(exc).__name__})"

            print(f"  id={r.id:<3} {r.name[:30]:32} {str(r.db_type)[:12]:14} {state}")

        print()
        print(f"total={len(rows)}  ok={ok}  ilegibles={broken}  sin password={empty}")
        if broken:
            print("\nACCION NECESARIA: re-cifrar esas credenciales con la FERNET_KEY actual.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
