import unittest
import os
import sqlite3
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from app.core.database import Base, get_db
from app.db.init_db import init_db
from app.models.role import Role, Domain
from app.models.user import User
from app.models.permission import RoleTablePermission
from app.models.learning import QueryLearningMemory
from app.models.connection import CorporateConnection
from app.services.dynamic_schema import DynamicSchemaPruningService
from app.services.query_engine import QueryEngine
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
