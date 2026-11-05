import unittest
import os
import sqlite3
import json
import itertools

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from app.core.database import Base, get_db
from app.db.init_db import init_db
from app.modules.auth.models import Role, Domain, User
from app.modules.admin_catalog.models import RoleTablePermission, CorporateConnection
from app.modules.chat_engine.models import QueryLearningMemory
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.modules.chat_engine.engine import QueryEngine
from app.core.constants import (
    ROLE_ADMINISTRADOR,
    ROLE_DIRECTOR_EJECUTIVO,
    ROLE_ANALISTA_FINANCIERO,
    ROLE_GERENTE_TALENTO,
    ROLE_ANALISTA_BI,
    ROLE_INGENIERO_TI,
    ROLE_OFICIAL_SEGURIDAD,
    ROLE_USUARIO
)

TEST_DB_URL = "sqlite:///./test_self_healing_and_roles.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestSelfHealingAndCorporateRoles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)
        db = TestingSessionLocal()
        init_db(db)
        db.close()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)
        if os.path.exists("./test_self_healing_and_roles.db"):
            try:
                os.remove("./test_self_healing_and_roles.db")
            except Exception:
                pass

    def setUp(self):
        self.client = TestClient(app)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_corporate_roles_and_domains_seeded(self):
        """Verifies that all 8 corporate roles and enterprise domains are properly seeded in database."""
        roles = {r.name for r in self.db.query(Role).all()}
        expected_roles = {
            ROLE_ADMINISTRADOR,
            ROLE_DIRECTOR_EJECUTIVO,
            ROLE_ANALISTA_FINANCIERO,
            ROLE_GERENTE_TALENTO,
            ROLE_ANALISTA_BI,
            ROLE_INGENIERO_TI,
            ROLE_OFICIAL_SEGURIDAD,
            ROLE_USUARIO
        }
        for exp_r in expected_roles:
            self.assertIn(exp_r, roles, f"Role {exp_r} must be seeded in database.")

        domains = {d.name for d in self.db.query(Domain).all()}
        self.assertIn("Economía & Finanzas", domains)
        self.assertIn("Tecnología & TI", domains)
        self.assertIn("Talento & Personas", domains)
        self.assertIn("Seguridad & Gobernanza", domains)

    def test_corporate_role_table_permissions_assigned(self):
        """Verifies that functional table permissions are assigned across corporate roles."""
        fin_role = self.db.query(Role).filter(Role.name == ROLE_ANALISTA_FINANCIERO).first()
        self.assertIsNotNone(fin_role)
        fin_perms = {p.table_name for p in self.db.query(RoleTablePermission).filter(RoleTablePermission.role_id == fin_role.id).all()}
        self.assertIn("fact_ventas", fin_perms)
        self.assertIn("dim_categorias", fin_perms)

        ti_role = self.db.query(Role).filter(Role.name == ROLE_INGENIERO_TI).first()
        self.assertIsNotNone(ti_role)
        ti_perms = {p.table_name for p in self.db.query(RoleTablePermission).filter(RoleTablePermission.role_id == ti_role.id).all()}
        self.assertIn("dim_servidores", ti_perms)
        self.assertIn("fact_consumo_recursos", ti_perms)

    def test_matriz_de_los_ocho_roles(self):
        """La matriz por area, rol por rol.

        Que 5 de los 8 roles tengan la matriz correcta no alcanza: el producto
        promete que dos personas con roles distintos reciben respuestas distintas,
        y eso solo se comprueba por comparación. Si un rol gana tablas de otro, la
        promesa de aislamiento por area es falsa aunque los tests por rol sigan
        verdes.

        Los roles por area se fijan con su lista EXACTA. La razon para no usar
        `assertIn`: un permiso de mas no rompe ninguna asercion positiva, y es
        exactamente el bug que este test existe para cazar.
        """
        negocio = {"dim_categorias", "dim_productos", "dim_clientes",
                   "fact_ventas", "fact_ingresos_costos"}
        tech = {"dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos"}
        personal = {"dim_empleados"}
        surveys = {"Answer", "Question", "Survey", "answer", "question", "survey"}

        esperado = {
            ROLE_ADMINISTRADOR: negocio | tech | personal | surveys,
            # Rentabilidad consolidada y cartera, NO el detalle transaccional.
            # Rentabilidad consolidada y catálogo. NO la cartera ni el detalle.
            ROLE_DIRECTOR_EJECUTIVO: (
                {"fact_ingresos_costos", "dim_categorias", "dim_productos"}
                | personal | surveys
            ),
            ROLE_ANALISTA_FINANCIERO: negocio | personal | surveys,
            ROLE_GERENTE_TALENTO: personal | surveys,
            # Sin el bloque transaccional. Comparte matriz con el Ingeniero de TI a
            # proposito: se separan en la capa 2, no en la capa 1.
            ROLE_ANALISTA_BI: tech | personal | surveys,
            ROLE_INGENIERO_TI: tech | personal | surveys,
            ROLE_OFICIAL_SEGURIDAD: tech | personal | surveys | {"dim_categorias", "dim_productos"},
            ROLE_USUARIO: surveys | {"dim_categorias", "dim_productos"},
        }

        for nombre, tablas in esperado.items():
            rol = self.db.query(Role).filter(Role.name == nombre).first()
            self.assertIsNotNone(rol, f"no se sembro el rol {nombre}")
            granted = {
                p.table_name for p in self.db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == rol.id,
                    RoleTablePermission.is_allowed == True,  # noqa: E712
                ).all()
            }
            self.assertEqual(
                granted, tablas,
                f"La matriz de '{nombre}' no es la declarada. Un permiso de mas "
                f"rompe el aislamiento por area aunque todos los tests por rol "
                f"pasen.",
            )

    def test_ningun_rol_trae_las_tablas_de_otro_area(self):
        """El cruce de areas, que es la promesa central del producto.

        La matriz por rol de arriba verifica que cada uno tenga SU lista. Esto
        verifica la otra mitad, que es la que el usuario perceive: si el rol de
        finanzas puede ver `dim_servidores` y el de infraestructura puede ver
        `fact_ventas`, entonces las dos listas estan bien pero el aislamiento no
        existe, y un assert por rol no lo detectaria.

        El Analista de Datos cruza areas a proposito, asi que no se cuenta como
        fuga: tiene catalogo, personal y tecnica, y NO tiene el bloque de negocio.
        """
        negocio = {"dim_clientes", "fact_ventas", "fact_ingresos_costos"}
        tech = {"dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos"}

        # (rol, tablas del area ajena que NO debe tener)
        cruces = [
            (ROLE_ANALISTA_FINANCIERO, tech),
            (ROLE_INGENIERO_TI, negocio),
            (ROLE_GERENTE_TALENTO, negocio),
            (ROLE_GERENTE_TALENTO, tech),
            (ROLE_ANALISTA_BI, negocio),
            (ROLE_OFICIAL_SEGURIDAD, negocio),
            (ROLE_DIRECTOR_EJECUTIVO, tech),
            (ROLE_DIRECTOR_EJECUTIVO, {"fact_ventas", "dim_clientes"}),
            (ROLE_USUARIO, negocio),
            (ROLE_USUARIO, tech),
            (ROLE_USUARIO, {"dim_empleados"}),
        ]
        for nombre, ajenas in cruces:
            rol = self.db.query(Role).filter(Role.name == nombre).first()
            granted = {
                p.table_name for p in self.db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == rol.id,
                    RoleTablePermission.is_allowed == True,  # noqa: E712
                ).all()
            }
            self.assertEqual(
                granted & ajenas, set(),
                f"'{nombre}' tiene tablas de otra area ({sorted(granted & ajenas)}). "
                f"El aislamiento entre roles no se sostiene con la lista correcta "
                f"de cada uno: hace falta que no se toquen.",
            )

    def test_cada_rol_ve_algo_que_ningun_otro_ve(self):
        """Contrapunto: que el aislamiento no sea solo "nadie ve finanzas".

        Si dos roles tuvieran la misma matriz, la pregunta "que ve este perfil" no
        tendria respuesta distinguible y la demo no demostraria nada.

        EXCEPCION DOCUMENTADA: `ROLE_ANALISTA_BI` y `ROLE_INGENIERO_TI` comparten
        tabla a proposito. Ambos trabajan sobre metricas tecnicas; lo que los
        separa es la CAPA 2, no la capa 1:

          - el nombre "Ingeniero de Infraestructura & TI" matchea la rama tecnica
            del guard de dominio, asi que TI recibe un denegado temprano si pregunta
            por ventas o margenes, aunque la capa 1 lo frena igual
          - "Analista de Datos & BI" no matchea ninguna rama: es un perfil
            transversal, y su proposito es cruzar areas

        La separacion existe, pero vive en otra capa. Este test la excluye del
        alcance de la matriz a proposito, y `test_bi_y_ti_se_diferencian_en_el_guard`
        verifica que la diferencia siga existiendo.
        """
        matrices = {}
        for nombre in (ROLE_ADMINISTRADOR, ROLE_DIRECTOR_EJECUTIVO,
                       ROLE_ANALISTA_FINANCIERO, ROLE_GERENTE_TALENTO,
                       ROLE_ANALISTA_BI, ROLE_INGENIERO_TI,
                       ROLE_OFICIAL_SEGURIDAD, ROLE_USUARIO):
            rol = self.db.query(Role).filter(Role.name == nombre).first()
            matrices[nombre] = frozenset(
                p.table_name for p in self.db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == rol.id,
                    RoleTablePermission.is_allowed == True,  # noqa: E712
                ).all()
            )

        compartible = frozenset({ROLE_ANALISTA_BI, ROLE_INGENIERO_TI})
        for a, b in itertools.combinations(matrices, 2):
            if {a, b} == compartible:
                continue
            self.assertNotEqual(
                matrices[a], matrices[b],
                f"'{a}' y '{b}' ven exactamente las mismas tablas. Dos perfiles "
                f"indistinguibles hacen que la matriz no demuestre nada.",
            )

    def test_bi_y_ti_se_diferencian_en_el_guard_de_dominio(self):
        """La compensacion del test anterior: si comparten matriz, tienen que
        separarse en la capa 2, y seguir separandose.

        Este es el unico punto donde el aislamiento depende del NOMBRE del rol
        (`governance_guard` clasifica por substring), asi que un cambio de nombre
        en `constants.py` puede borrarlo en silencio. Sin este test, el Analista de
        Datos y el Ingeniero de TI serian el mismo rol con dos etiquetas.
        """
        from app.modules.chat_engine.governance_guard import GovernanceGuard

        tablas = {"dim_servidores"}
        pregunta_finanzas = "cuales son las ventas totales"

        ti = GovernanceGuard.check_domain_governance(
            pregunta_finanzas, ROLE_INGENIERO_TI, tablas)
        bi = GovernanceGuard.check_domain_governance(
            pregunta_finanzas, ROLE_ANALISTA_BI, tablas)

        self.assertIsNotNone(
            ti,
            "El Ingeniero de TI debe recibir un denegado de dominio sobre finanzas. "
            "Es la unica capa que lo distingue del Analista de Datos.",
        )
        self.assertIsNone(
            bi,
            "El Analista de Datos es un perfil transversal: el guard de dominio no "
            "le restringe por area. Si esto cambia, cambio el diseno a proposito.",
        )

    def test_un_usuario_demo_por_rol_y_ninguno_sin_matriz(self):
        """Cada rol corporativo tiene una cuenta, y ninguna entra al producto para
        descubrir que no tiene tablas asignadas: un login que funciona pero no
        muestra datos hace que el producto parezca roto."""
        esperados = {
            "admin": ROLE_ADMINISTRADOR,
            "director": ROLE_DIRECTOR_EJECUTIVO,
            "economista": ROLE_ANALISTA_FINANCIERO,
            "talento": ROLE_GERENTE_TALENTO,
            "bi": ROLE_ANALISTA_BI,
            "ti": ROLE_INGENIERO_TI,
            "seguridad": ROLE_OFICIAL_SEGURIDAD,
            "consultor": ROLE_USUARIO,
        }
        for username, rol_nombre in esperados.items():
            u = self.db.query(User).filter(User.username == username).first()
            self.assertIsNotNone(u, f"falta el usuario demo {username}")
            self.assertIsNotNone(u.role_id, f"{username} quedo sin rol asignado")
            self.assertEqual(
                u.role.name, rol_nombre,
                f"{username} deberia tener el rol {rol_nombre}.",
            )
            granted = self.db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == u.role_id,
                RoleTablePermission.is_allowed == True,  # noqa: E712
            ).count()
            self.assertGreater(
                granted, 0,
                f"{username} ({rol_nombre}) no tiene tablas: entra al producto y "
                f"recibe 'el rol no tiene tablas asignadas'.",
            )

    def test_no_quedan_alias_en_el_catalogo(self):
        """La migracion de alias corre en el arranque; si un alias sobrevive,
        aparece en el desplegable de 'Editar Rol' del panel de admin y el usuario
        puede asignarse un rol que no tiene matriz."""
        from app.db.init_db import _ALIAS_ROLES

        for alias in _ALIAS_ROLES:
            self.assertIsNone(
                self.db.query(Role).filter(Role.name == alias).first(),
                f"El alias '{alias}' no deberia existir en el catalogo.",
            )

    def test_data_profiling_and_sample_extraction(self):
        """Verifies that DynamicSchemaPruningService samples real column values for data profiling."""
        cols = DynamicSchemaPruningService.get_physical_table_columns("fact_ventas", include_samples=True)
        if cols:
            has_samples = any(len(c.get("samples", [])) > 0 for c in cols)
            self.assertTrue(has_samples, "Data profiling should extract real sample values from table columns.")

        prompt_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=self.db,
            user_role=ROLE_ANALISTA_FINANCIERO,
            connection_id=1,
            is_admin=False
        )
        self.assertIn("schema_prompt", prompt_info)
        self.assertTrue(len(prompt_info["allowed_tables"]) > 0)

    def test_query_learning_memory_persistence(self):
        """Verifies that QueryLearningMemory accumulates successful query patterns for autonomous learning."""
        test_q = "ventas totales por mes en 2024"
        test_sql = "SELECT strftime('%Y-%m', fecha_venta) as mes, SUM(monto_total) as total FROM fact_ventas GROUP BY 1;"
        
        QueryEngine._persist_learning_memory(
            db=self.db,
            question=test_q,
            sql=test_sql,
            connection_id=1,
            user_role=ROLE_ANALISTA_FINANCIERO,
            tables_used=["fact_ventas"],
            was_healed=False
        )

        memory = self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.question_pattern == test_q
        ).first()

        self.assertIsNotNone(memory)
        self.assertEqual(memory.successful_sql, test_sql)
        self.assertEqual(memory.execution_count, 1)
        self.assertFalse(memory.was_self_healed)

        # Update / increment count
        QueryEngine._persist_learning_memory(
            db=self.db,
            question=test_q,
            sql=test_sql,
            connection_id=1,
            user_role=ROLE_ANALISTA_FINANCIERO,
            tables_used=["fact_ventas"],
            was_healed=True
        )

        self.db.refresh(memory)
        self.assertEqual(memory.execution_count, 2)
        self.assertTrue(memory.was_self_healed)

        # Check Few-Shot retrieval
        few_shots = QueryEngine._retrieve_few_shot_memories(self.db, test_q, connection_id=1)
        self.assertIn(test_q, few_shots)
        self.assertIn(test_sql, few_shots)

if __name__ == "__main__":
    unittest.main()
