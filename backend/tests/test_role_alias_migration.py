"""Migracion de los roles alias a la matriz corporativa.

`roles` arrastro 4 filas alias ("Administrador", "Economista", "TI", "Usuario")
que duplicaban un rol corporativo con otro nombre. Esta migracion las reasigna y
borra.

Lo que se verifica aca, que es donde la migracion puede hacer dano real:
  - un usuario en un alias conserva su acceso (mismo rol, mismos permisos) y
    NO queda con `role_id = NULL`
  - borrar la fila del alias no se lleva por delante su matriz de permisos
  - la reasignacion no duplica filas: los alias ya sembraban la MISMA matriz que
    su corporativo, asi que un UPDATE a ciegas dejaria dos filas por par
    (rol, conexion, tabla) y el panel de gobernanza contaria permisos de mas
  - cuando alias y corporativo discrepan sobre una columna gana el mas restrictivo
  - es idempotente: la segunda pasada no rompe ni reimprime nada
  - si el corporativo destino no existe, el alias NO se borra

La ultima es la que mas importa para una instalacion existente: perder una
matriz de permisos en silencio es peor que quedar con un rol de mas.
"""
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.constants import (
    ROLE_ADMINISTRADOR, ROLE_ANALISTA_FINANCIERO,
    ROLE_INGENIERO_TI, ROLE_USUARIO,
)
from app.db.init_db import _ALIAS_ROLES, _migrate_role_aliases
from app.modules.admin_catalog.models import (
    CorporateConnection, DatabaseType, RoleDomainLink,
    RoleTablePermission, RoleColumnPermission, ColumnPermissionType,
)
from app.modules.auth.models import Role, User, Domain

CORPORATE = {
    "Administrador": ROLE_ADMINISTRADOR,
    "Economista": ROLE_ANALISTA_FINANCIERO,
    "TI": ROLE_INGENIERO_TI,
    "Usuario": ROLE_USUARIO,
}


class TestRoleAliasMigration(unittest.TestCase):
    """Cada test arma su propia DB con un alias y sus permisos a mano: correr
    contra la metadata sembrada probaria el seed, no la migracion."""

    def setUp(self):
        import app.modules.auth.models  # noqa: F401
        import app.modules.admin_catalog.models  # noqa: F401
        import app.modules.telemetry_audit.models  # noqa: F401
        import app.modules.chat_engine.models  # noqa: F401

        self.path = "./test_role_alias_migration.db"
        if os.path.exists(self.path):
            os.remove(self.path)
        self.eng = create_engine(
            f"sqlite:///{self.path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.eng)
        self.db = sessionmaker(autocommit=False, autoflush=False, bind=self.eng)()

    def tearDown(self):
        self.db.close()
        self.eng.dispose()
        if os.path.exists(self.path):
            os.remove(self.path)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _rol(self, name, description="x"):
        r = Role(name=name, description=description)
        self.db.add(r)
        self.db.commit()
        return r

    def _conexion(self):
        c = CorporateConnection(
            name=f"conn_{os.urandom(4).hex()}",
            db_type=DatabaseType.SQLITE,
            host="/tmp/x.db",
            port=0,
            database_name="x.db",
            username="u",
            encrypted_password="",
            is_active=True,
            is_uploaded=False,
        )
        self.db.add(c)
        self.db.commit()
        return c

    def _usuario(self, username, role_id):
        u = User(
            username=username,
            hashed_password="x",
            is_admin=False,
            is_active=True,
            role_id=role_id,
        )
        self.db.add(u)
        self.db.commit()
        return u

    def _tabla_perm(self, role_id, conn_id, table, is_allowed=True):
        p = RoleTablePermission(
            role_id=role_id, connection_id=conn_id, schema_name="public",
            table_name=table, is_allowed=is_allowed, granted_by_admin=True,
        )
        self.db.add(p)
        self.db.commit()
        return p

    def _col_perm(self, role_id, conn_id, table, column, ptype):
        p = RoleColumnPermission(
            role_id=role_id, connection_id=conn_id, schema_name="public",
            table_name=table, column_name=column, permission_type=ptype,
        )
        self.db.add(p)
        self.db.commit()
        return p

    def _tablas_de(self, role_id):
        return {
            p.table_name for p in self.db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == role_id,
                RoleTablePermission.is_allowed == True,  # noqa: E712
            ).all()
        }

    # ------------------------------------------------------------------
    # 1. El usuario conserva el acceso
    # ------------------------------------------------------------------

    def test_usuario_del_alias_queda_en_el_corporativo(self):
        alias = self._rol("Economista")
        target = self._rol(ROLE_ANALISTA_FINANCIERO)
        conn = self._conexion()
        self._tabla_perm(alias.id, conn.id, "fact_ventas")
        user = self._usuario("economista", alias.id)

        _migrate_role_aliases(self.db)

        self.assertIsNone(
            self.db.query(Role).filter(Role.name == "Economista").first(),
            "La fila del alias debe quedar borrada.",
        )
        self.db.refresh(user)
        self.assertEqual(
            user.role_id, target.id,
            "El usuario debe quedar en el rol corporativo, no en NULL: "
            "`User.role_id` es ON DELETE SET NULL, asi que borrar el alias sin "
            "reasignar antes deja una cuenta valida sin ningun rol.",
        )
        self.assertEqual(
            self._tablas_de(target.id), {"fact_ventas"},
            "La matriz de permisos tiene que sobrevivir al borrado del alias.",
        )

    def test_is_admin_no_se_toca(self):
        """La migracion mueve roles, no privilegios: un admin con alias sigue admin."""
        alias = self._rol("Administrador")
        self._rol(ROLE_ADMINISTRADOR)
        u = User(
            username="admin", hashed_password="x",
            is_admin=True, is_active=True, role_id=alias.id,
        )
        self.db.add(u)
        self.db.commit()

        _migrate_role_aliases(self.db)

        self.db.refresh(u)
        self.assertTrue(u.is_admin)
        self.assertIsNotNone(u.role_id)

    # ------------------------------------------------------------------
    # 2. Sin duplicar filas
    # ------------------------------------------------------------------

    def test_no_duplica_permisos_ya_presentes_en_el_corporativo(self):
        """El caso real: los alias sembraban la MISMA matriz que su corporativo.
        Un UPDATE a ciegas dejaria dos filas por (rol, conexion, tabla)."""
        alias = self._rol("TI")
        target = self._rol(ROLE_INGENIERO_TI)
        conn = self._conexion()
        for t in ("dim_servidores", "fact_incidentes_ti"):
            self._tabla_perm(alias.id, conn.id, t)
            self._tabla_perm(target.id, conn.id, t)

        _migrate_role_aliases(self.db)

        rows = self.db.query(RoleTablePermission).filter(
            RoleTablePermission.table_name.in_(["dim_servidores", "fact_incidentes_ti"])
        ).all()
        self.assertEqual(
            len(rows), 2,
            "Un permiso por tabla, no dos: el panel de gobernanza cuenta filas y "
            "un duplicado infla la visibilidadMatrix.",
        )
        self.assertEqual(self._tablas_de(target.id), {"dim_servidores", "fact_incidentes_ti"})

    def test_no_duplica_permisos_de_columna(self):
        alias = self._rol("Economista")
        target = self._rol(ROLE_ANALISTA_FINANCIERO)
        conn = self._conexion()
        for t in (alias, target):
            self._col_perm(t.id, conn.id, "dim_clientes", "tarjeta_credito_token",
                           ColumnPermissionType.BLOCKED)

        _migrate_role_aliases(self.db)

        rows = self.db.query(RoleColumnPermission).filter(
            RoleColumnPermission.column_name == "tarjeta_credito_token"
        ).all()
        self.assertEqual(len(rows), 1)

    def test_no_duplica_links_de_dominio(self):
        alias = self._rol("Economista")
        target = self._rol(ROLE_ANALISTA_FINANCIERO)
        dom = Domain(name="Finanzas", description="x")
        self.db.add(dom)
        self.db.commit()
        for r in (alias, target):
            self.db.add(RoleDomainLink(role_id=r.id, domain_id=dom.id))
        self.db.commit()

        _migrate_role_aliases(self.db)

        links = self.db.query(RoleDomainLink).filter(
            RoleDomainLink.domain_id == dom.id
        ).all()
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].role_id, target.id)

    # ------------------------------------------------------------------
    # 3. Discrepancia de columnas: gana el mas restrictivo
    # ------------------------------------------------------------------

    def test_columna_discrepante_gana_el_mas_restrictivo(self):
        """Fail-closed: si el alias bloqueaba y el corporativo permitia, el
        corporativo tiene que quedar bloqueado. Migrar es reasignar acceso, no
        abrirlo."""
        alias = self._rol("Economista")
        target = self._rol(ROLE_ANALISTA_FINANCIERO)
        conn = self._conexion()
        self._col_perm(target.id, conn.id, "dim_clientes", "iban", ColumnPermissionType.ALLOWED)
        self._col_perm(alias.id, conn.id, "dim_clientes", "iban", ColumnPermissionType.BLOCKED)

        _migrate_role_aliases(self.db)

        rows = self.db.query(RoleColumnPermission).filter(
            RoleColumnPermission.role_id == target.id,
            RoleColumnPermission.column_name == "iban",
        ).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].permission_type, ColumnPermissionType.BLOCKED)

    def test_columna_mas_permisisiva_del_alias_no_abre_el_corporativo(self):
        """Simetrico del anterior, y por eso la migracion NUNCA amplia: si el
        alias permitia y el corporativo bloqueaba, gana el bloqueo. Un residuo del
        seed viejo no es una autorizacion, y una migracion que concede acceso por
        su cuenta es un agujero con forma de codigo de arranque."""
        alias = self._rol("Economista")
        target = self._rol(ROLE_ANALISTA_FINANCIERO)
        conn = self._conexion()
        self._col_perm(target.id, conn.id, "dim_clientes", "sector", ColumnPermissionType.BLOCKED)
        self._col_perm(alias.id, conn.id, "dim_clientes", "sector", ColumnPermissionType.ALLOWED)

        _migrate_role_aliases(self.db)

        row = self.db.query(RoleColumnPermission).filter(
            RoleColumnPermission.role_id == target.id,
            RoleColumnPermission.column_name == "sector",
        ).first()
        self.assertEqual(row.permission_type, ColumnPermissionType.BLOCKED)

    def test_tabla_denegada_en_el_corporativo_no_se_reabre_sola(self):
        """`is_allowed=False` es una revocacion explicita de un admin. Si el alias
        la tenia permitida, la migracion no puede devolverle el acceso."""
        alias = self._rol("Economista")
        target = self._rol(ROLE_ANALISTA_FINANCIERO)
        conn = self._conexion()
        self._tabla_perm(target.id, conn.id, "dim_servidores", is_allowed=False)
        self._tabla_perm(alias.id, conn.id, "dim_servidores", is_allowed=True)

        _migrate_role_aliases(self.db)

        dup = self.db.query(RoleTablePermission).filter(
            RoleTablePermission.role_id == target.id,
            RoleTablePermission.table_name == "dim_servidores",
        ).first()
        self.assertFalse(
            dup.is_allowed,
            "Una revocacion explicita no se deshace por una fila alias que si la "
            "permitia. Si el acceso tiene que volver, es una decision del admin.",
        )

    # ------------------------------------------------------------------
    # 4. Idempotencia
    # ------------------------------------------------------------------

    def test_segunda_pasada_no_hace_nada(self):
        alias = self._rol("Economista")
        target = self._rol(ROLE_ANALISTA_FINANCIERO)
        conn = self._conexion()
        self._tabla_perm(alias.id, conn.id, "fact_ventas")
        user = self._usuario("eco", alias.id)

        _migrate_role_aliases(self.db)
        role_id_1 = user.role_id
        self._tablas_1 = self._tablas_de(target.id)

        _migrate_role_aliases(self.db)  # no debe reventar nada

        self.db.refresh(user)
        self.assertEqual(user.role_id, role_id_1)
        self.assertEqual(self._tablas_de(target.id), self._tablas_1)
        self.assertEqual(self._tablas_de(target.id), {"fact_ventas"})

    def test_corrida_completa_migra_los_cuatro_alias(self):
        conn = self._conexion()
        for alias_name, target_name in CORPORATE.items():
            alias = self._rol(alias_name)
            target = self._rol(target_name)
            self._tabla_perm(alias.id, conn.id, f"tabla_de_{alias_name}")
            self._usuario(f"u_{alias_name}", alias.id)

        _migrate_role_aliases(self.db)

        for alias_name, target_name in CORPORATE.items():
            self.assertIsNone(
                self.db.query(Role).filter(Role.name == alias_name).first(),
                f"El alias {alias_name} deberia estar borrado.",
            )
            target = self.db.query(Role).filter(Role.name == target_name).first()
            self.assertIn(f"tabla_de_{alias_name}", self._tablas_de(target.id))
            u = self.db.query(User).filter(User.username == f"u_{alias_name}").first()
            self.assertEqual(u.role_id, target.id)

    def test_alias_sin_corporativo_no_se_borra(self):
        """La instalacion a medio migrar: existe el alias pero todavia no el
        corporativo. Borrarlo dejaria al usuario en NULL sin avisar."""
        alias = self._rol("Economista")
        conn = self._conexion()
        self._tabla_perm(alias.id, conn.id, "fact_ventas")
        user = self._usuario("eco", alias.id)

        _migrate_role_aliases(self.db)  # ROLE_ANALISTA_FINANCIERO no existe

        self.db.refresh(user)
        self.assertEqual(
            user.role_id, alias.id,
            "Sin destino no hay adonde moverlo: el usuario conserva su rol.",
        )
        self.assertIsNotNone(
            self.db.query(Role).filter(Role.name == "Economista").first(),
            "El alias debe sobrevivir cuando su corporativo no esta.",
        )
        self.assertEqual(self._tablas_de(alias.id), {"fact_ventas"})

    # ------------------------------------------------------------------
    # 5. El mapa de alias cubre lo que dice cubrir
    # ------------------------------------------------------------------

    def test_el_mapa_apunta_a_roles_que_existen_en_constants(self):
        from app.core import constants

        for alias_name, target_name in _ALIAS_ROLES.items():
            self.assertEqual(
                CORPORATE[alias_name], target_name,
                f"El mapa de la migracion y el de este test tienen que coincidir "
                f"sobre {alias_name}: si divergen, uno de los dos miente.",
            )
            self.assertIn(
                target_name, {
                    constants.ROLE_ADMINISTRADOR,
                    constants.ROLE_DIRECTOR_EJECUTIVO,
                    constants.ROLE_ANALISTA_FINANCIERO,
                    constants.ROLE_GERENTE_TALENTO,
                    constants.ROLE_ANALISTA_BI,
                    constants.ROLE_INGENIERO_TI,
                    constants.ROLE_OFICIAL_SEGURIDAD,
                    constants.ROLE_USUARIO,
                },
                f"{target_name} no es un rol corporativo de la matriz de 8.",
            )


if __name__ == "__main__":
    unittest.main()