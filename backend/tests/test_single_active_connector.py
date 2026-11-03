"""Una sola conexion activa.

`is_active` se leia como un singleton pero las escrituras no mantenian la
exclusion: `upload_database_file` clavaba `is_active=True` sin apagar las
demas. Con dos conectores marcadas, el motor (que elige por `ORDER BY id DESC`)
respondia contra la que tiene menos permisos y todos los no-admin se quedaban
sin datos.

Se verifica por el servicio real, no por SQL: es la logica que se rompio.
"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.admin_catalog.models import CorporateConnection
from app.modules.auth.models import Role
import app.modules.admin_catalog.models  # noqa: F401
import app.modules.auth.models  # noqa: F401
import app.modules.telemetry_audit.models  # noqa: F401
import app.modules.chat_engine.models  # noqa: F401


class TestSingleActiveConnector(unittest.TestCase):

    def setUp(self):
        self.eng = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=self.eng)
        self.db = sessionmaker(bind=self.eng)()

    def tearDown(self):
        self.db.close()
        self.eng.dispose()

    def _conn(self, name, active=True):
        c = CorporateConnection(name=name, db_type="SQLITE", host=name,
                                port=0, database_name=name, username="admin",
                                encrypted_password="", is_active=active,
                                is_uploaded=True)
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c

    def _actives(self):
        self.db.expire_all()
        return [
            c.id for c in self.db.query(CorporateConnection)
            .filter(CorporateConnection.is_active == True)
            .order_by(CorporateConnection.id.desc()).all()
        ]

    # --------------------------------------------------------------
    def test_activate_exclusively_turns_off_the_others(self):
        from app.modules.catalog.services.connector_service import ConnectorDomainService

        a = self._conn("A")
        ConnectorDomainService._activate_exclusively(self.db, a.id)
        self.db.commit()

        b = self._conn("B")
        ConnectorDomainService._activate_exclusively(self.db, b.id)
        self.db.commit()

        self.assertEqual(self._actives(), [b.id])

    def test_toggle_active_does_not_leave_two_active(self):
        """El toggle de la UI es la via normal para cambiar de fuente."""
        from app.modules.catalog.services.connector_service import ConnectorDomainService

        a = self._conn("A")
        self.db.expire_all()
        self.assertEqual(self._actives(), [a.id])

        ConnectorDomainService.toggle_connector_active(self.db, a.id)
        self.assertEqual(self._actives(), [])

        b = self._conn("B")
        self.assertEqual(self._actives(), [b.id])

        # Encender A tiene que apagar B, no acumular.
        ConnectorDomainService.toggle_connector_active(self.db, a.id)
        self.assertEqual(self._actives(), [a.id])

    def test_migration_normalizes_existing_multi_active_state(self):
        """La migracion de arranque quita el estado que el bug dejo."""
        import app.db.init_db as init_db_mod

        a = self._conn("A")
        b = self._conn("B")
        c = self._conn("C")
        self.assertEqual(len(self._actives()), 3)

        init_db_mod.init_db(self.db)

        # Queda exactamente una. `init_db` tambien siembra su conexion de
        # plataforma como activa, asi que la que gana no es necesariamente una de
        # las tres del test: lo que se fija es la exclusion, no el id.
        actives = self._actives()
        self.assertEqual(len(actives), 1, f"activas: {actives}")

    def test_migration_is_idempotent(self):
        import app.db.init_db as init_db_mod

        a = self._conn("A")
        b = self._conn("B")
        init_db_mod.init_db(self.db)
        after_first = self._actives()
        self.assertEqual(len(after_first), 1)
        init_db_mod.init_db(self.db)
        init_db_mod.init_db(self.db)
        self.assertEqual(self._actives(), after_first)

    def test_migration_grants_no_permissions(self):
        """Normalizar cual es la fuente NO puede abrir acceso a nadie."""
        import app.db.init_db as init_db_mod

        from app.modules.admin_catalog.models import RoleTablePermission

        a = self._conn("A")
        b = self._conn("B")
        role = Role(name="Economista", description="x")
        self.db.add(role)
        self.db.commit()

        init_db_mod.init_db(self.db)

        granted = self.db.query(RoleTablePermission).filter(
            RoleTablePermission.connection_id.in_([a.id, b.id])
        ).all()
        self.assertEqual(granted, [], "La migracion no concede permisos: default-deny.")


if __name__ == "__main__":
    unittest.main()