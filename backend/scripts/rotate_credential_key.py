"""Re-cifra credenciales de conector tras un cambio de FERNET_KEY.

Que la aplicacion siga funcionando al rotar la clave NO depende solo de que la
nueva clave sea valida: lo cifrado con la clave anterior queda ilegible para siempre.
Este script descifra con la clave vieja (derivada del SECRET_KEY por defecto que
figura en .env.example, tracked en el repo) y re-cifra con la FERNET_KEY actual.

No imprime ningun secreto: solo conteos y exito/fallo por conexion.

Uso (desde backend/, con PYTHONPATH=.):
    py scripts/rotate_credential_key.py --dry-run
    py scripts/rotate_credential_key.py --apply
"""
import argparse
import base64
import hashlib
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from main import app  # noqa: F401  registra los mappers de SQLAlchemy
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import encrypt_credential


def legacy_key() -> bytes:
    """La clave que usaba la app antes de que FERNET_KEY estuviera definida."""
    example = Path(__file__).resolve().parents[2] / ".env.example"
    old_secret = None
    if example.exists():
        for line in example.read_text(encoding="utf-8").splitlines():
            if line.startswith("SECRET_KEY="):
                old_secret = line.split("=", 1)[1].strip()
                break
    if old_secret is None:
        old_secret = settings.DEFAULT_SECRET_KEY
    return base64.urlsafe_b64encode(hashlib.sha256(old_secret.encode()).digest())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="solo informa (es el comportamiento por defecto)")
    parser.add_argument("--apply", action="store_true", help="escribe los cambios")
    args = parser.parse_args()

    if not settings.FERNET_KEY:
        print("ERROR: settings.FERNET_KEY vacio. No se puede re-cifrar.", file=sys.stderr)
        return 2

    old, new = Fernet(legacy_key()), Fernet(settings.FERNET_KEY.encode())
    db = SessionLocal()
    migrated = skipped = failed = 0
    try:
        rows = db.execute(text(
            "SELECT id, name, encrypted_password FROM corporate_connections "
            "WHERE encrypted_password IS NOT NULL AND encrypted_password <> '' ORDER BY id"
        )).fetchall()

        if not rows:
            print("no hay credenciales cifradas que migrar.")
            return 0

        for r in rows:
            try:
                plain = old.decrypt(r.encrypted_password.encode())
            except InvalidToken:
                # Ya ilegible con la clave vieja: no hay de donde recuperarlo.
                print(f"  id={r.id} {r.name[:34]:36} NO recuperable con la clave anterior")
                failed += 1
                continue

            if not args.apply:
                print(f"  id={r.id} {r.name[:34]:36} se puede migrar ({len(plain)} bytes)")
                skipped += 1
                continue

            db.execute(
                text("UPDATE corporate_connections SET encrypted_password = :p WHERE id = :i"),
                {"p": encrypt_credential(plain.decode()), "i": r.id},
            )
            migrated += 1
            print(f"  id={r.id} {r.name[:34]:36} re-cifrada OK")

        if args.apply:
            db.commit()
            print(f"\nmigradas={migrated}  no recuperables={failed}")
        else:
            print(f"\nmigrables={skipped}  no recuperables={failed}")
            print("dry-run: nada escrito. Usa --apply para ejecutar.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
