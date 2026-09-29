import unittest
import sqlite3
import tempfile
import os
from unittest.mock import MagicMock

from app.modules.catalog.services.null_manager import NullManagerService
from app.modules.chat_engine.kpi_calculator import KPICalculator
from app.modules.chat_engine.engine import QueryEngine
from app.modules.admin_catalog.models import DatabaseType


class TestNullPolicyAndVisualizations(unittest.TestCase):

    def setUp(self):
        # Create a temporary SQLite database for auditing and remediation tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE test_sales (
                id INTEGER PRIMARY KEY,
                category TEXT,
                amount REAL,
                region TEXT
            )
        """)
        # Insert 5 rows: 2 rows with NULLs, 3 clean rows
        # Row 1: clean (Electronics, 100.0, North)
        # Row 2: category NULL, amount 200.0, North
        # Row 3: category Electronics, amount NULL, South
        # Row 4: clean (Electronics, 100.0, North)
        # Row 5: clean (Books, 50.0, South)
        cur.executemany(
            "INSERT INTO test_sales VALUES (?, ?, ?, ?)",
            [
                (1, "Electronics", 100.0, "North"),
                (2, None, 200.0, "North"),
                (3, "Electronics", None, "South"),
                (4, "Electronics", 100.0, "North"),
                (5, "Books", 50.0, "South"),
            ]
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        import gc
        gc.collect()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_audit_nulls_sqlite(self):
        """Verifica que el scanner detecte con precisión tablas, columnas y celdas con NULL."""
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path
        mock_conn.null_policy = "open"

        audit = NullManagerService.audit_connection_nulls(mock_conn)

        self.assertTrue(audit["has_nulls"])
        self.assertEqual(len(audit["tables"]), 1)

        table_info = audit["tables"][0]
        self.assertEqual(table_info["table_name"], "test_sales")
        self.assertEqual(table_info["total_rows"], 5)

        # Columns with nulls: category (1), amount (1)
        col_names = [c["column_name"] for c in table_info["columns_with_nulls"]]
        self.assertIn("category", col_names)
        self.assertIn("amount", col_names)

    def test_apply_policy_delete_rows(self):
        """Verifica que la política 'delete_rows' elimine las filas con NULL preservando las demás."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path

        result = NullManagerService.apply_null_policy(mock_conn, "delete_rows", mock_db)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["policy"], "delete_rows")

        # Check in DB that rows 2 and 3 were deleted, remaining 3 rows
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM test_sales")
        count = cur.fetchone()[0]
        conn.close()

        self.assertEqual(count, 3)

    def test_apply_policy_mode(self):
        """Verifica que la política 'mode' impute los NULLs con la moda estadística."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path

        result = NullManagerService.apply_null_policy(mock_conn, "mode", mock_db)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["policy"], "mode")

        # Verify no nulls remain in the table
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM test_sales WHERE category IS NULL OR amount IS NULL")
        null_count = cur.fetchone()[0]
        # And category for row 2 should be the mode ("Electronics")
        cur.execute("SELECT category FROM test_sales WHERE id = 2")
        row2_cat = cur.fetchone()[0]
        conn.close()

        self.assertEqual(null_count, 0)
        self.assertEqual(row2_cat, "Electronics")

    def test_apply_policy_nearest(self):
        """Verifica que la política 'nearest' impute los NULLs con el valor anterior/siguiente."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path

        result = NullManagerService.apply_null_policy(mock_conn, "nearest", mock_db)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["policy"], "nearest")

        # Verify no nulls remain
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM test_sales WHERE category IS NULL OR amount IS NULL")
        null_count = cur.fetchone()[0]
        conn.close()

        self.assertEqual(null_count, 0)

    def test_dynamic_chart_series_generation(self):
        """Verifica que build_dynamic_visualization genere series ECharts pobladas y válidas."""
        columns = ["categoria", "ventas"]
        rows = [
            {"categoria": "Tecnología", "ventas": 50000},
            {"categoria": "Hogar", "ventas": 32000},
            {"categoria": "Moda", "ventas": 18000},
        ]

        kpis, chart_type, chart_option, summary, exec_rep = KPICalculator.build_dynamic_visualization(
            question="Ventas por categoría",
            columns=columns,
            rows=rows,
            user_role="Gerente"
        )

        self.assertIn("series", chart_option)
        self.assertGreater(len(chart_option["series"]), 0)
        first_series = chart_option["series"][0]
        self.assertIn("data", first_series)
        self.assertGreater(len(first_series["data"]), 0)

    def test_in_memory_null_remediation(self):
        """Verifica que el motor remedie nulos en memoria cuando el usuario lo solicita."""
        sample_rows = [
            {"id": 1, "producto": "Laptop", "precio": 1000},
            {"id": 2, "producto": None, "precio": 500},
            {"id": 3, "producto": "Mouse", "precio": None},
        ]
        columns = ["id", "producto", "precio"]

        # 1. delete_rows
        cleaned_del = QueryEngine._apply_in_memory_null_remediation(sample_rows, columns, "delete_rows")
        self.assertEqual(len(cleaned_del), 1)
        self.assertEqual(cleaned_del[0]["producto"], "Laptop")

        # 2. mode
        cleaned_mode = QueryEngine._apply_in_memory_null_remediation(sample_rows, columns, "mode")
        self.assertEqual(len(cleaned_mode), 3)
        self.assertIsNotNone(cleaned_mode[1]["producto"])

    def test_prompt1_early_null_pause(self):
        """Verifica que el Prompt 1 con nulos y política 'open' pause la respuesta sin mostrar gráficos ni KPIs distorsionados."""
        import asyncio
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path
        mock_conn.null_policy = "open"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_conn
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_conn
        mock_db.query.return_value.order_by.return_value.first.return_value = mock_conn

        response = asyncio.run(
            QueryEngine.execute_query(
                question="SELECT * FROM test_sales",
                user_role="Administrador",
                is_admin=True,
                db=mock_db,
                connection_id=1
            )
        )

        # 1. Null detection was triggered
        self.assertIsNotNone(response.nulls_detected)
        self.assertTrue(response.nulls_detected["has_nulls"])
        self.assertEqual(response.nulls_detected["null_rows_count"], 2)

        # 2. Distorted KPIs and charts are suppressed
        self.assertEqual(len(response.kpis), 0)
        self.assertEqual(response.chart_type, "none")
        self.assertEqual(len(response.chart_option.get("series", [])), 0)

        # 3. Conversational response warns about nulls and asks for remediation
        self.assertIn("Valores nulos detectados", response.conversational_response)
        self.assertIn("test_sales", response.conversational_response)

        # 4. Options embed the original question for context preservation
        options = response.nulls_detected["options"]
        self.assertEqual(len(options), 3)
        self.assertIn("SELECT * FROM test_sales", options[0]["prompt"])

    def test_prompt2_remediation_answers_original_question(self):
        """Verifica que el Prompt 2 reciba la acción de remediación, conserve el contexto de la consulta original y devuelva los datos limpios."""
        import asyncio
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path
        mock_conn.null_policy = "open"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_conn
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_conn
        mock_db.query.return_value.order_by.return_value.first.return_value = mock_conn

        # Simulate user clicking "Eliminar registros con nulos"
        remediation_prompt = "Tratar nulos en test_sales (eliminar registros con nulos) para la consulta: SELECT * FROM test_sales"
        response = asyncio.run(
            QueryEngine.execute_query(
                question=remediation_prompt,
                user_role="Administrador",
                is_admin=True,
                db=mock_db,
                connection_id=1,
                conversation_history=[
                    {"question": "SELECT * FROM test_sales", "sql": "SELECT * FROM test_sales"}
                ]
            )
        )

        # 1. Did NOT pause again
        self.assertIsNone(response.nulls_detected)

        # 2. Clean data returned (no nulls)
        self.assertGreater(len(response.data_rows), 0)
        for r in response.data_rows:
            self.assertIsNotNone(r.get("category"))
            self.assertIsNotNone(r.get("amount"))

        # 3. Confirmation banner is present
        self.assertIn("Tratamiento de nulos", response.conversational_response)
        self.assertIn("Eliminación de registros con nulos", response.conversational_response)


if __name__ == "__main__":
    unittest.main()
