"""Utilidad de mantenimiento de cuentas de prueba.

Muestra el estado y opcionalmente desbloquea cuentas o restaura las contrasenas demo
del README. Existe porque una suite puede dejar cuentas bloqueadas o con la
contrasena cambiada, y antes eso lo reparaba `init_db` en silencio al reiniciar.

Uso:
    py scripts/unlock_users.py
    py scripts/unlock_users.py --unlock ti admin
    py scripts/unlock_users.py --reset-demo-passwords
"""
import sys
import warnings

warnings.filterwarnings("ignore")

from main import app  # noqa: F401  registra los mappers de SQLAlchemy
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import get_password_hash

# Las mismas del README. No se guardan en ningun log: solo se vuelven a hashear.
DEMO_PASSWORDS = {
    "admin": "admin123",
    "economista": "economista123",
    "felipe_economista": "economista123",
    "ti": "ti123",
    "juan_ti": "ti123",
}


def main() -> int:
    db = SessionLocal()
    try:
        if "--reset-demo-passwords" in sys.argv:
            for username, password in DEMO_PASSWORDS.items():
                db.execute(
                    text("UPDATE users SET hashed_password = :h, must_change_password = FALSE "
                         "WHERE username = :u"),
                    {"h": get_password_hash(password), "u": username},
                )
            db.commit()
            print(f"contrasenas demo restauradas: {', '.join(sorted(DEMO_PASSWORDS))}")
        else:
            rows = db.execute(text(
                "SELECT username, is_active, failed_login_attempts, locked_until "
                "FROM users ORDER BY username"
            )).fetchall()

            print("estado de cuentas:")
            for r in rows:
                lock = "LIBRE" if not r.locked_until else f"BLOQUEADO hasta {r.locked_until}"
                print(f"  {r.username:20} activo={str(r.is_active):5} "
                      f"intentos={r.failed_login_attempts}  {lock}")

        if "--unlock" in sys.argv:
            idx = sys.argv.index("--unlock")
            targets = sys.argv[idx + 1:] if idx + 1 < len(sys.argv) else []
            for name in targets:
                db.execute(
                    text("UPDATE users SET locked_until = NULL, failed_login_attempts = 0 "
                         "WHERE username = :u"),
                    {"u": name},
                )
            db.commit()
            print(f"desbloqueadas: {', '.join(targets)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
