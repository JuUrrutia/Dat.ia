"""init_db debe crear las cuentas demo, pero no reescribir las existentes.

Antes de este fix, en cada arranque (main.py:58 llama a init_db) el bloque de
cuentas demo existentes:
  - rehasheaba la contrasena al valor demo, deshaciendo cambios del admin
  - hacia is_active = True, reviviendo cuentas desactivadas
  - ponia failed_login_attempts = 0 y locked_until = None, anulando el lockout

Con eso, reiniciar Docker reiniciaba el contador de intentos de fuerza bruta.
"""

import unittest
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.db.init_db import init_db
from app.modules.auth.models import User

DEMO = "economista"
DEMO_PASSWORD = "economista123"


class TestInitDbDoesNotMutateExistingUsers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        try:
            init_db(db)
        finally:
            db.close()

    def setUp(self):
        self.db = SessionLocal()
        self.user = self.db.query(User).filter(User.username == DEMO).first()
        self.assertIsNotNone(self.user, f"la cuenta demo {DEMO} deberia existir tras init_db")
        self._snapshot = {
            "hashed_password": self.user.hashed_password,
            "is_active": self.user.is_active,
            "failed_login_attempts": self.user.failed_login_attempts,
            "locked_until": self.user.locked_until,
        }

    def tearDown(self):
        user = self.db.query(User).filter(User.username == DEMO).first()
        for field, value in self._snapshot.items():
            setattr(user, field, value)
        self.db.commit()
        self.db.close()

    def test_init_db_preserves_password_and_lock_state(self):
        self.user.hashed_password = get_password_hash("una-clave-que-el-admin-eligio")
        self.user.is_active = False
        self.user.failed_login_attempts = 4
        self.user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        self.db.commit()
        self.db.expire_all()

        init_db(self.db)
        self.db.expire_all()

        user = self.db.query(User).filter(User.username == DEMO).first()

        self.assertNotEqual(
            user.hashed_password, get_password_hash(DEMO_PASSWORD),
            "init_db reescribio la contrasena a la de demo: el cambio del admin no persiste",
        )
        self.assertFalse(
            user.is_active,
            "init_db reactivo una cuenta desactivada",
        )
        self.assertEqual(
            user.failed_login_attempts, 4,
            "init_db limpio el contador de intentos fallidos",
        )
        self.assertIsNotNone(
            user.locked_until,
            "init_db levanto el bloqueo de la cuenta",
        )

    def test_init_db_still_backfills_missing_role(self):
        self.user.role_id = None
        self.db.commit()
        self.db.expire_all()

        init_db(self.db)
        self.db.expire_all()

        user = self.db.query(User).filter(User.username == DEMO).first()
        self.assertIsNotNone(
            user.role_id,
            "init_db dejo de asignar el rol cuando falta: esa parte debe seguir funcionando",
        )


if __name__ == "__main__":
    unittest.main()
