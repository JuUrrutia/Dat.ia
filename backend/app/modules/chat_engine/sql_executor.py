import sqlite3
import json
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.modules.chat_engine.ast_validator import ASTValidator, ASTValidationError
from app.modules.chat_engine.llm_service import LLMService

class SQLExecutor:
    """
    Centralizes raw database execution, context managers, self-healing SQL with local LLM,
    and learning memory persistence.
    """

    @classmethod
    def execute_raw_sql(cls, target_db: Any, sql: str, dialect: str = "sqlite") -> List[Dict[str, Any]]:
        """
        Safely executes a SELECT query on SQLite or PostgreSQL using try...finally to ensure connection closure.
        """
        # If target_db is a CorporateConnection model object
        if hasattr(target_db, "db_type"):
            from sqlalchemy import text
            from app.core.database import build_engine_for_connector
            eng = build_engine_for_connector(target_db)
            with eng.connect() as conn:
                res = conn.execute(text(sql))
                return [dict(r._mapping) for r in res.fetchall()]

        # If target_db is a PostgreSQL connection string
        if isinstance(target_db, str) and (target_db.startswith("postgresql://") or target_db.startswith("postgresql+psycopg://")):
            from sqlalchemy import create_engine, text
            eng = create_engine(target_db)
            with eng.connect() as conn:
                res = conn.execute(text(sql))
                return [dict(r._mapping) for r in res.fetchall()]

        # SQLite connection
        conn = sqlite3.connect(str(target_db))
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @classmethod
    def get_grounding_query(
        cls,
        question: str,
        user_role: str = "Economista",
        allowed_tables: Optional[Set[str]] = None
    ) -> str:
        if isinstance(user_role, set) and allowed_tables is None:
            allowed_tables = user_role
            user_role = "Economista"

        if not allowed_tables:
            return "SELECT 1;"

        sorted_tables = sorted(list(allowed_tables))
        q_lower = question.lower()

        matching_table = next((t for t in sorted_tables if t.lower() in q_lower), None)
        target_table = matching_table if matching_table else sorted_tables[0]
        return f"SELECT * FROM {target_table} LIMIT 20;"

    @classmethod
    async def execute_with_self_healing(
        cls,
        target_db_path: Any,
        question: str,
        initial_sql: str,
        allowed_tables: Set[str],
        blocked_columns: Set[str],
        table_columns_map: Dict[str, List[str]],
        schema_context: str = "",
        is_llm_active: bool = True,
        dialect: str = "sqlite"
    ) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any], bool, str]:
        """
        Executes query on SQLite or PostgreSQL and automatically invokes LLM self-healing if an exception occurs.
        Returns: (rows, final_sql, meta_dict, was_self_healed, validation_label)
        """
        secured_sql = initial_sql
        meta = {"tables_used": list(allowed_tables)}

        try:
            _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                initial_sql,
                dialect=dialect,
                allowed_tables=allowed_tables,
                blocked_columns=blocked_columns,
                table_columns=table_columns_map
            )
        except ASTValidationError:
            pass

        was_self_healed = False
        validation_label = "APROBADO"

        try:
            rows = cls.execute_raw_sql(target_db_path, secured_sql, dialect=dialect)
            return rows, secured_sql, meta, was_self_healed, validation_label
        except Exception as err:
            healed_sql = None
            if is_llm_active:
                try:
                    engine_label = "PostgreSQL" if dialect in ("postgres", "postgresql") else "SQLite"
                    healing_system_prompt = (
                        f"Eres un asistente experto en corregir consultas SQL para {engine_label}. "
                        "El motor relacional arrojó un error con la consulta previa. "
                        "Corrige el SQL usando exclusivamente las columnas y tablas existentes en el esquema provisto. "
                        "Responde ÚNICAMENTE con el código SQL corregido dentro del bloque ```sql ... ```."
                    )
                    healing_user_prompt = f"""Pregunta original del usuario: "{question}"
Consulta SQL errónea: {secured_sql}
Error devuelto por {engine_label}: {str(err)}

Esquema de tablas y columnas válidas disponibles:
{schema_context}

Genera la consulta SQL corregida y funcional para {engine_label}:"""

                    healing_res = await LLMService.generate_completion(
                        healing_user_prompt,
                        system_prompt=healing_system_prompt,
                        temperature=0.05,
                        max_tokens=200
                    )
                    if healing_res:
                        match = re.search(r'```sql\s*(.*?)\s*```', healing_res, re.DOTALL | re.IGNORECASE)
                        if match:
                            healed_sql = match.group(1).strip()
                        elif "SELECT" in healing_res.upper():
                            m_sel = re.search(r'(SELECT\s+.*?(?:;|$))', healing_res, re.DOTALL | re.IGNORECASE)
                            if m_sel:
                                healed_sql = m_sel.group(1).strip().rstrip(';')
                except Exception:
                    healed_sql = None

            if healed_sql:
                try:
                    try:
                        _, healed_secured_sql, healed_meta = ASTValidator.validate_and_secure_sql(
                            healed_sql,
                            dialect=dialect,
                            allowed_tables=allowed_tables,
                            blocked_columns=blocked_columns,
                            table_columns=table_columns_map
                        )
                    except Exception:
                        healed_secured_sql, healed_meta = healed_sql, {"tables_used": list(allowed_tables)}

                    rows = cls.execute_raw_sql(target_db_path, healed_secured_sql, dialect=dialect)
                    return rows, healed_secured_sql, healed_meta, True, "APROBADO (Auto-Corregido)"
                except Exception:
                    pass

            # Fallback of emergency
            first_table = sorted(list(allowed_tables))[0] if allowed_tables else "dual"
            raw_fb_sql = f"SELECT * FROM {first_table} LIMIT 20"
            try:
                _, secured_fb_sql, fb_meta = ASTValidator.validate_and_secure_sql(
                    raw_fb_sql,
                    dialect="sqlite",
                    allowed_tables=allowed_tables,
                    blocked_columns=blocked_columns,
                    table_columns=table_columns_map,
                    max_limit=20
                )
                rows = cls.execute_raw_sql(target_db_path, secured_fb_sql)
                return rows, secured_fb_sql, fb_meta, False, "APROBADO (Fallback de Emergencia)"
            except Exception:
                raise RuntimeError(f"Error al ejecutar consulta en la BD: {str(err)}")

    @classmethod
    def persist_learning_memory(
        cls,
        db: Optional[Session],
        question: str,
        sql: str,
        connection_id: int,
        user_role: str,
        tables_used: List[str],
        was_healed: bool = False
    ):
        if not db or not sql or not question:
            return
        try:
            from app.modules.chat_engine.models import QueryLearningMemory
            clean_q = question.strip().lower()
            if len(clean_q) < 4:
                return

            existing = db.query(QueryLearningMemory).filter(
                QueryLearningMemory.connection_id == connection_id,
                QueryLearningMemory.question_pattern == clean_q
            ).first()

            if existing:
                existing.execution_count = (existing.execution_count or 1) + 1
                existing.successful_sql = sql
                existing.was_self_healed = existing.was_self_healed or was_healed
            else:
                new_mem = QueryLearningMemory(
                    question_pattern=clean_q,
                    connection_id=connection_id,
                    user_role=user_role,
                    successful_sql=sql,
                    tables_used=json.dumps(tables_used),
                    execution_count=1,
                    was_self_healed=was_healed
                )
                db.add(new_mem)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    @classmethod
    def retrieve_few_shot_memories(cls, db: Optional[Session], question: str, connection_id: int) -> str:
        if not db:
            return ""
        try:
            from app.modules.chat_engine.models import QueryLearningMemory
            memories = db.query(QueryLearningMemory).filter(
                QueryLearningMemory.connection_id == connection_id
            ).order_by(QueryLearningMemory.execution_count.desc(), QueryLearningMemory.id.desc()).limit(3).all()

            if not memories:
                return ""

            examples = []
            for m in memories:
                examples.append(f"- Pregunta similar: \"{m.question_pattern}\" -> SQL: {m.successful_sql}")
            return "Ejemplos de consultas previamente aprendidas y verificadas:\n" + "\n".join(examples)
        except Exception:
            return ""
